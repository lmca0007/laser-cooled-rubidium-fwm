"""Closed-loop 2D MOT optimisation sweeps, driven through runmanager's remote API.

Run on bec-krb2-control (where runmanager runs), in the py38 env, with runmanager open on
4wavemixing.py and lyse running fluoro_frame. For each scan it sets linspace globals,
engages, waits for lyse to write results/fluoro_frame N into every shot file, fits the
peak, writes the optimum back into the global and moves on to the next scan.

    python Z:\\Experiments\\krb2\\4wavemixing\\tools\\mot_scan.py --dry-run
    python Z:\\Experiments\\krb2\\4wavemixing\\tools\\mot_scan.py --only src_trap_amp
    python Z:\\Experiments\\krb2\\4wavemixing\\tools\\mot_scan.py
    python tools/mot_scan.py --replay Z:\\Experiments\\krb2\\4wavemixing\\2026\\10\\22\\0004

Scans (ranges are centred on each global's value when the scan starts):
  coils_tn      source_coil_top_current x source_coil_north_current, +-0.4 V
  coils_bs      source_coil_bottom_current x source_coil_south_current, +-0.4 V
  gradient      alpha +-0.05 (all four coils become alpha*V) x rb_source_MOT_trap_frequency +-3 MHz
  src_trap_amp  rb_source_MOT_trap_amplitude +-0.2
  src_repump    rb_source_MOT_repump_amplitude +-0.2 x rb_source_MOT_repump_frequency +-4 MHz
  push          rb_push_amplitude +-0.15 x rb_push_frequency +-3 MHz

Before the scans (skip with --skip-checks), with keep_2d_mot_on = True so the 2D MOT is never
switched off during a shot:
  stability     8 identical shots. If N_f scatters by more than 20 % or changes by more than 20 %
                over the 8 shots, a 10 s inter_shot_wait is added and it checks again; if it's
                still unstable the run stops. Keep source_mot_led_enable = False.
  load curve    rb_science_MOT_load_time 0.5-10 s, fitted with N = R tau (1 - exp(-t/tau)).
                The load time is set to tau/2 (1-6 s) for the scans, where N_f tracks the loading
                rate R, and restored at the end.

A value is only written back if the best shot reaches MIN_SIGNAL and the fitted peak
stands clear of the scatter. Otherwise the global keeps its old value. After every scan
one shot is run at the resulting values, so BLACS holds them between shots (the source
AOMs are static DDSs and keep the last shot's settings). If that check shot is below
MIN_CHECK_FRACTION of the expected N_f (from the load curve, or the best check shot so far),
the scan's values are undone and the run pauses until you fix the lasers and press Enter.
Then the scan runs again. On 22 Oct the repump drifted off over 30 min and spoiled four scans.

Needs globals alpha = 1, inter_shot_wait = 0 and keep_2d_mot_on = False in the MOT group (the
remote API can't create globals). inter_shot_wait, keep_2d_mot_on and rb_science_MOT_load_time
are restored at the end. Results (PNG per scan, summary.jsonl) go to logs\\mot_scans\\<timestamp>\\.
On Ctrl+C or an error, the globals of the scan in progress are restored; shots already
queued in BLACS keep running, so clear the BLACS queue by hand.
"""
import argparse
import datetime
import json
import sys
import time
from pathlib import Path

try:
    import labscript_utils.h5_lock  # noqa: F401  must come before h5py when labscript is installed
except ImportError:
    pass
import h5py
import numpy as np

DATA_ROOT = Path(r"Z:\Experiments\krb2\4wavemixing")
LOG_ROOT = DATA_ROOT / "logs" / "mot_scans"
METRIC = ("fluoro_frame", "N")
COILS = ["source_coil_north_current", "source_coil_south_current",
         "source_coil_top_current", "source_coil_bottom_current"]
COIL_MAX = 10.0  # V, the source coil saturation in the Magneatos globals


def axis(name, n, half, limits=(None, None)):
    """One scan axis: n points over +-half around the global's current value."""
    return dict(name=name, n=n, half=half, limits=limits)


