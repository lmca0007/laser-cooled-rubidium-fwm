"""Apply andorsolis_squeeze.patch to the installed labscript_devices, without git.

Run on bec-krb2-analysis (where the camera workers run), in the same env as BLACS, with BLACS closed:

    python Z:\\Experiments\\krb2\\4wavemixing\\lab\\patches\\apply_andorsolis_squeeze.py --check
    python Z:\\Experiments\\krb2\\4wavemixing\\lab\\patches\\apply_andorsolis_squeeze.py

The original file is kept next to it as blacs_workers.py.orig. Running it again does nothing.
"""
import argparse
import importlib.util
import shutil
from pathlib import Path

HELPER = '''def _drop_frame_axis(img):
    """Single frames come back as (1, ny, nx). Return (ny, nx), which pyqtgraph and lyse can show."""
    if getattr(img, 'ndim', 0) == 3 and img.shape[0] == 1:
        return img[0]
    return img

'''

# (old, new) text replacements, each old string must appear exactly once
EDITS = [
    ("class AndorCamera(object):", HELPER + "class AndorCamera(object):"),
    ("        return images # This may be a 3D array of several images",
     "        return _drop_frame_axis(images) # 3D only if several images"),
    ("                images.append(downloaded)",
     "                images.append(_drop_frame_axis(downloaded))"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report what would change, without writing")
    args = ap.parse_args()

    # Find the package without importing it, so the Andor drivers are not needed
    spec = importlib.util.find_spec("labscript_devices")
    if spec is None:
        raise SystemExit("labscript_devices not found. Activate the env that BLACS uses first.")
    target = Path(spec.submodule_search_locations[0]) / "AndorSolis" / "blacs_workers.py"
    print(f"file   {target}")

    text = target.read_text(encoding="utf-8")
    if "_drop_frame_axis" in text:
        print("already patched, nothing to do")
        return

    bad = [old.strip() for old, _ in EDITS if text.count(old) != 1]
    if bad:
        raise SystemExit("file differs from labscript-devices 3.3.0, edit by hand (see README.md). Not found once:\n  "
                         + "\n  ".join(bad))

    for old, new in EDITS:
        text = text.replace(old, new)
    if args.check:
        print("ok, patch applies cleanly (run without --check to write it)")
        return

    shutil.copy2(target, target.with_name(target.name + ".orig"))
    target.write_text(text, encoding="utf-8")
    print("patched, original saved as blacs_workers.py.orig. Restart BLACS.")


if __name__ == "__main__":
    main()
