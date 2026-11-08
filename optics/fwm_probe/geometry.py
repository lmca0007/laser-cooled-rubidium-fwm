"""Table geometry for the FWM probe, shared by the PyOpticL layout, the plan view and the checks.

Frame: the thesis axes [THESIS Sec. 4.1.5], origin at the cloud, all lengths in mm.
    +X  along the differential pumping tube, from the source chamber to the science cell.
        The main chamber (6" spherical octagon) is at -X. Bellows and the gate valve are at +X.
    +Y  to the left when you look along +X. The side-imaging beam enters from +Y. The side
        camera is at -Y [THESIS Sec. 7.5.1, user].
    +Z  up, against gravity.
Angles in the X-Y plane are counterclockwise from +X, seen from above.

The horizontal MOT beams cross at 45 deg to the side-imaging axis [THESIS Sec. 7.5.1]:
    axis A  45 deg <-> 225 deg  (left-valve port <-> right-source port)
    axis B 135 deg <-> 315 deg  (left-source port <-> right-valve port)
User: the probe runs at 4 deg to axis B. It enters on the left, beside the retro optic of axis B
(the left-source port), tilted towards the old imaging beam. So the retro beam B of that axis
travels at 315 deg, the incoming beam F at 135 deg, and the probe at 311 deg.

Every value has a source. ASSUMED values are placeholders: measure them on the table.

    python optics/fwm_probe/geometry.py           # clearance checks
    python optics/fwm_probe/geometry.py --plot    # also writes fwm_probe_plan.png
"""
import argparse
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent

# --- Science cell [THESIS Sec. 4.1.4] -----------------------------------------------------
CELL_SIDE = 40.0                 # external side of each square flat
CELL_HEIGHT = 40.0
CELL_WALL = 4.0
CELL_FLAT_TO_FLAT = CELL_SIDE * (1 + math.sqrt(2))      # 96.57 mm
FLAT_NORMALS_DEG = [45.0 * i for i in range(8)]         # seals at 0 and 180 deg (the X axis)
SEAL_DEG = (0.0, 180.0)
REDUCER_OFFSET = 24.8            # [THESIS] 2-3/4" flange offset on the custom 6" reducer
CF275_RADIUS = 34.9              # 2-3/4" CF flange, 69.85 mm OD (standard)

# --- Vacuum hardware along X ---------------------------------------------------------------
# [THESIS Sec. 4.1.4-4.1.5]: the cell hangs off the main chamber, a Kimball MCF600-SphOct-F2C8
# spherical octagon with its two 6" faces on the X axis, through a custom 6" to 2-3/4" reducer.
# The source chamber is on the other 6" face, and the DPT is in that reducer. At +X: bellows,
# then the gate valve.
# Sizes along X and Z: [CAD] the SolidWorks side view from the user (2026-10-26), scaled by the
# cell width (65 px = 96.57 mm, so 1.486 mm/px, cloud at x = 452.5 px). Check: each 2-3/4" CF
# flange measures 47 px = 69.9 mm (standard 69.85 mm). A side view does not show sizes along Y.
# The spherical octagon has 8-fold symmetry about X, so its Y half-width is its Z half-height.
CAD_MM_PER_PX = CELL_SIDE * (1 + math.sqrt(2)) / 65
SEAL_TUBE_LENGTH = 97.0          # [CAD] cell flat (48.3 mm) to the flange (146 mm at -X, 145 mm at +X)
SEAL_TUBE_RADIUS = 13.0          # [CAD] 17-18 px glass tube
# (name, x from, x to, half-width in Y), mm from the cloud
VACUUM_PARTS = [
    ('2-3/4" CF flange, cell side', -161.0, -146.0, CF275_RADIUS),       # [CAD] 344-354 px
    ("spherical octagon (main chamber)", -270.0, -161.0, 91.0),          # [CAD] 271-344 px, 122 px high
    ('2-3/4" CF flange, source side', -285.0, -270.0, CF275_RADIUS),     # [CAD] 261-271 px
    ("tube to the source (DPT inside)", -338.0, -285.0, CF275_RADIUS),   # [CAD] 225-261 px, flange size
    ("source chamber (2D MOT)", -445.0, -338.0, 54.0),                   # [CAD] 153-225 px. Y: ASSUMED
    ('2-3/4" CF flange, +X', 145.0, 158.0, CF275_RADIUS),                # [CAD] 550-559 px
    ("bellows and gate valve", 158.0, 600.0, CF275_RADIUS),              # [THESIS] order. Length ASSUMED
]

