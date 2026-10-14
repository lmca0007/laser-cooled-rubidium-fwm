"""Table geometry for the FWM probe, shared by the PyOpticL layout and the checks.

Frame: origin at the atom cloud, in the plane of the horizontal MOT beams.
    +x  along MOT axis 1-5 (face 1 at -x, face 5 at +x). The forward pump F
        enters through face 1 and travels +x. Its retro-reflection B travels -x.
    +y  along MOT axis 3-7 (face 3 at -y, face 7 at +y).
Octagon faces are numbered 1 to 8 counterclockwise, with face 1 at -x (180 deg),
face 2 at 225 deg (side imaging), and face 8 at 135 deg. Faces 4 and 8 carry the
glass-to-metal seals, so the vacuum system runs along the 135/315 deg axis
(the thesis X axis, along the differential pumping tube). All lengths are in mm.

Run this file to print the clearance checks:
    python optics/fwm_probe/geometry.py
"""
import math

import numpy as np

# --- Science cell (S. thesis, Sec. 4.1.4) --------------------------------------------------
# "an octagonal glass cell made from 4 mm thick glass, with 40 mm (external) square optical
#  flats on 6 sides, and glass to metal seals attached to the other two faces that oppose
#  each other."
CELL_SIDE = 40.0              # external side of each flat
CELL_HEIGHT = 40.0            # square flats: height = side
CELL_WALL = 4.0
CELL_FLAT_TO_FLAT = CELL_SIDE * (1 + math.sqrt(2))       # 96.57 mm across the flats
FACE_ANGLE_DEG = {face: 180 + 45 * (face - 1) for face in range(1, 9)}   # outward normals
SEAL_FACES = (4, 8)           # glass-to-metal seals: main chamber one side, bellows + gate valve other

# ASSUMED (not in the thesis text): seal and vacuum hardware sizes. Measure these.
SEAL_TUBE_OD = 25.4           # glass/metal tube from each seal face to its flange
SEAL_TUBE_LENGTH = 50.0       # from the outside of the face to the CF flange
CF275_FLANGE_OD = 69.85       # 2-3/4" CF flange on each seal (thesis: 6" to 2-3/4" reducer)
CF275_FLANGE_THICKNESS = 12.7
VACUUM_KEEPOUT_RADIUS = 110.0  # beyond the flanges: reducer / 6" octagon / bellows / gate valve
VACUUM_KEEPOUT_LENGTH = 600.0  # keep-out length along the axis, each side of the cell
MOUNT_HALF_WIDTH = 20.0       # half-width of a 1/2" optic in its mount, for keep-out checks

# --- Values from the lab (answers given for this layout) ----------------------------------
MOT_BEAM_RADIUS = 12.7        # the MOT beam fills 1 inch optics: edge at the 12.7 mm optic radius
MOT_NEAREST_OPTIC = 300.0     # nearest MOT-beam optic is 30 cm or more from the cloud
PROBE_WAIST = 0.12            # focused probe at the cloud, about 100 um (1/e^2 radius)

# --- Design choices (see README.md) -------------------------------------------------------
THETA_DEG = 4.0               # probe to forward-pump angle (Lezama et al. 2001 use 4 deg)
D_MIRROR_X = -280.0           # last probe mirror: inside the 300 mm free zone, 20 mm spare
D_MIRROR_EDGE_GAP = 1.5       # probe centre to the D-mirror straight edge, on the mirror face
D_MIRROR_THICKNESS = 6.0      # substrate thickness behind the straight edge
CLEARANCE_MARGIN = 1.0        # minimum gap between any probe hardware and the MOT beam edge
PROBE_ARM_LENGTH = 480.0      # fibre collimator to D-mirror, along the arm (arm runs along -y)
LENS_FOCAL_LENGTH = 500.0     # focuses the collimated probe onto the cloud
PROBE_INPUT_RADIUS = 1.0      # collimated probe 1/e^2 radius from the fibre collimator
PROBE_DUMP_X = 260.0          # probe beam dump on the retro side, before the retro optics
PROBE_DUMP_DIAMETER = 6.0     # small dump (for example a razor-blade stack) beside the MOT beam

