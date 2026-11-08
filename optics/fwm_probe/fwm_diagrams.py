"""Diagrams A, B and C of the FWM setup, drawn with matplotlib and LaTeX (TeX Live).

    A  wave vectors at the cloud (representative: the probe angle is enlarged)
    B  the probe optics and the photodiodes, with the beam path unfolded into a line
    C  laser frequencies from the AOMs, and the Rb-87 double-Lambda at the Zeeman resonance

Every number comes from code: geometry.py (probe arm, power HWP), polarisation.py (QWP angle),
and reports/2026-10-25_mot_characterisation/fwm_model.json and lab_constants.py (powers,
detunings, Zeeman shifts). Run fwm_model.py first if you change its inputs.

    python optics/fwm_probe/fwm_diagrams.py        # writes figures/fig_[abc]_*.pdf and .png
"""
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Circle, ConnectionPatch, Ellipse, FancyArrowPatch, Polygon, Rectangle

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
REPORT = REPO / "reports" / "2026-10-25_mot_characterisation"
OUT = HERE / "figures"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPORT))

import geometry as geo  # noqa: E402
import lab_constants as lc  # noqa: E402
import polarisation as pol  # noqa: E402

MODEL = json.loads((REPORT / "fwm_model.json").read_text())

# Rb-87 [STECK]: F=2 -> F'=3 at zero field, from the D2 centre and the hyperfine shifts
NU_D2_THZ = 384.2304844685
NU0_THZ = NU_D2_THZ - 2.563005979e-3 + 193.7407e-6
G_F, G_FP = 1 / 2, 2 / 3                 # Lande g of 5S1/2 F=2 and 5P3/2 F'=3 [STECK]

PUMP, PROBE, CONJ, GREY, INK = "#b2182b", "#1f5aa6", "#8e2a8e", "#8a8f94", "#111111"

plt.rcParams.update({
    "text.usetex": True,
    "text.latex.preamble": r"\usepackage{amsmath}\usepackage{upgreek}"
                           r"\usepackage[detect-all]{siunitx}",
    "font.family": "serif",
    "font.size": 9,
    "axes.linewidth": 0.6,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "savefig.dpi": 300,
})


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print("wrote", OUT / f"{name}.pdf")


# --- A: wave vectors ------------------------------------------------------------------------

def figure_a(theta_draw=20.0):
    """Wave vectors in the pump frame (+x along F, +y to the left of F, seen from above). Each input beam
    ends at the cloud. The probe sits on the same side of B as on the table, with the angle enlarged to
    theta_draw. The conjugate leaves the cloud back along the probe."""
    p_true = geo.deg_of(geo.to_pump_frame(geo.probe_direction()))      # 176 deg
    side = math.copysign(1.0, p_true - 180.0)                           # -1: probe clockwise of B
    p_deg = 180.0 + side * theta_draw

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.set_aspect("equal")
    ax.axis("off")
    L = 3.0
    k_f, k_b = np.array([L, 0.0]), np.array([-L, 0.0])
    k_p = L * geo.unit_deg(p_deg)
    k_c = -k_p
    d_p = k_p / L
    n_p = side * np.array([-d_p[1], d_p[0]])                            # towards B, away from the probe source side

    # the cloud as a Gaussian blob
    for r, a in ((0.42, 0.10), (0.28, 0.16), (0.15, 0.30)):
        ax.add_patch(Circle((0, 0), r, color=GREY, alpha=a, lw=0))

    def vec(start, end, c, ls="-", lw=1.6):
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=11, color=c, lw=lw, ls=ls,
                                     shrinkA=0, shrinkB=0))

    # inputs, from the source side to the cloud
    vec(-k_f, (0, 0), PUMP)
    vec(-k_b, (0, 0), PUMP)
    vec(-k_p, (0, 0), PROBE)
    # the conjugate leaves the cloud towards the probe source, drawn just beside the probe
    off = -0.13 * n_p
    vec(off, off + 0.85 * k_c, CONJ)
    # q1 = k_p - k_B joins the tails of k_p and k_B
    vec(-k_p, -k_b, GREY, ls=(0, (3, 2)), lw=1.1)

    ax.text(*(-k_f + [-0.15, 0]), r"$\mathbf{k}_F$", color=PUMP, ha="right", va="center", fontsize=11)
    ax.text(*(-k_b + [0.15, 0]), r"$\mathbf{k}_B$", color=PUMP, ha="left", va="center", fontsize=11)
    ax.text(*(-k_p - 0.25 * d_p), r"$\mathbf{k}_p$", color=PROBE, ha="left", va="center", fontsize=11)
    ax.text(*(off + 0.85 * k_c - 0.3 * n_p), r"$\mathbf{k}_c = -\mathbf{k}_p$", color=CONJ, ha="center",
            va="top", fontsize=11)
    ax.text(*((-k_p - k_b) / 2 + [0.22, 0]), r"$\mathbf{q}_1$", color=GREY, ha="left", va="center", fontsize=10)
    ax.text(-1.6, 0.12, r"pump $F$", color=PUMP, ha="center", va="bottom", fontsize=8.5)
    ax.text(1.6, 0.12, r"pump $B$", color=PUMP, ha="center", va="bottom", fontsize=8.5)
    rot = math.degrees(math.atan2(-d_p[1], -d_p[0]))
    ax.text(*(-0.55 * k_p + 0.2 * n_p), "probe", color=PROBE, ha="center", va="center", fontsize=8.5,
            rotation=rot)
    ax.text(*(off + 0.55 * k_c - 0.22 * n_p), "conjugate", color=CONJ, ha="center", va="center", fontsize=8.5,
            rotation=rot)

    # angle arc between the B input and the probe input
    r = 0.85
    a0, a1 = sorted((0.0, side * theta_draw))
    ax.add_patch(Arc((0, 0), 2 * r, 2 * r, theta1=a0, theta2=a1, color=INK, lw=0.7))
    ax.text(*(1.12 * r * geo.unit_deg(side * theta_draw / 2)), r"$\theta$", color=INK, ha="center", va="center",
            fontsize=10)

    ax.set_xlim(-3.7, 4.0)
    ax.set_ylim(-1.75, 0.7)
    save(fig, "fig_a_wavevectors")


