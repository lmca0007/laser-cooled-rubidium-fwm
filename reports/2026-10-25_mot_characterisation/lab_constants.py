"""Apparatus and atomic constants for the 22 Oct 2026 MOT characterisation.

Each value carries its source and a confirmed flag. confirmed = True means a measurement, a
datasheet, or the user gave the value for this apparatus. confirmed = False means an estimate
or a design value that can be wrong for the lab today. The other scripts in this folder read
their inputs only from here.

    python reports/2026-10-25_mot_characterisation/lab_constants.py     # prints the table
"""
import math
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA = REPO / "data" / "2026-10-22"
FIGURES = HERE / "figures"
sys.path.insert(0, str(REPO / "analysis" / "probe_angle"))
sys.path.insert(0, str(REPO / "tools"))

import max_probe_angle as mpa  # noqa: E402  Rb-87 data [STECK] and the FWM washout helpers

THESIS = ("S. Tempone-Wiltshire, \"Development of a rapid Rubidium-87 Bose Einstein Condensate "
          "apparatus\", PhD thesis, Monash University (2019), localstorage/Seb PhDThesis-6.pdf")


@dataclass(frozen=True)
class Const:
    value: float
    unit: str
    source: str
    confirmed: bool
    rel_err: float = 0.0     # 1 sigma, as a fraction of value