# positions along the probe arm, measured from the fibre collimator
ARM_POSITIONS = {
    'input HWP': 30.0,          # rotates the fibre output onto the PBS transmission axis
    'PBS (clean-up polariser)': 60.0,
    'pick-off plate R:T 90:10': 110.0,
    'HWP': 160.0,
    'QWP': 185.0,
}
PICKOFF_THICKNESS = 3.0       # pick-off plate substrate, at 45 deg incidence
PICKOFF_INDEX = 1.5
PICKOFF_DUMP_DISTANCE = 40.0  # forward probe reflection (90 %) to a beam dump, towards +x
PHOTODIODE_DISTANCE = 80.0    # returning FWM signal reflection (90 %) to the photodiode, towards -x

# MOT optics positions (context only: set these to the real table)
MOT_INPUT_QWP_X = -320.0
MOT_RETRO_QWP_X = 320.0
MOT_RETRO_MIRROR_X = 350.0
WAVELENGTH_NM = 780.241


def theta():
    return math.radians(THETA_DEG)


def d_mirror_centre():
    """Point where the probe hits the D-mirror (on the probe line through the cloud)."""
    return np.array([D_MIRROR_X, -D_MIRROR_X * math.tan(theta())])


def probe_direction():
    """Unit vector of the probe after the D-mirror (towards and through the cloud)."""
    s = d_mirror_centre()
    return -s / np.linalg.norm(s)


def arm_direction():
    """The probe arm runs along -y from the fibre collimator to the D-mirror."""
    return np.array([0.0, -1.0])


def d_mirror_normal():
    """Normal of the reflecting face (bisects the incoming and outgoing directions)."""
    n = probe_direction() - arm_direction()
    return n / np.linalg.norm(n)


def rotation_deg(vector):
    return math.degrees(math.atan2(vector[1], vector[0]))


def pickoff_lateral_shift():
    """Sideways walk of the transmitted probe through the tilted pick-off plate (Snell's law).
    The plate at 45 deg moves the beam towards -x, so the fibre starts this far towards +x."""
    a = math.radians(45)
    return PICKOFF_THICKNESS * math.sin(a) * (
        1 - math.cos(a) / math.sqrt(PICKOFF_INDEX ** 2 - math.sin(a) ** 2))


def fibre_position():
    spot = d_mirror_centre()
    return np.array([spot[0] + pickoff_lateral_shift(), spot[1] + PROBE_ARM_LENGTH])


def arm_y(distance_from_fibre):
    """Table y of a point on the probe arm (the arm runs along -y)."""
    return fibre_position()[1] - distance_from_fibre


def lens_distance_from_fibre():
    """The lens sits one focal length before the cloud, along the folded path."""
    d_to_cloud = np.linalg.norm(d_mirror_centre())
    return PROBE_ARM_LENGTH - (LENS_FOCAL_LENGTH - d_to_cloud)


def probe_waist_at_cloud(wavelength_nm=WAVELENGTH_NM):
    """Focused Gaussian waist w0 = lambda f / (pi w_in) (Kogelnik & Li 1966)."""
    return wavelength_nm * 1e-6 * LENS_FOCAL_LENGTH / (math.pi * PROBE_INPUT_RADIUS)


def d_mirror_clearance():
    """Closest distance from the D-mirror hardware to the MOT axis, minus the beam radius.

    The straight edge sits D_MIRROR_EDGE_GAP from the probe spot, on the MOT side of the
    face. The substrate behind that edge reaches D_MIRROR_THICKNESS along -normal. The
    mount clamps the round side, away from the MOT beam, so it is further out."""
    spot = d_mirror_centre()
    n = d_mirror_normal()
    along_face = np.array([-n[1], n[0]])
    if along_face[1] > 0:           # choose the face direction that points towards the MOT axis
        along_face = -along_face
    edge = spot + D_MIRROR_EDGE_GAP * along_face
    back_corner = edge - D_MIRROR_THICKNESS * n
    closest = min(abs(edge[1]), abs(back_corner[1]))
    return closest - MOT_BEAM_RADIUS, edge, back_corner


