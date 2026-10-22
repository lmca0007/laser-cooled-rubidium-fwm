# CLAUDE.md

Four-wave mixing (FWM) experiment on the krb2 apparatus. This includes the labscript sequence, lyse analysis and lab notes.

## Lab layout
- `bec-krb2-control.physics.monash.edu` runs BLACS and runmanager. It also runs zlock.
- `bec-krb2-analysis.physics.monash.edu` runs lyse. It also runs the remote BLACS camera workers (`RemoteBLACS imaging_pc`), which drive the side IMAQdx camera and the bottom Andor camera.
- `bec-krb2-img` is the PC with this repo and VSCode. It can only reach the other two PCs through the shared `Z:\` drive.
- All three map the share as `Z:\`. Shots are written to `Z:\Experiments\krb2\4wavemixing\YYYY\MM\DD\NNNN\`.
- When debugging the other PCs, ask the user to copy logs and terminal output to `Z:\Experiments\krb2\4wavemixing\logs\`.

## Workflow
- Edit code in this repo, then run `python tools/deploy_to_z.py`. runmanager and lyse load the deployed copies from `Z:\Experiments\krb2\4wavemixing\`, not this repo. The deploy script keeps the deployed `globals/fwm_globals.h5` unless you pass `--update-globals`.
- Use the anaconda `py38` env for Python, for example `h5py` to inspect shot files. If the env isn't activated, prepend `envs\py38` and `envs\py38\Library\bin` to PATH, or h5py fails with a DLL load error.

## Known issues and gotchas
- **Imaging globals.** `Absorption_Imaging` and `Fluorescence_Imaging` decide whether any camera exposes. `Side_Imaging` and `Bottom_Imaging` pick the camera. With both imaging globals off, the shot has no `/images` group. Lyse scripts must handle missing images and missing result columns.
- **Andor frame shape.** The bottom camera saves frames as `(1, 1024, 1024)`, and the side camera as `(2200, 2752)`. Lyse scripts call `squeeze`. BLACS shows `TypeError: data.shape[2] must be <= 4` until the patch is applied on bec-krb2-analysis. To apply it, run `lab/patches/apply_andorsolis_squeeze.py`, which doesn't need git. Reinstalling labscript-devices undoes the patch.
- **Side-camera triggers.** Side camera triggers must not touch. If `drop_time + exposure/2` is short, back-to-back exposures overlap and runmanager reports "two overlapping triggerings". That is why the side fluorescence branch waits `side_interframe_time` before absorption imaging.
- **No BOMs.** lyse reads scripts with the Windows default encoding, so a UTF-8 BOM shows up as `ï»¿` and causes a SyntaxError. Save `.py` files as UTF-8 without BOM.
- **BLACS `check/retry`.** `INFO BLACS.AnalysisSubmission.mainloop: Processed signal: check/retry` every 10 s is normal idle logging, not an error. Submission is working if a `Submitting run file ...` line is followed by the shot appearing in lyse.
- **`saturation_calibration.py`.** It is a side-camera calibration routine with a crop in side pixels. It skips shots without side absorption images.
