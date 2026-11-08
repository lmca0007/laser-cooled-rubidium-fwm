"""3D MOT number, size, density, temperature estimate and 2D MOT flux for 22 Oct 2026.

Reads the reduced shot data in data/2026-10-22 (no lab share). Writes:
    mot_properties.csv     one row per shot: flags, N_f, Gaussian fit, trace levels
    mot_summary.json       the numbers that README.md and fwm_model.py use
    figures/timeline.png, figures/load_curves.png, figures/cloud_0056.png

    python reports/2026-10-25_mot_characterisation/mot_properties.py

N_f is the lyse fluoro_frame result: the full-frame sum of (atoms - dark) side-camera counts.
The atom number comes from N_f through a photon budget (atom_number_budget). Each input of
that budget has a source in lab_constants.py.
"""
import csv
import datetime
import json
import math
import sys

import h5py
import numpy as np
from scipy.optimize import curve_fit
from scipy.special import erf

import lab_constants as lc
from lab_constants import C

sys.path.insert(0, str(lc.REPO / "reports" / "2026-10-22_lost_mot_and_fwm_probe"))
from mot_comparison import pd_levels  # noqa: E402
from mot_scan import load_rate_curve  # noqa: E402

SAT_BLOCK = 16300        # block mean (counts) at which all 64 raw pixels sit at the 14-bit ceiling
NEAR_SAT = 14000         # block mean above which some raw pixels can reach the ceiling
MIN_FIT_SIGNAL = 2e8     # N_f below this has no cloud to fit (0006 with no MOT gave |N_f| < 1e6)
FIT_BIN = 2              # extra binning of the 8x8 frames for the Gaussian fit
LED_ON = range(15, 17)   # 0015-0016: source LED on [mot_scan_fwm README Sec. 1]
RELOCK_AFTER = 44        # the repump was re-locked between 0044 and 0045 (user)
LOAD_CURVES = {"0019": "1.0 ms", "0040": "0.6 ms (before the re-lock)"}
MC_SAMPLES = 20000

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
CRITICAL = "#d03b3b"


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.tick_params(colors=INK2, labelsize=8)
    ax.xaxis.label.set_color(INK2)
    ax.yaxis.label.set_color(INK2)
    ax.title.set_color(INK)


# ---------------------------------------------------------------------------
# Per-shot measurements
# ---------------------------------------------------------------------------

def gauss2d(xy, off, amp, x0, y0, sx, sy):
    x, y = xy
    return off + amp * np.exp(-(x - x0) ** 2 / (2 * sx ** 2) - (y - y0) ** 2 / (2 * sy ** 2))


def fit_cloud(img, mask, shape_raw):
    """2D Gaussian + offset fit of a frame in mean counts per raw pixel, binned bin x bin.

    Saturated blocks are left out. Positions and widths come back in raw pixels. The cloud
    sits near the top edge, so the fitted integral amp 2 pi sx sy also counts the part that
    falls outside the frame, and `inside` gives the fraction of it inside.
    """
    k = C["bin"].value * FIT_BIN
    ny, nx = img.shape[0] // FIT_BIN, img.shape[1] // FIT_BIN
    z = img[:ny * FIT_BIN, :nx * FIT_BIN].reshape(ny, FIT_BIN, nx, FIT_BIN).mean(axis=(1, 3))
    m = mask[:ny * FIT_BIN, :nx * FIT_BIN].reshape(ny, FIT_BIN, nx, FIT_BIN).all(axis=(1, 3))
    yy, xx = (np.mgrid[:ny, :nx] + 0.5) * k - 0.5
    zc = np.clip(z, 0, None)
    s = zc.sum()
    x0, y0 = (zc * xx).sum() / s, (zc * yy).sum() / s
    p0 = [0, z.max(), x0, y0, 250, 250]
    bounds = ([-np.inf, 0, -2000, -2000, 2 * k, 2 * k], [np.inf, np.inf, 5000, 5000, 3000, 3000])
    p, cov = curve_fit(gauss2d, (xx[m], yy[m]), z[m], p0=p0, bounds=bounds, maxfev=5000)
    err = np.sqrt(np.diag(cov))
    h, w = shape_raw

    def frac(c, sig, n):
        return 0.5 * (erf((n - 0.5 - c) / (math.sqrt(2) * sig)) - erf((-0.5 - c) / (math.sqrt(2) * sig)))
    resid = z[m] - gauss2d((xx[m], yy[m]), *p)
    return dict(fit_off=p[0], fit_amp=p[1], fit_x=p[2], fit_y=p[3], fit_sx=abs(p[4]), fit_sy=abs(p[5]),
                fit_sx_err=err[4], fit_sy_err=err[5],
                fit_integral=p[1] * 2 * math.pi * abs(p[4] * p[5]),
                fit_inside=frac(p[2], abs(p[4]), w) * frac(p[3], abs(p[5]), h),
                fit_rms_resid=float(np.std(resid) / p[1]))