C = {
    # --- Side imaging ------------------------------------------------------------------------
    "pixel_at_atoms": Const(4.485e-6, "m", "[THESIS] Fig. 7.3: 4.48 um, M = 1.01 +/- 0.01 from a "
                            "drop-time fit. Global side_pixel_size.", True, 0.01),
    "bin": Const(8, "px", "data/README.md: the reduced frames are 8x8 block sums", True),
    "adc_max": Const(16383, "counts", "GT2750 manual (14-bit) and [THESIS] Sec. 7.4", True),
    "full_well": Const(15200, "e-", "Allied Vision GT2750 datasheet, saturation capacity", True, 0.05),
    # 0 dB maps the full well onto the 14-bit range. The sequence sets no gain, so the camera
    # default (0 dB) applies. Not checked on the camera.
    "e_per_count": Const(15200 / 16383, "e-/count", "full_well / adc_max at 0 dB gain (assumed)",
                         False, 0.2),
    "qe_780": Const(0.30, "", "Sony ICX694 typical spectral response at 780 nm (about 40 % of the "
                    "peak QE of 0.75). Not read from a measured curve.", False, 0.27),
    "collection": Const(0.0070, "", "[THESIS] Sec. 7.5: 1 inch f = 75 mm lens 75 mm from the atoms, "
                        "half-angle 9.6 deg, (1 - cos)/2. Lens distance +/- 5 mm.", True, 0.13),
    "optics_transmission": Const(0.90, "", "two AR-coated achromats and one cell wall (estimate)",
                                 False, 0.06),
    # --- MOT beams ---------------------------------------------------------------------------
    "mot_waist": Const(14e-3, "m", "user: 28 mm 1/e^2 diameter at the atoms", True, 0.05),
    "p_horizontal": Const(25e-3, "W", "user: measured by hand, each horizontal beam, retro-reflected",
                          True, 0.1),
    "p_vertical": Const(11e-3, "W", "user: measured by hand, vertical beam "
                        "(cooling only, [THESIS] Sec. 4.3), retro-reflected", True, 0.1),
    # The imaging pulse uses science_trap_aom amplitude 0.45, the MOT load 0.5. The AOM power
    # at 0.45 is not measured, so the beam powers above carry a 30 % error during imaging.
    "imaging_power_factor": Const(1.0, "", "4wavemixing.py: amplitude 0.45 against 0.5 for the "
                                  "load (not measured)", False, 0.3),
    # --- AOM lock points (double pass) -------------------------------------------------------
    "cooling_lock": Const(180e6, "Hz", "[THESIS] Sec. 4.3: cooling laser 180 MHz below "
                          "F=2->F'=3, AOMs double pass (user confirmed)", True),
    "repump_lock": Const(194e6, "Hz", "[THESIS] Sec. 4.3: repump 194 MHz below F=1->F'=2", True),
    # --- Coils -------------------------------------------------------------------------------
    "quad_gauss_per_cm_per_amp": Const(1.75, "G/cm/A", "[THESIS] Sec. 4.4 (design value)", False, 0.05),
    # The Magneato sense voltage is I_coil / 2000 x R_s (App. C), with R_s = 100 ohm for the
    # quad (Sec. 4.5.1). [LABHW] gives 7 A at 0.45 V control. 0056 has 0.9 V control and a
    # 0.70 V monitor: 14 A both ways, so Quad_voltage is the sense voltage.
    "quad_amp_per_monitor_volt": Const(2000 / 100, "A/V", "[THESIS] Sec. 4.5.1 and App. C: "
                                       "LA 150-P (1:2000) into 100 ohm. Agrees with [LABHW].", True, 0.05),
    "quad_amp_per_control_volt": Const(7 / 0.45, "A/V", "[LABHW] p. 16-17: 0.45 V control gives "
                                       "about 7 A (clamp ammeter)", True, 0.1),
    "bias_x_gauss_per_amp": Const(6.25, "G/A", "[THESIS] Sec. 4.4.6: X pair (along the DPT), 170 mm "
                                  "square formers, 60 turns (design value)", False, 0.05),
    "bias_y_gauss_per_amp": Const(1.28, "G/A", "[THESIS] Sec. 4.4.6: Y pair (side-imaging axis), "
                                  "200 mm square formers, 16 turns (design value)", False, 0.05),
    "bias_z_gauss_per_amp": Const(4.5, "G/A", "[THESIS] Sec. 4.4.6: Z pair (gravity), 24 turns on "
                                  "the quad coils (design value)", False, 0.05),
    # Neither [LABHW] p. 13-14 nor [THESIS] App. C gives R_s or R3/R4 for the bias drivers.
    "bias_amp_per_control_volt": Const(float("nan"), "A/V", "UNKNOWN. Measure with a clamp ammeter, "
                                       "as [LABHW] p. 17 does for the quad.", False),
    # --- Cloud, as built ([THESIS] Sec. 5.4.2) -----------------------------------------------
    "thesis_N": Const(4e9, "atoms", "[THESIS] Sec. 5.4.2: about 4e9 atoms after a 4 s load", True, 0.25),
    "thesis_sigma_h": Const(2.5e-3, "m", "[THESIS] Sec. 5.4.2: Gaussian width 2.5 mm horizontal "
                            "(0.5 ms drop). Taken as sigma: the thesis does not give the convention.",
                            False, 0.2),
    "thesis_sigma_v": Const(1.1e-3, "m", "[THESIS] Sec. 5.4.2: 1.1 mm vertical, as above", False, 0.2),
    "thesis_T": Const(700e-6, "K", "[THESIS] Fig. 5.13: 700 uK by time of flight, full MOT", True, 0.15),
    # --- FWM probe and detector --------------------------------------------------------------
    "probe_power_available": Const(0.2, "W", "user: about 200 mW in free space at the science table",
                                   True, 0.1),
    "probe_beam_diameter": Const(3e-3, "m", "[THESIS] Sec. 4.3.1: each beam line is 3 mm 1/e^2 "
                                 "diameter after its double pass. User: the probe arrives in free space.",
                                 True, 0.2),
    "probe_angle": Const(4.0, "deg", "user: probe at 4 deg to the MOT beam axis", True),
    "det_responsivity": Const(0.5, "A/W", "[DET36A] responsivity curve at 780 nm", True, 0.05),
    "det_capacitance": Const(40e-12, "F", "[DET36A] junction capacitance (typical, 10 V bias)", True, 0.2),
    "det_dark": Const(0.35e-9, "A", "[DET36A] dark current (typical)", True, 0.5),
    "det_bias": Const(10.0, "V", "[DET36A] reverse bias: the output cannot exceed it", True),
    "ar_reflectance": Const(0.005, "", "[THORLABS-B] -B AR coating, R_avg < 0.5 % (650-1050 nm), "
                            "upper limit", True),
    "pbs_extinction": Const(1e-3, "", "[THORLABS-PBS] Tp:Ts > 1000:1, upper limit of the leak", True),
    "daq_rate": Const(5e4, "S/s", "4wavemixing.py:44, ni_pcie_6363_0 acquisition_rate", True),
    "mot_jitter": Const(0.029, "", "README Sec. 1: the six check shots 0045-0056 scatter by 2.9 %",
                        True, 0.3),
    # --- Absorption calibration (not used for N, see README) --------------------------------
    "isat_counts": Const(5262, "counts", "global side_rb87_saturation_intensity (OD_calc.py "
                         "default, +/- 162). The pulse time of that calibration is not recorded.",
                         False, 0.03),
}

