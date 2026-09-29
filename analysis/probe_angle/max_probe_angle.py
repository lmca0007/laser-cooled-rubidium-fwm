"""
Maximum probe angle for four-wave mixing in the laser-cooled Rb-87 cloud
=======================================================================

Question
--------
The FWM pumps are the retro-reflected MOT beams: a forward pump F and its
retro-reflection B (k_B = -k_F). A probe P crosses the cloud at an angle theta
to F. How large can theta be before thermal motion of the atoms washes out the
four-wave-mixing signal, and what stops theta being made arbitrarily small?

Physics (each claim is tagged with its source; full citations in REFERENCES)
----------------------------------------------------------------------------
1. Phase matching. With counter-propagating pumps (k_F + k_B = 0) the
   phase-conjugate signal C is emitted along k_C = -k_P for any probe angle,
   with small-signal reflectivity R = tan^2(|kappa| L) ~ |kappa L|^2 [YARIV1977].
   So phase matching does not limit the angle. A probe offset in frequency by
   delta leaves a residual mismatch dk = 2 (2 pi delta) / c along the probe,
   which scales the signal by sinc^2(dk L / 2) [BOYD2008]. This is checked below.

2. Gratings. Each pump interferes with the probe and writes a grating in the
   atomic medium. Its wavevector is the difference of the two writing beams'
   wavevectors [MORETTI2009 Eq. (1); ZHAO2009]:
       F with P:  q_T = |k_F - k_P| = 2 k sin(theta/2)   (transmission grating)
       B with P:  q_R = |k_B - k_P| = 2 k cos(theta/2)   (reflection grating)
   Either grating can scatter the other pump into C. Atomic motion shortens a
   grating's lifetime by an amount set by the pump-probe angle: the residual
   Doppler effect [DUCLOY1984].

3. Which atomic coherence stores the grating.
   (a) Optical coherences and excited-state populations decay at
       gamma_perp = Gamma/2 in the radiative limit [STECK].
   (b) Ground-state Zeeman (Raman) coherences between m_F sublevels live far
       longer. They give the narrow, magnetically sensitive FWM resonances used
       for magnetometry [CARDOSO2000; AKULSHIN2011; MORETTI2009].

4. Motional dephasing. An atom that moves ~1/q along q scrambles the grating
   phase. For a 1D Maxwell-Boltzmann distribution with v_s = sqrt(kB T / m),
   the retrieved signal decays as exp(-t^2 / tau_D^2), with
       tau_D = 1 / (q v_s)                                      [ZHAO2009]
   Zhao et al. measured tau_D = 25 +/- 1 us at theta = 3 deg and T ~ 100 uK in a
   Rb-87 MOT, and longer lifetimes as theta was reduced (reproduced in
   validate_against_zhao). Equivalently, each atom sees the two-photon (Raman)
   resonance Doppler-shifted by q.v, a residual Doppler width ~ q v. The same
   scale sets the recoil-induced resonances that appear in the probe spectrum
   of sub-Doppler-cooled atoms [GUO1992; BERMAN1999].

5. Consequence.
   - For the fast optical coherences (3a), cold atoms are effectively
     Doppler-free (k v_s << Gamma/2), so the angle hardly matters.
   - For the ground-state coherences (3b), the reflection grating (q ~ 2k)
     washes out within ~1 us, so only the transmission grating survives. Its
     lifetime sets the maximum angle:
         theta_max(tau) = 2 arcsin( 1 / (2 k v_s tau) ),
     where tau is the coherence time the measurement needs.

6. What sets tau. Motional dephasing only has to beat the other limits:
   - atoms leaving the probe beam: tau_L ~ 1.31 r0 / v_r, with
     v_r = sqrt(2 kB T / m) [ZHAO2009];
   - free fall out of the probe once the MOT is off. Gravity limits storage
     in a released MOT cloud [ZHAO2009];
   - residual magnetic-field inhomogeneity [MORETTI2009] and other intrinsic
     decoherence (enter with --tau-intrinsic-us);
   - or a target resonance linewidth for the magnetometer.

7. Minimum angle. Separating C spatially from the backward pump requires the
   beams to clear each other at the pick-off optic. Gaussian beam radii grow
   as w(z) = w0 sqrt(1 + (z/z_R)^2), with z_R = pi w0^2 / lambda [KOGELNIK1966].
   At sub-degree angles, polarisation separation (Zhao et al. used a Glan
   prism at 0.2 deg [ZHAO2009]) or heterodyne detection [AKULSHIN2011] replaces
   spatial separation.

8. Temperature. No shot has measured T yet. The Doppler limit
   T_D = 145.57 uK [STECK] is used as the reference. Polarisation-gradient
   cooling reaches well below it [LETT1988], so T_D is conservative once PGC
   is enabled. Measure T by time of flight with
   analysislib/krb2/fit_temperature.py in lyse, then pass --temperature-uK.

Beam-overlap geometry and free-fall times are derived here from elementary
geometry and kinematics; they are not taken from the literature.

Usage (from the repo root):
    python analysis/probe_angle/max_probe_angle.py
    python analysis/probe_angle/max_probe_angle.py --temperature-uK 40 --probe-waist-um 200
Figures are written to analysis/probe_angle/output/.
"""
import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import constants as sc

