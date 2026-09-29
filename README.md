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
| `analysis/probe_angle/max_probe_angle.py` | Maximum and minimum probe-pump angle for the FWM probe (motional dephasing, phase matching, beam separation), with literature sources for each physical claim |
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

1. Copy `4wavemixing.py` to `userlib\labscriptlib\krb2\` on the control PC.
2. In runmanager, load **only** `globals/fwm_globals.h5`. Don't load `base_experiment_globals.h5` or `calibrations.h5` alongside it: its groups duplicate theirs, and runmanager refuses duplicate globals.
3. Turn on `Absorption_Imaging` or `Fluorescence_Imaging` to get images. Both are off by default.
4. Bottom imaging: the MOT mirror servo and bottom imaging mirror now switch straight after PGC. Before, they switched at the start of the old magnetic trap stage. With no trap holding the cloud, check that the mirrors have moved before the exposure. At default settings they are commanded at the same time as the camera trigger.
