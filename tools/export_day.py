"""Export a reduced copy of one day of shots, small enough to commit, for analysis off site.

Each run folder Z:\\Experiments\\krb2\\4wavemixing\\YYYY\\MM\\DD\\NNNN becomes one file
data/YYYY-MM-DD/NNNN.h5, with one group per shot file (named like the shot file). Each shot group keeps:
    globals, shot_properties, time_markers   copied unchanged (root attrs too)
    traces/<name>/t, values                  block means over TRACE_DECIMATE samples (50 kHz -> 1 kHz)
    images/<camera>/<orientation>/<frame>    IMG_BIN x IMG_BIN block sums (uint32, lossless sums)
    results/<lyse script>                    all attrs, plus datasets up to SMALL_DATASET elements
The sequence script is stored once per version in scripts/<sha1>.py, and the shot group's
'script_sha1' attr points to it. data/YYYY-MM-DD/shots.csv has one row per shot with every
scalar global and lyse result, for a quick look without h5py.

    python tools/export_day.py 2026-10-22
    python tools/export_day.py 2026-10-22 --runs 0061 0062
"""
import argparse
import csv
import glob
import hashlib
import os
from pathlib import Path

import h5py
import numpy as np

REPO = Path(__file__).resolve().parent.parent
SHOTS = Path(r"Z:\Experiments\krb2\4wavemixing")
IMG_BIN = 8
TRACE_DECIMATE = 50
SMALL_DATASET = 10000
COMPRESS = dict(compression="gzip", compression_opts=6, shuffle=True)


def block_sum(img, k):
    h, w = (img.shape[0] // k) * k, (img.shape[1] // k) * k
    return img[:h, :w].reshape(h // k, k, w // k, k).sum(axis=(1, 3), dtype=np.uint64).astype(np.uint32)


def block_mean(x, k):
    n = (len(x) // k) * k
    return x[:n].reshape(-1, k).mean(axis=1)


def scalar(v):
    """Return v as a csv-friendly scalar, or None if it is not one."""
    if isinstance(v, bytes):
        v = v.decode(errors="replace")
    if isinstance(v, np.ndarray):
        if v.size != 1:
            return None
        v = v.item()
    if isinstance(v, (bool, int, float, str, np.generic)):
        return v.item() if isinstance(v, np.generic) else v
    return None


def export_shot(src, out, script_dir, row):
    with h5py.File(src, "r") as h:
        for k, v in h.attrs.items():
            out.attrs[k] = v
        for name in ("globals", "shot_properties", "time_markers"):
            if name in h:
                h.copy(h[name], out, name=name)

        if "script" in h:
            text = h["script"][()]
            text = text if isinstance(text, bytes) else str(text).encode()
            sha = hashlib.sha1(text).hexdigest()
            path = script_dir / ("%s.py" % sha)
            if not path.exists():
                path.write_bytes(text)
            out.attrs["script_sha1"] = sha

        if "data/traces" in h:
            for name, ds in h["data/traces"].items():
                a = ds[()]
                g = out.create_group("traces/%s" % name)
                g.create_dataset("t", data=block_mean(a["t"], TRACE_DECIMATE), **COMPRESS)
                g.create_dataset("values", data=block_mean(a["values"], TRACE_DECIMATE).astype(np.float32), **COMPRESS)
                g.attrs["decimation"] = TRACE_DECIMATE
                g.attrs["raw_samples"] = len(a)

        if "images" in h:
            def image(name, obj):
                if isinstance(obj, h5py.Dataset):
                    frame = np.squeeze(obj[()])
                    if frame.ndim == 2:
                        d = out.create_dataset("images/" + name, data=block_sum(frame, IMG_BIN), **COMPRESS)
                        d.attrs["bin"] = IMG_BIN
                        d.attrs["raw_shape"] = obj.shape
                        d.attrs["raw_dtype"] = str(obj.dtype)
            h["images"].visititems(image)

        if "results" in h:
            for script, g in h["results"].items():
                o = out.create_group("results/%s" % script)
                skipped = []
                for k, v in g.attrs.items():
                    o.attrs[k] = v
                    s = scalar(v)
                    if s is not None:
                        row["%s.%s" % (script, k)] = s
                for k, ds in g.items():
                    if isinstance(ds, h5py.Dataset) and ds.size <= SMALL_DATASET:
                        o.create_dataset(k, data=ds[()])
                    else:
                        skipped.append(k)
                if skipped:
                    o.attrs["skipped_large_datasets"] = ", ".join(skipped)

        if "globals" in h:
            for k, v in h["globals"].attrs.items():
                s = scalar(v)
                if s is not None:
                    row[k] = s


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("date", help="YYYY-MM-DD")
    p.add_argument("--runs", nargs="*", help="run folders to export (default: all)")
    args = p.parse_args()

    y, m, d = args.date.split("-")
    day = SHOTS / y / m / d
    dest = REPO / "data" / args.date
    script_dir = dest / "scripts"
    script_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for run in sorted(os.listdir(day)):
        if args.runs and run not in args.runs:
            continue
        files = sorted(glob.glob(str(day / run / "*.h5")))
        if not files:
            continue
        with h5py.File(dest / ("%s.h5" % run), "w") as out:
            out.attrs["source"] = str(day / run)
            out.attrs["img_bin"] = IMG_BIN
            out.attrs["trace_decimation"] = TRACE_DECIMATE
            for f in files:
                name = os.path.basename(f)[:-3]
                row = {"run": run, "shot": name}
                try:
                    export_shot(f, out.create_group(name), script_dir, row)
                except OSError as e:  # unreadable or half-written shot file
                    row["export_error"] = str(e)
                rows.append(row)
        print("%s: %d shots, %.1f MB" % (run, len(files), os.path.getsize(dest / ("%s.h5" % run)) / 1e6), flush=True)

    first = ["run", "shot", "sequence_index"]
    cols = first + sorted({k for r in rows for k in r} - set(first))
    csv_path = dest / ("shots.csv" if not args.runs else "shots_partial.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print("wrote", csv_path)


if __name__ == "__main__":
    main()
