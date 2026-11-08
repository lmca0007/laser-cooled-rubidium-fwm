"""Backward four-wave-mixing signal from the krb2 MOT, and the probe power that maximises it.

Every input comes from lab_constants.py, where each value carries its source: the thesis
[THESIS], the lab manual [LABHW], Steck [STECK], datasheets, or a value the user gave. The
default cloud is the thesis MOT. Run 0056 from this folder is the second case.

    python reports/2026-10-25_mot_characterisation/fwm_model.py
    python reports/2026-10-25_mot_characterisation/fwm_model.py --bias-G 3 --pump-aom-MHz 83.5

Geometry (user): the probe crosses the cloud at 4 deg to one horizontal MOT axis. That retro
pair is the main pump pair. The other horizontal pair and the vertical pair are also on.

Model: stationary two-level atoms in steady state, scalar fields [ABRAMS1978; YARIV1977].
    The local response to the total field E (units sqrt(I_sat)) is
        S(E) = (i - d) E / (1 + d^2 + |E|^2),        d = 2 Delta / Gamma.
    E holds all six MOT beams as three standing waves 2 a_j cos(phi_j) e^(i gamma_j), plus the
    probe a_p e^(i psi) and the conjugate a_c e^(-i psi). Averaging S e^(-/+ i psi) over the
    independent phases phi_1..3 and psi gives the parts of the polarisation that radiate along
    +k_p and -k_p. The probe enters to all orders, so the model saturates with probe power.
    This extends Abrams-Lind: it keeps the pump standing waves and the probe saturation.
        dA_p/dz =  (i alpha/2) S_p(A_p)                    forward, from A_p(z_min)
        dA_c/dz = -(i alpha/2) [S_c0 + X A_c + Y A_c*]      backward, A_c(z_max) = 0
    alpha(z) follows the Gaussian cloud along the probe. X and Y are numerical derivatives.
    The conjugate does not act back on the probe (R << 1). R = |A_c / A_p|^2 at the entry.

Pair phases. Each retro pair writes its own phase-matched conjugate, proportional to
e^(2 i gamma_j). gamma_j depends on the retro path lengths, which drift. The model evaluates
the four phase cases {1, i} x {1, i} for pairs 2 and 3. Their mean is the incoherent sum in the
weak-probe limit. The min and max bound the shot-to-shot spread. A scalar model overstates this
interference, because the pairs have different circular polarisations.

Transverse profile. Each ray through the cloud is independent (large Fresnel number). The
conjugate power is the integral of R(OD(x, y), s_p(x, y)) I_p(x, y) over the probe area.

Motion. A two-level grating lives 1/Gamma = 26 ns, much less than the motional washout time
1/(q v_s) [ZHAO2009], so the washout factor is close to 1. The probe pushes the atoms. The model
gives the longest probe pulse that keeps the Doppler shift below Gamma/4.

Zeeman. Two-level atoms show no Zeeman resonance. The script gives the design numbers for the
Delta m = 2 ground-state (Raman) resonance [LEZAMA2001; MORETTI2009]: bias field, coil
currents, the probe AOM setting and the expected width. It does not predict its height.
"""
import argparse
import json
import math

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.special import erfc

import lab_constants as lc
from lab_constants import C, mpa

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
PAIR_PHASES = [(1, 1), (1, 1j), (1j, 1), (1j, 1j)]          # pairs 2 and 3, relative to pair 1
LOADS = {"1 MOhm": 1e6, "100 kOhm": 1e5, "10 kOhm": 1e4, "1 kOhm": 1e3}
E_CHARGE = 1.602176634e-19


# --- Two-level medium --------------------------------------------------------------------

def _nodes(n_pump=6, n_probe=12):
    """Gauss-Chebyshev nodes for cos(phi) (exact for a uniform phase) and a uniform psi grid."""
    c = np.cos(np.pi * (np.arange(n_pump) + 0.5) / n_pump)
    psi = 2 * np.pi * np.arange(n_probe) / n_probe
    c1, c2, c3, ps = np.meshgrid(c, c, c, psi, indexing="ij")
    return c1.ravel(), c2.ravel(), c3.ravel(), np.exp(1j * ps.ravel())


