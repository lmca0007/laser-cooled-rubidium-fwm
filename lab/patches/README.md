# AndorSolis frame shape patch (imaging PC)

## Problem

The Andor bottom camera returns each frame as `(1, 1024, 1024)`. The side camera returns `(2200, 2752)`.

- BLACS shows `TypeError: data.shape[2] must be <= 4` when you inspect the bottom camera.
- lyse `OD_calc.py` stopped with `Invalid shape (1, 1024, 1024) for image data`.

## Fix

`andorsolis_squeeze.patch` drops the size-1 axis in `AndorCamera.snap` and `AndorCamera.grab_multiple` (single acquisition mode). Shots then store `(1024, 1024)`.

The lyse scripts in this repo also call `squeeze`, so they work with old and new shots.

## Apply on the imaging PC

The camera workers run on `bec-krb2-analysis` (`RemoteBLACS imaging_pc` in `4wavemixing.py`). Reinstalling labscript-devices there undoes the patch, so apply it again after every reinstall.

1. Close BLACS and the remote camera server on bec-krb2-analysis.
2. Open a terminal there and activate the env that runs them (`conda activate py38`).
3. Run `python Z:\Experiments\krb2\4wavemixing\lab\patches\apply_andorsolis_squeeze.py --check`. It finds the installed `labscript_devices\AndorSolis\blacs_workers.py` and reports whether the patch applies cleanly.
4. Run the same command without `--check`. It saves the original as `blacs_workers.py.orig`. Running it again does nothing.
5. Start BLACS and the camera server again. Then inspect the bottom camera.

If the script reports that the file differs, make the three edits shown in `andorsolis_squeeze.patch` by hand. The patch was made against labscript-devices 3.3.0. If git is installed, `git apply andorsolis_squeeze.patch` from the `site-packages` folder does the same thing as the script.
