"""Offline checks for the labscript sequence (no lab hardware needed).

Needs labscript, labscript-devices, labscript-utils and runmanager installed, and a
labscript profile (run `labscript-profile-create` once).

Subcommands (run from the repo root):

  compile   Compile a script + globals into a shot .h5, which you can open in runviewer.
                python tools/check_sequence.py compile --set Absorption_Imaging=True

  ctdiff    Compare the connection tables of two shot files, e.g. an offline compile
            against a shot taken in the lab.
                python tools/check_sequence.py ctdiff tools/_out/shot.h5 path/to/lab_shot.h5

  regress   Compile the original BEC-lab script (from git) and the cleaned script over a
            set of stage/imaging configurations. Compares their connection tables and
            every output channel's timeline.
                python tools/check_sequence.py regress
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import labscript_utils.h5_lock  # labscript requires this to be imported before h5py
except ImportError:
    pass
import h5py
import numpy as np

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / 'tools' / '_out'
SCRIPT = REPO / '4wavemixing.py'
GLOBALS = [REPO / 'globals' / 'fwm_globals.h5']

# Original script as pulled from the BEC experiment, and the globals it ran with
OLD_REF = '52f3332'
OLD_GLOBALS = [REPO / 'localstorage' / '4wavemixing' / 'base_experiment_globals.h5']
# The old script imports analysislib.krb2 (and through it pythonlib's alkali), which
# live in the lab userlib snapshot
OLD_USERLIB = REPO / 'localstorage' / 'labscript-suite' / 'userlib'
# Stages the cleaned script no longer has; turned off when compiling the old script
OLD_ONLY_STAGES = ['s04_MT', 's05_RF_Evaporation', 's06_Decompress', 's07_Hybrid_Evaporation',
                   's07p5_Trap_for_Exp', 's08_Load_Uniform_Trap', 's09_Spin_Rotating_Trap',
                   's10_RFPulse', 's11_QDKR', 's12_Raman', 'Faraday_Imaging', 'Levitate']
# Channels whose timelines are expected to differ in the bottom-imaging configs: the
# mirror moves were relocated from the (removed) magnetic trap stage.
EXPECTED_BOTTOM_DIFFS = {'mot_mirror_servo', 'bottom_imaging_mirror'}


# ---------------------------------------------------------------------------
# Compiling
# ---------------------------------------------------------------------------

def make_run_file(script, globals_files, overrides, run_file):
    import runmanager

    groups = runmanager.get_all_groups([str(p) for p in globals_files])
    sequence_globals = runmanager.get_globals(groups)
    for name, expr in overrides.items():
        for group in sequence_globals.values():
            if name in group:
                _, units, _ = group[name]
                group[name] = (expr, units, '')
                break
        else:
            raise SystemExit(f'--set {name}: no such global in {[str(p) for p in globals_files]}')
    evaled, _, _ = runmanager.evaluate_globals(sequence_globals)
    shots = runmanager.expand_globals(sequence_globals, evaled)
    if len(shots) != 1:
        raise SystemExit('Globals define a scan (more than one shot); set scanned globals to a single value')
    now = datetime.datetime.now()
    basename = Path(script).stem
    sequence_attrs = {
        'script_basename': basename,
        'sequence_date': now.strftime('%Y-%m-%d'),
        'sequence_index': 0,
        'sequence_id': now.strftime('%Y%m%dT%H%M%S') + '_' + basename,
    }
    runmanager.make_single_run_file(str(run_file), sequence_globals, shots[0], sequence_attrs, 0, 1)


def compile_shot(script, globals_files, overrides, run_file, timeline_file=None):
    """Compile script into run_file the same way runmanager's batch compiler does."""
    import labscript

    script = Path(script).resolve()
    make_run_file(script, globals_files, overrides, run_file)
    cwd = os.getcwd()
    os.chdir(script.parent)
    try:
        labscript.labscript_init(str(run_file), labscript_file=str(script))
        code = compile(script.read_text(), str(script), 'exec', dont_inherit=True)
        exec(code, {'__name__': '__main__', '__file__': str(script)})
        if timeline_file is not None:
            Path(timeline_file).write_text(json.dumps(output_timelines(), indent=0))
    finally:
        labscript.labscript_cleanup()
        os.chdir(cwd)