REPO = Path(__file__).resolve().parents[2]
DEFAULT_GLOBALS = REPO / 'globals' / 'fwm_globals.h5'
OUTPUT = Path(__file__).resolve().parent / 'output'

REFERENCES = {
    'STECK': (
        'D. A. Steck, "Rubidium 87 D Line Data", revision 2.3.4 (8 August 2025), '
        'http://steck.us/alkalidata. Table 1 (mu_B/h), Table 2 (mass), Table 3 (D2 wavelength, '
        'Gamma, Doppler temperature), hyperfine-structure figure (ground g_F = +/-1/2 -> 0.70 MHz/G; '
        'ground splitting 6.834 682 610 904 GHz), optical Bloch equations (gamma_perp = Gamma/2 + gamma_c).'),
    'ZHAO2009': (
        'B. Zhao, Y.-A. Chen, X.-H. Bao, T. Strassel, C.-S. Chuu, X.-M. Jin, J. Schmiedmayer, '
        'Z.-S. Yuan, S. Chen, J.-W. Pan, "A millisecond quantum memory for scalable quantum networks", '
        'Nature Physics 5, 95-99 (2009), doi:10.1038/nphys1153, arXiv:0807.5064. '
        'Spin-wave dephasing from atomic motion: signal ~ exp(-t^2/tau_D^2), tau_D = 1/(dk v_s), '
        'v_s = sqrt(kB T/m); tau_D = 25 +/- 1 us at theta = 3 deg, T ~ 100 uK (Rb-87 MOT), rising to 283 us '
        'as theta is reduced to 0.2 deg; transit loss tau_L ~ 1.31 r0/v_r; Glan-prism separation at 0.2 deg; '
        'free fall limits storage in a MOT.'),
    'MORETTI2009': (
        'D. Moretti, D. Felinto, J. W. R. Tabosa, "Collapses and revivals of stored orbital angular '
        'momentum of light in a cold atomic ensemble", Phys. Rev. A 79, 023825 (2009), '
        'doi:10.1103/PhysRevA.79.023825, arXiv:0901.0939. Backward FWM in a Cs MOT with writing beams at '
        '~3 deg; ground-state (Zeeman) coherence grating ~ Omega_W Omega_W\'* (Eq. 1), i.e. wavevector '
        'k_W - k_W\'; decay from residual inhomogeneous magnetic field; Larmor collapses/revivals '
        'observed for > 15 us; cloud ~2 mm.'),
    'DUCLOY1984': (
        'M. Ducloy, D. Bloch, "Polarization properties of phase-conjugate mirrors: Angular dependence and '
        'disorienting collision effects in resonant backward four-wave mixing for Doppler-broadened '
        'degenerate transitions", Phys. Rev. A 30, 3107 (1984), doi:10.1103/PhysRevA.30.3107. '
        'Residual Doppler effect: atomic motion shortens the lifetime of the optically induced gratings, '
        'set by the pump-probe angle.'),
    'YARIV1977': (
        'A. Yariv, D. M. Pepper, "Amplified reflection, phase conjugation, and oscillation in degenerate '
        'four-wave mixing", Opt. Lett. 1, 16-18 (1977), doi:10.1364/OL.1.000016. Counter-propagating pumps '
        'give a conjugate along -k_probe; reflectivity tan^2(|kappa| L).'),
    'BOYD2008': (
        'R. W. Boyd, Nonlinear Optics, 3rd ed. (Academic Press, 2008), Sec. 2.2 (coupled-wave equations): '
        'phase-mismatch factor sinc^2(dk L / 2).'),
    'KOGELNIK1966': (
        'H. Kogelnik, T. Li, "Laser beams and resonators", Appl. Opt. 5, 1550-1567 (1966), '
        'doi:10.1364/AO.5.001550. Gaussian beam radius w(z), Rayleigh range pi w0^2/lambda.'),
    'GUO1992': (
        'J. Guo, P. R. Berman, B. Dubetsky, G. Grynberg, "Recoil-induced resonances in nonlinear '
        'spectroscopy", Phys. Rev. A 46, 1426 (1992), doi:10.1103/PhysRevA.46.1426. Recoil-induced '
        'resonances in near-degenerate FWM and pump-probe spectra, observable below the Doppler limit.'),
    'BERMAN1999': (
        'P. R. Berman, "Comparison of recoil-induced resonances and the collective atomic recoil laser", '
        'Phys. Rev. A 59, 585 (1999), doi:10.1103/PhysRevA.59.585, arXiv:physics/9809002. q = k1 - k2, '
        'recoil frequency hbar q^2/2M, Raman Doppler width q P0/M with P0 = M u (u = most probable speed); '
        'probe gain for delta < 0, absorption for delta > 0.'),
    'CARDOSO2000': (
        'G. C. Cardoso, J. W. R. Tabosa, "Four-wave mixing in dressed cold cesium atoms", Opt. Commun. 185, '
        '353 (2000), doi:10.1016/S0030-4018(00)01033-6. Backward FWM phase conjugation in a MOT; narrow '
        'resonances from Raman processes among degenerate Zeeman levels.'),
    'AKULSHIN2011': (
        'A. M. Akulshin, R. J. McLean, A. I. Sidorov, P. Hannaford, "Probing degenerate two-level atomic '
        'media by coherent optical heterodyning", J. Phys. B 44, 175502 (2011), '
        'doi:10.1088/0953-4075/44/17/175502. Ground-state Zeeman coherence enables nonlinear wave mixing; '
        'heterodyne detection gives kHz-level spectral resolution.'),
    'LETT1988': (
        'P. D. Lett, R. N. Watts, C. I. Westbrook, W. D. Phillips, P. L. Gould, H. J. Metcalf, '
        '"Observation of atoms laser cooled below the Doppler limit", Phys. Rev. Lett. 61, 169 (1988), '
        'doi:10.1103/PhysRevLett.61.169.'),
}