# Ranges around values that already make a good MOT. Twice the 22 Oct ranges: the fitted
# widths there were 0.2-0.5 V on the coils and 2-4 MHz on the AOMs, and several optima sat on
# the edge. The sweeps don't touch the repump laser, so they didn't cause that run's drift.
SCANS = {
    "coils_tn": [axis("source_coil_top_current", 7, 0.4, limits=(0, COIL_MAX)),
                 axis("source_coil_north_current", 7, 0.4, limits=(0, COIL_MAX))],
    "coils_bs": [axis("source_coil_bottom_current", 7, 0.4, limits=(0, COIL_MAX)),
                 axis("source_coil_south_current", 7, 0.4, limits=(0, COIL_MAX))],
    # alpha's upper limit is set at run time so that no coil exceeds COIL_MAX. alpha moves all
    # four coils at once, so it stays narrow with finer steps (0026 fitted a width of 0.023).
    "gradient": [axis("alpha", 7, 0.05, limits=(0, None)),
                 axis("rb_source_MOT_trap_frequency", 7, 3)],
    "src_trap_amp": [axis("rb_source_MOT_trap_amplitude", 9, 0.2, limits=(0, 1))],
    "src_repump": [axis("rb_source_MOT_repump_amplitude", 5, 0.2, limits=(0, 1)),
                   axis("rb_source_MOT_repump_frequency", 9, 4)],
    "push": [axis("rb_push_amplitude", 5, 0.15, limits=(0, 1)),
             axis("rb_push_frequency", 7, 3)],
}
# A scan's best point must reach this N_f (integrated counts) before anything is applied.
# Shot 0004 (good MOT, 1 ms exposure) gave 6.9e9; run 0006 (no MOT) gave |N| < 1e6.
MIN_SIGNAL = 1e8
# Refuse a scan whose N_f correlates this strongly with shot order (sequence 0009 was -1.0)
MAX_ORDER_DRIFT = 0.8
# Stability check: identical shots must scatter less than this (std/mean)
MAX_STABILITY_CV = 0.2
# ... and change by less than this fraction of the mean over the run (linear fit). Spearman isn't
# used here: 8 shots that fall steadily by 2 % each (sequence 0017, LED off) give -0.88.
MAX_STABILITY_DRIFT = 0.2
STABILITY_SHOTS = 8
# Pause the run when a scan's check shot falls below this fraction of the expected N_f
# (on 22 Oct the first check shot of the repump drift was at 65 %, 0022)
MIN_CHECK_FRACTION = 0.7
# Load-curve check: load times scanned, and the bounds on the load time it picks
LOAD_TIMES = (0.5, 10.0, 8)
LOAD_TIME_LIMITS = (1.0, 6.0)
REQUIRED_GLOBALS = ["alpha", "inter_shot_wait", "keep_2d_mot_on"]


# ---------------------------------------------------------------------------
# Ranges and global strings
# ---------------------------------------------------------------------------

def strip_comment(raw):
    return str(raw).split("#")[0].strip()


def scan_range(ax, centre):
    """lo, hi for an axis around centre, clipped to its limits. Returns (lo, hi, clipped)."""
    lo, hi = centre - ax["half"], centre + ax["half"]
    lim_lo, lim_hi = ax["limits"]
    clipped = False
    if lim_lo is not None and lo < lim_lo:
        lo, clipped = lim_lo, True
    if lim_hi is not None and hi > lim_hi:
        hi, clipped = lim_hi, True
    return lo, hi, clipped


def linspace_str(lo, hi, n, prev):
    return "linspace(%.6g,%.6g,%d)#%s" % (lo, hi, n, prev)


# ---------------------------------------------------------------------------
# Reading shots
# ---------------------------------------------------------------------------

def read_shot(path, names):
    """(values of names, N) for a shot, or None if lyse hasn't written N yet."""
    try:
        with h5py.File(path, "r") as f:
            group = f.get("results/%s" % METRIC[0])
            if group is None or METRIC[1] not in group.attrs:
                return None
            g = f["globals"].attrs
            return [float(g[n]) for n in names], float(group.attrs[METRIC[1]])
    except (OSError, KeyError):
        return None  # still being written by BLACS or lyse