def output_timelines():
    """Every output's value over the shot, as [(time, value), ...] with repeats removed."""
    from labscript.compiler import compiler
    from labscript.outputs import Output

    timelines = {}
    for device in compiler.inventory:
        if not isinstance(device, Output) or not hasattr(device, 'raw_output'):
            continue
        values = np.asarray(device.raw_output)
        if len(values) == 1:
            times = [0.0]
        else:
            clock_line = device.parent_clock_line
            times = clock_line.parent_device.times[clock_line]
        timeline = []
        for time, value in zip(times, values):
            value = round(float(value), 9)
            if not timeline or timeline[-1][1] != value:
                timeline.append((round(float(time), 9), value))
        timelines[device.name] = timeline
    return timelines


def shot_summary(run_file):
    with h5py.File(run_file, 'r') as f:
        markers = [(m['label'].decode(), round(float(m['time']), 9)) for m in f['time_markers'][:]]
        stop_time = max(float(f['devices'][d].attrs['stop_time'])
                        for d in f['devices'] if 'stop_time' in f['devices'][d].attrs)
    return markers, stop_time


# ---------------------------------------------------------------------------
# Comparing
# ---------------------------------------------------------------------------

def connection_table(run_file):
    with h5py.File(run_file, 'r') as f:
        table = f['connection table'][:]
    return {row['name']: row for row in table}


def parsed(value):
    """Decode JSON-serialised properties so key order doesn't count as a difference
    (BLACS compares the deserialised values too)."""
    prefix = b'Content-Type: application/json '
    if isinstance(value, bytes) and value.startswith(prefix):
        return json.loads(value[len(prefix):])
    return value


def ctdiff(file_a, file_b):
    """Print connection table differences; return True if identical."""
    a, b = connection_table(file_a), connection_table(file_b)
    identical = True
    for name in sorted(set(a) | set(b)):
        if name not in a or name not in b:
            where = file_b if name not in a else file_a
            print(f'  only in {Path(where).name}: {name.decode()}')
            identical = False
            continue
        for field in a[name].dtype.names:
            if parsed(a[name][field]) != parsed(b[name][field]):
                print(f'  {name.decode()}.{field}:\n      {a[name][field]!r}\n   vs {b[name][field]!r}')
                identical = False
    return identical


def regress_configs():
    configs = {'default': {}}
    for pgc in (False, True):
        for camera in ('Side', 'Bottom'):
            for kind in ('Fluorescence', 'Absorption'):
                name = f"{'pgc_' if pgc else ''}{camera.lower()}_{kind.lower()}"
                configs[name] = {
                    's03_PGC': str(pgc),
                    'Side_Imaging': str(camera == 'Side'),
                    'Bottom_Imaging': str(camera == 'Bottom'),
                    f'{kind}_Imaging': 'True',
                }
    return configs