# Rb-87 D2 line [STECK], taken from analysis/probe_angle/max_probe_angle.py where it exists
GAMMA = mpa.GAMMA_D2                       # s^-1
GAMMA_HZ = GAMMA / (2 * math.pi)           # 6.0666 MHz
T_DOPPLER = mpa.T_DOPPLER                  # K
M_RB87 = mpa.M_RB87                        # kg
LAMBDA = mpa.LAMBDA_D2                     # m
K_D2 = mpa.K_D2
KB = mpa.KB
HBAR = mpa.HBAR
H = 2 * math.pi * HBAR
NU = mpa.C / LAMBDA
ISAT_ISO = 35.7713                         # W/m^2, isotropic pumping [STECK Table 7]
ISAT_CYCLING = 16.6933                     # W/m^2, sigma+ cycling [STECK Table 7]
SIGMA_ISO = HBAR * 2 * math.pi * NU * GAMMA / (2 * ISAT_ISO)   # 1.36e-13 m^2 [STECK Eq. 50]
# Excited-state splittings and F=2 transition strengths [STECK Fig. 3, Table 9]
DELTA_32 = 266.650e6                       # Hz, F'=3 - F'=2
DELTA_31 = 266.650e6 + 156.947e6           # Hz, F'=3 - F'=1
S23, S22, S21 = 7 / 10, 1 / 4, 1 / 20
P_F2_TO_F1, P_F1_TO_F1 = 1 / 2, 5 / 6      # decay branching of F'=2 and F'=1 to F=1


def cooling_detuning(f_aom_hz):
    """Double pass below the 180 MHz lock: Delta = 2 f - 180 MHz (negative = red)."""
    return 2 * f_aom_hz - C["cooling_lock"].value


def repump_detuning(f_aom_hz):
    return 2 * f_aom_hz - C["repump_lock"].value


def beam_intensity(power, waist=None):
    """Peak intensity 2P / (pi w^2) of a Gaussian beam."""
    w = C["mot_waist"].value if waist is None else waist
    return 2 * power / (math.pi * w ** 2)


def mot_saturation(power_factor=1.0):
    """Total s = sum(I) / I_sat,iso over the six beams (four horizontal passes, two vertical)."""
    i = 4 * beam_intensity(C["p_horizontal"].value) + 2 * beam_intensity(C["p_vertical"].value)
    return power_factor * i / ISAT_ISO


def counts_per_photon():
    """Camera counts per photon that leaves the atoms towards the lens."""
    return C["optics_transmission"].value * C["qe_780"].value / C["e_per_count"].value


