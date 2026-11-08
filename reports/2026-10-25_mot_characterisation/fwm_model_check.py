"""Checks of fwm_model.solve against closed-form limits from the literature, and the
non-degenerate probe of the double-Lambda diagram (probe at pump + delta).

    python reports/2026-10-25_mot_characterisation/fwm_model_check.py

1. Beer-Lambert. A weak probe with no pumps has the transmission exp(-OD / (1 + d^2)) [STECK].
   The probe step (nz = 60) holds this to 1 % up to OD' = 5. At OD' = 20 with no pumps, T is 2x
   too high. The MOT pumps saturate the cloud, so the model does not reach that case. At the
   operating points, nz = 240 changes R by 0.3 % or less.
2. Abrams-Lind, weak pumps. For |kappa| << alpha, R = |kappa sin(wL) / (w cos(wL) + alpha sin(wL))|^2
   goes to |kappa|^2 ((1 - e^(-2 alpha L)) / (2 alpha))^2 [ABRAMS1978]. The two-level chi(3) gives
   |kappa| [BOYD2008 Sec. 6.3], so R = s_F s_B (1 - e^(-OD'))^2 / (1 + d^2), OD' = OD / (1 + d^2).
   This holds for any density profile along the probe, because kappa and alpha scale together.
3. Pair phases. With weak pumps and a thin cloud, the mean R over the four phase cases is the
   sum of the R of each pair alone (incoherent sum).
4. Non-degenerate probe, delta = 0. The weak-probe solver below (respond, reflectivity) must give
   the same R and T as fwm_model.solve with the MOT pumps.
5. Non-degenerate probe, weak pumps. Third-order perturbation of the same Bloch equations gives
   S_c = -(i/4) L(-delta) [L(0) + L(delta)*] / (1 + i delta) s a_p*, with L(nu) = 1 / (1/2 - i(d/2 + nu))
   in units of Gamma. This is the weak-field case of [FU1979].

Non-degenerate solver. The pumps are at omega, the probe at omega + delta and the conjugate at
omega - delta. The probe and the conjugate are weak, so the code linearises the two-level Bloch
equations about the pump-only steady state at each pump phase, and solves them at -delta and
+delta. It keeps the pump standing waves to all orders, like fwm_model. The pump phases set the
mean. Then
    dA_p/dz =  (i alpha/2) (pp A_p + pc A_c*),     dA_c/dz = -(i alpha/2) (cc A_c + cp A_p*),
which is linear, so exp(OD M) solves it for any density profile. The probe saturation of
fwm_model is not in it. R = |A_c / A_p|^2 at the entry face.

The real double Lambda has a Raman resonance between |F=2, m=0> and |F=2, m=2>. A two-level
atom does not have it. So this R shows only what the moving grating costs at delta = 4.2 MHz.
"""
import math

import numpy as np
from scipy.linalg import expm

import lab_constants as lc
from fwm_model import Medium, PAIR_PHASES, _nodes, clouds, solve
from lab_constants import C

S_WEAK = 1e-4                  # pump saturation parameter of each beam
D = [0.0, -2 * 13.0 / 6.0666]  # on resonance, and the FWM detuning (-13 MHz)
OD = [0.1, 1.0, 5.0, 20.0]
OD_BEER = [0.1, 1.0, 5.0]
DELTA_MHZ = [0.0, 4.2, -4.2]   # probe - pump: degenerate, imaging_push_aom 85.60 and 81.40 MHz


def run(d, a_pairs, od, phases=(1, 1)):
    n = len(od)
    medium = Medium(np.full(n, d), a_pairs, np.tile(phases, (n, 1)))
    return solve(medium, np.asarray(od, float), np.full(n, 1e-8))


# --- Non-degenerate probe ----------------------------------------------------------------