class Medium:
    """Batched local response. d: (B,) detunings. a_pairs: beam amplitudes of the three pairs.
    phases: (B, 2) complex phase factors of pairs 2 and 3."""

    def __init__(self, d, a_pairs, phases):
        c1, c2, c3, self.ep = _nodes()
        self.epc = np.conj(self.ep)
        self.d = np.asarray(d, float)[:, None]
        ph = np.asarray(phases, complex)
        self.pump = 2 * (a_pairs[0] * c1[None] + a_pairs[1] * c2[None] * ph[:, :1]
                         + a_pairs[2] * c3[None] * ph[:, 1:2])

    def source(self, ap, ac=0.0):
        e = self.pump + np.asarray(ap)[:, None] * self.ep + np.asarray(ac).reshape(-1, 1) * self.epc
        s = (1j - self.d) * e / (1 + self.d ** 2 + e.real ** 2 + e.imag ** 2)
        return (s * self.epc).mean(1), (s * self.ep).mean(1)


def solve(medium, od, s_p, nz=60):
    """R and the probe transmission for each batch entry (Gaussian density along the probe)."""
    od = np.asarray(od, float)
    a0 = np.sqrt(np.maximum(s_p, 1e-8)).astype(complex)
    z = np.linspace(-4, 4, nz + 1)
    dz = z[1] - z[0]

    def rho(x):
        return np.exp(-x ** 2 / 2) / math.sqrt(2 * math.pi)

    ap, coef = a0.copy(), []
    for i in range(nz + 1):
        sp, sc = medium.source(ap)
        eps = 1e-4 * np.maximum(1, np.abs(ap))
        d1 = (medium.source(ap, eps)[1] - sc) / eps
        d2 = (medium.source(ap, 1j * eps)[1] - sc) / (1j * eps)
        coef.append((sc, (d1 + d2) / 2, (d1 - d2) / 2))
        if i < nz:                                      # midpoint step for the probe
            k1 = 0.5j * od * rho(z[i]) * sp
            ap = ap + dz * 0.5j * od * rho(z[i] + dz / 2) * medium.source(ap + 0.5 * dz * k1)[0]
    ac = np.zeros_like(a0)
    for i in range(nz, 0, -1):                          # trapezoid step for the conjugate

        def f(j, a):
            s0, x, y = coef[j]
            return -0.5j * od * rho(z[j]) * (s0 + x * a + y * np.conj(a))

        k1 = f(i, ac)
        ac = ac - dz * 0.5 * (k1 + f(i - 1, ac - dz * k1))
    return np.abs(ac / a0) ** 2, np.abs(ap / a0) ** 2


def solve_cases(d, a_pairs, od, s_p):
    """Run every (d, od, s_p) entry for the four pair-phase cases. Returns (4, n) arrays."""
    n = len(od)
    ph = np.repeat(PAIR_PHASES, n, axis=0)
    medium = Medium(np.tile(np.broadcast_to(d, (n,)), 4), a_pairs, ph)
    r, t = solve(medium, np.tile(od, 4), np.tile(s_p, 4))
    return r.reshape(4, n), t.reshape(4, n)


def washout(theta, temperature):
    """Mean of exp(-t^2/tau_D^2) over a grating that lives exp(-Gamma t), for both gratings."""
    out = []
    for q in (mpa.q_transmission(theta), mpa.q_reflection(theta)):
        x = mpa.tau_dephasing(q, temperature) * lc.GAMMA / 2
        out.append(math.sqrt(math.pi) * x * math.exp(x ** 2) * erfc(x) if x < 25 else 1 - 1 / (2 * x ** 2))
    return out


# --- Cloud, probe and signal -------------------------------------------------------------

def clouds():
    summary = json.load(open(lc.HERE / "mot_summary.json"))["cloud_0056"]
    out = {
        "thesis": dict(N=C["thesis_N"].value, sigma_h=C["thesis_sigma_h"].value,
                       sigma_v=C["thesis_sigma_v"].value, label="thesis MOT [THESIS Sec. 5.4.2]"),
        "0056": dict(N=summary["N_atoms"]["median"], sigma_h=summary["sigma_x_mm"] * 1e-3,
                     sigma_v=summary["sigma_y_mm"] * 1e-3, label="run 0056 (this report)"),
    }
    for c in out.values():
        # Peak column OD along a horizontal probe. The two horizontal widths are taken as equal.
        c["od0"] = lc.SIGMA_ISO * c["N"] / (2 * math.pi * c["sigma_h"] * c["sigma_v"])
        c["T"] = C["thesis_T"].value
    return out


