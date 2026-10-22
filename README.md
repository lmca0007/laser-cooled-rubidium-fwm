# Laser-cooled rubidium four-wave mixing

labscript control sequence for four-wave mixing in a laser-cooled Rb-87 cloud. It runs on the Monash BEC lab apparatus (krb2). The sequence was cut down from the BEC experiment's control script to the stages this experiment needs:

MOT load → CMOT → PGC → hold/drop → fluorescence or absorption imaging (side or bottom camera) → between-shot MOT defaults

## Layout

| Path | What |
|---|---|
| `4wavemixing.py` | The labscript sequence, including the connection table |
| `globals/fwm_globals.h5` | runmanager globals: stage switches, MOT/CMOT/PGC/imaging parameters, lyse analysis settings, and the `Cameras`/`Magneatos` calibrations |
| `tools/make_fwm_globals.py` | Rebuilds `globals/fwm_globals.h5` from the archived BEC globals file (keep-list lives here) |
| `tools/check_sequence.py` | Offline compile, connection-table diff, and regression check against the original script |
| `analysis/lyse/` | lyse routines (`single_shot/`, `multishot/`) and `lyse_4wavemixing.ini`, the lyse config that loads them from Z: |
| `lab/connection_table.py` | Reference copy of the BLACS connection table on the lab PC |
| `lab/patches/` | Patch for the Andor camera frame shape (imaging PC), with steps |
| `tools/deploy_to_z.py` | Copies the code to `Z:\Experiments\krb2\4wavemixing\` |
| `tools/mot_scan.py` | Closed-loop 2D MOT sweeps through runmanager's remote API (see below) |
| `tools/export_day.py` | Exports a reduced copy of one day of shots into `data/`, for analysis off site |
| `data/` | Reduced shot data (globals, lyse results, 1 kHz traces, 8×8-binned frames), see `data/README.md` |
| `reports/` | Dated lab reports with the findings and the scripts that reproduce them |
| `analysis/probe_angle/max_probe_angle.py` | Maximum and minimum probe-pump angle for the FWM probe (motional dephasing, phase matching, beam separation), with literature sources for each physical claim |
| `optics/fwm_probe/` | FWM probe table layout: PyOpticL 3D model, geometry and clearance checks, polarisation model |
| `media/` | Reference camera images (no BEC) |
| `localstorage/` | Not tracked. Snapshot of the lab's labscript-suite folder, the original globals and the Aug 2026 shots |

## Offline development

```
pip install -r requirements.txt
labscript-profile-create                 # once; creates ~/labscript-suite

python tools/check_sequence.py compile                                    # default globals
python tools/check_sequence.py compile --set Absorption_Imaging=True --set s03_PGC=True
```

`compile` writes `tools/_out/shot.h5`, which you can open in runviewer. `--set` overrides a global for that compile only. To change a value permanently, edit `globals/fwm_globals.h5` in runmanager.

The original BEC globals file is archived in `localstorage/`. To regenerate the globals from it after changing the keep-list, run `python tools/make_fwm_globals.py`. **This overwrites `globals/fwm_globals.h5`**, including any edits made in runmanager.

`python tools/check_sequence.py regress` compiles the original script (from git) and this one across stage and imaging configurations, and checks that every output channel does the same thing.

## Connection table: keep it in sync with BLACS

BLACS on the lab PC has its own `connection_table.py` (`userlib\labscriptlib\krb2\`). It rejects any shot whose connection table is not a subset of it. So:

- Don't rename, remove or rewire devices in `4wavemixing.py`. Hardware this experiment doesn't use (dipole-trap, RF-evaporation, Raman and kick AOMs) stays defined and is held gated off in the sequence.
- Adding hardware, such as a probe-beam AOM or photodiode channel, means changing the lab's `connection_table.py` too and recompiling it in BLACS.
- The coil unit conversions read the `Magneatos` globals, so don't change those values.
- To check against a shot taken in the lab: `python tools/check_sequence.py ctdiff tools/_out/shot.h5 <lab_shot.h5>`. Differences in unit-conversion class paths, `__version__` and camera or NI default properties come from labscript versions, not wiring.

## In the lab

Everything for this experiment lives in `Z:\Experiments\krb2\4wavemixing\`. runmanager already writes shots there (`YYYY\MM\DD\NNNN`), because the folder name is the script name `4wavemixing`. Don't rename `4wavemixing.py`. Don't change `experiment_shot_storage` in labconfig: the BEC experiment shares it.

1. Run `python tools/deploy_to_z.py` (add `--dry-run` to preview). It copies the code and leaves the shot folders alone. It copies `globals/fwm_globals.h5` only if Z: has none.
2. In runmanager, open `Z:\Experiments\krb2\4wavemixing\4wavemixing.py`. Load **only** `Z:\Experiments\krb2\4wavemixing\globals\fwm_globals.h5`. Don't load `base_experiment_globals.h5` or `calibrations.h5` alongside it: its groups duplicate theirs, and runmanager refuses duplicate globals. (The 2026-10-14 test shot ran the old BEC script with all 336 BEC globals.)
3. In lyse, use File → Load configuration and pick `Z:\Experiments\krb2\4wavemixing\analysis\lyse\lyse_4wavemixing.ini`. Leave the lab autoload config alone: the BEC experiment uses it.
4. On the imaging PC, apply the Andor frame patch in `lab/patches/` (see its README).
5. Turn on `Absorption_Imaging` or `Fluorescence_Imaging` to get images. Both are off by default.
6. Bottom imaging: the MOT mirror servo and bottom imaging mirror now switch straight after PGC. Before, they switched at the start of the old magnetic trap stage. With no trap holding the cloud, check that the mirrors have moved before the exposure. At default settings they are commanded at the same time as the camera trigger.

## Automated MOT sweeps

`tools/mot_scan.py` runs the 2D MOT optimisation scans from the lab manual in a closed loop. It scans the coil pairs, then gradient against detuning, the source AOM amplitudes and frequencies, and the push beam. For each scan it sets the linspace globals through runmanager's remote API and engages. It then waits for lyse to write `fluoro_frame` `N` into every shot file, fits the peak, and writes the optimum back into the global, with the old value as a `#` comment. If the optimum lands on the edge of the range, it recentres and rescans once.