# --- MOT beams [THESIS Sec. 5.4.2] ----------------------------------------------------------
MOT_WAIST = 14.0                 # 28 mm 1/e^2 diameter
MOT_CLEAR = 1.2 * MOT_WAIST      # an aperture 1.2x the diameter passes about 95 % [THESIS]
AXIS_DEG = {"A": 45.0, "B": 135.0}
# Retro ends: B at the left-source port (user), A at the right-source port (user, 2026-10-26:
# "retro A easily clears the chamber").
RETRO_DEG = {"A": 225.0, "B": 135.0}
PROBE_AXIS = "B"
RETRO_OPTIC_RADIUS = 25.4        # ASSUMED 2" HR-coated QWP [THESIS: one optic, QWP + HR coating]
RETRO_MOUNT_MARGIN = 12.0        # ASSUMED mount rim beyond the optic
RETRO_DISTANCE = {"B": 400.0, "A": 400.0}   # ASSUMED: cloud to the retro optic. MEASURE.
INPUT_DISTANCE = {"B": 400.0, "A": 400.0}   # ASSUMED: cloud to the last input optic. MEASURE.

# --- Side imaging [THESIS Sec. 7.5.1] -------------------------------------------------------
IMAGING_RADIUS = 10.0            # 2 cm 1/e^2 diameter beam, from +Y
CAMERA_LENS1 = 75.0              # f = 75 mm 1" achromat, about 75 mm from the atoms
CAMERA_LENS2 = 225.0             # second f = 75 mm achromat, about 150 mm further
CAMERA_CHIP = 300.0              # 75 mm after the second lens
LENS_RADIUS = 12.7

# --- Probe ----------------------------------------------------------------------------------
THETA_DEG = 4.0                  # user: probe to MOT axis B
PROBE_WAIST = 4.0                # fwm_model.py recommendation (1/e^2 radius at the cloud)
PROBE_INPUT_RADIUS = 1.5         # [THESIS Sec. 4.3.1] 3 mm 1/e^2 diameter after the double pass
TELESCOPE = (-75.0, 200.0)       # Galilean pair, 2.67x (stock focal lengths)
D_MIRROR_RADIUS = 12.7           # 1" D-shaped mirror (the 8 mm beam needs more than 1/2")
D_MIRROR_EDGE_GAP_W = 1.5        # straight edge 1.5 probe radii from the probe centre (99 % passes)
D_MIRROR_THICKNESS = 6.0         # substrate behind the straight edge
CLEARANCE_MARGIN = 1.0
DUMP_RADIUS = 8.0                # transmitted-probe dump
# The D-mirror folds the beam by 90 deg (45 deg incidence). M1 sits M1_GAP upstream and turns the
# main arm into it. M1 sits in the wedge between MOT beam B and the old imaging beam, and the
# main arm runs parallel to beam B, outwards, so it stays clear of both.
ARM_FOLD_DEG = -90.0
M1_GAP = 60.0
MAIN_ARM_DEG = -45.0
# Positions along the arm, measured back from the D-mirror (upstream is +Y)
ARM_PARTS = {
    "telescope f = +200 mm": 60.0,
    "telescope f = -75 mm": 185.0,
    "lambda/4 (circular)": 215.0,
    "PBS B (polariser, PD ref port)": 245.0,
    "lambda/2 at 22.5 deg": 275.0,
    "PBS A (pick-off, PD FWM port)": 305.0,
    "PBS (power dump)": 345.0,
    "lambda/2 (power)": 375.0,
}
PD_OFFSET = 60.0                 # photodiodes sideways from their cube
PBS_REFLECT_TURN = 90.0          # a PBS cube turns its reflected beam 90 deg to the left of travel
PROBE_SOURCE_POWER = 200.0       # mW, user: about 200 mW of free-space light
PROBE_POWER = 3.23               # mW at the cloud, fwm_model.py recommendation (push limit)
CONJUGATE_POWER = 0.0289         # mW, fwm_model.py, thesis cloud, mean over the pair phases
WAVELENGTH_NM = 780.241


