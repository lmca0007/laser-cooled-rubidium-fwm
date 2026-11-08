"""Maps of the 22 Oct 2026 2D MOT parameter sweeps, with a valid or spoiled label for each.

Reads data/2026-10-22/shots.csv and mot_properties.csv (run mot_properties.py first). Writes
scan_summary.csv and figures/scans_valid.png, figures/scans_spoiled.png, figures/scans_1d.png.

    python reports/2026-10-25_mot_characterisation/scan_maps.py

N_f is the metric the optimiser used. "Normalised" divides each shot by the check-shot level,
interpolated in time between the check shots before and after the scan. That removes a slow
drift, but not a fast one. fit_peak (tools/mot_scan.py) finds the optimum: a Gaussian + offset,
or the best point if the fit fails or peaks outside the range.
"""
import csv
import datetime

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import lab_constants as lc
from mot_scan import at_edge, fit_peak

# Verdicts. A scan is valid if the MOT was stable through it: the check shots before and after
# agree and N_f does not trend with shot order (shots run in a shuffled order).
SCANS = {
    "0020": ("coils_tn 1", "trend", "taken as the repump drift started, one shot saturated"),
    "0021": ("coils_tn 2", "trend", "N_f falls 27 % from the first to the last 10 shots (drift)"),
    "0023": ("coils_bs 1", "spoiled", "repump drift"),
    "0024": ("coils_bs 2", "spoiled", "repump drift, N_f falls 43 % through the scan"),
    "0026": ("gradient", "spoiled", "repump drift, N_f falls 55 % through the scan"),
    "0028": ("src_trap_amp 1", "spoiled", "repump drift, N_f about 9x below the stable MOT"),
    "0029": ("src_trap_amp 2", "spoiled", "repump drift, N_f about 9x below the stable MOT"),
    "0031": ("src_repump 1", "spoiled", "repump drift"),
    "0032": ("src_repump 2", "spoiled", "repump drift"),
    "0034": ("push 1", "spoiled", "repump fixed during the scan: N_f rises 9x through it"),
    "0035": ("push 2", "valid", "after the repump fix, no trend with shot order"),
    "0041": ("coils_tn", "spoiled", "before the re-lock, N_f 3x below the later checks"),
    "0043": ("coils_bs", "spoiled", "before the re-lock"),
    "0046": ("coils_bs", "valid", "after the re-lock"),
    "0048": ("gradient 1", "valid", "after the re-lock"),
    "0049": ("gradient 2", "valid", "after the re-lock"),
    "0051": ("src_trap_amp", "valid", "after the re-lock"),
    "0053": ("src_repump", "valid", "after the re-lock"),
    "0055": ("push", "valid", "after the re-lock"),
    "0038": ("z_bias", "valid", "6 s load, but the bias moves the cloud on the camera"),
}
# 0035 starts right after the repump fix, so the check before it (0033) is from the drift
NORM_REFS = {"0035": ["0036"]}
AXES = {
    "coils_tn": ["source_coil_top_current", "source_coil_north_current"],
    "coils_bs": ["source_coil_bottom_current", "source_coil_south_current"],
    "gradient": ["alpha", "rb_source_MOT_trap_frequency"],
    "src_trap_amp": ["rb_source_MOT_trap_amplitude"],
    "src_repump": ["rb_source_MOT_repump_amplitude", "rb_source_MOT_repump_frequency"],
    "push": ["rb_push_amplitude", "rb_push_frequency"],
    "z_bias": ["z_bias_MOT_load_current"],
}
LABELS = {
    "source_coil_top_current": "top coil (V)", "source_coil_north_current": "north coil (V)",
    "source_coil_bottom_current": "bottom coil (V)", "source_coil_south_current": "south coil (V)",
    "alpha": "alpha (all four coils x alpha)",
    "rb_source_MOT_trap_frequency": "2D cooling AOM (MHz)",
    "rb_source_MOT_trap_amplitude": "2D cooling AOM amplitude",
    "rb_source_MOT_repump_amplitude": "2D repump AOM amplitude",
    "rb_source_MOT_repump_frequency": "2D repump AOM (MHz)",
    "rb_push_amplitude": "push AOM amplitude", "rb_push_frequency": "push AOM (MHz)",
    "z_bias_MOT_load_current": "z bias control (V)",
}
DETUNING = {"rb_source_MOT_trap_frequency": lc.cooling_detuning, "rb_push_frequency": lc.cooling_detuning,
            "rb_source_MOT_repump_frequency": lc.repump_detuning}

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
ORANGE, CRITICAL = "#eb6834", "#d03b3b"
RAMP = ["#fcfcfb", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]