def probe_dump_clearance():
    """Distance from the edge of the retro-side probe dump to the MOT beam edge."""
    y = PROBE_DUMP_X * probe_direction()[1] / probe_direction()[0]
    return abs(y) - PROBE_DUMP_DIAMETER / 2 - MOT_BEAM_RADIUS, y


def minimum_theta_for_clearance():
    """Smallest angle at which the D-mirror edge and substrate clear the MOT beam."""
    lo, hi = 0.5, 15.0
    global THETA_DEG
    saved = THETA_DEG
    try:
        for _ in range(60):
            THETA_DEG = (lo + hi) / 2
            if d_mirror_clearance()[0] >= CLEARANCE_MARGIN:
                hi = THETA_DEG
            else:
                lo = THETA_DEG
    finally:
        THETA_DEG = saved
    return hi


def seal_axis():
    """Unit vector along the vacuum axis, towards face 8."""
    a = math.radians(FACE_ANGLE_DEG[8])
    return np.array([math.cos(a), math.sin(a)])


def vacuum_keepout_start():
    """Distance from the cell centre, along the seal axis, where the CF flange starts."""
    return CELL_FLAT_TO_FLAT / 2 + SEAL_TUBE_LENGTH


def vacuum_margin(point, half_width=MOUNT_HALF_WIDTH):
    """Clearance of a part (centre `point`, half-width `half_width`) from the vacuum system.
    Inside the seal-tube zone, the tube radius applies. Beyond it, the keep-out radius applies."""
    p = np.asarray(point, dtype=float)
    s = abs(p @ seal_axis())
    r = abs(p @ np.array([-seal_axis()[1], seal_axis()[0]]))
    if s < CELL_FLAT_TO_FLAT / 2:
        return float('inf')        # beside the cell: the seal hardware is not there
    radius = SEAL_TUBE_OD / 2 if s < vacuum_keepout_start() else VACUUM_KEEPOUT_RADIUS
    if s > vacuum_keepout_start() + VACUUM_KEEPOUT_LENGTH:
        return float('inf')
    return r - radius - half_width


def probe_parts():
    """Probe hardware positions in the table plane (name -> (point, half-width))."""
    parts = {'fibre collimator': (fibre_position(), MOUNT_HALF_WIDTH)}
    for name, dist in ARM_POSITIONS.items():
        parts[name] = (np.array([fibre_position()[0], arm_y(dist)]), MOUNT_HALF_WIDTH)
    parts['lens'] = (np.array([fibre_position()[0], arm_y(lens_distance_from_fibre())]), MOUNT_HALF_WIDTH)
    parts['D-mirror'] = (d_mirror_centre(), MOUNT_HALF_WIDTH)
    pick = np.array([fibre_position()[0], arm_y(ARM_POSITIONS['pick-off plate R:T 90:10'])])
    parts['pick-off dump'] = (pick + [PICKOFF_DUMP_DISTANCE, 0], 10.0)
    parts['photodiode'] = (pick - [PHOTODIODE_DISTANCE, 0], 25.0)
    parts['retro-side probe dump'] = (np.array([PROBE_DUMP_X, PROBE_DUMP_X * probe_direction()[1]
                                                / probe_direction()[0]]), PROBE_DUMP_DIAMETER / 2)
    return parts


def probe_beam_vacuum_margin(step=2.0):
    """Smallest clearance of the probe beam (arm and folded path) from the vacuum system."""
    worst = (float('inf'), None)
    arm = [np.array([fibre_position()[0], arm_y(d)]) for d in np.arange(0, PROBE_ARM_LENGTH, step)]
    folded = [d_mirror_centre() + t * probe_direction()
              for t in np.arange(0, np.linalg.norm(d_mirror_centre()) + PROBE_DUMP_X, step)]
    for p in arm + folded:
        m = vacuum_margin(p, half_width=1.0)
        if m < worst[0]:
            worst = (m, p)
    return worst