# --- Directions -----------------------------------------------------------------------------

def unit_deg(a):
    return np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])


def deg_of(v):
    return math.degrees(math.atan2(v[1], v[0]))


def forward_pump_direction():
    """F of axis B travels from the right-valve input to the left-source retro: 135 deg."""
    return unit_deg(AXIS_DEG[PROBE_AXIS])


def probe_source_deg():
    """Side the probe comes from: the retro port of axis B, turned THETA towards +Y."""
    return AXIS_DEG[PROBE_AXIS] - THETA_DEG


def probe_direction():
    """Unit vector of the probe at the cloud (311 deg): 4 deg from the retro beam B."""
    return -unit_deg(probe_source_deg())


def arm_direction():
    """Direction of travel from M1 into the D-mirror."""
    return unit_deg(deg_of(probe_direction()) + ARM_FOLD_DEG)


def main_arm_direction():
    """Direction of travel in the main arm, into M1."""
    return unit_deg(MAIN_ARM_DEG)


def m1_centre():
    return d_mirror_centre() - M1_GAP * arm_direction()


def m1_normal():
    n = arm_direction() - main_arm_direction()
    return n / np.linalg.norm(n)


def to_pump_frame(v):
    """Thesis X-Y vector -> frame with +x along F of axis B and +y = z x x (for polarisation.py)."""
    x = forward_pump_direction()
    y = np.array([-x[1], x[0]])
    return np.array([v @ x, v @ y])


def offset_from_axis(point, axis=PROBE_AXIS):
    a = unit_deg(AXIS_DEG[axis])
    return abs(point[0] * -a[1] + point[1] * a[0])


# --- The D-mirror ---------------------------------------------------------------------------

def d_mirror_distance_min():
    """Closest D-mirror distance from the cloud at which its edge and substrate clear the MOT
    beam's 95 % aperture (MOT_CLEAR) by CLEARANCE_MARGIN."""
    lo, hi = 50.0, 3000.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if d_mirror_clearance(mid)[0] >= CLEARANCE_MARGIN:
            hi = mid
        else:
            lo = mid
    return hi


def d_mirror_centre(distance=None):
    return (distance or d_mirror_distance()) * unit_deg(probe_source_deg())


def d_mirror_normal():
    """Normal of the reflecting face: bisects the arm beam and the outgoing probe."""
    n = probe_direction() - arm_direction()
    return n / np.linalg.norm(n)


def d_mirror_clearance(distance):
    """Margin (mm) of the straight edge and its back corner from the MOT_CLEAR radius."""
    spot = d_mirror_centre(distance)
    n = d_mirror_normal()
    along = np.array([-n[1], n[0]])
    if offset_from_axis(spot + along) > offset_from_axis(spot):
        along = -along                              # the face direction towards the MOT axis
    edge = spot + D_MIRROR_EDGE_GAP_W * PROBE_WAIST * along
    corner = edge - D_MIRROR_THICKNESS * n
    closest = min(offset_from_axis(edge), offset_from_axis(corner))
    return closest - MOT_CLEAR, edge, corner


def d_mirror_distance():
    """Place the D-mirror just outside the MOT beam, in front of the retro optic if there is
    room. Otherwise behind it, if the probe passes outside the retro mount. None if neither."""
    d_min = d_mirror_distance_min() + 5.0
    if d_min + D_MIRROR_RADIUS < RETRO_DISTANCE[PROBE_AXIS]:
        return d_min
    if RETRO_DISTANCE[PROBE_AXIS] >= beyond_retro_distance():
        return RETRO_DISTANCE[PROBE_AXIS] + 40.0
    return None