def load():
    shots = pd.read_csv(lc.DATA / "shots.csv")
    shots["run"] = shots["run"].map(lambda r: "%04d" % r)
    props = pd.read_csv(lc.HERE / "mot_properties.csv", dtype={"run": str})
    keep = ["shot", "time", "fit_integral", "saturation", "fit_inside"]
    df = shots.merge(props[keep], on="shot", how="left").copy()
    df["t"] = df["time"].map(lambda s: datetime.datetime.fromisoformat(s).timestamp() if isinstance(s, str) else np.nan)
    return df


def normalise(df, run):
    """N_f of each shot over the check-shot level, interpolated in time."""
    g = df[df.run == run]
    n_run = df.groupby("run").size()
    checks = df[df.run.map(n_run) == 1]
    checks = checks[np.isclose(checks.side_camera_exposure_time, g.side_camera_exposure_time.iloc[0])
                    & np.isclose(checks.rb_science_MOT_load_time, g.rb_science_MOT_load_time.iloc[0])]
    before = checks[checks.t < g.t.min()].tail(1)
    after = checks[checks.t > g.t.max()].head(1)
    ref = pd.concat([before, after])
    if run in NORM_REFS:
        ref = checks[checks.run.isin(NORM_REFS[run])]
    if ref.empty:
        return None, []
    level = np.interp(g.t, ref.t, ref["fluoro_frame.N"])
    return g["fluoro_frame.N"].values / level, list(ref.run)


def analyse(df):
    out = []
    for run, (name, verdict, reason) in SCANS.items():
        g = df[df.run == run].sort_values("t")
        axes = AXES[name.split()[0]]
        x = g[axes].values.astype(float)
        y = g["fluoro_frame.N"].values
        norm, refs = normalise(df, run)
        rho = spearmanr(np.arange(len(g)), g["fluoro_frame.N"])[0]
        opt, method, params, sig = fit_peak(x, y)
        row = dict(run=run, scan=name, verdict=verdict, reason=reason, n=len(g), axes=" x ".join(axes),
                   load_s=g.rb_science_MOT_load_time.iloc[0], exposure_ms=1e3 * g.side_camera_exposure_time.iloc[0],
                   order_rho=rho, n_saturated=int((g.saturation == "saturated").sum()),
                   N_f_max=y.max(), N_f_median=np.median(y), method=method, significant=sig,
                   check_runs=" ".join(refs))
        for i, a in enumerate(axes):
            lo, hi = x[:, i].min(), x[:, i].max()
            nu = len(np.unique(np.round(x[:, i], 9)))
            row["opt_%d" % i] = opt[i]
            row["range_%d" % i] = "%.4g-%.4g" % (lo, hi)
            row["edge_%d" % i] = bool(at_edge(opt[i], lo, hi, nu))
            if a in DETUNING:
                row["opt_%d_detuning_MHz" % i] = DETUNING[a](opt[i] * 1e6) / 1e6
        if norm is not None:
            nopt, nmethod, _, nsig = fit_peak(x, norm)
            row.update({"norm_opt_%d" % i: nopt[i] for i in range(len(axes))})
            row["norm_method"], row["norm_significant"] = nmethod, nsig
        out.append(dict(row=row, x=x, y=y, norm=norm, opt=opt, axes=axes, params=params))
    return out


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.tick_params(colors=INK2, labelsize=7)
    ax.xaxis.label.set_color(INK2)
    ax.yaxis.label.set_color(INK2)


def grid_mean(x, z):
    ux, uy = np.unique(np.round(x[:, 0], 9)), np.unique(np.round(x[:, 1], 9))
    m = np.full((len(uy), len(ux)), np.nan)
    for i, a in enumerate(ux):
        for j, b in enumerate(uy):
            sel = np.isclose(x[:, 0], a) & np.isclose(x[:, 1], b)
            if sel.any():
                m[j, i] = z[sel].mean()
    return ux, uy, m


def edges(u):
    d = np.diff(u) / 2 if len(u) > 1 else np.array([0.5])
    return np.concatenate([[u[0] - d[0]], u[:-1] + d, [u[-1] + d[-1]]])


