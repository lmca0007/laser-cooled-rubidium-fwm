"""MOT brightness, size and photodiode levels for the evening shots of 22 Oct 2026.

Reads the reduced shot data in data/2026-10-22 (made by tools/export_day.py), so it runs
without the lab share. Prints one row per shot and writes mot_comparison.csv next to this file.

    python reports/2026-10-22_lost_mot_and_fwm_probe/mot_comparison.py
"""
import csv
from pathlib import Path

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent / "data" / "2026-10-22"
RUNS = ["0055", "0056", "0057", "0058", "0059", "0060", "0061", "0062", "0063"]
SIDE_PIXEL_UM = 4.485   # side camera pixel at the atoms, from lyse fit_frame_roi_fluoro
ROI_HALF = 30           # binned pixels either side of the brightest bin


def cloud(shot):
    """Background-subtracted fluorescence sum, centroid and rms size in raw side-camera pixels."""
    g = shot["images/side/fluorescence_rb87"]
    k = int(g["atoms"].attrs["bin"])
    img = g["atoms"][()].astype(float) - g["dark"][()].astype(float)
    img -= np.median(img)
    iy, ix = np.unravel_index(img.argmax(), img.shape)
    y0, x0 = max(iy - ROI_HALF, 0), max(ix - ROI_HALF, 0)
    sub = img[y0:iy + ROI_HALF, x0:ix + ROI_HALF].clip(0)
    y, x = np.mgrid[:sub.shape[0], :sub.shape[1]]
    s = sub.sum()
    cy, cx = (sub * y).sum() / s, (sub * x).sum() / s
    sy = np.sqrt((sub * (y - cy) ** 2).sum() / s)
    sx = np.sqrt((sub * (x - cx) ** 2).sum() / s)
    noise = 1.4826 * np.median(np.abs(img - np.median(img)))
    return dict(sum=s, peak_snr=img.max() / noise, y=(cy + y0) * k, x=(cx + x0) * k, sy=sy * k, sx=sx * k)


def pd_levels(shot):
    """Mean mot_fluorescence (V) at the end of the load and, if CMOT ran, during the 100 ms hold."""
    if "traces/mot_fluorescence" not in shot:
        return {}
    t = shot["traces/mot_fluorescence/t"][()]
    v = shot["traces/mot_fluorescence/values"][()]
    marks = {m["label"].decode(): m["time"] for m in shot["time_markers"][()]}
    t_load = marks.get("MOT has been fully loaded")
    out = {"pd_load": v[(t > t_load - 0.1) & (t < t_load)].mean()} if t_load else {}
    if "MOT has been compressed" in marks:
        tc = marks["MOT has been compressed"]
        out["pd_cmot"] = v[(t > tc + 0.01) & (t < tc + 0.09)].mean()
    out["pd_light_off"] = v[t > t.max() - 0.5].mean()
    return out


def main():
    rows = []
    for run in RUNS:
        with h5py.File(DATA / ("%s.h5" % run), "r") as f:
            for name, shot in f.items():
                gl = shot["globals"].attrs
                row = dict(run=run, shot=name,
                           keep_2d_mot_on=bool(gl.get("keep_2d_mot_on", False)),
                           load_time_s=float(gl["rb_science_MOT_load_time"]),
                           exposure_ms=float(gl["side_camera_exposure_time"]) * 1e3,
                           cmot=bool(gl["s02_CMOT"]), pgc=bool(gl["s03_PGC"]))
                row.update(cloud(shot))
                row.update(pd_levels(shot))
                rows.append(row)

    ref = next(r for r in rows if r["run"] == "0056")["sum"]
    print("%-5s %-6s %-5s %-5s %-5s %-9s %-7s %-6s %-12s %-12s %-6s %-6s" % (
        "run", "2D on", "load", "exp", "C/P", "sum", "/0056", "SNR", "centre y,x", "rms y,x px", "PD", "PDcmot"))
    for r in rows:
        print("%-5s %-6s %-5.0f %-5.1f %-5s %-9.3g %-7.4f %-6.0f %5.0f,%-6.0f %4.0f,%-7.0f %-6.3f %s" % (
            r["run"], r["keep_2d_mot_on"], r["load_time_s"], r["exposure_ms"],
            "%d/%d" % (r["cmot"], r["pgc"]), r["sum"], r["sum"] / ref, r["peak_snr"],
            r["y"], r["x"], r["sy"], r["sx"], r.get("pd_load", np.nan),
            "%.3f" % r["pd_cmot"] if "pd_cmot" in r else "-"))
    print("rms size in um = px x %.3f" % SIDE_PIXEL_UM)

    with open(HERE / "mot_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