def trace_level(shot, name, t_end):
    """Median of a 1 kHz trace over the last 0.1 s of the MOT load."""
    if "traces/" + name not in shot or t_end is None:
        return np.nan
    t = shot["traces/%s/t" % name][()]
    v = shot["traces/%s/values" % name][()]
    sel = (t > t_end - 0.1) & (t < t_end)
    return float(np.median(v[sel])) if sel.any() else np.nan


def read_day():
    rows, images = [], {}
    for path in sorted(lc.DATA.glob("[0-9][0-9][0-9][0-9].h5")):
        run = path.stem
        with h5py.File(path, "r") as f:
            for name, shot in f.items():
                if "run time" not in shot.attrs:
                    continue    # compiled but never run
                gl = shot["globals"].attrs
                ff = shot.get("results/fluoro_frame")
                n_f = float(ff.attrs["N"]) if ff is not None and "N" in ff.attrs else np.nan
                row = dict(run=run, shot=name, n_in_run=len(f),
                           time=datetime.datetime.strptime(shot.attrs["run time"], "%Y%m%dT%H%M%S").isoformat(),
                           exposure_ms=float(gl["side_camera_exposure_time"]) * 1e3,
                           load_s=float(gl["rb_science_MOT_load_time"]),
                           led=bool(gl.get("source_mot_led_enable", False)),
                           z_bias=float(gl["z_bias_MOT_load_current"]),
                           keep_2d=bool(gl.get("keep_2d_mot_on", False)),
                           N_f=n_f)
                marks = {m["label"].decode(): m["time"] for m in shot["time_markers"][()]} if "time_markers" in shot else {}
                t_load = marks.get("MOT has been fully loaded")
                row.update(pd_levels(shot))
                for tr in ("Quad_voltage", "Z_Bias_voltage", "IGC_voltage"):
                    row[tr] = trace_level(shot, tr, t_load)
                g = shot.get("images/side/fluorescence_rb87")
                if g is not None and "atoms" in g and "dark" in g:
                    atoms = g["atoms"][()] / 64.0
                    dark = g["dark"][()] / 64.0
                    row["max_block"] = float(atoms.max())
                    row["n_sat_blocks"] = int((atoms >= SAT_BLOCK).sum())
                    row["saturation"] = ("saturated" if row["n_sat_blocks"] else
                                         "near" if atoms.max() >= NEAR_SAT else "ok")
                    if n_f >= MIN_FIT_SIGNAL:
                        img = atoms - dark
                        try:
                            row.update(fit_cloud(img, atoms < SAT_BLOCK, tuple(g["atoms"].attrs["raw_shape"])))
                        except (RuntimeError, ValueError) as e:
                            print("  fit failed for %s: %s" % (name, e))
                        if run == "0056":
                            images[run] = img
                rows.append(row)
    return rows, images


# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------

def depump_rate_per_s(s):
    """F=2 -> F=1 loss rate during the repump-free resonant pulse.

    Off-resonant excitation of F'=2 (266.65 MHz away) and F'=1 (423.6 MHz) at strengths 1/4 and
    1/20 relative to 7/10 for F'=3, followed by decay to F=1 with probability 1/2 and 5/6
    [STECK Table 9, Fig. 3]. Far detuned, so these excitations do not saturate.
    """
    g = lc.GAMMA_HZ
    d = (lc.S22 / lc.S23) * lc.P_F2_TO_F1 / (4 * (lc.DELTA_32 / g) ** 2) \
        + (lc.S21 / lc.S23) * lc.P_F1_TO_F1 / (4 * (lc.DELTA_31 / g) ** 2)
    return lc.GAMMA / 2 * s * d