# --- Rb-87 data [STECK] ---------------------------------------------------------------------
M_RB87 = 1.443160895e-25            # kg, Table 2
LAMBDA_D2 = 780.241209686e-9        # m (vacuum), Table 3; MOT beams = FWM pumps drive the D2 line
GAMMA_D2 = 38.117e6                 # s^-1 (= 2 pi x 6.0666 MHz), Table 3
T_DOPPLER = 145.57e-6               # K, Table 3
MU_B_OVER_H = 1.39962449361e6       # Hz/G, Table 1
G_F_GROUND = 0.5                    # |g_F| for both 5S1/2 F=1 and F=2, hyperfine-structure figure
F_HFS_GROUND = 6.834682610904e9     # Hz, hyperfine-structure figure
LARMOR_HZ_PER_G = G_F_GROUND * MU_B_OVER_H   # 0.70 MHz/G

K_D2 = 2 * math.pi / LAMBDA_D2
KB, HBAR, C, G_ACCEL = sc.k, sc.hbar, sc.c, sc.g
FWHM_PER_SIGMA = math.sqrt(8 * math.log(2))


# --- Shot context ---------------------------------------------------------------------------

@dataclass
class Sequence:
    source: str
    cmot: bool = True
    pgc: bool = False
    depumped_to_f1: bool = False
    drop_time: float = float('nan')