def beyond_retro_distance():
    """Smallest retro distance at which the probe (1.5 w) passes outside the retro mount."""
    need = RETRO_OPTIC_RADIUS + RETRO_MOUNT_MARGIN + D_MIRROR_EDGE_GAP_W * PROBE_WAIST
    return need / math.sin(math.radians(THETA_DEG))


def mirror_between_cell_and_retro():
    return d_mirror_distance() < RETRO_DISTANCE[PROBE_AXIS]


# --- Arm, detectors and dumps ---------------------------------------------------------------

def arm_point(back):
    """Table point `back` mm upstream of M1 along the main arm."""
    return m1_centre() - back * main_arm_direction()


def parts():
    """Name -> (point, half-width) for the probe hardware in the table plane."""
    out = {"D-mirror (1\")": (d_mirror_centre(), D_MIRROR_RADIUS), "M1 (1\")": (m1_centre(), 12.7)}
    for name, back in ARM_PARTS.items():
        out[name] = (arm_point(back), 15.0)
    side = np.array([-main_arm_direction()[1], main_arm_direction()[0]])     # left of the beam
    out["PD FWM (lens, pinhole, DET36A/M)"] = (arm_point(ARM_PARTS["PBS A (pick-off, PD FWM port)"])
                                               - PD_OFFSET * side, 20.0)
    out["PD ref"] = (arm_point(ARM_PARTS["PBS B (polariser, PD ref port)"]) + PD_OFFSET * side, 15.0)
    out["transmitted-probe dump"] = (transmitted_dump(), DUMP_RADIUS)
    return out


def transmitted_dump():
    """Dump for the probe after the cloud, just outside the MOT beam on the input side of B."""
    d = probe_direction()
    for t in np.arange(100.0, 3000.0, 1.0):
        p = t * d
        if offset_from_axis(p) - DUMP_RADIUS - MOT_CLEAR >= CLEARANCE_MARGIN:
            return p
    return None


def probe_input_side_clear():
    """Is the dump before the input optics of axis B (else the probe hits the input mount)?"""
    return np.linalg.norm(transmitted_dump()) + DUMP_RADIUS < INPUT_DISTANCE[PROBE_AXIS]


def power_hwp_deg():
    """Power HWP angle that leaves PROBE_POWER at the cloud. The power PBS passes cos^2(2 theta)
    of the H input, and PBS B (after the HWP at 22.5 deg) passes half of the rest."""
    return 0.5 * math.degrees(math.acos(math.sqrt(PROBE_POWER / (0.5 * PROBE_SOURCE_POWER))))


def probe_waist_check():
    """Galilean telescope magnification against the target waist."""
    f1, f2 = TELESCOPE
    return PROBE_INPUT_RADIUS * abs(f2 / f1), (f1 + f2)


def face_crossing(direction):
    """Where a beam from the cloud along `direction` crosses the outer face it leaves through:
    (flat normal in deg, offset from the flat centre in mm)."""
    best = None
    for a in FLAT_NORMALS_DEG:
        n = unit_deg(a)
        c = direction @ n
        if c <= 1e-9:
            continue
        t = (CELL_FLAT_TO_FLAT / 2) / c
        if best is None or t < best[0]:
            best = (t, a, float(t * direction @ np.array([-n[1], n[0]])))
    return best[1], best[2]


def vacuum_parts():
    """VACUUM_PARTS plus the two glass seal tubes, as (name, x from, x to, half-width)."""
    face = CELL_FLAT_TO_FLAT / 2
    return [("seal tube, -X", -face - SEAL_TUBE_LENGTH, -face, SEAL_TUBE_RADIUS),
            ("seal tube, +X", face, face + SEAL_TUBE_LENGTH, SEAL_TUBE_RADIUS)] + VACUUM_PARTS


