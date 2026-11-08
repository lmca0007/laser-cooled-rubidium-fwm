"""Compare the raw side-camera frames of a MOT shot and an empty shot with the same settings.

Two pairs, each with the same exposure and camera settings:
    evening, 0.6 ms: 0056 (MOT, 1 s load) against 0057 (no MOT after the beam reroute, 6 s load)
    morning, 1.0 ms: 0003 (MOT, 9 s load) against 0002 (no MOT, 9 s load, 8 min earlier)
The empty shots 0002, 0006 and 0057-0060 all give |N_f| < 1e6 counts.

Writes figures/mot_vs_empty.png and prints the frame levels.

    python reports/2026-10-25_mot_characterisation/mot_vs_empty.py
"""
import h5py
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LogNorm, TwoSlopeNorm  # noqa: E402

import lab_constants as lc  # noqa: E402
from mot_properties import INK, INK2, SERIES, style  # noqa: E402

PAIRS = [("0056", "0057", "0.6 ms exposure"), ("0003", "0002", "1.0 ms exposure")]
EMPTY_RUNS = ("0002", "0006", "0057", "0058", "0059", "0060")
FAR_ROWS = slice(180, None)   # binned rows far below the cloud (cloud centre at row 53)


def frame(run, shot=0):
    """Return the atoms and dark frames of a shot, in mean counts per raw pixel."""
    with h5py.File(lc.DATA / ("%s.h5" % run), "r") as f:
        g = f[sorted(f)[shot]]["images/side/fluorescence_rb87"]
        b = int(f.attrs["img_bin"]) ** 2
        return g["atoms"][:] / b, g["dark"][:] / b


def levels(run):
    atoms, dark = frame(run)
    diff = atoms - dark
    return dict(atoms=atoms.mean(), dark=dark.mean(), diff=diff.mean(), noise=diff.std(),
                far=diff[FAR_ROWS].mean(), peak=diff.max(), N_f=diff.sum() * 64)


def main():
    print("%-5s %-9s %-9s %-10s %-10s %-10s %-8s %-10s" % (
        "run", "atoms", "dark", "atoms-dark", "noise", "far rows", "peak", "N_f"))
    for run in sorted({r for p in PAIRS for r in p[:2]} | set(EMPTY_RUNS)):
        v = levels(run)
        print("%-5s %-9.1f %-9.1f %-10.2f %-10.2f %-10.2f %-8.0f %-10.3g" % (
            run, v["atoms"], v["dark"], v["diff"], v["noise"], v["far"], v["peak"], v["N_f"]))
    sums = np.array([levels(r)["N_f"] for r in EMPTY_RUNS])
    print("empty shots: N_f mean %.2g, std %.2g counts" % (sums.mean(), sums.std(ddof=1)))

    fig = plt.figure(figsize=(16, 7.4))
    # columns: MOT, empty, colour bar, spacer, difference, colour bar, spacer, cut
    gs = fig.add_gridspec(len(PAIRS), 8, width_ratios=[1, 1, 0.05, 0.22, 1, 0.05, 0.3, 1.25], wspace=0.08,
                          hspace=0.35, left=0.02, right=0.95, top=0.87, bottom=0.08)
    for i, (mot, empty, label) in enumerate(PAIRS):
        row = [fig.add_subplot(gs[i, j]) for j in (0, 1, 4, 7)]
        cax_raw, cax_diff = fig.add_subplot(gs[i, 2]), fig.add_subplot(gs[i, 5])
        a_mot, d_mot = frame(mot)
        a_emp, d_emp = frame(empty)
        norm = LogNorm(vmin=d_emp.min(), vmax=a_mot.max())
        for ax, img, title in ((row[0], a_mot, "%s atoms frame (MOT)" % mot),
                               (row[1], a_emp, "%s atoms frame (no MOT)" % empty)):
            im = ax.imshow(img, cmap="viridis", norm=norm, interpolation="nearest")
            ax.set_title(title, fontsize=9, color=INK)
            ax.set_xticks([])
            ax.set_yticks([])
        cb = fig.colorbar(im, cax=cax_raw)
        cb.set_label("counts per pixel (log)", fontsize=8)
        cb.ax.tick_params(labelsize=7)

        diff = a_emp - d_emp
        im = row[2].imshow(diff, cmap="RdBu_r", norm=TwoSlopeNorm(0, -8, 8), interpolation="nearest")
        row[2].set_title("%s atoms - dark (no MOT)\nmean %.2f, std %.2f counts" % (empty, diff.mean(), diff.std()),
                         fontsize=9, color=INK)
        row[2].set_xticks([])
        row[2].set_yticks([])
        cb = fig.colorbar(im, cax=cax_diff)
        cb.set_label("counts per pixel", fontsize=8)
        cb.ax.tick_params(labelsize=7)

        # cut through the MOT peak row, raw counts on a log scale
        y0 = np.unravel_index(np.argmax(a_mot - d_mot), a_mot.shape)[0]
        x_mm = np.arange(a_mot.shape[1]) * lc.C["pixel_at_atoms"].value * 8e3
        ax = row[3]
        style(ax)
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        ax.semilogy(x_mm, a_mot[y0], color=SERIES[0], lw=2, label="MOT, atoms\n(%s)" % mot)
        ax.semilogy(x_mm, a_emp[y0], color=SERIES[1], lw=2, label="no MOT, atoms\n(%s)" % empty)
        ax.semilogy(x_mm, d_emp[y0], color=INK, lw=1, ls=":", label="no MOT, dark\n(%s, under orange)" % empty)
        ax.set_xlabel("x (mm)", fontsize=8)
        ax.set_ylabel("counts per pixel", fontsize=8)
        ax.set_title("Cut through the MOT peak (row %d), %s" % (y0, label), fontsize=9)
        ax.legend(fontsize=7, frameon=False, loc="center right", labelcolor=INK2)
    fig.suptitle("Side camera, 8x8 binned: MOT against empty shots with the same settings", color=INK, fontsize=11)
    out = lc.FIGURES / "mot_vs_empty.png"
    fig.savefig(out, dpi=130)
    print("wrote", out)


if __name__ == "__main__":
    main()