def load_sequence(path):
    """Evaluate the runmanager globals the way runmanager does (python expressions)."""
    try:
        import h5py
        raw = {}
        with h5py.File(path, 'r') as f:
            for group in f['globals'].values():
                raw.update({k: str(v) for k, v in group.attrs.items()})
    except (OSError, ImportError) as err:
        print(f'  (could not read {path}: {err}; using defaults)')
        return Sequence(source='defaults')

    namespace = {name: getattr(np, name) for name in ('linspace', 'arange', 'pi', 'sqrt')}
    values, pending = {}, dict(raw)
    while pending:
        progress = False
        for name, expr in list(pending.items()):
            try:
                values[name] = namespace[name] = eval(expr, {'__builtins__': {}}, namespace)
            except NameError:
                continue
            except Exception:
                values[name] = None
            del pending[name]
            progress = True
        if not progress:
            break

    pgc = bool(values.get('s03_PGC', False))
    # In 4wavemixing.py the repump is switched off repump_wait before the end of PGC,
    # optically pumping the atoms into F=1; without PGC the repump stays on (F=2).
    return Sequence(
        source=str(path),
        cmot=bool(values.get('s02_CMOT', True)),
        pgc=pgc,
        depumped_to_f1=pgc and bool(values.get('repump_wait', 0)),
        drop_time=float(values.get('drop_time', float('nan'))),
    )


# --- Physics --------------------------------------------------------------------------------

def v_1d(T):
    """1D rms thermal speed sqrt(kB T/m): the v_s of [ZHAO2009]."""
    return np.sqrt(KB * T / M_RB87)


def v_most_probable_2d(T):
    """sqrt(2 kB T/m): radial speed v_r of [ZHAO2009], most probable speed u of [BERMAN1999]."""
    return np.sqrt(2 * KB * T / M_RB87)


def q_transmission(theta, k=K_D2):
    """|k_F - k_P| for a probe at theta to the forward pump [MORETTI2009; ZHAO2009]."""
    return 2 * k * np.sin(theta / 2)


def q_reflection(theta, k=K_D2):
    """|k_B - k_P| with k_B = -k_F (retro-reflected pump)."""
    return 2 * k * np.cos(theta / 2)


def tau_dephasing(q, T):
    """1/e time of the retrieved signal, exp(-t^2/tau^2), tau = 1/(q v_s) [ZHAO2009]."""
    return 1 / (q * v_1d(T))


def raman_doppler_fwhm_hz(q, T):
    """FWHM of the Doppler-shifted two-photon detuning q.v over the 1D Maxwell-Boltzmann
    distribution (Gaussian, rms q v_s). This is the residual Doppler width [DUCLOY1984; BERMAN1999]."""
    return FWHM_PER_SIGMA * q * v_1d(T) / (2 * math.pi)


def theta_max_for_tau(tau, T, k=K_D2):
    """Largest angle whose transmission grating survives for tau (inverse of tau_dephasing).
    Returns pi (any angle) if even the maximum q = 2k survives."""
    x = 1 / (2 * k * v_1d(T) * tau)
    return 2 * math.asin(x) if x < 1 else math.pi


def theta_max_for_linewidth(fwhm_hz, T, k=K_D2):
    x = 2 * math.pi * fwhm_hz / (FWHM_PER_SIGMA * 2 * k * v_1d(T))
    return 2 * math.asin(x) if x < 1 else math.pi


def tau_transit(r0, T):
    """Atoms leaving a probe of radius r0: tau_L ~ 1.31 r0 / v_r [ZHAO2009]."""
    return 1.31 * r0 / v_most_probable_2d(T)