# --- B: probe optics, unfolded --------------------------------------------------------------

def figure_b():
    rec = MODEL["recommended"]
    p_cloud = rec["p_W"] * 1e3
    p_arm = 2 * p_cloud
    p_src = geo.PROBE_SOURCE_POWER
    p_conj = rec["conjugate_W"]["thesis"]["mean"] * 1e6
    p_out = p_cloud * MODEL["twin_beams"]["probe_transmission"]
    det = MODEL["detector"]["100 kOhm"]
    pd_fwm_v = det["signal_V"]
    pd_ref_v = p_cloud * 1e-3 * lc.C["det_responsivity"].value * 1e3
    _, _, qwp = pol.solve_waveplates(1, 0.0)

    fig, ax = plt.subplots(figsize=(11.2, 3.3))
    ax.set_xlim(0, 1120)
    ax.set_ylim(330, 0)
    ax.axis("off")
    ax.set_aspect("equal")

    def text(x, y, s, c=INK, ha="center", size=8.5, alpha=1.0, va="baseline"):
        ax.text(x, y, s, color=c, ha=ha, va=va, fontsize=size, alpha=alpha)

    def arrow(x0, y0, x1, y1, c):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=9, color=c, lw=1.2,
                                     shrinkA=0, shrinkB=0))

    text(20, 28, r"\textsc{Forward}: probe", PROBE, ha="left", size=9.5)
    text(20, 318, r"\textsc{Return}: conjugate", CONJ, ha="left", size=9.5)
    # forward beam: thin up to the telescope, wide after it
    ax.plot([20, 590], [150, 150], color=PROBE, lw=1.2)
    ax.add_patch(Polygon([(590, 148), (650, 142), (1080, 142), (1080, 158), (650, 158), (590, 152)],
                         color=PROBE, alpha=0.15, lw=0))
    ax.plot([590, 1080], [150, 150], color=PROBE, lw=1.2)
    arrow(30, 150, 62, 150, PROBE)
    arrow(980, 150, 1020, 150, PROBE)
    # return beam
    arrow(900, 172, 262, 172, CONJ)
    ax.plot([246, 20], [172, 172], color=CONJ, lw=1.2, alpha=0.35)
    arrow(254, 178, 254, 252, CONJ)
    # powers (probe) and states
    for x, s in ((40, rf"\SI{{{p_src:.0f}}}{{mW}}"), (190, rf"\SI{{{p_arm:.1f}}}{{mW}}"),
                 (296, rf"\SI{{{p_arm:.1f}}}{{mW}}"), (470, rf"\SI{{{p_cloud:.1f}}}{{mW}}"),
                 (860, rf"\SI{{{p_cloud:.1f}}}{{mW}}, $w = \SI{{{geo.PROBE_WAIST:.0f}}}{{mm}}$"),
                 (1050, rf"$\approx\SI{{{p_out:.1f}}}{{mW}}$")):
        text(x, 98, s, PROBE)
    for x, s in ((190, "H"), (296, "H"), (384, r"$45^\circ$"), (470, "H"), (560, r"$\sigma$, same as $F$")):
        text(x, 128, s, PROBE)
    # return states: circular until the QWP, H through PBS B, 45 deg after the HWP at 22.5 deg
    for x, s, a in ((860, rf"\SI{{{p_conj:.0f}}}{{\micro W}}, $\sigma$ opposite to $F$", 1), (560, r"$\sigma$", 1),
                    (470, "H", 1), (384, "H", 1), (296, r"$45^\circ$", 1),
                    (110, rf"\SI{{{p_conj / 2:.0f}}}{{\micro W}} to the laser", 0.55)):
        text(x, 194, s, CONJ, alpha=a)

    def plate(x, rot=0.0):
        ax.add_patch(Rectangle((x, 132), 7, 36, fc="#dfe6ee", ec=INK, lw=0.8,
                               transform=matplotlib.transforms.Affine2D().rotate_deg_around(x + 3.5, 150, rot)
                               + ax.transData))

    def cube(x):
        ax.add_patch(Rectangle((x, 136), 28, 28, fc="#eef2f6", ec=INK, lw=0.9))
        ax.plot([x, x + 28], [164, 136], color=INK, lw=0.8)

    # power HWP and PBS
    plate(76)
    text(80, 232, r"$\lambda/2$", size=8)
    text(80, 246, rf"${geo.power_hwp_deg():.1f}^\circ$", size=8)
    cube(128)
    ax.plot([142, 142], [136, 70], color=PROBE, lw=1.2, alpha=0.5)
    ax.add_patch(Rectangle((134, 54), 16, 16, fc="#333333", ec="none"))
    text(156, 62, rf"\SI{{{p_src - p_arm:.0f}}}{{mW}} dump", ha="left", size=8)
    text(142, 232, "PBS", size=8)
    # PBS A and PD FWM
    cube(240)
    text(254, 122, "PBS A", size=8.5)
    ax.add_patch(Ellipse((254, 232), 26, 7, fc="#dfe6ee", ec=INK, lw=0.8))
    ax.add_patch(Rectangle((240, 258), 28, 22, fc="white", ec=CONJ, lw=1.4))
    text(276, 268, rf"PD FWM: \SI{{{p_conj / 2:.0f}}}{{\micro W}}", CONJ, ha="left")
    text(276, 283, rf"lens, pinhole, DET36A/M, \SI{{100}}{{k\ohm}} $\rightarrow$ \SI{{{pd_fwm_v:.2f}}}{{V}}",
         ha="left", size=8)
    # HWP at 22.5 deg
    plate(331)
    text(334, 232, r"$\lambda/2$", size=8)
    text(334, 246, r"$22.5^\circ$", size=8)
    # PBS B and PD ref
    cube(420)
    text(434, 232, "PBS B", size=8.5)
    arrow(434, 136, 434, 82, PROBE)
    ax.add_patch(Rectangle((420, 56), 28, 22, fc="white", ec=INK, lw=1.2))
    text(456, 66, rf"PD ref: \SI{{{p_cloud:.1f}}}{{mW}}", PROBE, ha="left")
    text(456, 80, rf"use \SI{{1}}{{k\ohm}} (\SI{{{pd_ref_v:.1f}}}{{V}}) or an ND filter", ha="left", size=8)
    # QWP, tilted
    plate(516, rot=3)
    text(519, 232, rf"$\lambda/4$ at ${qwp:+.0f}^\circ$", size=8)
    text(519, 246, r"tilt $2$--$3^\circ$", size=8)
    # telescope
    ax.add_patch(Polygon([(586, 136), (590, 150), (586, 164), (594, 164), (598, 150), (594, 136)],
                         fc="#dfe6ee", ec=INK, lw=0.8))
    ax.add_patch(Ellipse((652, 150), 10, 36, fc="#dfe6ee", ec=INK, lw=0.8))
    text(620, 232, "telescope (mm)", size=8)
    f1, f2 = geo.TELESCOPE
    text(620, 246, rf"${f1:.0f}$, ${{+{f2:.0f}}}$", size=8)
    # M1 and the D-mirror (folds, drawn unfolded)
    for x in (712, 752):
        ax.plot([x, x], [136, 164], color=INK, lw=2.5, alpha=0.5)
    text(752, 232, r"M1, D-mirror", size=8)
    text(752, 246, "(unfolded)", size=8)
    # cloud
    for r, a in ((22, 0.12), (14, 0.2), (7, 0.55)):
        ax.add_patch(Circle((900, 150), r, color=GREY, alpha=a, lw=0))
    text(900, 232, rf"cloud, ${geo.THETA_DEG:.0f}^\circ$ to beam B", size=8)
    # dump
    ax.add_patch(Rectangle((1082, 140), 14, 20, fc="#333333", ec="none"))
    text(1089, 232, "dump", size=8)
    save(fig, "fig_b_probe_optics")