def face_crossing(face_angle_deg, direction_sign):
    """Where the probe line crosses the outer plane of a face, as an offset along the flat."""
    a = math.radians(face_angle_deg)
    n = np.array([math.cos(a), math.sin(a)])
    d = probe_direction() * direction_sign
    t = (CELL_FLAT_TO_FLAT / 2) / (d @ n)
    p = t * d
    return float(p @ np.array([-n[1], n[0]]))


def report():
    spot = d_mirror_centre()
    margin, edge, corner = d_mirror_clearance()
    dump_margin, dump_y = probe_dump_clearance()
    print(f'probe angle to forward pump  : {THETA_DEG:.2f} deg')
    print(f'D-mirror spot                : x = {spot[0]:.1f} mm, y = {spot[1]:.2f} mm, '
          f'face normal at {rotation_deg(d_mirror_normal()):.2f} deg')
    print(f'D-mirror edge / back corner  : y = {edge[1]:.2f} / {corner[1]:.2f} mm '
          f'-> {margin:.2f} mm clear of the {MOT_BEAM_RADIUS} mm MOT beam edge')
    print(f'minimum angle for {CLEARANCE_MARGIN} mm margin: {minimum_theta_for_clearance():.2f} deg '
          f'with the D-mirror at x = {D_MIRROR_X:.0f} mm')
    print(f'retro-side probe dump        : y = {dump_y:.2f} mm at x = {PROBE_DUMP_X:.0f} mm '
          f'-> {dump_margin:.2f} mm clear of the MOT beam edge')
    print(f'probe at the retro QWP plane : y = {MOT_RETRO_QWP_X * probe_direction()[1] / probe_direction()[0]:.2f} mm')
    print(f'lens (f = {LENS_FOCAL_LENGTH:.0f} mm)         : {lens_distance_from_fibre():.1f} mm from the fibre collimator')
    print(f'probe waist at the cloud     : {probe_waist_at_cloud() * 1e3:.0f} um '
          f'(input radius {PROBE_INPUT_RADIUS} mm)')
    print(f'\nscience cell                 : {CELL_SIDE:.0f} mm flats, {CELL_FLAT_TO_FLAT:.2f} mm across the flats, '
          f'{CELL_WALL:.0f} mm glass; seals on faces {SEAL_FACES[0]} and {SEAL_FACES[1]}')
    half_flat = CELL_SIDE / 2
    for face, sign in ((1, -1), (5, 1)):
        off = face_crossing(FACE_ANGLE_DEG[face], sign)
        print(f'probe through face {face}         : {off:+.2f} mm from the flat centre '
              f'({half_flat - abs(off):.1f} mm to the flat edge)')
    faces_ok = all(abs(face_crossing(FACE_ANGLE_DEG[f], sg)) < half_flat - CELL_WALL for f, sg in ((1, -1), (5, 1)))

    print(f'\nvacuum axis (faces 4-8) keep-out: tube r = {SEAL_TUBE_OD / 2:.1f} mm to '
          f'{vacuum_keepout_start():.0f} mm, then r = {VACUUM_KEEPOUT_RADIUS:.0f} mm (ASSUMED)')
    vac_ok = True
    for name, (point, half) in probe_parts().items():
        m = vacuum_margin(point, half)
        if m < 0:
            vac_ok = False
        flag = 'COLLIDES' if m < 0 else 'ok'
        m_text = 'n/a (beside the cell)' if m == float('inf') else f'{m:+7.1f} mm'
        print(f'  {name:28s} at ({point[0]:7.1f}, {point[1]:6.1f}): {m_text}  {flag}')
    beam_margin, beam_point = probe_beam_vacuum_margin()
    if beam_margin < 0:
        vac_ok = False
        print(f'  probe beam passes through the keep-out at ({beam_point[0]:.1f}, {beam_point[1]:.1f})  COLLIDES')

    ok = (margin >= CLEARANCE_MARGIN and dump_margin >= 0 and D_MIRROR_X > -MOT_NEAREST_OPTIC
          and faces_ok and vac_ok)
    print('\nCLEARANCE OK' if ok else '\nCLEARANCE PROBLEM')
    return ok


if __name__ == '__main__':
    report()
