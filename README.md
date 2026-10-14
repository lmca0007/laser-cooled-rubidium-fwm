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