def collect(folder, names, n_expected, stall_timeout, poll=2.0):
    """Wait until every shot in folder has N. Stops when nothing new arrives for stall_timeout."""
    done = {}
    last_progress = time.time()
    while True:
        files = sorted(folder.glob("*.h5"))
        for p in files:
            if p not in done:
                r = read_shot(p, names)
                if r is not None:
                    done[p] = r
                    last_progress = time.time()
        print("\r  %d/%d shots analysed" % (len(done), n_expected), end="", flush=True)
        if len(done) >= n_expected:
            print()
            break
        if time.time() - last_progress > stall_timeout:
            print()
            if len(done) >= 0.8 * n_expected:
                print("  WARNING: no new results for %d s, fitting %d/%d shots"
                      % (stall_timeout, len(done), n_expected))
                break
            raise RuntimeError("no new results for %d s (%d/%d shots). Is lyse running fluoro_frame?"
                               % (stall_timeout, len(done), n_expected))
        time.sleep(poll)
    # In run-number order, which is the order BLACS ran them
    shots = [done[p] for p in sorted(done)]
    x = np.array([v for v, _ in shots])
    y = np.array([n for _, n in shots])
    return x, y


def order_drift(y):
    """Spearman correlation of N with shot order. Near +-1 means N tracks time, not the scan."""
    if len(y) < 5:
        return 0.0
    from scipy.stats import spearmanr
    return float(spearmanr(np.arange(len(y)), y)[0])


def wait_for_new_sequence(date_folder, before, n_expected, timeout=300, poll=1.0):
    """The sequence folder that engage() created, once all its shot files exist."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        new = [d for d in date_folder.glob("*") if d.is_dir() and d.name not in before]
        if new:
            folder = max(new, key=lambda d: d.name)
            if len(list(folder.glob("*.h5"))) >= n_expected:
                return folder
        time.sleep(poll)
    raise RuntimeError("runmanager did not compile %d shots into a new folder in %s within %d s"
                       % (n_expected, date_folder, timeout))


# ---------------------------------------------------------------------------
# Fitting
# ---------------------------------------------------------------------------

def gauss1d(x, c, a, x0, s):
    return c + a * np.exp(-(x - x0) ** 2 / (2 * s ** 2))


def gauss2d(xy, c, a, x0, y0, sx, sy):
    x, y = xy
    return c + a * np.exp(-(x - x0) ** 2 / (2 * sx ** 2) - (y - y0) ** 2 / (2 * sy ** 2))


def argmax_mean(x, y):
    """Coordinates of the scan point with the largest mean N (averaging any repeats)."""
    keys, inverse = np.unique(np.round(x, 9), axis=0, return_inverse=True)
    means = np.bincount(inverse.ravel(), weights=y) / np.bincount(inverse.ravel())
    return keys[np.argmax(means)]


def fit_peak(x, y):
    """Optimum of N over the scan points x (shape (n, d), d = 1 or 2).

    Returns (optimum, method, params, significant). Uses a Gaussian + offset fit, or the
    best point if the fit fails or puts the peak outside the scanned range. The peak must
    be at least one scan step wide, so a single bright shot can't make a narrow "fit".
    significant is True only for a Gaussian whose height is 3x the fit residual scatter and
    whose width is between one step (a peak carried by a single point) and twice the range
    (a slope with no peak: 0029 fitted a width of 10x the range).
    """
    from scipy.optimize import curve_fit

    best = argmax_mean(x, y)
    lo, hi = x.min(axis=0), x.max(axis=0)
    span = np.where(hi > lo, hi - lo, 1.0)
    step = np.array([span[i] / max(len(np.unique(np.round(x[:, i], 9))) - 1, 1) for i in range(x.shape[1])])
    c0, a0 = y.min(), y.max() - y.min()
    try:
        if x.shape[1] == 1:
            p0 = [c0, a0, best[0], max(span[0] / 4, step[0])]
            bounds = ([-np.inf, 0, -np.inf, step[0]], [np.inf, np.inf, np.inf, 10 * span[0]])
            p, _ = curve_fit(gauss1d, x[:, 0], y, p0=p0, bounds=bounds, maxfev=20000)
            opt = np.array([p[2]])
            resid = y - gauss1d(x[:, 0], *p)
        else:
            p0 = [c0, a0, best[0], best[1], max(span[0] / 4, step[0]), max(span[1] / 4, step[1])]
            bounds = ([-np.inf, 0, -np.inf, -np.inf, step[0], step[1]],
                      [np.inf, np.inf, np.inf, np.inf, 10 * span[0], 10 * span[1]])
            p, _ = curve_fit(gauss2d, (x[:, 0], x[:, 1]), y, p0=p0, bounds=bounds, maxfev=20000)
            opt = np.array([p[2], p[3]])
            resid = y - gauss2d((x[:, 0], x[:, 1]), *p)
    except (RuntimeError, ValueError) as e:
        return best, "argmax (fit failed: %s)" % e, None, False
    if np.any(opt < lo) or np.any(opt > hi):
        return best, "argmax (fit peak outside range)", p.tolist(), False
    widths = np.array(p[3:] if x.shape[1] == 1 else p[4:])
    resolved = np.all(widths > 1.05 * step) and np.all(widths < 2 * span)
    return opt, "gaussian", p.tolist(), bool(p[1] > 3 * np.std(resid) and resolved)


def at_edge(opt, lo, hi, n):
    """Whether opt is within half a step of either end of lo..hi."""
    step = (hi - lo) / max(n - 1, 1)
    return opt <= lo + step / 2 or opt >= hi - step / 2


def plot_scan(path, names, x, y, opt, params, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4.5))
    if x.shape[1] == 1:
        ax.plot(x[:, 0], y, "o")
        if params is not None:
            xs = np.linspace(x[:, 0].min(), x[:, 0].max(), 200)
            ax.plot(xs, gauss1d(xs, *params), "-")
        ax.axvline(opt[0], color="k", ls="--")
        ax.set_xlabel(names[0])
        ax.set_ylabel("N_f")
    else:
        sc = ax.scatter(x[:, 0], x[:, 1], c=y, s=80, cmap="Blues", edgecolors="k")
        fig.colorbar(sc, label="N_f")
        ax.plot(*opt, "rx", ms=14, mew=3)
        ax.set_xlabel(names[0])
        ax.set_ylabel(names[1])
    ax.set_title(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------------------
# runmanager
# ---------------------------------------------------------------------------

def connect():
    try:
        from runmanager.remote import Client
    except ImportError:
        sys.exit("runmanager.remote not found. Run this on bec-krb2-control in the py38 env.")
    client = Client()
    try:
        client.get_shuffle()
    except Exception as e:
        sys.exit("Can't reach runmanager's remote server (%s). Is runmanager open?" % e)
    return client


def current_value(client, raw_globals, name):
    """Numeric value of a global, from its raw string (comment stripped) or runmanager's evaluation."""
    if name not in raw_globals:
        raise KeyError("global %r not found in runmanager. Add it to the MOT group." % name)
    try:
        return float(strip_comment(raw_globals[name]))
    except ValueError:
        value = client.get_globals(raw=False)[name]
        if np.ndim(value):
            raise ValueError("global %r is already a scan (%r). Set it to a single value first."
                             % (name, raw_globals[name]))
        return float(value)


