# AndorSolis frame shape patch (imaging PC)

## Problem

The Andor bottom camera returns each frame as `(1, 1024, 1024)`. The side camera returns `(2200, 2752)`.

- BLACS shows `TypeError: data.shape[2] must be <= 4` when you inspect the bottom camera.
- lyse `OD_calc.py` stopped with `Invalid shape (1, 1024, 1024) for image data`.

## Fix

`andorsolis_squeeze.patch` drops the size-1 axis in `AndorCamera.snap` and `AndorCamera.grab_multiple` (single acquisition mode). Shots then store `(1024, 1024)`.

The lyse scripts in this repo also call `squeeze`, so they work with old and new shots.

## Apply on the imaging PC

1. Close BLACS.
2. Find the file: `<py38 env>\Lib\site-packages\labscript_devices\AndorSolis\blacs_workers.py`.
3. Compare it with the `-` lines of the patch. The patch was made against labscript-devices 3.3.0. If the lab file differs, make the same three edits by hand.
4. From the `site-packages` folder, run: `git apply --check <this folder>\andorsolis_squeeze.patch`, then `git apply <this folder>\andorsolis_squeeze.patch`.
5. Start BLACS. Inspect the bottom camera.