def t_fall(distance):
    """Free-fall time from rest through `distance` (kinematics; gravity limit noted in [ZHAO2009])."""
    return math.sqrt(2 * distance / G_ACCEL)


def gaussian_radius(w0, z, wavelength=LAMBDA_D2):
    """w(z) = w0 sqrt(1 + (z/z_R)^2), z_R = pi w0^2 / lambda [KOGELNIK1966]."""
    z_r = math.pi * w0 ** 2 / wavelength
    return w0 * math.sqrt(1 + (z / z_r) ** 2)


def theta_min_separation(w_pump, w_probe, distance, clearance):
    """Smallest angle at which the conjugate (along -k_P) clears the backward pump
    (along -k_F) at a pick-off optic `distance` from the cloud, with both beam radii
    grown per [KOGELNIK1966] and `clearance` beam radii of margin (geometry)."""
    spread = clearance * (gaussian_radius(w_pump, distance) + gaussian_radius(w_probe, distance))
    return math.atan(spread / distance)


def interaction_length(theta, cloud_diameter, w_pump):
    """Probe path length inside both the cloud and the forward pump (geometry: a probe
    crossing a pump of radius w at theta overlaps it over ~2w/sin(theta))."""
    if theta == 0:
        return cloud_diameter
    return min(cloud_diameter, 2 * w_pump / math.sin(theta))


def phase_mismatch_factor(delta_hz, length):
    """sinc^2(dk L/2) with dk = 2 (2 pi delta)/c for a probe offset by delta [BOYD2008; YARIV1977]."""
    x = 2 * (2 * math.pi * delta_hz) / C * length / 2
    return (math.sin(x) / x) ** 2 if x else 1.0


def recoil_frequency_hz(q):
    """hbar q^2 / 2M, the recoil frequency of [BERMAN1999], in Hz."""
    return HBAR * q ** 2 / (2 * M_RB87) / (2 * math.pi)


# --- Checks ---------------------------------------------------------------------------------

def monte_carlo_check(T=100e-6, theta=math.radians(3), n=400_000, seed=1):
    """Numerically average exp(i q v t) over Maxwell-Boltzmann velocities and check the
    retrieved signal |<.>|^2 falls to 1/e at tau_D (confirms the Gaussian form used)."""
    rng = np.random.default_rng(seed)
    v = rng.normal(0, v_1d(T), n)
    q = q_transmission(theta)
    tau = tau_dephasing(q, T)
    return abs(np.mean(np.exp(1j * q * v * tau))) ** 2


def validate_against_zhao():
    """[ZHAO2009]: theta = 3 deg, v_s = 0.1 m/s (T ~ 100 uK) -> measured 25 +/- 1 us."""
    theta = math.radians(3)
    q = q_transmission(theta)
    v_s = 0.1
    return {
        'spin-wave wavelength (um)': 2 * math.pi / q * 1e6,
        'predicted tau_D (us)': 1 / (q * v_s) * 1e6,
        'measured tau_D (us)': '25 +/- 1',
    }


# --- Report ---------------------------------------------------------------------------------

def deg(rad):
    return math.degrees(rad)


def fmt_angle(rad):
    if rad >= math.pi - 1e-12:
        return 'any'
    d = deg(rad)
    return f'{d:.3g} deg ({rad * 1e3:.3g} mrad)'


def fmt_time(t):
    return f'{t * 1e6:.3g} us' if t < 1e-3 else f'{t * 1e3:.3g} ms'


def fmt_hz(f):
    for unit, scale in (('GHz', 1e9), ('MHz', 1e6), ('kHz', 1e3)):
        if f >= scale:
            return f'{f / scale:.3g} {unit}'
    return f'{f:.3g} Hz'