def vacuum_margin(point, half):
    """Plan-view distance from the nearest vacuum part, minus the part half-width (< 0: overlap)."""
    m = float("inf")
    for _, x0, x1, r in vacuum_parts():
        dx = max(x0 - point[0], 0.0, point[0] - x1)
        dy = max(abs(point[1]) - r, 0.0)
        if dx == 0 and dy == 0:
            d = -min(point[0] - x0, x1 - point[0], r - abs(point[1]))
        else:
            d = math.hypot(dx, dy)
        m = min(m, d - half)
    return m


def mot_optics():
    """Name -> (point, half-width) of the retro and input optics of both horizontal MOT axes."""
    half = RETRO_OPTIC_RADIUS + RETRO_MOUNT_MARGIN
    out = {}
    for name in AXIS_DEG:
        r = unit_deg(RETRO_DEG[name])
        out[f"retro {name}"] = (RETRO_DISTANCE[name] * r, half)
        out[f"input {name}"] = (-INPUT_DISTANCE[name] * r, half)
    return out


def beam_vacuum_margin(direction, start, stop, radius):
    """Smallest vacuum margin of a beam from the cloud, sampled from `start` to `stop` mm."""
    return min(vacuum_margin(t * direction, radius) for t in np.arange(start, stop, 1.0))


def mot_margin(point, half):
    """Distance from the 95 % aperture of either horizontal MOT beam, minus the half-width."""
    m = float("inf")
    for name in AXIS_DEG:
        a = unit_deg(AXIS_DEG[name])
        if abs(point @ a) < max(RETRO_DISTANCE[name], INPUT_DISTANCE[name]) + 50:
            m = min(m, offset_from_axis(point, name) - MOT_CLEAR - half)
    return m


def imaging_margin(point, half):
    """Distance from the old side-imaging beam (+Y) and the camera optics (-Y)."""
    if point[1] > 0:
        return abs(point[0]) - IMAGING_RADIUS - half
    return abs(point[0]) - LENS_RADIUS - half if -point[1] < CAMERA_CHIP + 40 else float("inf")


