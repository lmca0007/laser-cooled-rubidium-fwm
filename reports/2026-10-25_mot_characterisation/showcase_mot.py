"""The lyse Gaussian-fit figure (viridis image, side cuts, colour bar) for the best MOT shot.

Runs the plot and fit code of analysis/lyse/single_shot/fit_frame_roi.py without lyse. The
script copies the functions gaussian, gauss_1d, calc_moments2d, plot_results, rebin and fit
from that file, so the figure has the same layout as the lyse window. Writes:
    figures/showcase_<run>_lyse.png

    python reports/2026-10-25_mot_characterisation/showcase_mot.py [--run 0056]

The default shot is 0056, the last check shot of the evening. It has all the scan optima, a
1 s load, the 0.6 ms exposure, and no saturated blocks. The six check shots 0045-0056 agree
to 2.9 % (README Sec. 1).

The reduced frames are 8x8 block sums, so the script divides them by 64. The fit result is
in the binned pixels, and the script multiplies it by 8 to compare it with the lyse values
in shots.csv, which lyse fitted on the full frame.
"""
import argparse
import ast
import json

import h5py
import matplotlib
import matplotlib.ticker
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import lab_constants as lc  # noqa: E402
from lab_constants import C  # noqa: E402

LYSE_SCRIPT = lc.REPO / "analysis" / "lyse" / "single_shot" / "fit_frame_roi.py"
LYSE_FUNCTIONS = ("gaussian", "gauss_1d", "calc_moments2d", "plot_results", "rebin", "fit")


def lyse_functions():
    """Return the plot and fit functions of the lyse script, in a namespace without lyse."""
    tree = ast.parse(LYSE_SCRIPT.read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in LYSE_FUNCTIONS]
    ns = {}
    exec("from pylab import *\nfrom scipy import optimize\nimport matplotlib.gridspec as gridspec", ns)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(LYSE_SCRIPT), "exec"), ns)
    return ns


def read_frame(run, shot=0):
    """Return (atoms - dark) in mean counts per raw pixel, the shot name and the binning."""
    with h5py.File(lc.DATA / ("%s.h5" % run), "r") as f:
        name = sorted(f)[shot]
        g = f[name]["images/side/fluorescence_rb87"]
        bin_px = int(f.attrs["img_bin"])
        img = (g["atoms"][:].astype(float) - g["dark"][:].astype(float)) / bin_px ** 2
    return img, name, bin_px


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default="0056")
    ap.add_argument("--shot", type=int, default=0)
    args = ap.parse_args()

    img, name, bin_px = read_frame(args.run, args.shot)
    ns = lyse_functions()
    plt.rcParams["image.cmap"] = "viridis"
    fig = plt.figure("atomfit - " + name, figsize=(9, 6))
    # fluorescence counts have no clip level, as in fit_frame_roi_fluoro.py
    params, err = ns["fit"](name, img, binsize=1, fit_od0=True, clip=np.inf)

    # plot_results labels the image "Optical density". This frame is fluorescence.
    image_ax = fig.axes[0]
    image_ax.set_title("Side fluorescence, counts per pixel", fontsize=10)
    # plot_results removes every tick. Put the colour bar ticks back, so the scale shows.
    cbar_ax = fig.axes[1]
    cbar_ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(6))
    cbar_ax.tick_params(labelsize=8)
    px_mm = C["pixel_at_atoms"].value * bin_px * 1e3
    sx_mm, sy_mm = abs(params[3]) * px_mm, abs(params[4]) * px_mm

    # 1 mm scale bar, as the lyse figure has no axis ticks
    ny, nx = img.shape
    x0, y0 = 0.05 * nx, 0.92 * ny
    image_ax.plot([x0, x0 + 1 / px_mm], [y0, y0], color="white", lw=3)
    image_ax.text(x0 + 0.5 / px_mm, y0 - 0.03 * ny, "1 mm", color="white", ha="center", fontsize=9)

    summary_path = lc.HERE / "mot_summary.json"
    label = "Run %s: sigma = %.2f x %.2f mm (lyse fit)" % (args.run, sx_mm, sy_mm)
    if args.run == "0056" and summary_path.exists():
        s = json.loads(summary_path.read_text())
        c = s["cloud_0056"]
        n = c["N_atoms_fit"]
        cpa = s["budget_0.6ms"]["counts_per_atom_mc"]["median"]
        # The camera signal is in counts, not atoms: each atom gives about 6 counts
        label += "\nSignal %.1e counts / %.1f counts per atom = %.1e atoms (%.1e to %.1e)" % (
            c["fit_integral"], cpa, n["median"], n["p16"], n["p84"])
        label += "\nPeak density %.0e cm^-3, 1 s load, 0.6 ms exposure" % c["peak_density_cm3"]["median"]
    fig.suptitle(label, fontsize=10)
    fig.subplots_adjust(top=0.85)

    out = lc.FIGURES / ("showcase_%s_lyse.png" % args.run)
    fig.savefig(out, dpi=150)
    print("wrote", out)
    print("fit (binned px): amp %.1f, x %.1f, y %.1f, sx %.2f, sy %.2f, offset %.2f" % tuple(params[:6]))
    print("fit (raw px):    x %.0f, y %.0f, sx %.0f, sy %.0f" % tuple(np.array(params[1:5]) * bin_px))
    print("sigma: %.3f x %.3f mm" % (sx_mm, sy_mm))


if __name__ == "__main__":
    main()