def report(args, seq):
    T = args.temperature_uK * 1e-6
    r_probe = args.probe_waist_um * 1e-6
    w_pump = args.pump_waist_mm * 1e-3
    cloud = args.cloud_diameter_mm * 1e-3
    temps = sorted({args.temperature_uK, *args.compare_temperatures_uK})

    print('\n=== Shot sequence (from the runmanager globals) ===')
    print(f'  source: {seq.source}')
    stage = 'CMOT -> PGC' if seq.pgc else ('CMOT, no PGC' if seq.cmot else 'MOT, no CMOT/PGC')
    print(f'  cooling: {stage}; atoms in {"F=1 (depumped)" if seq.depumped_to_f1 else "F=2 (repump on)"}; '
          f'|g_F| = 1/2 either way -> Larmor {LARMOR_HZ_PER_G / 1e6:.3f} MHz/G [STECK]')
    if not seq.pgc:
        print('  PGC is off, so the cloud is at MOT/CMOT temperature. T_D is the reference, not a measurement.')
    else:
        print('  PGC is on, so the cloud should be below T_D [LETT1988]. T_D is conservative here.')

    print('\n=== Inputs (not in the shot files: measure these) ===')
    print(f'  temperature          {args.temperature_uK:g} uK   (default = Doppler limit T_D [STECK])')
    print(f'  probe waist r0       {args.probe_waist_um:g} um   (default ~ detection-mode waist of [ZHAO2009])')
    print(f'  pump (MOT beam) w    {args.pump_waist_mm:g} mm   (ASSUMED - measure the MOT beam)')
    print(f'  cloud diameter       {args.cloud_diameter_mm:g} mm   (default ~ MOT cloud of [MORETTI2009]; '
          'measure with the side camera)')
    print(f'  pick-off distance    {args.pickoff_distance_m:g} m    (ASSUMED - first optic that must separate C)')

    print('\n=== Validation ===')
    for key, val in validate_against_zhao().items():
        print(f'  [ZHAO2009] {key:28s} {val if isinstance(val, str) else f"{val:.3g}"}')
    mc = monte_carlo_check()
    print(f'  Monte-Carlo |<exp(i q v tau_D)>|^2 = {mc:.4f} (expect 1/e = {math.exp(-1):.4f})')

    print('\n=== 1. Phase matching [YARIV1977; BOYD2008] ===')
    print('  Counter-propagating pumps: k_C = -k_P for every theta, so there is no angle limit from phase matching.')
    for label, delta in (('Larmor offset at 1 G', LARMOR_HZ_PER_G), ('ground hyperfine', F_HFS_GROUND)):
        print(f'  probe offset {fmt_hz(delta):>10s} ({label}): sinc^2(dk L/2) over the {args.cloud_diameter_mm:g} mm '
              f'cloud = {phase_mismatch_factor(delta, cloud):.4f}')

    print('\n=== 2-3. Gratings and the coherence that stores them ===')
    print(f'  optical coherence lifetime 2/Gamma = {fmt_time(2 / GAMMA_D2)} [STECK]; '
          f'k v_s = 2 pi x {fmt_hz(K_D2 * v_1d(T) / (2 * math.pi))} vs Gamma/2 = 2 pi x '
          f'{fmt_hz(GAMMA_D2 / 2 / (2 * math.pi))}')
    print('  -> optical-coherence FWM is effectively Doppler-free in the cold cloud, at any angle.')
    print(f'  reflection grating (q ~ 2k): ground-state coherence washes out in '
          f'{fmt_time(tau_dephasing(q_reflection(0), T))} [ZHAO2009 formula] -> only the transmission grating '
          'carries the narrow Zeeman (magnetometry) signal [DUCLOY1984].')
    print(f'\n  {"theta":>8s} {"grating period":>15s} ' + ' '.join(f'{f"tau_D @ {t:g} uK":>16s}' for t in temps))
    for theta_deg in (0.05, 0.1, 0.2, 0.5, 1, 2, 3, 5, 10, 20):
        q = q_transmission(math.radians(theta_deg))
        cells = ' '.join(f'{fmt_time(tau_dephasing(q, t * 1e-6)):>16s}' for t in temps)
        print(f'  {theta_deg:7g}d {2 * math.pi / q * 1e6:12.4g} um {cells}')

    print('\n=== 4. Maximum angle: motional dephasing no worse than the other limits ===')
    limits = {
        f'transit out of the {args.probe_waist_um:g} um probe [ZHAO2009]': tau_transit(r_probe, T),
        f'free fall through the probe waist (kinematics)': t_fall(r_probe),
    }
    if args.tau_intrinsic_us:
        limits['intrinsic decoherence (--tau-intrinsic-us) [MORETTI2009]'] = args.tau_intrinsic_us * 1e-6
    for name, tau in limits.items():
        print(f'  {name:58s} tau = {fmt_time(tau):>9s} -> theta_max = {fmt_angle(theta_max_for_tau(tau, T))}')
    tau_req = min(limits.values())
    theta_bal = theta_max_for_tau(tau_req, T)
    print(f'  => binding limit {fmt_time(tau_req)}: theta_max = {fmt_angle(theta_bal)} at T = {args.temperature_uK:g} uK')

    print('\n=== 5. Maximum angle for a magnetometer linewidth (residual Raman Doppler FWHM) ===')
    print(f'  {"target FWHM":>12s} {"= B resolution":>15s} ' + ' '.join(f'{f"theta_max @ {t:g} uK":>24s}' for t in temps))
    for fwhm_khz in args.linewidths_kHz:
        cells = ' '.join(f'{fmt_angle(theta_max_for_linewidth(fwhm_khz * 1e3, t * 1e-6)):>24s}' for t in temps)
        print(f'  {fmt_hz(fwhm_khz * 1e3):>12s} {fwhm_khz * 1e3 / LARMOR_HZ_PER_G * 1e3:11.4g} mG {cells}')
    print('  (Zeeman components are only resolved while the Larmor frequency exceeds this width [STECK g_F].)')

    print('\n=== 6. Minimum angle: getting the conjugate past the retro-reflected pump ===')
    theta_min = theta_min_separation(w_pump, r_probe, args.pickoff_distance_m, args.clearance)
    print(f'  spatial separation at {args.pickoff_distance_m:g} m with {args.clearance:g} radii of clearance '
          f'[KOGELNIK1966]: theta_min = {fmt_angle(theta_min)}')
    if theta_min > theta_bal:
        print(f'  theta_min > theta_max: separate C by polarisation (Glan prism, [ZHAO2009]) or by '
              'heterodyne beat [AKULSHIN2011], not by angle alone.')
    L = interaction_length(theta_bal, cloud, w_pump)
    print(f'  interaction length at theta_max: {L * 1e3:.3g} mm (cloud {args.cloud_diameter_mm:g} mm); '
          f'small-signal R ~ (kappa L)^2 [YARIV1977] -> {(L / cloud) ** 2:.0%} of the full-cloud value')

    print('\n=== 7. Recoil-induced resonances at theta_max [GUO1992; BERMAN1999] ===')
    q = q_transmission(theta_bal)
    print(f'  recoil frequency hbar q^2/2M = {fmt_hz(recoil_frequency_hz(q))}; Raman Doppler width q u = 2 pi x '
          f'{fmt_hz(q * v_most_probable_2d(T) / (2 * math.pi))}')
    print('  RIR features sit within ~q u of zero probe-pump detuning (gain below, absorption above).')
    print('  Keep the Larmor-shifted FWM signal outside that band, or expect it to be distorted.')

    print('\n=== References ===')
    for key, text in REFERENCES.items():
        print(f'  [{key}] {text}')
    return tau_req, limits