def respond(d, delta, a_pairs, phases=(1, 1)):
    """Weak-probe response (pp, pc, cc, cp), averaged over the pump phases. Units of Gamma.
    S_p = pp a_p + pc a_c* radiates at omega + delta, S_c = cc a_c + cp a_p* at omega - delta."""
    c1, c2, c3, _ = _nodes(n_probe=1)
    p = 2 * (a_pairs[0] * c1 + a_pairs[1] * c2 * phases[0] + a_pairs[2] * c3 * phases[1]) / math.sqrt(2)
    g, det = 0.5, d / 2                                  # p: Rabi frequency Omega / Gamma
    w0 = -(1 + d ** 2) / (1 + d ** 2 + 2 * np.abs(p) ** 2)
    s0 = -0.5j * p * w0 / (g - 1j * det)
    zero = np.zeros_like(p)
    # Bloch equations in (sigma, sigma*, w): the Jacobian, and d(rhs)/d Omega, d(rhs)/d Omega*
    a0 = np.stack([np.stack([-(g - 1j * det) + zero, zero, -0.5j * p], -1),
                   np.stack([zero, -(g + 1j * det) + zero, 0.5j * np.conj(p)], -1),
                   np.stack([-1j * np.conj(p), 1j * p, -1 + zero], -1)], -2)
    g_om = np.stack([-0.5j * w0, zero, 1j * np.conj(s0)], -1)[..., None]
    g_omc = np.stack([zero, 0.5j * w0, -1j * s0], -1)[..., None]
    eye = np.eye(3)

    def sigma(nu, b):
        return np.linalg.solve(-1j * nu * eye - a0, b)[:, 0, 0].mean()

    return sigma(delta, g_om), sigma(delta, g_omc), sigma(-delta, g_om), sigma(-delta, g_omc)


def reflectivity(coef, od, back_action=True):
    """R and the probe transmission T for one ray of optical depth `od`."""
    pp, pc, cc, cp = coef
    m = 0.5j * np.array([[pp, pc if back_action else 0], [np.conj(cp), np.conj(cc)]])
    t = expm(od * m)                                     # (A_p, A_c*) from entry to exit
    rc = -t[1, 0] / t[1, 1]                              # A_c* at the entry, for A_c* = 0 at exit
    return abs(rc) ** 2, abs(t[0, 0] + t[0, 1] * rc) ** 2


def beam_average(coef, cloud, waist, n=41):
    """Weak-probe P_c / P_p for a Gaussian probe of 1/e^2 radius `waist` centred on the cloud."""
    od_grid = np.geomspace(1e-3, cloud["od0"], 60)
    r_grid = np.array([reflectivity(coef, od)[0] for od in od_grid])
    sx, sy = cloud["sigma_h"], cloud["sigma_v"]
    x, y = np.linspace(-4 * sx, 4 * sx, n), np.linspace(-4 * sy, 4 * sy, n)
    xx, yy = np.meshgrid(x, y, indexing="ij")
    od = cloud["od0"] * np.exp(-xx ** 2 / (2 * sx ** 2) - yy ** 2 / (2 * sy ** 2))
    weight = 2 / (math.pi * waist ** 2) * np.exp(-2 * (xx ** 2 + yy ** 2) / waist ** 2)
    r = np.exp(np.interp(np.log(od), np.log(od_grid), np.log(r_grid)))
    return float(np.trapezoid(np.trapezoid(r * weight, y, axis=1), x))