def report():
    global PROBE_WAIST
    ok = True
    print(f"probe: {THETA_DEG:.1f} deg to MOT axis {PROBE_AXIS}, travels at {deg_of(probe_direction()):.0f} deg; "
          f"enters beside the axis-{PROBE_AXIS} retro optic (left, source end)")
    mag, length = probe_waist_check()
    print(f"telescope {TELESCOPE[0]:+.0f}/{TELESCOPE[1]:+.0f} mm: {PROBE_INPUT_RADIUS} mm -> {mag:.2f} mm "
          f"(target {PROBE_WAIST} mm), {length:.0f} mm long")
    print(f"power HWP at {power_hwp_deg():.1f} deg: {PROBE_SOURCE_POWER:.0f} mW -> {PROBE_POWER} mW at the cloud "
          f"(PBS B passes half)")
    d_min = d_mirror_distance_min()
    saved, PROBE_WAIST = PROBE_WAIST, PROBE_INPUT_RADIUS
    d_small = d_mirror_distance_min()
    PROBE_WAIST = saved
    print(f"D-mirror must be >= {d_min:.0f} mm from the cloud to clear the MOT beam ({MOT_CLEAR:.1f} mm radius); "
          f"{d_small:.0f} mm without the telescope (w = {PROBE_INPUT_RADIUS} mm)")
    print(f"a {THETA_DEG:.0f} deg probe needs the axis-{PROBE_AXIS} retro optic >= {d_min + 5 + D_MIRROR_RADIUS:.0f} mm "
          f"from the cloud (D-mirror in front of it) or >= {beyond_retro_distance():.0f} mm (probe passes outside it)")
    print(f"axis-{PROBE_AXIS} retro optic at {RETRO_DISTANCE[PROBE_AXIS]:.0f} mm (ASSUMED). ", end="")
    if d_mirror_distance() is None:
        print("NO ROOM for the D-mirror. Measure the real distance.")
        return False
    if mirror_between_cell_and_retro():
        print(f"D-mirror fits in front of it at {d_mirror_distance():.0f} mm.")
    else:
        print(f"D-mirror behind it at {d_mirror_distance():.0f} mm.")
    spot = d_mirror_centre()
    margin, edge, corner = d_mirror_clearance(d_mirror_distance())
    print(f"D-mirror spot ({spot[0]:.1f}, {spot[1]:.1f}), face normal {deg_of(d_mirror_normal()):.1f} deg, "
          f"AOI {math.degrees(math.acos(abs(d_mirror_normal() @ arm_direction()))):.1f} deg, M1 AOI "
          f"{math.degrees(math.acos(abs(m1_normal() @ main_arm_direction()))):.1f} deg, "
          f"edge margin {margin:.1f} mm")
    dump = transmitted_dump()
    print(f"the axis-{PROBE_AXIS} input optic must be >= {np.linalg.norm(dump) + DUMP_RADIUS:.0f} mm from the cloud, "
          f"or the transmitted probe enters the MOT input optics")
    print(f"transmitted-probe dump at {np.linalg.norm(dump):.0f} mm ({dump[0]:.0f}, {dump[1]:.0f}); "
          f"axis-{PROBE_AXIS} input optic at {INPUT_DISTANCE[PROBE_AXIS]:.0f} mm (ASSUMED): "
          f"{'clear' if probe_input_side_clear() else 'PROBE HITS THE INPUT OPTIC MOUNT'}")
    ok &= probe_input_side_clear()
    for name, d in (("in", -probe_direction()), ("out", probe_direction())):
        a, off = face_crossing(d)
        print(f"probe {name:3s} through the flat at {a:.0f} deg, {off:+.1f} mm from its centre "
              f"({CELL_SIDE / 2 - abs(off) - PROBE_WAIST * 1.5:.1f} mm to spare at 1.5 w)")
    print("MOT optics (distances ASSUMED), margin in mm from the vacuum hardware [CAD]:")
    for name, (p, half) in mot_optics().items():
        vm = vacuum_margin(p, half)
        ok &= vm >= 0
        print(f"  {name:8s} at {deg_of(p):4.0f} deg, {np.linalg.norm(p):4.0f} mm  ({p[0]:7.1f}, {p[1]:7.1f})  "
              f"vac {vm:+6.0f}  {'ok' if vm >= 0 else 'COLLIDES'}")
    print("beams past the vacuum hardware (margin of the 95 % aperture or 1.5 w):")
    beams = {f"MOT beam {n}, {s} side": (unit_deg(RETRO_DEG[n]) * sign, d[n], MOT_CLEAR)
             for n in AXIS_DEG for s, sign, d in (("retro", 1, RETRO_DISTANCE), ("input", -1, INPUT_DISTANCE))}
    beams["probe, in"] = (-probe_direction(), d_mirror_distance(), 1.5 * PROBE_WAIST)
    beams["probe, out"] = (probe_direction(), np.linalg.norm(transmitted_dump()), 1.5 * PROBE_WAIST)
    for name, (u, length, radius) in beams.items():
        vm = beam_vacuum_margin(u, CELL_FLAT_TO_FLAT / 2, length, radius)
        ok &= vm >= 0
        print(f"  {name:22s} vac {vm:+6.0f}  {'ok' if vm >= 0 else 'CLIPS'}")
    print("parts (margin in mm from the vacuum hardware, the imaging beam and camera, the MOT beams):")
    for name, (p, half) in parts().items():
        vm, im = vacuum_margin(p, half), imaging_margin(p, half)
        mm = margin if name.startswith("D-mirror") else mot_margin(p, half)
        bad = vm < 0 or im < 0 or mm < 0
        ok &= not bad
        fmt = lambda m: "   n/a" if m == float("inf") else f"{m:+6.0f}"
        print(f"  {name:34s} ({p[0]:7.1f}, {p[1]:7.1f})  vac {fmt(vm)}  img {fmt(im)}  mot {fmt(mm)}  "
              f"{'COLLIDES' if bad else 'ok'}")
    print("\nCLEARANCE OK" if ok else "\nCLEARANCE PROBLEM")
    return ok