# --- Figures --------------------------------------------------------------------------------

INK, INK_2, MUTED, GRID, AXIS, SURFACE = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7', '#fcfcfb'
TEMP_RAMP = ['#86b6ef', '#2a78d6', '#104281']   # ordinal blue ramp, validated light -> dark


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, which='major', color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=INK_2, labelsize=9)
    ax.xaxis.label.set_color(INK_2)
    ax.yaxis.label.set_color(INK_2)


def reference_line(ax, y, label, x_text, ha):
    ax.axhline(y, color=MUTED, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.text(x_text, y * 1.12, label, color=INK_2, fontsize=8.5, va='bottom', ha=ha)


def temp_label(t_uK):
    return f'{t_uK:.0f} µK' + (' (T_D)' if abs(t_uK - T_DOPPLER * 1e6) < 0.01 else '')


def field_label(b_gauss):
    return f'{b_gauss:g} G' if b_gauss >= 1 else f'{b_gauss * 1e3:g} mG'


def plot(args, limits):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    OUTPUT.mkdir(parents=True, exist_ok=True)
    temps = sorted({args.temperature_uK, *args.compare_temperatures_uK})[:3]
    theta = np.radians(np.logspace(-2, np.log10(30), 400))
    q = q_transmission(theta)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8), facecolor=SURFACE)
    fig.suptitle('Probe-angle limits for ground-state-coherence FWM in the Rb-87 cloud',
                 color=INK, fontsize=12, x=0.01, ha='left')

    for color, t in zip(TEMP_RAMP[-len(temps):], temps):
        tau = tau_dephasing(q, t * 1e-6)
        ax1.plot(np.degrees(theta), tau * 1e6, color=color, linewidth=2, label=temp_label(t))
        fwhm = raman_doppler_fwhm_hz(q, t * 1e-6)
        ax2.plot(np.degrees(theta), fwhm, color=color, linewidth=2, label=temp_label(t))

    ax1.errorbar([3], [25], yerr=[1], fmt='o', color=INK, markersize=8, markeredgecolor=SURFACE,
                 markeredgewidth=2, zorder=5, label='Zhao et al. 2009, measured (100 µK)')
    for name, tau in limits.items():
        reference_line(ax1, tau * 1e6, f'{name.split(" [")[0]} at {temp_label(args.temperature_uK)}', 55, 'right')
    ax1.set(xscale='log', yscale='log', xlabel='probe–pump angle θ (deg)',
            ylabel='signal lifetime τ_D (µs)')
    ax1.set_title('Motional dephasing of the transmission grating', color=INK_2, fontsize=10, loc='left')

    for b_gauss in args.plot_fields_G:
        reference_line(ax2, b_gauss * LARMOR_HZ_PER_G, f'Larmor frequency at {field_label(b_gauss)}', 0.0115, 'left')
    ax2.set(xscale='log', yscale='log', xlabel='probe–pump angle θ (deg)',
            ylabel='residual Raman Doppler FWHM (Hz)')
    ax2.set_title('Resonance width vs Zeeman splitting', color=INK_2, fontsize=10, loc='left')

    for ax in (ax1, ax2):
        style_axes(ax)
        ax.set_xlim(0.01, 60)
        ax.legend(frameon=False, fontsize=8.5, labelcolor=INK_2, loc='lower left' if ax is ax1 else 'lower right')
    fig.tight_layout()
    path = OUTPUT / 'probe_angle_limits.png'
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    print(f'\nFigure written to {path}')