class Table:
    """R(OD, s_p) at one detuning: mean, min and max over the pair phases, interpolated in logs."""

    OD = np.geomspace(0.01, 80, 15)
    SP = np.geomspace(1e-3, 300, 19)

    def __init__(self, d, a_pairs):
        od, sp = np.meshgrid(self.OD, self.SP, indexing="ij")
        r, t = solve_cases(d, a_pairs, od.ravel(), sp.ravel())
        shape = od.shape
        self.r = {k: f(r, 0).reshape(shape) for k, f in (("mean", np.mean), ("min", np.min), ("max", np.max))}
        self.t = t.mean(0).reshape(shape)
        grid = (np.log(self.OD), np.log(self.SP))
        self._f = {k: RegularGridInterpolator(grid, np.log(np.maximum(v, 1e-30))) for k, v in self.r.items()}
        self._t = RegularGridInterpolator(grid, self.t)

    def __call__(self, od, sp, which="mean"):
        od = np.asarray(od, float)
        lo = od < self.OD[0]                    # thin limit below the grid: R ~ OD^2
        x = np.log(np.clip(od, self.OD[0], self.OD[-1]))
        y = np.log(np.clip(sp, self.SP[0], self.SP[-1]))
        r = np.exp(self._f[which](np.stack([x, y], -1)))
        return np.where(lo, r * (np.maximum(od, 1e-12) / self.OD[0]) ** 2, r)

    def transmission(self, od, sp):
        x = np.log(np.clip(od, self.OD[0], self.OD[-1]))
        y = np.log(np.clip(sp, self.SP[0], self.SP[-1]))
        return self._t(np.stack([x, y], -1))


def conjugate_power(table, cloud, power, waist, which="mean", n=61):
    """Conjugate power (W) for a Gaussian probe of 1/e^2 radius `waist` centred on the cloud."""
    sx, sy = cloud["sigma_h"], cloud["sigma_v"]
    x = np.linspace(-4 * sx, 4 * sx, n)
    y = np.linspace(-4 * sy, 4 * sy, n)
    xx, yy = np.meshgrid(x, y, indexing="ij")
    od = cloud["od0"] * np.exp(-xx ** 2 / (2 * sx ** 2) - yy ** 2 / (2 * sy ** 2))
    intensity = 2 * power / (math.pi * waist ** 2) * np.exp(-2 * (xx ** 2 + yy ** 2) / waist ** 2)
    integrand = table(od, intensity / lc.ISAT_ISO, which) * intensity
    return float(np.trapezoid(np.trapezoid(integrand, y, axis=1), x))


def push_limit(s_p, d, s_mot):
    """Longest probe pulse before the probe's push Doppler-shifts the atoms by Gamma/4.
    The probe photon rate is its share of the two-level scattering rate [STECK]."""
    rate = lc.GAMMA / 2 * s_p / (1 + d ** 2 + s_mot + s_p)
    v_max = lc.GAMMA / 4 / lc.K_D2
    return v_max / (lc.HBAR * lc.K_D2 / lc.M_RB87 * rate)


def push_s_max(pulse, d, s_mot):
    """Largest probe peak intensity (I_sat) that push_limit allows for `pulse`."""
    rate = lc.GAMMA / 4 / lc.K_D2 / (lc.HBAR * lc.K_D2 / lc.M_RB87 * pulse)
    return rate * (1 + d ** 2 + s_mot) / (lc.GAMMA / 2 - rate) if rate < lc.GAMMA / 2 else np.inf


# --- Detection ---------------------------------------------------------------------------

def noise_budget(p_signal, p_background, load, temperature=295.0):
    """Rms noise power (W) of the DET36A/M into `load`, over its single-pole noise bandwidth."""
    resp, cap = C["det_responsivity"].value, C["det_capacitance"].value
    f3 = 1 / (2 * math.pi * load * cap)
    bw = math.pi / 2 * f3
    i_dc = resp * (p_signal + p_background) + C["det_dark"].value
    johnson = math.sqrt(4 * lc.KB * temperature / load * bw)
    shot = math.sqrt(2 * E_CHARGE * i_dc * bw)
    return dict(f3dB_Hz=f3, rise_s=2.2 * load * cap, johnson_W=johnson / resp, shot_W=shot / resp,
                total_W=math.hypot(johnson, shot) / resp, volts_per_W=resp * load)