def regress():
    OUT.mkdir(parents=True, exist_ok=True)
    old_script = OUT / '4wavemixing_original.py'
    old_source = subprocess.check_output(['git', 'show', f'{OLD_REF}:4wavemixing.py'], cwd=REPO, text=True)
    # Same RemoteBLACS import shim as the cleaned script, so it compiles on labscript >= 3.2
    old_source = old_source.replace(
        'from labscript import start, stop, add_time_marker, Trigger, RemoteBLACS',
        'from labscript import start, stop, add_time_marker, Trigger\n'
        'try:\n    from labscript import RemoteBLACS\n'
        'except ImportError:\n    from labscript.remote import RemoteBLACS')
    old_script.write_text(old_source)

    paths = [str(OLD_USERLIB), str(OLD_USERLIB / 'pythonlib'), os.environ.get('PYTHONPATH')]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, paths)))
    all_ok = True
    for name, flags in regress_configs().items():
        results = {}
        for which, script, globals_files, extra in [
            ('old', old_script, OLD_GLOBALS, {s: 'False' for s in OLD_ONLY_STAGES}),
            ('new', SCRIPT, GLOBALS, {}),
        ]:
            run_file = OUT / f'regress_{name}_{which}.h5'
            timeline = run_file.with_suffix('.json')
            cmd = [sys.executable, __file__, '_compile', str(script), str(run_file), str(timeline),
                   '--globals', *map(str, globals_files)]
            for k, v in {**extra, **flags}.items():
                cmd += ['--set', f'{k}={v}']
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if proc.returncode:
                print(f'[{name}] {which} script failed to compile:\n{proc.stderr[-2000:]}')
                all_ok = False
                break
            results[which] = run_file, json.loads(timeline.read_text())
        if len(results) != 2:
            continue

        (old_file, old_tl), (new_file, new_tl) = results['old'], results['new']
        problems = []
        if not ctdiff(old_file, new_file):
            problems.append('connection table differs (see above)')
        if shot_summary(old_file) != shot_summary(new_file):
            problems.append(f'time markers/stop time differ:\n    old {shot_summary(old_file)}\n    new {shot_summary(new_file)}')
        expected = EXPECTED_BOTTOM_DIFFS if flags.get('Bottom_Imaging') == 'True' else set()
        changed = sorted(ch for ch in set(old_tl) | set(new_tl) if old_tl.get(ch) != new_tl.get(ch))
        unexpected = [ch for ch in changed if ch not in expected]
        for ch in unexpected:
            problems.append(f'{ch} timeline differs:\n    old {old_tl.get(ch)}\n    new {new_tl.get(ch)}')
        note = f" (expected changes: {', '.join(c for c in changed if c in expected)})" if set(changed) & expected else ''
        print(f"[{name}] {'OK' if not problems else 'DIFFERENT'}{note}")
        for p in problems:
            print('  ' + p)
        all_ok &= not problems
    print('\nAll configurations match.' if all_ok else '\nDifferences found.')
    return all_ok


# ---------------------------------------------------------------------------

def parse_sets(pairs):
    overrides = {}
    for pair in pairs or []:
        name, _, expr = pair.partition('=')
        overrides[name.strip()] = expr.strip()
    return overrides


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('compile', help='compile a shot file offline')
    p.add_argument('--script', type=Path, default=SCRIPT)
    p.add_argument('--globals', type=Path, nargs='+', default=GLOBALS)
    p.add_argument('--set', action='append', metavar='NAME=EXPR', help='override a global (repeatable)')
    p.add_argument('--out', type=Path, default=OUT / 'shot.h5')

    p = sub.add_parser('ctdiff', help='compare the connection tables of two shot files')
    p.add_argument('file_a', type=Path)
    p.add_argument('file_b', type=Path)

    sub.add_parser('regress', help='compare the cleaned script against the original')

    p = sub.add_parser('_compile')  # internal: one isolated compile per process
    p.add_argument('script', type=Path)
    p.add_argument('run_file', type=Path)
    p.add_argument('timeline', type=Path)
    p.add_argument('--globals', type=Path, nargs='+', required=True)
    p.add_argument('--set', action='append')

    args = parser.parse_args()
    if args.command == 'compile':
        args.out.parent.mkdir(parents=True, exist_ok=True)
        compile_shot(args.script, args.globals, parse_sets(args.set), args.out)
        markers, stop_time = shot_summary(args.out)
        print(f'\nCompiled {args.out}  (stop time {stop_time:.4f} s)')
        for label, time in markers:
            print(f'  {time:10.4f} s  {label}')
    elif args.command == 'ctdiff':
        same = ctdiff(args.file_a, args.file_b)
        print('Connection tables identical.' if same else 'Connection tables differ.')
        sys.exit(0 if same else 1)
    elif args.command == 'regress':
        sys.exit(0 if regress() else 1)
    elif args.command == '_compile':
        compile_shot(args.script, args.globals, parse_sets(args.set), args.run_file, args.timeline)


if __name__ == '__main__':
    main()
