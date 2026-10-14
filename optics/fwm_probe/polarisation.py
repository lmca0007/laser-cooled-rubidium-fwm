"""Polarisation chain for the FWM probe, the MOT pumps and the returning FWM signal.

Fields are complex 3-vectors in the fixed table frame of geometry.py, with time
dependence exp(-i w t). The spin of a field about a fixed axis a is
    s_a = Im(E* x E) . a
so s_x = +1 is sigma+ about +x, whatever the direction of travel.

Optics:
- Waveplate: a phase delay along a fixed fast-axis vector. The same plate acts on a
  forward and a backward beam with the same physical axis.
- Mirror: ideal metal (image method), E_t -> -E_t, E_n -> +E_n. An optional extra
  phase on the p component models a real coated mirror.

Atoms (FWM signal): the Zeeman-coherence scheme of Moretti, Felinto & Tabosa,
Phys. Rev. A 79, 023825 (2009), Fig. 1. The strong writing beam W and the probe W'
have opposite circular polarisation, the read beam R counter-propagates to W with
the circular polarisation opposite to W, and the retrieved signal D has the
circular polarisation opposite to R. In a retro-reflected MOT beam, W = F and
R = B. The signal is taken as the complex conjugate of the probe field at the
cloud (a vector phase conjugate). For a circular probe this gives exactly the
Moretti polarisations (probe sigma-, signal sigma+ about +x).

Run:
    python optics/fwm_probe/polarisation.py [--mirror-retardance-deg 10] [--forward-pump sigma+]
"""
import argparse
import math

import numpy as np

import geometry as geo

X, Y, Z = np.eye(3)


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def spin(E, axis):
    E = E / np.linalg.norm(E)
    return float(np.imag(np.cross(np.conj(E), E)) @ unit(axis))


def waveplate(E, k, fast_axis, retardance_waves):
    """Delay the component along the slow axis by 2 pi * retardance."""
    k = unit(k)
    f = unit(fast_axis - (fast_axis @ k) * k)
    s = np.cross(k, f)
    return (E @ f) * f + np.exp(1j * 2 * math.pi * retardance_waves) * (E @ s) * s


def mirror(E, k_in, normal, p_phase_deg=0.0):
    """Ideal metal mirror, with an optional extra phase on the p component."""
    n = unit(normal)
    k_in = unit(k_in)
    k_out = k_in - 2 * (k_in @ n) * n
    E_out = -E + 2 * (E @ n) * n
    if p_phase_deg:
        s = unit(np.cross(k_out, n)) if np.linalg.norm(np.cross(k_out, n)) > 1e-9 else unit(np.cross(k_out, Z))
        p = np.cross(s, k_out)
        E_out = (E_out @ s) * s + np.exp(1j * math.radians(p_phase_deg)) * (E_out @ p) * p
    return E_out, k_out


def fast_axis(k, angle_deg):
    """Fast axis at angle_deg from horizontal. Zero is the beam's right-hand side and
    positive angles turn towards up: counterclockwise when you look along the beam
    (from the fibre towards the cell). The reference is k x z."""
    k = unit(k)
    h = unit(np.cross(k, Z))
    return math.cos(math.radians(angle_deg)) * h + math.sin(math.radians(angle_deg)) * Z


def describe(E, k):
    """Name the state about +x, and give the purity about the beam's own direction k."""
    E = E / np.linalg.norm(E)
    own = spin(E, k)
    about_x = spin(E, X)
    if abs(own) > 0.999:
        return f'circular, sigma{"+" if about_x > 0 else "-"} about +x (spin {own:+.4f} about k)'
    if abs(own) < 1e-3:
        return f'linear (spin {own:+.4f} about k)'
    return f'elliptical (spin {own:+.4f} about k)'


# --- The system ---------------------------------------------------------------------------

def mot_pumps(forward_sign):
    """Forward pump F through the input QWP, and B after the retro QWP + mirror."""
    kF = X
    E = unit(Y + 0 * Z)                                    # linear, horizontal, from the MOT optics
    qwp_in = fast_axis(kF, 45 if forward_sign > 0 else -45)
    F = waveplate(E, kF, qwp_in, 0.25)
    if spin(F, X) * forward_sign < 0:                    # pick the input QWP sign that gives F
        qwp_in = fast_axis(kF, -45 if forward_sign > 0 else 45)
        F = waveplate(E, kF, qwp_in, 0.25)
    qwp_retro = fast_axis(kF, 45)
    E = waveplate(F, kF, qwp_retro, 0.25)
    E, kB = mirror(E, kF, -X)
    B = waveplate(E, kB, qwp_retro, 0.25)
    return F, B, kB


