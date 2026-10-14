"""Copy the FWM code to the shared drive folder Z:\\Experiments\\krb2\\4wavemixing.

Shots are written to the same folder by runmanager (YYYY/MM/DD/NNNN), so this script
never touches those. globals/fwm_globals.h5 is copied only if it is missing on the
destination, so edits made in runmanager are not overwritten (use --update-globals to force).

    python tools/deploy_to_z.py --dry-run
    python tools/deploy_to_z.py
"""
import argparse
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DEST = Path(r"Z:\Experiments\krb2\4wavemixing")

# Folders and files copied every time
CODE = ["4wavemixing.py", "README.md", "requirements.txt", "analysis", "lab", "tools", "media"]
SKIP_DIRS = {"__pycache__", "output", "_out"}
GLOBALS = Path("globals") / "fwm_globals.h5"


def files_to_copy():
    for item in CODE:
        path = REPO / item
        if path.is_file():
            yield path
        elif path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file() and not SKIP_DIRS & set(f.relative_to(path).parts) and f.suffix != ".pyc":
                    yield f


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--dry-run", action="store_true", help="list what would be copied")
    ap.add_argument("--update-globals", action="store_true", help="overwrite globals/fwm_globals.h5 on the destination")
    args = ap.parse_args()

    if not args.dry_run and not args.dest.parent.exists():
        raise SystemExit(f"{args.dest.parent} not found. Is the shared drive mounted?")

    jobs = [(f, args.dest / f.relative_to(REPO)) for f in files_to_copy()]
    g_dst = args.dest / GLOBALS
    if args.update_globals or not g_dst.exists():
        jobs.append((REPO / GLOBALS, g_dst))
    else:
        print(f"keep   {g_dst} (already exists)")

    for src, dst in jobs:
        print(f"{'would copy' if args.dry_run else 'copy'}  {dst}")
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    print(f"{len(jobs)} file(s) {'would be ' if args.dry_run else ''}copied to {args.dest}")


if __name__ == "__main__":
    main()