Run it on bec-krb2-control in the py38 env, with runmanager open and lyse running `fluoro_frame`:

```
python Z:\Experiments\krb2\4wavemixing\tools\mot_scan.py --dry-run             # check shot counts, change nothing
python Z:\Experiments\krb2\4wavemixing\tools\mot_scan.py --only src_trap_amp   # one short scan
python Z:\Experiments\krb2\4wavemixing\tools\mot_scan.py                       # all scans
```

- Ranges are centred on the current values (±0.4 V on the coils, ±0.15–0.2 on AOM amplitudes, ±3–4 MHz on AOM frequencies, alpha ±0.05), so the script tunes a working MOT. It doesn't search for one.
- After each scan, one check shot runs at the new values. If it is below 70 % of the expected N_f, the scan's values are undone and the run pauses for you to fix the lasers. On 22 Oct the repump drifted off and spoiled four scans. Press Enter to take another check shot, and the scan runs again once N_f has recovered.
- A fit only counts if its width is between one scan step and twice the range. A wider fit is a slope with no peak.
- A value is written back only when the best shot reaches `MIN_SIGNAL` and the fitted peak clearly stands above the scatter. Otherwise the old value is kept.
- After each scan it runs one shot at the final values. This matters because the source AOMs are static DDSs: between shots, BLACS holds whatever the last shot used.
- During a run, the script sets `keep_2d_mot_on` = True, so the 2D MOT light and coils stay on through every shot. Gating the source AOMs each shot made the 2D MOT take about 10 s to recover. Start_Fresh now switches the quad off too, so every load starts from an empty trap.
- Before the scans, it runs two checks (skip them with `--skip-checks`):
  - **Stability:** 8 identical shots. The check fails if the scatter (std/mean) or the fitted change from first to last shot is over 20 %. On a fail it adds a 10 s `inter_shot_wait` and checks again. If it's still unstable, the run stops.
- Keep `source_mot_led_enable` = False. The source LED pulse each shot drains Rb from the source cell walls. With it on, N_f fell 25× over 8 back-to-back shots (0015). With it off, it changed by 14 % (0017).
  - **Load curve:** sets `rb_science_MOT_load_time` to τ/2 for the scans, so N_f follows the loading rate. The old load time is restored at the end.
- A scan whose N_f tracks shot order is refused.
- The MOT group needs the globals `alpha` = `1`, `inter_shot_wait` = `0` and `keep_2d_mot_on` = `False`.
- Each run writes a plot per scan and `summary.jsonl` to `logs\mot_scans\<timestamp>\`.
- Ctrl+C restores the globals of the scan in progress. Shots already queued in BLACS still run, so clear the queue by hand.
- `--replay <sequence folder>` fits an existing sequence without runmanager.