def run_scan(client, scan_id, axes, log_dir, index, stall_timeout, dry_run):
    raw = client.get_globals(raw=True)
    names = [a["name"] for a in axes]
    gradient = scan_id == "gradient"
    touched = names + (COILS if gradient else [])
    snapshot = {n: raw[n] for n in touched if n in raw}
    centres = {n: current_value(client, raw, n) for n in names}
    coil_v = {c: current_value(client, raw, c) for c in COILS} if gradient else {}
    if gradient:
        if abs(centres["alpha"] - 1) > 1e-9:
            raise ValueError("alpha is %g. Set it to 1 before the gradient scan." % centres["alpha"])
        axes = [dict(axes[0], limits=(0, COIL_MAX / max(coil_v.values())))] + axes[1:]

    results = []
    centre_override = {}
    for attempt in (1, 2):
        ranges, flags = [], []
        for a in axes:
            lo, hi, clipped = scan_range(a, centre_override.get(a["name"], centres[a["name"]]))
            ranges.append((lo, hi))
            if clipped:
                flags.append("%s range clipped to %.4g..%.4g" % (a["name"], lo, hi))
        new = {a["name"]: linspace_str(lo, hi, a["n"], strip_comment(snapshot[a["name"]]))
               for a, (lo, hi) in zip(axes, ranges)}
        if gradient:
            new.update({c: "alpha*%.6g#%.6g" % (v, v) for c, v in coil_v.items()})
        n_expected = int(np.prod([a["n"] for a in axes]))

        print("\n[%s] attempt %d" % (scan_id, attempt))
        for n, v in new.items():
            print("  %s = %s" % (n, v))
        client.set_globals(new, raw=True)
        try:
            if client.error_in_globals():
                raise RuntimeError("runmanager reports an error in the globals")
            n_shots = client.n_shots()
            print("  runmanager will make %d shots (expected %d)" % (n_shots, n_expected))
            if n_shots != n_expected:
                raise RuntimeError("expected %d shots but runmanager makes %d. Check the expansion "
                                   "column of %s (outer for scanned globals)" % (n_expected, n_shots, names))
            if dry_run:
                client.set_globals(snapshot, raw=True)
                print("  dry run: restored")
                return None

            client.set_shuffle(True)
            t0 = time.time()
            folder, x, y = engage_and_collect(client, names, n_expected, stall_timeout)
            print("  sequence %s" % folder)
        except BaseException:
            client.set_globals(snapshot, raw=True)
            print("\n  restored the globals of %s" % scan_id)
            raise

        opt, method, params, significant = fit_peak(x, y)
        if y.max() < MIN_SIGNAL:
            significant = False
            flags.append("best N_f %.3g is below MIN_SIGNAL %.3g: is there a MOT, and are the lasers locked?"
                         % (y.max(), MIN_SIGNAL))
        drift = order_drift(y)
        if abs(drift) >= MAX_ORDER_DRIFT:
            significant = False
            flags.append("N_f follows shot order (Spearman %.2f), not the scan: the MOT isn't recovering "
                         "between shots. Increase --wait." % drift)
        edges = [n for n, o, (lo, hi), a in zip(names, opt, ranges, axes)
                 if at_edge(o, lo, hi, a["n"]) and not _at_limit(o, a, lo, hi)]
        print("  optimum %s via %s (%s), N_f max %.3g, %.1f s/shot"
              % (dict(zip(names, np.round(opt, 4))), method, "clear peak" if significant else "NOT significant",
                 y.max(), (time.time() - t0) / len(y)))
        title = "%s attempt %d  %s\n%s" % (scan_id, attempt, folder.name,
                                         ", ".join("%s=%.4g" % (n, o) for n, o in zip(names, opt)))
        png = log_dir / ("%02d_%s_%d_%s.png" % (index, scan_id, attempt, folder.name))
        plot_scan(png, names, x, y, opt, params, title)
        results.append(dict(scan=scan_id, attempt=attempt, sequence=str(folder), axes=names,
                            ranges=ranges, optimum=opt.tolist(), method=method, params=params,
                            significant=significant, n_max=float(y.max()), n_shots=len(y),
                            edge=edges, flags=flags))
        if edges and attempt == 1 and y.max() >= MIN_SIGNAL:
            print("  optimum at the edge of %s, recentring and rescanning" % edges)
            centre_override = dict(zip(names, opt))
            continue
        if edges:
            flags.append("optimum still at the edge of %s after rescan" % edges)
        break

    # Apply the optimum only if the scan shows a clear peak, otherwise keep the old values.
    # Values are written without comments: the history is in summary.jsonl.
    if not significant:
        final = {n: strip_comment(v) for n, v in snapshot.items()}
        print("  no clear peak, keeping the previous values")
    elif gradient:
        alpha_opt, freq_opt = opt
        final = {c: "%.4g" % (alpha_opt * v) for c, v in coil_v.items()}
        final["alpha"] = "1"
        final[names[1]] = "%.4g" % freq_opt
    else:
        final = {n: "%.4g" % o for n, o in zip(names, opt)}
    client.set_globals(final, raw=True)
    print("  set: %s" % final)
    results[-1]["applied"] = final if significant else None

    # One shot at the final values, so BLACS holds them between shots instead of the last
    # shuffled scan point (the source AOMs are static DDSs)
    print("  running one shot at the final values")
    try:
        folder, _, y = engage_and_collect(client, [], 1, stall_timeout)
    except RuntimeError as e:
        print("  WARNING: check shot not analysed (%s)" % e)
        results[-1]["check_shot"] = None
    else:
        results[-1]["check_shot"] = dict(sequence=str(folder), n=float(y[0]))
        print("  check shot %s: N_f %.3g" % (folder.name, y[0]))
    return results