# --- C: frequencies and the double Lambda ----------------------------------------------------

def broken_marks(ax_top, ax_bottom, d=0.012):
    """Short diagonal marks on the left and right spines at an axis break."""
    for ax, y in ((ax_top, 0.0), (ax_bottom, 1.0)):
        kw = dict(transform=ax.transAxes, color=INK, clip_on=False, lw=0.7)
        for x in (0.0, 1.0):
            ax.plot((x - d, x + d), (y - 2.5 * d, y + 2.5 * d), **kw)


def figure_c():
    inp, zee = MODEL["inputs"], MODEL["zeeman"]
    b = zee["B_G"]
    lock = -lc.C["cooling_lock"].value / 1e6
    f_img = zee["probe_aom_Hz"][0] / 1e6
    nu_pump = inp["pump_detuning_MHz"]                       # 2 f_trap - 180
    nu_probe = 2 * f_img + lock
    delta = nu_probe - nu_pump                               # Raman detuning, = Zeeman split
    nu_conj = nu_pump - delta
    larmor = zee["larmor_Hz_per_G"] / 1e6                    # MHz/G per m in F = 2 (g_F mu_B / h)
    g_step = larmor * b                                      # MHz per m in F = 2
    e_step = g_step * G_FP / G_F                             # MHz per m' in F' = 3

    fig = plt.figure(figsize=(7.4, 5.6))
    gb = fig.add_gridspec(3, 1, height_ratios=[2.45, 0.95, 1.0], hspace=0.0)
    ae, ag_gap, ag = fig.add_subplot(gb[0]), fig.add_subplot(gb[1]), fig.add_subplot(gb[2])
    ag_gap.axis("off")
    xl = (-1.6, 4.9)
    for ax in (ae, ag_gap, ag):
        ax.set_xlim(*xl)
    ae.set_ylim(-16, 6.5)
    ag.set_ylim(-3.8, 6.5)
    ae.spines["bottom"].set_visible(False)
    ag.spines["top"].set_visible(False)
    ae.tick_params(bottom=False, labelbottom=False, top=True, labeltop=True, left=False, labelleft=False)
    ag.tick_params(left=False, labelleft=False)
    ae.set_xticks([1])
    ae.xaxis.set_label_position("top")
    ae.set_xlabel(r"$m_{F'}$")
    ag.set_xticks([0, 2])
    ag.set_xlabel(r"$m_F$")
    broken_marks(ae, ag, d=0.008)
    ae.set_title(rf"Double $\Lambda$ in $^{{87}}$Rb at $B = \SI{{{b:.1f}}}{{G}}$ along MOT axis B",
                 loc="left", fontsize=10, pad=22)

    i1, i2, i3 = 0, 2, 1                                         # |1> = |2,0>, |2> = |2,2>, |3> = |3',1>
    e3 = e_step * i3
    g1, g2 = g_step * i1, g_step * i2
    v1 = g1 + nu_pump                                            # pump F from |1>
    v2 = g2 + nu_pump                                            # pump B from |2>
    big_delta = v1 - e3
    hw = 0.3
    ae.plot([i3 - hw, i3 + hw], [e3] * 2, color=INK, lw=2.2)
    for m in (i1, i2):
        ag.plot([m - hw, m + hw], [g_step * m] * 2, color=INK, lw=2.2)
    ae.text(-1.5, 5.0, r"$5P_{3/2}$, $F'=3$", fontsize=9.5, va="center")
    ag.text(-1.5, 5.2, r"$5S_{1/2}$, $F=2$", fontsize=9.5, va="center")
    ae.text(i3, e3 + 0.9, r"$|3\rangle$", ha="center", va="bottom", fontsize=10)
    ag.text(i1 - hw - 0.1, g1, r"$|1\rangle$", ha="right", va="center", fontsize=10)
    ag.text(i2, g2 - 0.7, r"$|2\rangle$", ha="center", va="top", fontsize=10)
    # virtual levels and brackets
    xa, xb = 3.75, 4.4                                          # Delta + delta bracket, Delta bracket
    ae.plot([-0.5, xa], [v2, v2], color=INK, lw=0.9, ls=(0, (1.5, 1.5)))
    ae.plot([-0.5, xb], [v1, v1], color=INK, lw=0.9, ls=(0, (1.5, 1.5)))
    ae.plot([i3 + hw, xb], [e3, e3], color=GREY, lw=0.6, ls=":")
    for x, y, lab in ((xa, v2, rf"$\Delta + \delta = {v2 - e3:.2f}$ MHz"),
                      (xb, v1, rf"$\Delta = {big_delta:.2f}$ MHz")):
        ae.annotate("", (x, e3), (x, y), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.7, shrinkA=0,
                                                         shrinkB=0))
        ae.text(x + 0.12, (y + e3) / 2, lab, rotation=90, va="center", ha="left", fontsize=8)
    ag.plot([i1 + hw, xa], [g1, g1], color=GREY, lw=0.6, ls=":")
    ag.plot([i2 + hw, xa], [g2, g2], color=GREY, lw=0.6, ls=":")
    ag.annotate("", (xa, g2), (xa, g1), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.7, shrinkA=0,
                                                        shrinkB=0))
    ag.text(xa - 0.1, (g1 + g2) / 2, rf"$\delta = {g2 - g1:.2f}$ MHz", ha="right", va="center", fontsize=8.5)

    # transitions (ground axis -> excited axis)
    def transition(x_g, y_g, x_e, y_e, c, up):
        a, b_ = ((x_g, y_g), (x_e, y_e)) if up else ((x_e, y_e), (x_g, y_g))
        ax_a, ax_b = (ag, ae) if up else (ae, ag)
        fig.add_artist(ConnectionPatch(a, b_, "data", "data", axesA=ax_a, axesB=ax_b, color=c, lw=2.0,
                                       arrowstyle="-|>", mutation_scale=14, shrinkA=0, shrinkB=1))

    def parallel_x(g, e, g2_, y_e2):
        """x at y_e2 on the excited axis so that g2_ -> (x, y_e2) is parallel on the page to g -> e."""
        p0, p1 = ag.transData.transform(g), ae.transData.transform(e)
        q0 = ag.transData.transform(g2_)
        q1_y = ae.transData.transform((0, y_e2))[1]
        q1_x = q0[0] + (p1[0] - p0[0]) * (q1_y - q0[1]) / (p1[1] - p0[1])
        return ae.transData.inverted().transform((q1_x, q1_y))[0]

    # each pump runs parallel to the beam that shares its ground level
    transition(0.0, g1, 0.8, v1, PUMP, up=True)                                   # pump F, up from |1>
    transition(-0.25, g1, parallel_x((0.0, g1), (0.8, v1), (-0.25, g1), v2), v2, PROBE,
               up=False)                                                           # probe, down to |1>
    transition(2.0, g2, 1.25, v2, PUMP, up=True)                                  # pump B, up from |2>
    transition(2.28, g2, parallel_x((2.0, g2), (1.25, v2), (2.28, g2), v1), v1, CONJ,
               up=False)                                                           # conjugate, down to |2>

    # probe and conjugate labels in the axis break. The pumps label goes below the pump arrows, between
    # |1> and |2>, because the break has no room between the two pump arrows.
    ag_gap.set_ylim(0, 1)
    for x, y, lines, c, ha in (
            (-0.45, 0.55, [r"probe, $\sigma^+$", rf"$\nu_0 {nu_probe:+.2f}$ MHz"], PROBE, "right"),
            (2.45, 0.62, [r"conjugate, $\sigma^-$", rf"$\nu_0 {nu_conj:+.2f}$ MHz"], CONJ, "left")):
        ag_gap.text(x, y, "\n".join(lines), color=c, ha=ha, va="center", fontsize=8.5)
    ag.text(1.2, -0.8, "\n".join([r"pumps $F$ ($\sigma^+$), $B$ ($\sigma^-$)", rf"$\nu_0 {nu_pump:+.2f}$ MHz"]),
            color=PUMP, ha="center", va="top", fontsize=8.5)
    ag_gap.text(4.85, 0.18, "\n".join([r"optical gap", rf"$\nu_0 = \SI{{{NU0_THZ:.6f}}}{{THz}}$"]),
                ha="right", va="center", fontsize=8.5, color="#444444")
    save(fig, "fig_c_levels")
    return dict(delta=delta, big_delta=big_delta, nu_conj=nu_conj, g_step=g_step, e_step=e_step)


if __name__ == "__main__":
    figure_a()
    figure_b()
    print(figure_c())
