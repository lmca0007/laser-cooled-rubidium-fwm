"""Export the camera frames of shot files as 16-bit TIFF (camera counts) and viridis PNG.

Reads either the reduced day files in data/2026-10-22 (8x8 block sums, several shots in one
file) or full-resolution lab shot files from Z:\\Experiments\\krb2\\4wavemixing\\YYYY\\MM\\DD\\NNNN.
Writes frames/<shot>_<camera>_<kind>_<frame>.tif and .png.

    python reports/2026-10-25_mot_characterisation/extract_frames.py
    python reports/2026-10-25_mot_characterisation/extract_frames.py --runs 0002 0003 0056
    python reports/2026-10-25_mot_characterisation/extract_frames.py --files Z:\\...\\0056\\*.h5

The TIFF holds the mean counts per raw pixel: a reduced block sum is divided by the block
area (64), so its values stay on the 14-bit camera scale. The local frames are thus 8x8
binned. Only the lab shot files on Z:\\ hold the full 2752 x 2200 (side) and 1024 x 1024
(bottom) frames.
"""
import argparse
import glob

import h5py
import matplotlib
import numpy as np
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import lab_constants as lc  # noqa: E402

# 0001-0003 are the only runs with bottom-camera frames, and 0002-0003 the only runs with
# both cameras. 0056 is the best MOT (showcase_mot.py).
DEFAULT_RUNS = ("0001", "0002", "0003", "0056")
OUT = lc.HERE / "frames"


def shots_in(path):
    """Yield (shot name, shot group, binning) for a reduced day file or a lab shot file."""
    f = h5py.File(path, "r")
    if "images" in f:
        yield path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1][:-3], f, 1
    else:
        for name in sorted(f):
            yield name, f[name], int(f.attrs.get("img_bin", 1))


def frames(group):
    """Yield (camera, kind, frame, array) for each image dataset under /images."""
    if "images" not in group:
        return
    for camera, cg in group["images"].items():
        for kind, kg in cg.items():
            for frame, ds in kg.items():
                yield camera, kind, frame, np.squeeze(ds[()])


def save(img, stem, title):
    """Write a 16-bit TIFF of the counts and a viridis PNG with a colour bar."""
    Image.fromarray(np.clip(np.rint(img), 0, 65535).astype(np.uint16)).save(OUT / (stem + ".tif"))
    fig, ax = plt.subplots(figsize=(6, 6 * img.shape[0] / img.shape[1] + 0.6))
    im = ax.imshow(img, cmap="viridis", interpolation="nearest")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02, label="counts per pixel")
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(OUT / (stem + ".png"), dpi=120)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", nargs="*", default=DEFAULT_RUNS, help="runs in data/2026-10-22")
    ap.add_argument("--files", nargs="*", default=[], help="lab shot files (glob patterns)")
    args = ap.parse_args()

    paths = [str(lc.DATA / ("%s.h5" % r)) for r in args.runs]
    for pattern in args.files:
        paths += sorted(glob.glob(pattern))
    OUT.mkdir(exist_ok=True)
    n = 0
    for path in paths:
        for shot, group, bin_px in shots_in(path):
            for camera, kind, frame, raw in frames(group):
                img = raw.astype(float) / bin_px ** 2
                stem = "%s_%s_%s_%s" % (shot, camera, kind, frame)
                res = "%dx%d binned" % (bin_px, bin_px) if bin_px > 1 else "full resolution"
                save(img, stem, "%s\n%s %s %s, %s, max %.0f counts" % (shot, camera, kind, frame, res, img.max()))
                print("%-48s %s  %4d x %4d  max %6.0f" % (stem, res, img.shape[1], img.shape[0], img.max()))
                n += 1
    print("wrote %d frames to %s" % (n, OUT))


if __name__ == "__main__":
    main()