def fluorescence_in_mode(cloud, s_mot, d, modes=16):
    """MOT fluorescence through a pinhole that passes `modes` probe modes (2x the spot radius in
    each direction). Radiance of the cloud centre times the accepted etendue modes x lambda^2."""
    column = cloud["od0"] / lc.SIGMA_ISO
    rate = lc.GAMMA / 2 * s_mot / (1 + d ** 2 + s_mot)
    return column * rate * lc.H * lc.NU / (4 * math.pi) * modes * lc.LAMBDA ** 2


# --- Zeeman design -----------------------------------------------------------------------

def zeeman_design(b_gauss, pump_aom_hz, d, s_mot, axis_deg=135.0):
    """Bias currents for a field along the probe's MOT axis, and the Delta m = 2 resonance.

    axis_deg: direction of B in the thesis X-Y plane (X along the DPT, Y to the left)."""
    a = math.radians(axis_deg)
    bx, by = b_gauss * math.cos(a), b_gauss * math.sin(a)
    split = 2 * mpa.LARMOR_HZ_PER_G * b_gauss                     # m -> m +/- 2 in F = 2
    # Ground coherence decays at about the optical pumping (scattering) rate [STECK]
    width = 2 * (lc.GAMMA / 2 * s_mot / (1 + d ** 2 + s_mot)) / (2 * math.pi)
    # |2,2> -> |3',3'> shift: (g' m' - g m) mu_B B with g' = 2/3, g = 1/2 [STECK]
    optical = (2 / 3 * 3 - 0.5 * 2) * mpa.MU_B_OVER_H * b_gauss
    return dict(B_G=b_gauss, axis_deg=axis_deg, Bx_G=bx, By_G=by,
                Ix_A=bx / C["bias_x_gauss_per_amp"].value, Iy_A=by / C["bias_y_gauss_per_amp"].value,
                raman_split_Hz=split, raman_fwhm_Hz=width, cycling_shift_Hz=optical,
                probe_aom_Hz=[pump_aom_hz + split / 2, pump_aom_hz - split / 2],
                larmor_Hz_per_G=mpa.LARMOR_HZ_PER_G)


