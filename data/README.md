# Reduced shot data

These are cut-down copies of the shot files, small enough to keep in git, for analysis away from the lab. The full shot files stay on the share at `Z:\Experiments\krb2\4wavemixing\YYYY\MM\DD\NNNN\`. `tools/export_day.py` makes them:

```
python tools/export_day.py 2026-10-22
```

## Layout

```
data/2026-10-22/
    NNNN.h5        one file per run folder (sequence), one group per shot file
    shots.csv      one row per shot: every scalar global and lyse result
    scripts/       the labscript sequence, once per version (<sha1>.py)
```

Each shot group, named like the shot file (for example `2026-10-22_0061_4wavemixing_0`), contains:

| Path | Contents | Reduction |
|---|---|---|
| attrs | Root attrs of the shot file (`sequence_index`, `run time`, ...), plus `script_sha1` | None |
| `globals`, `shot_properties`, `time_markers` | Copied unchanged | None |
| `traces/<name>/t`, `values` | `mot_fluorescence`, `Quad_voltage`, `Z_Bias_voltage`, `IGC_voltage` | Block means of 50 samples: 50 kHz becomes 1 kHz |
| `images/<camera>/<orientation>/<frame>` | Camera frames, for example `side/fluorescence_rb87/atoms` and `dark` | 8×8 block **sums** as uint32. The sums are exact. Divide by 64 for mean counts |
| `results/<lyse script>` | All lyse attrs (N, fit centres and widths, ...), plus datasets of 10,000 elements or fewer | Large maps (OD, fluorescence image) are left out. Their names are in `skipped_large_datasets` |

## Reading it

```python
import h5py
with h5py.File("data/2026-10-22/0061.h5") as f:
    shot = f["2026-10-22_0061_4wavemixing_0"]
    globals_ = dict(shot["globals"].attrs)
    atoms = shot["images/side/fluorescence_rb87/atoms"][()] / 64.0    # mean counts per raw pixel
    t = shot["traces/mot_fluorescence/t"][()]
    v = shot["traces/mot_fluorescence/values"][()]
```

Side camera: 2200 × 2752 raw pixels, binned to 275 × 344, with a raw pixel of 4.485 µm at the atoms (lyse `fit_frame_roi_fluoro`).
