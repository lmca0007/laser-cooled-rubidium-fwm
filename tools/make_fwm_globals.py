"""Build globals/fwm_globals.h5 from the archived BEC-lab globals file.

Copies only the groups/globals the 4-wave-mixing sequence (and the lyse
analysis routines) use, strips the '#' scan history from each value, and
writes a fresh runmanager globals file (which also drops the ~300 MB of HDF5
free-space bloat in the original).

Usage (from the repo root):
    python tools/make_fwm_globals.py [--source PATH] [--output PATH]
"""
import argparse
import ast
import builtins
import io
import sys
import tokenize
from pathlib import Path

import h5py
import numpy

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO / 'localstorage' / '4wavemixing' / 'base_experiment_globals.h5'
DEFAULT_OUTPUT = REPO / 'globals' / 'fwm_globals.h5'
SCRIPT = REPO / '4wavemixing.py'

ALL = '*'

# group name -> ALL, or ('only', [names]) / ('except', [names])
KEEP = {
    'Stages': ('only', ['s01_Start_Fresh', 's02_CMOT', 's03_PGC']),
    'MOT': ('except', ['alpha']),
    'CMOT': ('except', ['alphas']),
    'PGC': ('except', ['pgc_optimise']),
    'Imaging': ('only', [
        'Absorption_Imaging', 'Fluorescence_Imaging', 'Side_Imaging', 'Bottom_Imaging',
        'drop_time', 'imaging_repump_time',
        'rb_imaging_repump', 'rb_imaging_repump_amplitude', 'rb_imaging_repump_frequency',
        'roi_full', 'roi_x1', 'roi_x2', 'roi_y1', 'roi_y2', 'shot_number',
    ]),
    # side_camera_pixel_size duplicates Cameras/side_pixel_size, which is what lyse reads
    'Side imaging': ('except', ['side_camera_pixel_size']),
    'Bottom imaging': ('only', [
        'bottom_camera_exposure_time', 'bottom_imaging_amplitude',
        'bottom_imaging_bias_x', 'bottom_imaging_bias_y', 'bottom_imaging_bias_z',
        'bottom_imaging_flourescence_time', 'bottom_imaging_frequency',
        'bottom_imaging_pulse_time', 'bottom_interframe_time', 'top_quarter_wave_plate',
    ]),
    # Read by lyse (OD_calc, fit_frame_roi, y_vs_x, y_vs_auto) and the script (verbose)
    'Analysis': ALL,
    # Calibrations: lyse pixel sizes/saturation, and the coil unit conversions
    # used by the connection table (these must match the lab's BLACS table)
    'Cameras': ALL,
    'Magneatos': ALL,
}

# Groups whose values are copied verbatim (no history stripping)
VERBATIM = {'Cameras', 'Magneatos'}


def strip_history(value):
    """Return the expression before the first '#' comment, ignoring '#' in strings."""
    try:
        for tok in tokenize.generate_tokens(io.StringIO(value).readline):
            if tok.type == tokenize.COMMENT:
                return value[:tok.start[1]].strip()
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return value.strip()


def selected(group, names):
    rule = KEEP[group]
    if rule == ALL:
        return list(names)
    kind, listed = rule
    missing = set(listed) - set(names)
    if missing:
        sys.exit(f'{group}: keep-list names not in source file: {sorted(missing)}')
    if kind == 'only':
        return [n for n in names if n in listed]
    return [n for n in names if n not in listed]


def names_in(expr):
    return {n.id for n in ast.walk(ast.parse(expr, mode='eval')) if isinstance(n, ast.Name)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    kept = {}  # group -> {name: (value, units, expansion)}
    all_source_globals = set()
    with h5py.File(args.source, 'r') as src:
        for group in src['globals']:
            all_source_globals.update(src['globals'][group].attrs.keys())
        for group in KEEP:
            g = src['globals'][group]
            names = sorted(g.attrs.keys())
            kept[group] = {}
            for name in selected(group, names):
                value = g.attrs[name]
                if group not in VERBATIM:
                    value = strip_history(value)
                if not value:
                    sys.exit(f'{group}/{name}: empty value after stripping history')
                kept[group][name] = (value, g['units'].attrs[name], g['expansion'].attrs[name])

    # Validate: every name used in a kept expression is a kept global or a known name
    kept_names = {n for group in kept.values() for n in group}
    known = kept_names | set(dir(builtins)) | set(dir(numpy))
    for group, globs in kept.items():
        for name, (value, _, _) in globs.items():
            unknown = names_in(value) - known
            if unknown:
                sys.exit(f'{group}/{name} = {value!r} references dropped/unknown names {sorted(unknown)}')

    # Validate: every source global referenced by the script was kept
    script_names = names_in_script(SCRIPT)
    needed = (script_names & all_source_globals) - kept_names
    if needed:
        sys.exit(f'4wavemixing.py uses globals that were dropped: {sorted(needed)}')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(args.output, 'w') as out:
        root = out.create_group('globals')
        for group, globs in kept.items():
            g = root.create_group(group)
            units = g.create_group('units')
            expansion = g.create_group('expansion')
            for name, (value, unit, exp) in globs.items():
                g.attrs[name] = value
                units.attrs[name] = unit
                expansion.attrs[name] = exp

    n = sum(len(g) for g in kept.values())
    print(f'Wrote {n} globals in {len(kept)} groups to {args.output} '
          f'({args.output.stat().st_size / 1024:.0f} KB)')


def names_in_script(path):
    tree = ast.parse(path.read_text())
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}


if __name__ == '__main__':
    main()
