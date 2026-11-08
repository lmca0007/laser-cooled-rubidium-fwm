"""Show what the CMOT and PGC stages did in the shots that used them.

Shots with s02_CMOT and s03_PGC on: 0002, 0003 (morning) and 0062, 0063 (evening). 0061 is the
same as 0062 with both stages off, so 0061 against 0062 is the only clean pair. Writes
figures/cmot_pgc_check.png and prints the stage levels of the traces.

    python reports/2026-10-25_mot_characterisation/cmot_pgc_check.py

The traces show that the coils and the light followed the stage commands. The frames show
the cloud after a 0.5 ms drop, which is too short to measure a temperature. So the shots
show that the stages ran and kept the atoms, but not that they cooled or compressed them.
"""
import h5py
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import lab_constants as lc  # noqa: E402
from mot_properties import INK, INK2, MUTED, SERIES, style  # noqa: E402

FRAMES = [("0061", "CMOT, PGC off"), ("0062", "CMOT, PGC on"), ("0063", "on, 2D MOT kept on, 1.0 ms"),
          ("0003", "on, 9 s load, 1.0 ms")]
PAIR = ("0061", "0062")
TRACES = [("Quad_voltage", "quad monitor (V)"), ("Z_Bias_voltage", "z bias monitor (V)"),
          ("mot_fluorescence", "MOT beam photodiode (V)")]
CROP = (slice(0, 140), slice(130, 300))   # binned rows, columns around the evening cloud
WINDOW = (-0.02, 0.13)                    # s, about the "MOT has been fully loaded" marker
# t after the loaded marker: CMOT ramp (0-5 ms), CMOT hold (5-105 ms), PGC (105-107 ms)
STAGE_LEVELS = {"MOT": -0.01, "CMOT hold": 0.05, "after PGC": 0.115}


def shot(run):
    f = h5py.File(lc.DATA / ("%s.h5" % run), "r")
    return f[sorted(f)[0]], int(f.attrs["img_bin"])


def loaded_time(g):
    for m in g["time_markers"][:]:
        if m["label"].decode().startswith("MOT has been fully loaded"):
            return float(m["time"])
    raise KeyError("no load marker")


def main():
    fig = plt.figure(figsize=(15, 8))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 0.9], hspace=0.38, wspace=0.18,
                          left=0.05, right=0.97, top=0.9, bottom=0.08)
    evening_max = 0
    imgs = []
    for run, _ in FRAMES:
        g, b = shot(run)
        k = g["images/side/fluorescence_rb87"]
        img = (k["atoms"][:] - k["dark"][:].astype(float)) / b ** 2
        imgs.append(img)
        if run != "0003":
            evening_max = max(evening_max, img[CROP].max())
    px_mm = lc.C["pixel_at_atoms"].value * 8e3
    for i, ((run, label), img) in enumerate(zip(FRAMES, imgs)):
        ax = fig.add_subplot(gs[0, i])
        crop = img[CROP]
        vmax = crop.max() if run == "0003" else evening_max
        im = ax.imshow(crop, cmap="viridis", vmin=0, vmax=vmax, interpolation="nearest")
        cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        cb.ax.tick_params(labelsize=7)
        ax.set_title("%s: %s\nN_f %.2g counts" % (run, label, img.sum() * 64), fontsize=9, color=INK)
        ax.set_xticks([])
        ax.set_yticks([])
        ny = crop.shape[0]
        ax.plot([5, 5 + 1 / px_mm], [ny - 8, ny - 8], color="white", lw=2.5)
        ax.text(5 + 0.5 / px_mm, ny - 12, "1 mm", color="white", ha="center", fontsize=8)

    for j, (name, ylabel) in enumerate(TRACES):
        ax = fig.add_subplot(gs[1, j])
        style(ax)
        for run, color in zip(PAIR, (MUTED, SERIES[0])):
            g, _ = shot(run)
            t0 = loaded_time(g)
            t = g["traces/%s/t" % name][:] - t0
            v = g["traces/%s/values" % name][:]
            sel = (t > WINDOW[0]) & (t < WINDOW[1])
            ax.plot(t[sel] * 1e3, v[sel], color=color, lw=1.8,
                    label="%s (%s)" % (run, "stages off" if run == PAIR[0] else "CMOT + PGC"))
            print("%s %-16s " % (run, name) + "  ".join(
                "%s %.3f" % (k, np.interp(dt, t, v)) for k, dt in STAGE_LEVELS.items()))
        for x, txt in ((0, "CMOT ramp"), (105, "PGC")):
            ax.axvline(x, color=INK2, lw=0.8, ls=":")
            ax.text(x + 1.5, ax.get_ylim()[1], txt, fontsize=7, color=INK2, va="top")
        ax.set_xlabel("time after the MOT load (ms)", fontsize=8)
        ax.set_ylabel(ylabel, fontsize=8)
        if j == 0:
            ax.legend(fontsize=7, frameon=False, loc="center left", labelcolor=INK2)
    fig.text(0.77, 0.25, "The 0003 traces match 0062.\nThe frames use a 0.5 ms drop,\nso they show no temperature.",
             fontsize=9, color=INK2, va="center")
    fig.suptitle("CMOT and PGC: side fluorescence frames (top, 0061-0063 on one scale) and stage traces (bottom)",
                 fontsize=11, color=INK)
    out = lc.FIGURES / "cmot_pgc_check.png"
    fig.savefig(out, dpi=130)
    print("wrote", out)


if __name__ == "__main__":
    main()