def engage_and_collect(client, names, n_expected, stall_timeout):
    """Engage runmanager and wait for lyse to analyse the new sequence. Returns (folder, x, y)."""
    client.set_run_shots(True)
    date_folder = DATA_ROOT / datetime.date.today().strftime(r"%Y\%m\%d")
    before = {d.name for d in date_folder.glob("*")} if date_folder.exists() else set()
    client.engage()
    folder = wait_for_new_sequence(date_folder, before, n_expected)
    x, y = collect(folder, names, n_expected, stall_timeout)
    return folder, x, y


def wait_for_recovery(client, ref, stall_timeout):
    """Pause until a check shot reaches MIN_CHECK_FRACTION of ref. Returns False to stop the run."""
    while True:
        answer = input("  Fix the lasers (repump lock?), then press Enter for a check shot, or q to stop: ")
        if answer.strip().lower() == "q":
            return False
        folder, _, y = engage_and_collect(client, [], 1, stall_timeout)
        print("  check shot %s: N_f %.3g (needs %.3g)" % (folder.name, y[0], MIN_CHECK_FRACTION * ref))
        if y[0] >= MIN_CHECK_FRACTION * ref:
            return True


def check_stability(client, wait, stall_timeout):
    """Run STABILITY_SHOTS identical shots. Returns (ok, mean, cv, drift, spearman, folder, y).

    runmanager only makes repeated shots from a list, so inter_shot_wait is set to
    linspace(wait, wait, n): n shots that differ in nothing.
    """
    client.set_globals({"inter_shot_wait": "linspace(%g,%g,%d)" % (wait, wait, STABILITY_SHOTS)}, raw=True)
    try:
        if client.n_shots() != STABILITY_SHOTS:
            raise RuntimeError("expected %d stability shots, runmanager makes %d. Check the expansion "
                               "column of inter_shot_wait (outer)" % (STABILITY_SHOTS, client.n_shots()))
        folder, _, y = engage_and_collect(client, [], STABILITY_SHOTS, stall_timeout)
    finally:
        client.set_globals({"inter_shot_wait": "%g" % wait}, raw=True)
    mean, cv, rho = float(y.mean()), float(y.std() / abs(y.mean())), order_drift(y)
    # Fitted change from the first shot to the last, as a fraction of the mean
    drift = float(np.polyfit(np.arange(len(y)), y, 1)[0] * (len(y) - 1) / abs(mean))
    ok = mean >= MIN_SIGNAL and cv <= MAX_STABILITY_CV and abs(drift) <= MAX_STABILITY_DRIFT
    return ok, mean, cv, drift, rho, folder, y