# --- Main --------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pump-aom-MHz", type=float, default=83.5, help="science_trap_aom during FWM")
    ap.add_argument("--angle-deg", type=float, default=C["probe_angle"].value, help="probe to its MOT axis")
    ap.add_argument("--bias-G", type=float, default=3.0, help="bias field along the probe's MOT axis")
    ap.add_argument("--pulse-us", type=float, default=None,
                    help="probe pulse (default: 5 samples at the AnalogIn rate)")
    args = ap.parse_args()

    s_pair = lc.beam_intensity(C["p_horizontal"].value) / lc.ISAT_ISO
    s_vert = lc.beam_intensity(C["p_vertical"].value) / lc.ISAT_ISO
    a_pairs = np.sqrt([s_pair, s_pair, s_vert])
    s_mot = lc.mot_saturation()
    delta = lc.cooling_detuning(args.pump_aom_MHz * 1e6)
    d = 2 * delta / lc.GAMMA_HZ
    cl = clouds()
    p_max = C["probe_power_available"].value
    w_beam = C["probe_beam_diameter"].value / 2

    print("pumps: %.1f MHz detuning (d = %.2f), each horizontal beam s = %.2f, vertical s = %.2f, "
          "six-beam s = %.1f" % (delta / 1e6, d, s_pair, s_vert, s_mot))
    for k, c in cl.items():
        print("cloud %-7s N = %.2g, sigma %.2f x %.2f mm, peak OD %.1f, T %.0f uK" % (
            k, c["N"], c["sigma_h"] * 1e3, c["sigma_v"] * 1e3, c["od0"], c["T"] * 1e6))

    table = Table(d, a_pairs)
    w_t, w_r = washout(math.radians(args.angle_deg), cl["thesis"]["T"])
    wash = ((w_t + w_r) / 2) ** 2

    # Probe power and waist that maximise the conjugate, for each cloud. The probe pulse needs
    # 5 AnalogIn samples, and the probe's push must stay below Gamma/4 for that pulse.
    pulse = args.pulse_us * 1e-6 if args.pulse_us else 5 / C["daq_rate"].value
    s_max = push_s_max(pulse, d, s_mot)
    powers = np.geomspace(1e-5, p_max, 61)
    waists = np.array([0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0]) * 1e-3
    s_of = 2 * powers[None] / (math.pi * waists[:, None] ** 2) / lc.ISAT_ISO
    best = {}
    for k, c in cl.items():
        grid = np.array([[conjugate_power(table, c, p, w) for p in powers] for w in waists]) * wash
        i, j = np.unravel_index(np.argmax(grid), grid.shape)
        allowed = np.where(s_of <= s_max, grid, 0)
        # Smallest power within 10 % of the allowed maximum: more light only adds background
        ok = np.argwhere(allowed >= 0.9 * allowed.max())
        i9, j9 = min(ok, key=lambda ij: powers[ij[1]])
        best[k] = dict(grid=grid, p_opt=powers[j], w_opt=waists[i], pc_opt=grid[i, j],
                       pc_allowed=allowed.max(), p_rec=powers[j9], w_rec=waists[i9], pc_rec=grid[i9, j9])
    rec = best["thesis"]
    p_rec, w_rec = rec["p_rec"], rec["w_rec"]
    s_peak = 2 * p_rec / (math.pi * w_rec ** 2) / lc.ISAT_ISO
    tau_max = push_limit(s_peak, d, s_mot)

    print("\nwashout: transmission grating %.4f, reflection grating %.4f (T = %.0f uK, %.1f deg)" % (
        w_t, w_r, cl["thesis"]["T"] * 1e6, args.angle_deg))
    print("probe pulse %.0f us (%.0f kS/s AnalogIn): the push limit allows a peak s up to %.1f" % (
        pulse * 1e6, C["daq_rate"].value / 1e3, s_max))
    for k, b in best.items():
        print("%-7s no push limit: %.3g uW at %.3g mW, w = %.1f mm. With it: %.3g uW, and within 10 %%: "
              "%.3g uW at %.3g mW, w = %.1f mm" % (
                  k, b["pc_opt"] * 1e6, b["p_opt"] * 1e3, b["w_opt"] * 1e3, b["pc_allowed"] * 1e6,
                  b["pc_rec"] * 1e6, b["p_rec"] * 1e3, b["w_rec"] * 1e3))
    pc = {k: {w: conjugate_power(table, c, p_rec, w_rec, w) * wash for w in ("mean", "min", "max")}
          for k, c in cl.items()}
    print("recommended probe: %.2f mW, w = %.1f mm (peak s = %.1f). Telescope %.2fx from the %.1f mm beam." % (
        p_rec * 1e3, w_rec * 1e3, s_peak, w_rec / w_beam, w_beam * 1e3))
    for k in cl:
        print("  %-7s conjugate %.3g uW (pair phases: %.3g to %.3g uW), R = %.2g %%" % (
            k, pc[k]["mean"] * 1e6, pc[k]["min"] * 1e6, pc[k]["max"] * 1e6, 100 * pc[k]["mean"] / p_rec))
    print("push limit at this probe: %.0f us before a Gamma/4 Doppler shift" % (tau_max * 1e6))

    # Backgrounds and noise for the recommended probe, at PD FWM. The two-PBS pick-off sends half
    # of the returning horizontal light to PD FWM (polarisation.py). Unpolarised fluorescence
    # loses another half at PBS B.
    fluor = 0.25 * fluorescence_in_mode(cl["thesis"], s_mot, d)
    leak = 0.5 * 2 * C["ar_reflectance"].value * C["pbs_extinction"].value * p_rec    # QWP faces past PBS B
    p_pd = {w: 0.5 * pc["thesis"][w] for w in ("mean", "max")}
    loads = {}
    for name, load in LOADS.items():
        nb = noise_budget(p_pd["mean"], fluor + leak, load)
        nb["fits_pulse"] = nb["rise_s"] * 5 <= pulse
        nb["snr"] = p_pd["mean"] / nb["total_W"]
        nb["signal_V"] = p_pd["mean"] * nb["volts_per_W"]
        nb["max_V"] = p_pd["max"] * nb["volts_per_W"]
        nb["saturates"] = nb["max_V"] > C["det_bias"].value
        loads[name] = nb
    usable = [n for n in LOADS if loads[n]["fits_pulse"] and not loads[n]["saturates"]]
    load_pick = usable[0] if usable else "1 kOhm"
    print("backgrounds: fluorescence %.2g nW (mode-matched pinhole), polarisation leak %.2g nW" % (
        fluor * 1e9, leak * 1e9))
    for name, nb in loads.items():
        print("  DET36A/M %-8s f3dB %7.0f Hz, noise %.2g nW, signal %.3g V (max %.3g V), SNR %.0f%s%s" % (
            name, nb["f3dB_Hz"], nb["total_W"] * 1e9, nb["signal_V"], nb["max_V"], nb["snr"],
            "" if nb["fits_pulse"] else "  (too slow for the pulse)",
            "  (saturates)" if nb["saturates"] else ""))
    print("  use %s" % load_pick)
    slope = np.gradient(np.log(table.r["mean"][:, 0]), np.log(table.OD))
    dlnr = float(np.interp(math.log(cl["thesis"]["od0"]), np.log(table.OD), slope))
    print("shot-to-shot: dlnR/dlnOD = %.2f, so %.1f %% MOT jitter gives %.1f %% on the conjugate" % (
        dlnr, 100 * C["mot_jitter"].value, 100 * dlnr * C["mot_jitter"].value))
    t_probe = float(np.ravel(table.transmission(cl["thesis"]["od0"], s_peak))[0])
    gain = 1 + pc["thesis"]["mean"] / p_rec
    print("twin beams: probe transmission %.2f, parametric gain G = %.4f, intensity-difference "
          "noise 1/(2G-1) = %.4f of shot noise [MCCORMICK2007]" % (t_probe, gain, 1 / (2 * gain - 1)))

    # Degenerate R against the common detuning (weak probe and recommended probe)
    det = np.linspace(-30, 6, 37)
    dscan = {}
    for k, c in cl.items():
        for label, sp in (("weak", 1e-3), ("rec", s_peak)):
            r, _ = solve_cases(2 * det / lc.GAMMA_HZ * 1e6, a_pairs, np.full(det.size, c["od0"]), np.full(det.size, sp))
            dscan[(k, label)] = r
    best_det = float(det[np.argmax(dscan[("thesis", "weak")].mean(0))])
    print("best common detuning (thesis cloud, weak probe): %+.0f MHz" % best_det)

    z = zeeman_design(args.bias_G, args.pump_aom_MHz * 1e6, d, s_mot)
    quad_a = 0.9 * C["quad_amp_per_control_volt"].value
    spread = quad_a * C["quad_gauss_per_cm_per_amp"].value * 0.1 * cl["thesis"]["sigma_h"] * 1e3
    print("\nZeeman design: B = %.1f G along the probe's MOT axis: I_X = %+.3f A, I_Y = %+.3f A [THESIS 4.4.6]" % (
        z["B_G"], z["Ix_A"], z["Iy_A"]))
    print("  Delta m = 2 resonance at delta = +/-%.2f MHz -> imaging_push_aom %.2f or %.2f MHz (double pass)" % (
        z["raman_split_Hz"] / 1e6, z["probe_aom_Hz"][0] / 1e6, z["probe_aom_Hz"][1] / 1e6))
    print("  width about %.1f MHz (optical pumping by the MOT beams). |2,2>->|3',3'> shifts %.1f MHz." % (
        z["raman_fwhm_Hz"] / 1e6, z["cycling_shift_Hz"] / 1e6))
    print("  quad on: %.0f A gives a %.1f G spread over 1 sigma of the cloud. Switch it off first." % (quad_a, spread))

    # --- Figure ---------------------------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4), facecolor=SURFACE)
    for ax in axs:
        ax.set_facecolor(SURFACE)
        ax.grid(True, color=GRID, lw=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(colors=INK2, labelsize=8)
    ramp = ["#d6e5f8", "#b0cdf2", "#86b6ef", "#5f9de6", "#3a84dc", "#2a78d6", "#1a5aa8", "#104281"]
    for w, row, col in zip(waists, best["thesis"]["grid"], ramp):
        axs[0].loglog(powers * 1e3, row * 1e6, color=col, lw=1.8, label="w = %.1f mm" % (w * 1e3))
        p_lim = s_max * lc.ISAT_ISO * math.pi * w ** 2 / 2
        axs[0].plot(p_lim * 1e3, np.interp(p_lim, powers, row) * 1e6, "|", color=INK2, ms=10, mew=1.5)
    axs[0].text(0.02, 0.97, "| = push limit for a %.0f us pulse" % (pulse * 1e6), transform=axs[0].transAxes,
                fontsize=7, color=INK2, va="top")
    axs[0].plot(p_rec * 1e3, rec["pc_rec"] * 1e6, "o", color=SERIES[1], ms=7, zorder=5)
    axs[0].annotate("%.1f mW, w = %.1f mm" % (p_rec * 1e3, w_rec * 1e3), (p_rec * 1e3, rec["pc_rec"] * 1e6), xytext=(8, -14), textcoords="offset points",
                    fontsize=8, color=INK, va="top")
    axs[0].set_xlabel("Probe Power (mW)", color=INK2)
    axs[0].set_ylabel("Conjugate Power (uW)", color=INK2)
    axs[0].set_title("Signal vs Probe Power", fontsize=9, loc="left", color=INK)
    axs[0].legend(fontsize=7, frameon=False)

    sp = Table.SP
    for k, col in (("thesis", SERIES[0]), ("0056", SERIES[2])):
        lo, mid, hi = (table(np.full(sp.size, cl[k]["od0"]), sp, w) for w in ("min", "mean", "max"))
        axs[1].fill_between(sp, lo, hi, color=col, alpha=0.15, lw=0)
        axs[1].loglog(sp, mid, color=col, lw=2, label="%s, OD %.0f" % (k, cl[k]["od0"]))
        axs[1].loglog(sp, mid * sp, color=col, lw=1.2, ls="--")
    axs[1].axvline(s_peak, color=MUTED, ls=":", lw=1)
    axs[1].set_ylim(1e-6, 2)
    axs[1].set_xlabel("Probe peak intensity (I_sat)", color=INK2)
    axs[1].set_ylabel("Reflectivity", color=INK2)
    axs[1].set_title("Saturation of the probe beam", fontsize=9, loc="left", color=INK)
    axs[1].legend(fontsize=7, frameon=False, loc="lower left")

    for (k, label), col, ls in ((("thesis", "weak"), SERIES[0], "-"), (("thesis", "rec"), SERIES[0], "--"),
                                (("0056", "weak"), SERIES[2], "-"), (("0056", "rec"), SERIES[2], "--")):
        axs[2].semilogy(det, dscan[(k, label)].mean(0), color=col, ls=ls, lw=1.8,
                        label="%s, %s probe" % (k, "weak" if label == "weak" else "%.0f I_sat" % s_peak))
    axs[2].axvline(delta / 1e6, color=MUTED, ls=":", lw=1)
    axs[2].text(delta / 1e6, axs[2].get_ylim()[0] * 2, " MOT", fontsize=7, color=INK2)
    axs[2].set_xlabel("Probe Detuning (MHz)", color=INK2)
    axs[2].set_ylabel("Reflectivity", color=INK2)
    axs[2].set_title("Degenerate FWM Reflectivity vs Probe Detuning", fontsize=9, loc="left", color=INK)
    axs[2].legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(lc.FIGURES / "fwm_model.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)

    out = dict(
        inputs=dict(vars(args), pump_detuning_MHz=delta / 1e6, s_pair=s_pair, s_vertical=s_vert, s_mot=s_mot,
                    clouds={k: {kk: v for kk, v in c.items()} for k, c in cl.items()},
                    washout=[w_t, w_r], probe_available_W=p_max, probe_beam_radius_m=w_beam),
        optimum={k: dict(p_W=b["p_opt"], w_m=b["w_opt"], pc_W=b["pc_opt"], pc_allowed_W=b["pc_allowed"],
                         p_rec_W=b["p_rec"], w_rec_m=b["w_rec"], pc_rec_W=b["pc_rec"]) for k, b in best.items()},
        recommended=dict(p_W=p_rec, w_m=w_rec, s_peak=s_peak, telescope=w_rec / w_beam, pulse_s=pulse,
                         s_max=s_max, push_limit_s=tau_max, conjugate_W=pc, load=load_pick),
        backgrounds_W=dict(fluorescence=fluor, polarisation_leak=leak),
        detector=loads, mot_jitter_on_signal=dlnr * C["mot_jitter"].value,
        twin_beams=dict(probe_transmission=t_probe, gain=gain, difference_noise=1 / (2 * gain - 1)),
        best_common_detuning_MHz=best_det, zeeman=z, quad_spread_G=spread,
    )
    for b in out["optimum"].values():
        b.update({kk: float(v) for kk, v in b.items()})
    json.dump(out, open(lc.HERE / "fwm_model.json", "w"), indent=1, default=float)
    print("\nwrote figures/fwm_model.png and fwm_model.json")


if __name__ == "__main__":
    main()