# --- Main -----------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--globals', type=Path, default=DEFAULT_GLOBALS, help='runmanager globals file')
    parser.add_argument('--temperature-uK', type=float, default=T_DOPPLER * 1e6)
    parser.add_argument('--compare-temperatures-uK', type=float, nargs='*', default=[20, 100])
    parser.add_argument('--probe-waist-um', type=float, default=100)
    parser.add_argument('--pump-waist-mm', type=float, default=5)
    parser.add_argument('--cloud-diameter-mm', type=float, default=2)
    parser.add_argument('--pickoff-distance-m', type=float, default=0.3)
    parser.add_argument('--clearance', type=float, default=2,
                        help='beam radii of margin for spatial separation (2 radii -> e^-8 of peak intensity)')
    parser.add_argument('--tau-intrinsic-us', type=float, default=None,
                        help='other ground-state decoherence time, e.g. from field inhomogeneity')
    parser.add_argument('--linewidths-kHz', type=float, nargs='*', default=[1, 10, 100, 1000])
    parser.add_argument('--plot-fields-G', type=float, nargs='*', default=[0.01, 0.1, 1])
    parser.add_argument('--no-plot', action='store_true')
    args = parser.parse_args()

    seq = load_sequence(args.globals)
    _, limits = report(args, seq)
    if not args.no_plot:
        plot(args, limits)


if __name__ == '__main__':
    main()