def load_rate_curve(t, a, tau):
    """MOT loading from empty: N(t) = R tau (1 - exp(-t/tau)), with a = R tau."""
    return a * (1 - np.exp(-t / tau))


def measure_load_curve(client, log_dir, stall_timeout):
    """Scan the 3D MOT load time, fit N(t), and set rb_science_MOT_load_time to tau/2.

    For t << tau, N ~ R t measures the loading rate R, which is what the 2D MOT scans should
    maximise. At t = tau/2 the MOT is ~40 % full: still close to linear in R, with enough signal.
    """
    from scipy.optimize import curve_fit

    name = "rb_science_MOT_load_time"
    old = strip_comment(client.get_globals(raw=True)[name])
    client.set_globals({name: "linspace(%g,%g,%d)" % LOAD_TIMES}, raw=True)
    try:
        if client.n_shots() != LOAD_TIMES[2]:
            raise RuntimeError("expected %d load-curve shots, runmanager makes %d"
                               % (LOAD_TIMES[2], client.n_shots()))
        client.set_shuffle(True)
        folder, x, y = engage_and_collect(client, [name], LOAD_TIMES[2], stall_timeout)
    except BaseException:
        client.set_globals({name: old}, raw=True)
        raise
    t = x[:, 0]
    result = dict(scan="load_curve", sequence=str(folder), t=t.tolist(), n=y.tolist(), previous=old)
    try:
        (a, tau), _ = curve_fit(load_rate_curve, t, y, p0=[y.max(), np.median(t)],
                                bounds=([0, 0.05], [np.inf, 100]))
    except (RuntimeError, ValueError) as e:
        a = tau = None
        print("  load-curve fit failed (%s), keeping %s = %s" % (e, name, old))
    if tau is not None and y.max() >= MIN_SIGNAL:
        load = float(np.clip(round(tau / 2, 1), *LOAD_TIME_LIMITS))
        print("  N(t) fit: tau = %.2f s, R = %.3g /s, plateau %.3g -> %s = %g s"
              % (tau, a / tau, a, name, load))
        result.update(tau=float(tau), rate=float(a / tau), plateau=float(a), applied=load)
    else:
        load = None
        print("  no usable load curve (best N_f %.3g), keeping %s = %s" % (y.max(), name, old))
    client.set_globals({name: "%g" % load if load is not None else old}, raw=True)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(t, y, "o")
    if tau is not None:
        ts = np.linspace(0, t.max(), 200)
        ax.plot(ts, load_rate_curve(ts, a, tau), "-", label="tau = %.2f s" % tau)
        ax.legend()
    ax.set_xlabel(name + " (s)")
    ax.set_ylabel("N_f")
    ax.set_title("load curve %s" % folder.name, fontsize=9)
    fig.tight_layout()
    fig.savefig(log_dir / ("00_load_curve_%s.png" % folder.name), dpi=100)
    plt.close(fig)
    return result