def main():
    worst = 0.0
    print("1. Beer-Lambert, no pumps")
    for d in D:
        _, t = run(d, np.zeros(3), OD_BEER)
        ref = np.exp(-np.asarray(OD_BEER) / (1 + d ** 2))
        err = np.abs(t / ref - 1)
        worst = max(worst, err.max())
        print("   d = %+.2f  T = %s  error %.1e" % (d, np.array2string(t, precision=4), err.max()))

    print("2. Abrams-Lind weak-pump limit, one pump pair")
    a = np.sqrt([S_WEAK, 0, 0])
    for d in D:
        r, _ = run(d, a, OD)
        odp = np.asarray(OD) / (1 + d ** 2)
        ref = S_WEAK ** 2 * (1 - np.exp(-odp)) ** 2 / (1 + d ** 2)
        err = np.abs(r / ref - 1)
        worst = max(worst, err.max())
        print("   d = %+.2f  R/R_AL = %s" % (d, np.array2string(r / ref, precision=4)))

    print("3. Pair phases, three pairs, OD 0.1")
    a = np.sqrt(S_WEAK * np.array([1.0, 0.7, 0.4]))
    single = sum(run(D[1], a * np.eye(3)[j], [0.1])[0][0] for j in range(3))
    mean = np.mean([run(D[1], a, [0.1], ph)[0][0] for ph in [(1, 1), (1, 1j), (1j, 1), (1j, 1j)]])
    worst = max(worst, abs(mean / single - 1))
    print("   mean of the four cases / incoherent sum = %.4f" % (mean / single))

    s_pair = lc.beam_intensity(C["p_horizontal"].value) / lc.ISAT_ISO
    s_vert = lc.beam_intensity(C["p_vertical"].value) / lc.ISAT_ISO
    a_mot = np.sqrt([s_pair, s_pair, s_vert])
    d_mot = D[1]
    print("4. Non-degenerate solver at delta = 0 against fwm_model.solve, MOT pumps, d = %+.2f" % d_mot)
    for od in (1.0, 8.8, 31.4):
        r_ref, t_ref = run(d_mot, a_mot, [od])
        r, t = reflectivity(respond(d_mot, 0.0, a_mot), od, back_action=False)
        err = max(abs(r / r_ref[0] - 1), abs(t / t_ref[0] - 1))
        worst = max(worst, err)
        print("   OD %4.1f  R %.4g / %.4g, T %.4g / %.4g  error %.1e" % (od, r, r_ref[0], t, t_ref[0], err))

    print("5. Non-degenerate solver, weak pumps, against third-order perturbation [FU1979]")
    a = np.sqrt([S_WEAK, 0, 0])
    for d in D:
        ratios = []
        for f in (0.0, 1.0, 4.2, -4.2, 20.0):
            nu = f / lc.GAMMA_HZ * 1e6

            def lor(x):
                return 1 / (0.5 - 1j * (d / 2 + x))
            ref = -0.25j * lor(-nu) * (lor(0) + np.conj(lor(nu))) / (1 + 1j * nu) * S_WEAK
            ratios.append(respond(d, nu, a)[3] / ref)
        err = max(abs(x - 1) for x in ratios)
        worst = max(worst, err)
        print("   d = %+.2f  cp/cp_ref at 0, 1, 4.2, -4.2, 20 MHz: %s" % (
            d, ", ".join("%.4f" % abs(x) for x in ratios)))
    print("largest relative error: %.1e" % worst)

    # --- R for the double-Lambda setting (two-level atoms) ---------------------------------
    w_rec = 4e-3                                          # recommended probe, fwm_model.json
    cl = clouds()
    print("\nR for a weak probe, MOT pumps at %.1f MHz (two-level atoms, no Raman resonance)" % (
        d_mot * lc.GAMMA_HZ / 2e6))
    print("   delta (MHz)  cloud    centre R: mean (min - max)      T      beam-average R (w = 4 mm)")
    for f in DELTA_MHZ:
        nu = f / lc.GAMMA_HZ * 1e6
        coefs = [respond(d_mot, nu, a_mot, ph) for ph in PAIR_PHASES]
        for k, c in cl.items():
            rt = np.array([reflectivity(cf, c["od0"]) for cf in coefs])
            avg = np.mean([beam_average(cf, c, w_rec) for cf in coefs])
            print("   %+5.1f        %-7s  %.3g (%.3g - %.3g)   %.3f  %.3g" % (
                f, k, rt[:, 0].mean(), rt[:, 0].min(), rt[:, 0].max(), rt[:, 1].mean(), avg))


if __name__ == "__main__":
    main()