def probe_arm(hwp_deg, qwp_deg, retardance_deg):
    """Probe from the PBS (transmitted = horizontal) to the cloud."""
    k = np.array([*geo.arm_direction(), 0.0])
    E0 = unit(np.cross(k, Z))                            # PBS transmits the horizontal (p) state
    E = waveplate(E0, k, fast_axis(k, hwp_deg), 0.5)
    E = waveplate(E, k, fast_axis(k, qwp_deg), 0.25)
    n = np.array([*geo.d_mirror_normal(), 0.0])
    E, k_cloud = mirror(E, k, n, retardance_deg)
    return E0, E, k_cloud


def signal_return(P, k_cloud, hwp_deg, qwp_deg, retardance_deg):
    """FWM signal = conjugate of the probe at the cloud, travelling back along -k_probe.
    The waveplates keep the physical fast axes they have for the forward probe."""
    S = np.conj(P)
    k = -k_cloud
    n = np.array([*geo.d_mirror_normal(), 0.0])
    E, k = mirror(S, k, n, retardance_deg)
    k_arm = np.array([*geo.arm_direction(), 0.0])
    E = waveplate(E, k, fast_axis(k_arm, qwp_deg), 0.25)
    E = waveplate(E, k, fast_axis(k_arm, hwp_deg), 0.5)
    return S, E, k


def solve_waveplates(target_sign, retardance_deg):
    """HWP and QWP angles that make the probe circular with spin target_sign about +x."""
    best = None
    for hwp in np.arange(-90, 90, 0.25):
        for qwp in np.arange(-90, 90, 0.25):
            _, P, _ = probe_arm(hwp, qwp, retardance_deg)
            score = spin(P, X) * target_sign  # purity about +x, max cos(theta)
            score -= 1e-6 * abs(hwp)          # among equal solutions, prefer the HWP near 0
            if best is None or score > best[0]:
                best = (score, hwp, qwp)
    return best


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--forward-pump', choices=['sigma+', 'sigma-'], default='sigma+',
                        help='circular state of the MOT beam entering face 1, about +x (check in the lab)')
    parser.add_argument('--mirror-retardance-deg', type=float, default=0.0,
                        help='extra s/p phase of the D-mirror coating at this angle of incidence')
    args = parser.parse_args()
    f_sign = 1 if args.forward_pump == 'sigma+' else -1

    print('=== MOT pumps (QWP in, QWP + mirror retro) ===')
    F, B, _ = mot_pumps(f_sign)
    print(f'  forward pump F : {describe(F, X)}')
    print(f'  backward pump B: {describe(B, -X)}  (same helicity, opposite sigma: standard MOT pair)')
    print('  -> F and B match Moretti et al. 2009: W and the read beam R have opposite circular polarisation.')

    print('\n=== Probe (must be circular, opposite to F: Moretti W\' vs W) ===')
    score, hwp, qwp = solve_waveplates(-f_sign, args.mirror_retardance_deg)
    E0, P, k_cloud = probe_arm(hwp, qwp, args.mirror_retardance_deg)
    print(f'  D-mirror s/p retardance: {args.mirror_retardance_deg:g} deg')
    print(f'  HWP fast axis {hwp:+.2f} deg, QWP fast axis {qwp:+.2f} deg '
          '(from horizontal, counterclockwise looking from the fibre towards the cell)')
    print(f'  probe at the cloud: {describe(P, k_cloud)}')

    print('\n=== FWM signal back through the probe optics ===')
    S, E_back, k_back = signal_return(P, k_cloud, hwp, qwp, args.mirror_retardance_deg)
    print(f'  signal at the cloud: {describe(S, -k_cloud)}')
    overlap = abs(np.vdot(unit(E0), E_back / np.linalg.norm(E_back))) ** 2
    print(f'  signal after the waveplates: {overlap:.4f} in the PBS transmission state')
    print('  -> the signal returns in the same linear state as the input probe (phase conjugation).')
    print('     A PBS cannot separate it from the probe, and it travels back towards the fibre.')
    print('     Use the non-polarising pick-off plate (R:T 90:10): 90 % of the signal goes to the photodiode,')
    print('     10 % of the probe power goes on to the cloud (Lezama et al. 2001 used a 50/50 splitter).')
    return hwp, qwp


if __name__ == '__main__':
    main()