def photons_per_atom(t_exp, s, depump_factor=1.0):
    """Photons scattered in t_exp on resonance: R t_dep (1 - exp(-t_exp / t_dep)) [STECK Eq. 48]."""
    r = lc.GAMMA / 2 * s / (1 + s)
    t_dep = 1 / (depump_factor * depump_rate_per_s(s))
    return r * t_dep * (1 - np.exp(-t_exp / t_dep)), t_dep


def atom_number_budget(t_exps, rng):
    """Monte Carlo of camera counts per atom for each exposure, with shared input samples.

    Returns {t_exp: samples} and {t_exp: central values}.
    """
    def lognorm(rel, n):
        return np.exp(rng.normal(0, rel, n))
    n = MC_SAMPLES
    s = lc.mot_saturation() * lognorm(C["imaging_power_factor"].rel_err, n) \
        * lognorm(C["p_horizontal"].rel_err, n) * lognorm(2 * C["mot_waist"].rel_err, n)
    # The depumping model leaves out polarisation, Zeeman shifts and re-absorbed light: 1.6x.
    dep = lognorm(0.5, n)
    qe = np.clip(rng.normal(C["qe_780"].value, C["qe_780"].value * C["qe_780"].rel_err, n), 0.1, 0.6)
    tr = np.clip(rng.normal(C["optics_transmission"].value, 0.05, n), 0.7, 0.99)
    col = C["collection"].value * lognorm(C["collection"].rel_err, n)
    epc = C["e_per_count"].value * lognorm(C["e_per_count"].rel_err, n)
    samples, central = {}, {}
    for t_exp in t_exps:
        samples[t_exp] = photons_per_atom(t_exp, s, dep)[0] * col * tr * qe / epc
        n0, t_dep0 = photons_per_atom(t_exp, lc.mot_saturation())
        central[t_exp] = dict(s=lc.mot_saturation(), photons=float(n0), t_depump_us=float(t_dep0 * 1e6),
                              counts_per_atom=float(n0 * C["collection"].value * lc.counts_per_photon()))
    return samples, central


def pct(a):
    lo, mid, hi = np.percentile(a, [16, 50, 84])
    return dict(median=float(mid), p16=float(lo), p84=float(hi))


def doppler_temperature(detuning_hz, s):
    """1D Doppler theory, kT = (hbar Gamma / 4)(1 + s + (2 delta / Gamma)^2) / (2 |delta| / Gamma) [LETT1989]."""
    x = 2 * abs(detuning_hz) / lc.GAMMA_HZ
    return lc.HBAR * lc.GAMMA / 4 * (1 + s + x ** 2) / x / lc.KB