def plot_maps(scans, path, title, use_norm):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", RAMP)
    n = len(scans)
    cols = 3
    rows = int(np.ceil(n / cols))
    fig, axs = plt.subplots(rows, cols, figsize=(4.3 * cols, 3.7 * rows), facecolor=SURFACE, squeeze=False)
    for ax in axs.ravel()[n:]:
        ax.set_visible(False)
    for ax, s in zip(axs.ravel(), scans):
        style(ax)
        z = s["norm"] if (use_norm and s["norm"] is not None) else s["y"] / 1e9
        ux, uy, m = grid_mean(s["x"], z)
        pc = ax.pcolormesh(edges(ux), edges(uy), m, cmap=cmap, shading="flat")
        cb = fig.colorbar(pc, ax=ax, fraction=0.05)
        cb.ax.tick_params(labelsize=7, colors=INK2)
        cb.set_label("N_f / check level" if (use_norm and s["norm"] is not None) else "N_f (10^9)", fontsize=7, color=INK2)
        ax.plot(*s["opt"], marker="+", ms=14, mew=2, color=ORANGE)
        r = s["row"]
        ax.set_xlabel(LABELS[s["axes"][0]], fontsize=8)
        ax.set_ylabel(LABELS[s["axes"][1]], fontsize=8)
        mark = "" if r["significant"] else " (fit not significant)"
        ax.set_title("%s %s: %s%s" % (r["run"], r["scan"], r["verdict"], mark), fontsize=8, loc="left", color=INK)
    fig.suptitle(title, fontsize=10, x=0.01, ha="left", color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor=SURFACE)
    plt.close(fig)


def plot_1d(scans, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, len(scans), figsize=(4.3 * len(scans), 3.5), facecolor=SURFACE, squeeze=False)
    for ax, s in zip(axs.ravel(), scans):
        style(ax)
        ax.grid(True, color=GRID, lw=0.6)
        ax.plot(s["x"][:, 0], s["y"] / 1e9, "o", color="#2a78d6", ms=6, mec=SURFACE, mew=1.2, label="N_f")
        if s["norm"] is not None:
            ax.plot(s["x"][:, 0], s["norm"] * np.median(s["y"]) / np.median(s["norm"]) / 1e9, "s", color=ORANGE, ms=4,
                    label="normalised, scaled to N_f")
        ax.axvline(s["opt"][0], color=MUTED, ls=":", lw=1)
        r = s["row"]
        ax.set_xlabel(LABELS[s["axes"][0]], fontsize=8)
        ax.set_ylabel("N_f (10^9)", fontsize=8)
        ax.set_title("%s %s: %s" % (r["run"], r["scan"], r["verdict"]), fontsize=8, loc="left", color=INK)
        ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor=SURFACE)
    plt.close(fig)


def main():
    lc.FIGURES.mkdir(exist_ok=True)
    df = load()
    scans = analyse(df)
    two_d = [s for s in scans if s["x"].shape[1] == 2]
    plot_maps([s for s in two_d if s["row"]["verdict"] == "valid"], lc.FIGURES / "scans_valid.png",
              "Valid 2D MOT scans, N_f normalised to the check shots (+ = fitted optimum)", True)
    plot_maps([s for s in two_d if s["row"]["verdict"] != "valid"], lc.FIGURES / "scans_spoiled.png",
              "Spoiled or trend-only scans, raw N_f (+ = fitted optimum). Do not use these optima.", False)
    plot_1d([s for s in scans if s["x"].shape[1] == 1], lc.FIGURES / "scans_1d.png")

    rows = [s["row"] for s in scans]
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(lc.HERE / "scan_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print("%-5s %-15s %-8s %-5s %-6s %-26s %-22s %-6s %s" % ("run", "scan", "verdict", "rho", "sig", "optimum", "normalised optimum", "edge", "detuning (MHz)"))
    for r in rows:
        n_ax = 2 if "opt_1" in r else 1
        opt = ", ".join("%.4g" % r["opt_%d" % i] for i in range(n_ax))
        nopt = ", ".join("%.4g" % r["norm_opt_%d" % i] for i in range(n_ax)) if "norm_opt_0" in r else "-"
        edge = "".join("E" if r["edge_%d" % i] else "." for i in range(n_ax))
        det = ", ".join("%+.1f" % r[k] for k in r if k.endswith("detuning_MHz"))
        print("%-5s %-15s %-8s %-+5.2f %-6s %-26s %-22s %-6s %s" % (r["run"], r["scan"], r["verdict"], r["order_rho"],
                                                                 r["significant"], opt, nopt, edge, det))


if __name__ == "__main__":
    main()