# --- Plan view (matplotlib, no FreeCAD needed) ----------------------------------------------

def plot(path=HERE / "fwm_probe_plan.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle

    ink, muted, mot, probe_c, sig_c, vac = "#1b2225", "#7c878b", "#c2412d", "#1f5aa6", "#8e2a8e", "#b9c1c4"
    fig, ax = plt.subplots(figsize=(10, 10), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")

    def beam(p0, p1, w, color, alpha=0.18, lw=1.4, ls="-"):
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        n = np.array([-d[1], d[0]]) * w
        ax.add_patch(Polygon([p0 + n, p1 + n, p1 - n, p0 - n], color=color, alpha=alpha, lw=0))
        ax.plot(*np.array([p0, p1]).T, color=color, lw=lw, ls=ls)

    # vacuum system along X [THESIS, CAD]
    for name, x0, x1, r in vacuum_parts():
        ax.add_patch(Rectangle((x0, -r), x1 - x0, 2 * r, color=vac, alpha=0.8, lw=0))
    ax.text(-215, 0, "main chamber\n(6\" spherical\noctagon)", ha="center", va="center", fontsize=7, color=ink)
    ax.text(-392, 0, "source\n(2D MOT)", ha="center", va="center", fontsize=7, color=ink)
    ax.text(380, 0, "bellows, gate valve", ha="center", va="center", fontsize=7, color=ink)
    r_out = CELL_FLAT_TO_FLAT / 2
    # cell
    rv = CELL_FLAT_TO_FLAT / 2 / math.cos(math.radians(22.5))
    oct_pts = [rv * unit_deg(22.5 + 45 * i) for i in range(8)]
    ax.add_patch(Polygon(oct_pts, fill=False, ec=ink, lw=1.5))
    # MOT axes
    for name in AXIS_DEG:
        u = unit_deg(RETRO_DEG[name])
        beam(-INPUT_DISTANCE[name] * u, RETRO_DISTANCE[name] * u, MOT_WAIST, mot, 0.12, 0.8)
        retro = RETRO_DISTANCE[name] * u
        n = np.array([-u[1], u[0]]) * RETRO_OPTIC_RADIUS
        ax.plot(*np.array([retro + n, retro - n]).T, color=ink, lw=4)
        ax.text(*(retro + 60 * u), "retro %s" % name, fontsize=8, ha="center", va="center", color=ink)
    fu = forward_pump_direction()
    ax.annotate("", xy=-120 * fu + 30 * fu, xytext=-120 * fu, arrowprops=dict(arrowstyle="-|>", color=mot))
    ax.text(*(-150 * fu + np.array([15, 0])), "F", color=mot, fontsize=10, weight="bold")
    ax.annotate("", xy=120 * fu - 30 * fu, xytext=120 * fu, arrowprops=dict(arrowstyle="-|>", color=mot))
    ax.text(*(150 * fu + np.array([-25, 0])), "B", color=mot, fontsize=10, weight="bold")
    # imaging
    beam(np.array([0, 450.0]), np.array([0, 60.0]), IMAGING_RADIUS, muted, 0.1, 0.8, "--")
    ax.text(8, 430, "old side-imaging beam (2 cm)", fontsize=8, color=muted, rotation=90, va="top")
    for y in (CAMERA_LENS1, CAMERA_LENS2):
        ax.add_patch(Rectangle((-LENS_RADIUS, -y - 2), 2 * LENS_RADIUS, 4, color=ink))
    ax.add_patch(Rectangle((-25, -CAMERA_CHIP - 50), 50, 50, fill=False, ec=ink, lw=1.2))
    ax.text(30, -CAMERA_CHIP - 25, "side camera\n(GT2750)", fontsize=8, va="center", color=ink)
    # probe and conjugate
    spot = d_mirror_centre()
    top = arm_point(max(ARM_PARTS.values()) + 40)
    beam(top, m1_centre(), PROBE_INPUT_RADIUS, probe_c, 0.25, 1.2)
    dump = transmitted_dump()
    beam(spot, dump, PROBE_WAIST, probe_c, 0.25, 1.4)
    off = 2.5 * np.array([-probe_direction()[1], probe_direction()[0]])
    ax.plot(*np.array([0.6 * dump + off, spot + off]).T, color=sig_c, lw=1.2)
    n = d_mirror_normal()
    along = np.array([-n[1], n[0]]) * D_MIRROR_RADIUS
    ax.plot(*np.array([spot + along, spot - along]).T, color=ink, lw=4)
    ax.add_patch(Circle(dump, DUMP_RADIUS, color=ink))
    side = np.array([-main_arm_direction()[1], main_arm_direction()[0]])
    m1 = m1_centre()
    beam(m1, spot, PROBE_WAIST, probe_c, 0.25, 1.2)
    mn = m1_normal()
    ax.plot(*np.array([m1 + 12.7 * np.array([-mn[1], mn[0]]), m1 - 12.7 * np.array([-mn[1], mn[0]])]).T,
            color=ink, lw=4)
    ax.text(*(m1 + np.array([-45, -10])), "M1", fontsize=8, color=ink)
    key = []
    for i, (name, back) in enumerate(sorted(ARM_PARTS.items(), key=lambda kv: -kv[1]), 1):
        p = arm_point(back)
        ax.add_patch(Rectangle(p - 9, 18, 18, fill=("PBS" not in name), fc="#e9edf1", ec=ink, lw=1))
        ax.text(*(p - 24 * side), str(i), fontsize=8, ha="center", va="center", color=ink)
        key.append("%d  %s" % (i, name))
    for name, (p, half) in parts().items():
        if name.startswith("PD"):
            ax.add_patch(Rectangle(p - 10, 20, 20, fc="white", ec=sig_c if "FWM" in name else ink, lw=1.5))
            below = "FWM" in name                    # above it, the label would hit part number 3
            ax.text(*(p + np.array([0, -16 if below else 16])), name.split(" (")[0], fontsize=7, ha="center",
                    va="top" if below else "bottom", color=ink)
    key += ["", "PD FWM: lens, pinhole, DET36A/M", "PD ref: probe power monitor"]
    ax.text(130, 730, "Probe arm, from the free-space\n200 mW beam:\n" + "\n".join(key), fontsize=8,
            va="top", color=ink, family="monospace")
    pa = arm_point(ARM_PARTS["PBS A (pick-off, PD FWM port)"])
    ax.plot(*np.array([pa, pa - PD_OFFSET * side]).T, color=sig_c, lw=1.2)
    ax.text(*(spot + np.array([-215, -45])), "D-mirror, %.0f mm\nfrom the cloud" % np.linalg.norm(spot),
            fontsize=8, color=ink)
    ax.text(*(dump + np.array([15, -10])), "probe dump", fontsize=8, color=ink)
    ax.text(*(0.5 * spot + np.array([-175, 15])), "probe %.0f mm w,\n%.0f° to axis B" % (
        PROBE_WAIST, THETA_DEG), fontsize=8, color=probe_c)
    ax.text(*(0.5 * spot + np.array([10, 25])), "conjugate (retraces probe)", fontsize=8, color=sig_c)
    # axes key
    ax.annotate("", xy=(-560, -480), xytext=(-620, -480), arrowprops=dict(arrowstyle="-|>", color=ink))
    ax.annotate("", xy=(-620, -420), xytext=(-620, -480), arrowprops=dict(arrowstyle="-|>", color=ink))
    ax.text(-555, -484, "+X (source → cell)", fontsize=8, va="center")
    ax.text(-620, -410, "+Y (left)", fontsize=8, ha="center")
    ax.set_xlim(-650, 650)
    ax.set_ylim(-500, 750)
    ax.set_aspect("equal")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_title("FWM probe, top view (thesis frame). Vacuum sizes from the CAD side view. "
                 "MOT optic distances: ASSUMED", fontsize=10, loc="left")
    ax.grid(True, color="#e1e0d9", lw=0.5)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()
    report()
    if args.plot:
        print("wrote", plot())