REFERENCES = dict(mpa.REFERENCES)
REFERENCES.update({
    "THESIS": THESIS + ". Ch. 4 (apparatus, AOM locks, coils, Magneato), ch. 5 (2D/3D MOT, CMOT, "
              "PGC results), ch. 7 (imaging, pixel size), app. C (Magneato transconductance).",
    "STECK": REFERENCES["STECK"] + " Table 7 (I_sat isotropic 3.577 mW/cm^2, cycling 1.669 mW/cm^2), "
             "Table 9 (F=2 strengths 7/10, 1/4, 1/20), Fig. 3 (excited splittings).",
    "LETT1989": "P. D. Lett et al., \"Optical molasses\", J. Opt. Soc. Am. B 6, 2084 (1989). "
                "1D Doppler temperature kT = (hbar Gamma / 4)(1 + s + (2 delta/Gamma)^2)/(2|delta|/Gamma).",
    "TOWNSEND1995": "C. G. Townsend et al., \"Phase-space density in the magneto-optical trap\", "
                    "Phys. Rev. A 52, 1423 (1995). MOT density and temperature against N and detuning.",
    "SESKO1991": "D. W. Sesko, T. G. Walker, C. E. Wieman, \"Behavior of neutral atoms in a "
                 "spontaneous force trap\", J. Opt. Soc. Am. B 8, 946 (1991). Radiation-trapping "
                 "density limit.",
    "DIECKMANN1998": "K. Dieckmann et al., \"Two-dimensional magneto-optical trap as a source of slow "
                     "atoms\", Phys. Rev. A 58, 3891 (1998). 9e9 atoms/s from a Rb 2D+ MOT.",
    "ABRAMS1978": "R. L. Abrams, R. C. Lind, \"Degenerate four-wave mixing in absorbing media\", "
                  "Opt. Lett. 2, 94 (1978), errata Opt. Lett. 3, 205 (1978). Two-level DFWM "
                  "reflectivity with absorption and saturating pumps.",
    "ZHOU2010": "Zhou et al., Chin. Phys. Lett. 27, 014211 (2010). Backward FWM in an 87Rb MOT.",
    "LABHW": "BEC Lab User Manual, \"iii. Hardware\" (20 Dec 2019), labhardware.pdf in the repo root. "
             "Bias supplies (bipolar), bias and quad Magneato monitors, quad 7 A at 0.45 V.",
    "DET36A": "Thorlabs DET36A/M Si biased detector, spec sheet: responsivity curve, 40 pF, 0.35 nA dark.",
    "THORLABS-B": "Thorlabs -B broadband AR coating (650-1050 nm), R_avg < 0.5 %.",
    "THORLABS-PBS": "Thorlabs polarising beamsplitter cubes, 620-1000 nm, extinction Tp:Ts > 1000:1.",
    "LEZAMA2001": "A. Lezama, G. C. Cardoso, J. W. R. Tabosa, \"Polarization dependence of four-wave "
                  "mixing in a degenerate two-level system\", Phys. Rev. A 63, 013805 (2001). "
                  "Backward FWM in a Cs MOT, probe at 4 deg, Zeeman-coherence resonances.",
    "MCCORMICK2007": "C. F. McCormick, V. Boyer, E. Arimondo, P. D. Lett, \"Strong relative intensity "
                     "squeezing by four-wave mixing in rubidium vapor\", Opt. Lett. 32, 178 (2007). "
                     "Twin-beam intensity-difference noise 1/(2G - 1) of the shot noise.",
    "DATASHEET": "Allied Vision Prosilica GT2750 datasheet and technical manual (Sony ICX694, "
                 "4.54 um cells, 14-bit, saturation capacity 15,200 e-).",
})


def main():
    print("%-28s %12s %-9s %-5s %-6s %s" % ("name", "value", "unit", "conf", "err", "source"))
    for k, c in C.items():
        print("%-28s %12.4g %-9s %-5s %-6s %s" % (k, c.value, c.unit, "yes" if c.confirmed else "NO",
                                              "%.0f%%" % (100 * c.rel_err), c.source))
    print("MOT s (six beams, isotropic I_sat) = %.1f" % mot_saturation())
    print("counts per photon at the lens = %.3f" % counts_per_photon())
    for name, f in [("MOT 83.5", 83.5e6), ("source 81.5", 81.5e6), ("push 87.4", 87.4e6),
                    ("CMOT 79", 79e6), ("PGC 55.5", 55.5e6), ("imaging 90", 90e6)]:
        print("cooling %-12s -> %+.1f MHz (%+.2f Gamma)" % (name, cooling_detuning(f) / 1e6,
                                                            cooling_detuning(f) / GAMMA_HZ))


if __name__ == "__main__":
    main()