def _at_limit(opt, ax, lo, hi):
    """Whether an edge optimum sits on a hardware limit, where rescanning can't go further."""
    lim_lo, lim_hi = ax["limits"]
    step = (hi - lo) / max(ax["n"] - 1, 1)
    return ((lim_lo is not None and opt <= lim_lo + step / 2) or
            (lim_hi is not None and opt >= lim_hi - step / 2))


# ---------------------------------------------------------------------------
# Replay (no runmanager)
# ---------------------------------------------------------------------------

def replay(folder, axes_names, log_dir):
    files = sorted(folder.glob("*.h5"))
    if not files:
        sys.exit("no shot files in %s" % folder)
    if not axes_names:
        values = {}
        for p in files:
            with h5py.File(p, "r") as f:
                for k, v in f["globals"].attrs.items():
                    if np.ndim(v) == 0 and isinstance(v, (int, float, np.number)) and not isinstance(v, bool):
                        values.setdefault(k, set()).add(float(v))
        axes_names = sorted(k for k, s in values.items() if len(s) > 1)
        print("varying globals: %s" % axes_names)
        if len(axes_names) > 2:
            sys.exit("more than two globals vary, pick the axes with --axes")
    shots = [(p, read_shot(p, axes_names)) for p in files]
    for p, r in shots:
        print("  %s  %s" % (p.name, "no N yet" if r is None else "%s N=%.4g" % (r[0], r[1])))
    good = [r for _, r in shots if r is not None]
    if not axes_names or len(good) < 3:
        return
    x = np.array([v for v, _ in good])
    y = np.array([n for _, n in good])
    opt, method, params, significant = fit_peak(x, y)
    print("optimum %s via %s, %s, N_f max %.3g (MIN_SIGNAL %.3g), shot-order Spearman %.2f (limit %.2f)"
          % (dict(zip(axes_names, np.round(opt, 4))), method,
             "clear peak" if significant else "NOT significant", y.max(), MIN_SIGNAL,
             order_drift(y), MAX_ORDER_DRIFT))
    log_dir.mkdir(parents=True, exist_ok=True)
    png = log_dir / ("replay_%s.png" % folder.name)
    plot_scan(png, axes_names, x, y, opt, params, "replay %s" % folder)
    print("plot: %s" % png)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated scan ids (default: all, in order)")
    ap.add_argument("--dry-run", action="store_true", help="set each scan's globals, check the shot count, restore")
    ap.add_argument("--stall-timeout", type=float, default=180,
                    help="give up when no shot finishes for this many seconds (default 180)")
    ap.add_argument("--wait", type=float, default=0,
                    help="inter_shot_wait (s) during the scans: a MOT-loading hold at the end of each shot "
                         "(default 0). If the stability check fails, 10 s is added and it is checked again. "
                         "The previous value is restored afterwards.")
    ap.add_argument("--skip-checks", action="store_true",
                    help="skip the stability check and the load-curve measurement")
    ap.add_argument("--replay", type=Path, help="fit an existing sequence folder (no runmanager)")
    ap.add_argument("--axes", help="comma-separated scanned globals for --replay")
    args = ap.parse_args()
    # A shot now lasts about 5 s plus the wait, so allow for that before calling it stalled
    args.stall_timeout = max(args.stall_timeout, 3 * (args.wait + 10))

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = LOG_ROOT / stamp
    if args.replay:
        replay(args.replay, args.axes.split(",") if args.axes else None, log_dir)
        return

    ids = args.only.split(",") if args.only else list(SCANS)
    unknown = [i for i in ids if i not in SCANS]
    if unknown:
        sys.exit("unknown scan ids %s, choose from %s" % (unknown, list(SCANS)))

    client = connect()
    raw = client.get_globals(raw=True)
    missing = [g for g in REQUIRED_GLOBALS if g not in raw]
    if missing:
        sys.exit("Add these globals to the MOT group in runmanager first: %s "
                 "(alpha = 1, inter_shot_wait = 0, keep_2d_mot_on = False)" % missing)
    if strip_comment(raw.get("source_mot_led_enable", "False")) == "True":
        print("WARNING: source_mot_led_enable is True. The LED pulse each shot drains Rb from the source "
              "cell walls, and N_f collapsed 25x over 8 back-to-back shots (0015). Set it to False.")
    old_raw = {g: raw[g] for g in ("inter_shot_wait", "keep_2d_mot_on", "rb_science_MOT_load_time")}
    if args.dry_run:
        for index, scan_id in enumerate(ids, 1):
            run_scan(client, scan_id, SCANS[scan_id], log_dir, index, args.stall_timeout, True)
        print("\ndry run done")
        return

    log_dir.mkdir(parents=True, exist_ok=True)
    print("logging to %s" % log_dir)

    def log(record):
        with open(log_dir / "summary.jsonl", "a") as f:
            f.write(json.dumps(dict(record, inter_shot_wait=wait)) + "\n")

    wait = args.wait
    client.set_globals({"inter_shot_wait": "%g" % wait, "keep_2d_mot_on": "True"}, raw=True)
    print("keep_2d_mot_on = True, inter_shot_wait = %g s for the scans" % wait)
    ref = None  # N_f a check shot should reach at the scan load time
    try:
        if not args.skip_checks:
            for attempt in (1, 2):
                print("\n[stability] %d identical shots, inter_shot_wait = %g s" % (STABILITY_SHOTS, wait))
                ok, mean, cv, drift, rho, folder, y = check_stability(client, wait, args.stall_timeout)
                print("  %s: mean N_f %.3g, scatter %.0f %%, drift %+.0f %% over the run "
                      "(Spearman %.2f) -> %s"
                      % (folder.name, mean, 100 * cv, 100 * drift, rho, "stable" if ok else "NOT stable"))
                log(dict(scan="stability", sequence=str(folder), n=y.tolist(), mean=mean, cv=cv,
                         drift=drift, spearman=rho, ok=ok))
                if ok:
                    break
                if attempt == 1:
                    wait += 10
                    print("  adding a %g s wait between shots and checking again" % wait)
            else:
                sys.exit("MOT still not stable between shots. Check the lasers' locks, the push shutter "
                         "and the 2D MOT on the ThorCam before scanning.")
            # Longer shots need a longer stall timeout
            args.stall_timeout = max(args.stall_timeout, 3 * (wait + 10))

            print("\n[load curve]")
            curve = measure_load_curve(client, log_dir, max(args.stall_timeout, 3 * (wait + LOAD_TIMES[1] + 10)))
            log(curve)
            if "tau" in curve:
                ref = curve["plateau"] * (1 - np.exp(-curve["applied"] / curve["tau"]))
                print("  check shots should reach %.3g (pause below %.3g)" % (ref, MIN_CHECK_FRACTION * ref))

        for index, scan_id in enumerate(ids, 1):
            touched = [a["name"] for a in SCANS[scan_id]] + (COILS if scan_id == "gradient" else [])
            while True:
                raw = client.get_globals(raw=True)
                before = {n: raw[n] for n in touched}
                results = run_scan(client, scan_id, SCANS[scan_id], log_dir, index, args.stall_timeout, False)
                for r in results or []:
                    log(r)
                check = (results[-1].get("check_shot") or {}).get("n") if results else None
                if check is None or ref is None or check >= MIN_CHECK_FRACTION * ref:
                    if check is not None:
                        ref = check if ref is None else max(ref, check)
                    break
                # The MOT faded during the scan (22 Oct: repump drift), so its fit can't be trusted
                client.set_globals(before, raw=True)
                print("\n  PAUSED: check shot N_f %.3g is %.0f %% of the expected %.3g. Undid %s and will "
                      "run it again." % (check, 100 * check / ref, ref, scan_id))
                log(dict(scan=scan_id, event="paused", check=check, reference=ref))
                if not wait_for_recovery(client, ref, args.stall_timeout):
                    sys.exit("stopped by user")
    finally:
        client.set_globals(old_raw, raw=True)
        print("restored %s" % old_raw)
    print("\ndone")


if __name__ == "__main__":
    main()