def fit_load_curve(t, y):
    (a, tau), cov = curve_fit(load_rate_curve, t, y, p0=[y.max(), np.median(t)], bounds=([0, 0.05], [np.inf, 100]))
    e = np.sqrt(np.diag(cov))
    return dict(plateau=float(a), tau=float(tau), tau_err=float(e[1]), rate=float(a / tau), n=len(t))


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def plot_timeline(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4.6), facecolor=SURFACE)
    style(ax)
    t = np.array([datetime.datetime.fromisoformat(r["time"]) for r in rows])
    y = np.array([r["N_f"] for r in rows]) / 1e9
    check = np.array([r["n_in_run"] == 1 for r in rows])
    exp = np.array([r["exposure_ms"] for r in rows])
    sat = np.array([r.get("saturation") == "saturated" for r in rows])
    for e, col, lab in [(1.0, SERIES[0], "1.0 ms exposure"), (0.6, SERIES[1], "0.6 ms exposure")]:
        sel = np.isclose(exp, e)
        ax.scatter(t[sel & ~check], y[sel & ~check], s=9, color=col, alpha=0.45, lw=0, label=lab + ", scan shots")
        ax.scatter(t[sel & check], y[sel & check], s=40, color=col, edgecolor=SURFACE, lw=1.5, zorder=3,
                   label=lab + ", check shots")
    ax.scatter(t[sat], y[sat], s=70, facecolor="none", edgecolor=CRITICAL, lw=1.2, zorder=4,
               label="saturated (any 8x8 block at 16383)")
    events = [("0015", "LED on"), ("0017", "LED off"), ("0036", "repump fixed"), ("0039", "0.6 ms"),
              ("0045", "repump re-lock"), ("0057", "MOT lost")]
    for run, label in events:
        r = next((r for r in rows if r["run"] == run), None)
        if r:
            tt = datetime.datetime.fromisoformat(r["time"])
            ax.axvline(tt, color=MUTED, lw=0.8, ls=":")
            ax.text(tt, ax.get_ylim()[1] if False else 12.2, " " + label, rotation=90, va="top", fontsize=7, color=INK2)
    ax.set_ylim(-0.3, 12.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_xlabel("time on 22 Oct 2026")
    ax.set_ylabel("N_f (10^9 counts)")
    ax.set_title("Side-camera fluorescence N_f for every shot. Load time changes too: see the CSV.",
                 fontsize=9, loc="left")
    ax.legend(fontsize=7, frameon=False, loc="center right", bbox_to_anchor=(1.0, 0.55))
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_load_curves(curves, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.5, 4.4), facecolor=SURFACE)
    style(ax)
    for i, (run, c) in enumerate(curves.items()):
        col = SERIES[i]
        t, y, sat = np.array(c["t"]), np.array(c["y"]) / 1e9, np.array(c["sat"])
        ax.plot(t[~sat], y[~sat], "o", color=col, ms=6, mec=SURFACE, mew=1.2, label="%s %s" % (run, c["label"]))
        if sat.any():
            ax.plot(t[sat], y[sat], "o", color=col, ms=6, mfc="none", mew=1.2, label="%s, some blocks saturated (masked in the fit)" % run)
        f = c["fit"]
        ts = np.linspace(0, t.max(), 200)
        ax.plot(ts, load_rate_curve(ts, f["plateau"], f["tau"]) / 1e9, "-", color=col, lw=2)
        ax.annotate("tau = %.2f s" % f["tau"], (ts[-1], f["plateau"] * (1 - math.exp(-ts[-1] / f["tau"])) / 1e9),
                    xytext=(-4, 6), textcoords="offset points", ha="right", fontsize=8, color=INK2)
    ax.set_xlabel("rb_science_MOT_load_time (s)")
    ax.set_ylabel("Gaussian fit integral (10^9 counts)")
    ax.set_title("3D MOT load curves, N = R tau (1 - exp(-t/tau))", fontsize=9, loc="left")
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_cloud(img, row, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", ["#fcfcfb", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
    k = C["bin"].value
    px_mm = C["pixel_at_atoms"].value * 1e3
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8), facecolor=SURFACE, gridspec_kw=dict(width_ratios=[1.3, 1, 1]))
    ax = axs[0]
    im = ax.imshow(img, cmap=cmap, extent=[0, img.shape[1] * k * px_mm, img.shape[0] * k * px_mm, 0])
    ax.set_title("0056 atoms - dark (mean counts / pixel)", fontsize=9, loc="left", color=INK)
    ax.set_xlabel("x (mm)", color=INK2)
    ax.set_ylabel("y (mm), row 0 at the top", color=INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    fig.colorbar(im, ax=ax, fraction=0.04)
    yy, xx = (np.mgrid[:img.shape[0], :img.shape[1]] + 0.5) * k - 0.5
    model = gauss2d((xx, yy), row["fit_off"], row["fit_amp"], row["fit_x"], row["fit_y"], row["fit_sx"], row["fit_sy"])
    iy = int(np.clip(round(row["fit_y"] / k), 0, img.shape[0] - 1))
    ix = int(np.clip(round(row["fit_x"] / k), 0, img.shape[1] - 1))
    for ax, data, mod, coord, lab in [(axs[1], img[iy], model[iy], xx[0], "x"), (axs[2], img[:, ix], model[:, ix], yy[:, 0], "y")]:
        style(ax)
        ax.plot(coord * px_mm, data, ".", color=SERIES[0], ms=3, label="data (8x8 blocks)")
        ax.plot(coord * px_mm, mod, "-", color=SERIES[1], lw=2, label="2D Gaussian fit")
        ax.set_xlabel("%s (mm)" % lab)
        ax.set_title("cut along %s, fit sigma = %.2f mm" % (
            lab, row["fit_s" + lab] * px_mm), fontsize=9, loc="left")
        ax.legend(fontsize=7, frameon=False)
    axs[1].set_ylabel("counts / pixel")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------------------

def main():
    rng = np.random.default_rng(1)
    lc.FIGURES.mkdir(exist_ok=True)
    rows, images = read_day()
    by_run = {}
    for r in rows:
        by_run.setdefault(r["run"], []).append(r)
    summary = {}

    # Load curves. 0019 has 6 saturated shots of 8, too few left to fit, so the curves use the
    # Gaussian integral, whose fit leaves the saturated blocks out. N_f is fitted for comparison.
    curves = {}
    for run, label in LOAD_CURVES.items():
        rs = by_run[run]
        t = np.array([r["load_s"] for r in rs])
        y = np.array([r["N_f"] for r in rs])
        yi = np.array([r["fit_integral"] for r in rs])
        sat = np.array([r.get("saturation") == "saturated" for r in rs])
        fit_nf = fit_load_curve(t, y)
        fit_int = fit_load_curve(t, yi)
        curves[run] = dict(t=t.tolist(), y=yi.tolist(), sat=sat.tolist(), label=label, fit=fit_int)
        summary["load_curve_" + run] = dict(N_f=fit_nf, fit_integral=fit_int, n_saturated=int(sat.sum()),
                                            sigma_x_px=[r["fit_sx"] for r in rs], sigma_y_px=[r["fit_sy"] for r in rs],
                                            integral=yi.tolist(), load_s=t.tolist())
    plot_load_curves(curves, lc.FIGURES / "load_curves.png")
    tau_morning = summary["load_curve_0019"]["fit_integral"]["tau"]
    tau_evening = summary["load_curve_0040"]["fit_integral"]["tau"]
    # Cloud size against number: sigma ~ N^(1/3) at a fixed density [SESKO1991; TOWNSEND1995]
    for run in LOAD_CURVES:
        lcv = summary["load_curve_" + run]
        n_ = np.log(lcv["integral"])
        lcv["size_exponent"] = dict(x=float(np.polyfit(n_, np.log(lcv["sigma_x_px"]), 1)[0]),
                                    y=float(np.polyfit(n_, np.log(lcv["sigma_y_px"]), 1)[0]))

    # Photon budget for each exposure
    budgets, central = atom_number_budget((1.0e-3, 0.6e-3), rng)
    for t_exp, cpa in budgets.items():
        summary["budget_%.1fms" % (t_exp * 1e3)] = dict(central[t_exp], counts_per_atom_mc=pct(cpa))
    summary["budget_ratio_1.0_over_0.6"] = pct(budgets[1.0e-3] / budgets[0.6e-3])
    isat_cpp = C["isat_counts"].value / (lc.ISAT_CYCLING / (lc.H * lc.NU) * C["pixel_at_atoms"].value ** 2)
    summary["isat_crosscheck_counts_per_photon"] = {
        "datasheet_route": lc.counts_per_photon(),
        "isat_route_30us": isat_cpp / 30e-6, "isat_route_200us": isat_cpp / 200e-6}

    # Per-shot derived values
    px = C["pixel_at_atoms"].value
    for r in rows:
        cpa = budgets.get(round(r["exposure_ms"], 1) * 1e-3)
        if cpa is None or not np.isfinite(r["N_f"]):
            continue
        r["N_atoms"] = float(r["N_f"] / np.median(cpa))
        if "fit_integral" in r:
            r["N_atoms_fit"] = float(r["fit_integral"] / np.median(cpa))
            sx, sy = r["fit_sx"] * px, r["fit_sy"] * px
            r["sigma_x_mm"], r["sigma_y_mm"] = sx * 1e3, sy * 1e3
            n_tot = r["N_atoms_fit"]
            r["peak_density_cm3"] = n_tot / ((2 * math.pi) ** 1.5 * sx * sx * sy) * 1e-6   # line of sight = x
            r["peak_od_weak"] = n_tot * lc.SIGMA_ISO / (2 * math.pi * sx * sy)
            r["halo_fraction"] = r["fit_off"] * 2200 * 2752 / r["N_f"]
        r["after_relock"] = int(r["run"]) > RELOCK_AFTER
        r["quad_A"] = r["Quad_voltage"] * C["quad_amp_per_monitor_volt"].value
        r["quad_G_cm"] = r["quad_A"] * C["quad_gauss_per_cm_per_amp"].value

    # Check shots and the improvement table
    def check(run):
        rs = by_run.get(run, [])
        return rs[0] if len(rs) == 1 else None
    def rate(r, tau):
        return r.get("fit_integral", r["N_f"]) / (tau * (1 - math.exp(-r["load_s"] / tau)))
    table = []
    for run, note in [("0004", "first MOT of the day"), ("0018", "LED off, stable (median of 8)"),
                      ("0022", "after coils_tn"), ("0033", "repump drifted off"),
                      ("0036", "repump fixed by hand"), ("0037", "end of the morning scans"),
                      ("0039", "0.6 ms exposure (median of 8)"), ("0042", "evening scans, before the re-lock"),
                      ("0044", "before the re-lock"), ("0045", "after the re-lock"),
                      ("0056", "end of the evening scans")]:
        rs = by_run[run]
        r = dict(rs[len(rs) // 2]) if len(rs) > 1 else dict(rs[0])
        if len(rs) > 1:
            r["N_f"] = float(np.median([x["N_f"] for x in rs]))
            r["fit_integral"] = float(np.median([x["fit_integral"] for x in rs]))
        tau = tau_morning if r["exposure_ms"] > 0.8 else tau_evening
        table.append(dict(run=run, note=note, time=r["time"][11:16], load_s=r["load_s"], exposure_ms=r["exposure_ms"],
                          N_f=r["N_f"], fit_integral=r.get("fit_integral", np.nan), fit_inside=r.get("fit_inside", np.nan),
                          z_bias=r["z_bias"], keep_2d=r["keep_2d"], saturation=r.get("saturation"), rate_f=rate(r, tau),
                          N_atoms=r.get("fit_integral", r["N_f"]) / np.median(budgets[round(r["exposure_ms"], 1) * 1e-3])))
    summary["improvement"] = table
    ev = [check("%04d" % i) for i in range(45, 57)]
    ev = [r for r in ev if r]
    nf = np.array([r["N_f"] for r in ev])
    summary["evening_checks"] = dict(runs=[r["run"] for r in ev], N_f=nf.tolist(), mean=float(nf.mean()),
                                     cv=float(nf.std(ddof=1) / nf.mean()),
                                     change=float(nf[-1] / nf[0] - 1))

    # Reference cloud: 0056, unsaturated, 0.6 ms, 1 s load, after the re-lock
    ref = check("0056")
    cpa = budgets[0.6e-3]
    n_atoms = ref["N_f"] / cpa
    n_atoms_fit = ref["fit_integral"] / cpa
    sx, sy = ref["fit_sx"] * px, ref["fit_sy"] * px
    dens = n_atoms_fit / ((2 * math.pi) ** 1.5 * sx * sx * sy) * 1e-6
    od = n_atoms_fit * lc.SIGMA_ISO / (2 * math.pi * sx * sy)
    s_load = lc.mot_saturation()
    det = lc.cooling_detuning(float(83.5e6))
    t_dopp = doppler_temperature(det, s_load)
    v_th = math.sqrt(lc.KB * t_dopp / lc.M_RB87)
    nph = summary["budget_0.6ms"]["photons"]
    v_rec = lc.HBAR * lc.K_D2 / lc.M_RB87
    blur = v_rec * math.sqrt(2 * nph / 3) * 0.6e-3 / math.sqrt(3)
    summary["cloud_0056"] = dict(
        N_f=ref["N_f"], fit_integral=ref["fit_integral"], fit_inside=ref["fit_inside"],
        N_atoms=pct(n_atoms), N_atoms_fit=pct(n_atoms_fit),
        sigma_x_mm=sx * 1e3, sigma_y_mm=sy * 1e3, sigma_x_err_mm=ref["fit_sx_err"] * px * 1e3,
        sigma_y_err_mm=ref["fit_sy_err"] * px * 1e3, centre_px=[ref["fit_x"], ref["fit_y"]],
        fit_rms_resid=ref["fit_rms_resid"], peak_density_cm3=pct(dens), peak_od_weak=pct(od),
        load_rate_atoms_s=pct(n_atoms_fit / (tau_evening * (1 - math.exp(-ref["load_s"] / tau_evening)))),
        doppler_T_uK=t_dopp * 1e6, mot_detuning_MHz=det / 1e6, mot_s=s_load,
        thermal_expansion_mm=v_th * 0.5e-3 * 1e3, recoil_blur_mm=blur * 1e3,
        halo_fraction=ref["halo_fraction"],
        quad_monitor_V=ref["Quad_voltage"], quad_A=ref["quad_A"], quad_G_cm=ref["quad_G_cm"],
        z_bias_monitor_V=ref["Z_Bias_voltage"], igc_V=ref["IGC_voltage"], pd_load_V=ref.get("pd_load"))
    plot_cloud(images["0056"], ref, lc.FIGURES / "cloud_0056.png")
    plot_timeline(rows, lc.FIGURES / "timeline.png")

    sat_runs = sorted({r["run"] for r in rows if r.get("saturation") == "saturated"})
    near_runs = sorted({r["run"] for r in rows if r.get("saturation") == "near"})
    summary["saturated_runs"] = sat_runs
    summary["near_saturation_runs"] = near_runs
    summary["lyse_fit_0056"] = "lyse fit_frame_roi_fluoro wx, wy = 266, 358 px (sigma)"

    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(lc.HERE / "mot_properties.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    with open(lc.HERE / "mot_summary.json", "w") as f:
        json.dump(summary, f, indent=1, default=float)

    # Console report
    print("saturated runs:", " ".join(sat_runs))
    print("near-saturation runs:", " ".join(near_runs))
    for run in LOAD_CURVES:
        a, u = summary["load_curve_" + run]["N_f"], summary["load_curve_" + run]["fit_integral"]
        e = summary["load_curve_" + run]["size_exponent"]
        print("load curve %s: N_f tau %.2f s plateau %.3g | integral tau %.2f +/- %.2f s plateau %.3g rate %.3g/s | sigma ~ N^(%.2f, %.2f)"
              % (run, a["tau"], a["plateau"], u["tau"], u["tau_err"], u["plateau"], u["rate"], e["x"], e["y"]))
    for k in ("budget_1.0ms", "budget_0.6ms"):
        b = summary[k]
        print("%s: s %.1f, photons/atom %.0f, t_depump %.0f us, counts/atom %.2f (MC %.2f [%.2f, %.2f])" % (
            k, b["s"], b["photons"], b["t_depump_us"], b["counts_per_atom"], b["counts_per_atom_mc"]["median"],
            b["counts_per_atom_mc"]["p16"], b["counts_per_atom_mc"]["p84"]))
    print("1.0/0.6 ms counts per atom:", summary["budget_ratio_1.0_over_0.6"])
    print("counts per photon cross-check:", summary["isat_crosscheck_counts_per_photon"])
    print("\n%-5s %-36s %-5s %-4s %-4s %-5s %-5s %-9s %-9s %-6s %-9s %-10s %-9s" % (
        "run", "note", "time", "load", "exp", "z", "2D", "N_f", "integral", "inside", "sat", "R_f (/s)", "N atoms"))
    for t in table:
        print("%-5s %-36s %-5s %-4.0f %-4.1f %-5.2f %-5s %-9.3g %-9.3g %-6.2f %-9s %-10.3g %-9.3g" % (
            t["run"], t["note"], t["time"], t["load_s"], t["exposure_ms"], t["z_bias"], t["keep_2d"], t["N_f"],
            t["fit_integral"], t["fit_inside"], t["saturation"], t["rate_f"], t["N_atoms"]))
    e = summary["evening_checks"]
    print("\nevening checks 0045-0056: mean %.3g, cv %.1f %%, first to last %+.1f %%" % (e["mean"], 100 * e["cv"], 100 * e["change"]))
    c = summary["cloud_0056"]
    print("0056: N_f %.3g, fit integral %.3g (inside frame %.0f %%), halo %.0f %% of N_f, sigma x,y = %.2f, %.2f mm, resid %.1f %%" % (
        c["N_f"], c["fit_integral"], 100 * c["fit_inside"], 100 * c["halo_fraction"], c["sigma_x_mm"], c["sigma_y_mm"],
        100 * c["fit_rms_resid"]))
    for k in ("N_atoms", "N_atoms_fit", "peak_density_cm3", "peak_od_weak", "load_rate_atoms_s"):
        print("  %-18s %.3g [%.3g, %.3g]" % (k, c[k]["median"], c[k]["p16"], c[k]["p84"]))
    print("  Doppler T (theory) %.0f uK at %.1f MHz, s = %.1f; thermal expansion %.3f mm, recoil blur %.3f mm" % (
        c["doppler_T_uK"], c["mot_detuning_MHz"], c["mot_s"], c["thermal_expansion_mm"], c["recoil_blur_mm"]))
    print("  quad monitor %.3f V -> %.1f A -> %.1f G/cm (unconfirmed)" % (c["quad_monitor_V"], c["quad_A"], c["quad_G_cm"]))


if __name__ == "__main__":
    main()
