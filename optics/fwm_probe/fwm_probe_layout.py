"""PyOpticL layout of the FWM probe around the octagonal science cell.

Run inside FreeCAD with the PyOpticL workbench installed (see README.md):
    Macro > Macros... > build_in_freecad.py > Execute
or from a terminal:
    FreeCAD.exe optics/fwm_probe/build_in_freecad.py

All positions come from geometry.py (thesis frame: X along the DPT, Y to the left, Z up), and
the waveplate angles from polarisation.py. For a plan view without FreeCAD, run
    python optics/fwm_probe/geometry.py --plot

Context parts follow the thesis: the 40 mm octagon with seals on the X axis [Sec. 4.1.4],
28 mm MOT beams retro-reflected by one HR-coated QWP each [Sec. 5.4.2], and the side imaging
along Y with two f = 75 mm achromats [Sec. 7.5.1]. Distances that geometry.py marks ASSUMED
(MOT optics, seal tubes, vacuum hardware) are placeholders.
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np
import Part
import FreeCAD as App
from PyOpticL.beam_path import BeamPath, Stop, _normalize_jones_vector, linear_polarization
from PyOpticL.layout import Component, Layout
from PyOpticL.library import optics, thorlabs
from PyOpticL.utils import Dimension as dim
from PyOpticL.utils import cylinder_shape

import geometry as geo
import polarisation as pol


# --- Custom part definitions -----------------------------------------------------------

def _octagon_prism(flat_to_flat, z0, height):
    """Octagonal prism with flats normal to 0, 45, 90, ... deg."""
    r = flat_to_flat / 2 / math.cos(math.radians(22.5))
    pts = [App.Vector(r * math.cos(math.radians(22.5 + 45 * i)),
                      r * math.sin(math.radians(22.5 + 45 * i)), z0) for i in range(9)]
    return Part.Face(Part.makePolygon(pts)).extrude(App.Vector(0, 0, height))


def _along(angle_deg, start, length, diameter):
    """Horizontal cylinder along angle_deg, from `start` to `start + length` from the origin."""
    a = math.radians(angle_deg)
    direction = App.Vector(math.cos(a), math.sin(a), 0)
    return Part.makeCylinder(diameter / 2, length, direction * start, direction)


class Octagon_Cell:
    """Science cell [THESIS Sec. 4.1.4]: 4 mm glass, 40 mm square flats, glass-to-metal seals on
    the two flats on the X axis. Seal tube size ASSUMED (geometry.py)."""

    object_group = "optics"
    object_color = (0.6, 0.8, 0.9)
    object_transparency = 70

    def shape(self):
        w = geo.CELL_WALL
        outer = _octagon_prism(geo.CELL_FLAT_TO_FLAT, -geo.CELL_HEIGHT / 2, geo.CELL_HEIGHT)
        inner = _octagon_prism(geo.CELL_FLAT_TO_FLAT - 2 * w, -geo.CELL_HEIGHT / 2 + w, geo.CELL_HEIGHT - 2 * w)
        cell = outer.cut(inner)
        half = geo.CELL_FLAT_TO_FLAT / 2
        for angle in geo.SEAL_DEG:
            tube = _along(angle, half - w, geo.SEAL_TUBE_LENGTH + w, 2 * geo.SEAL_TUBE_RADIUS)
            bore = _along(angle, half - w - 1, geo.SEAL_TUBE_LENGTH + w + 2, 2 * (geo.SEAL_TUBE_RADIUS - w))
            cell = cell.fuse(tube).cut(bore)
        return cell


class Vacuum_Keepout:
    """Vacuum hardware along X (geometry.VACUUM_PARTS): main chamber (spherical octagon), DPT tube
    and source at -X, bellows and gate valve at +X. Sizes from the CAD side view, drawn as
    cylinders about the X axis."""

    object_group = "optics"
    object_color = (0.9, 0.3, 0.3)
    object_transparency = 85

    def shape(self):
        shape = None
        for _, x0, x1, r in geo.VACUUM_PARTS:
            part = _along(0.0, x0, x1 - x0, 2 * r)
            shape = part if shape is None else shape.fuse(part)
        return shape


class Camera_Box:
    """Side camera body (GT2750) as a placeholder box, facing +Y."""

    object_group = "optics"
    object_color = (0.2, 0.2, 0.2)

    def shape(self):
        return Part.makeBox(50, 50, 50, App.Vector(-25, -50, -25))


class Beam_Dump:
    """Small absorbing beam dump (terminates the beam)."""

    object_group = "optics"
    object_color = (0.1, 0.1, 0.1)

    def __init__(self, diameter=2 * geo.DUMP_RADIUS, depth=10.0):
        self.diameter = diameter
        self.depth = depth

    def interfaces(self):
        return [Stop(position=(0, 0, 0), rotation=(0, 0, 0), diameter=dim(self.diameter, "mm"))]

    def shape(self):
        return cylinder_shape(diameter=self.diameter, height=self.depth,
                              position=(-self.depth, 0, 0), rotation=(0, 90, 0))


def waveplate(label, retardance, angle, inch=0.5):
    mount = thorlabs.Rotation_Mount_RSP05() if inch == 0.5 else thorlabs.Rotation_Mount_RSP1()
    return Component(label=label, definition=optics.Circular_Waveplate(
        diameter=dim(inch, "in"), retardance=retardance, fast_axis_angle=angle, mount_definition=mount))


def mirror(label, inch=1.0):
    return Component(label=label, definition=optics.Circular_Mirror(
        diameter=dim(inch, "in"), mount_definition=thorlabs.Mirror_Mount_KM100()))


def pbs(label, inch=0.5):
    return Component(label=label, definition=optics.Beamsplitter_Cube_on_Surface_Adapter(
        side_length=dim(inch, "in"), ref_polarization=90))


def lens(label, f, inch=1.0):
    kw = dict(mount_definition=thorlabs.Lens_Mount_L05G()) if inch == 0.5 else {}
    return Component(label=label, definition=optics.Spherical_Lens(
        diameter=dim(inch, "in"), focal_length=dim(f, "mm"), **kw))


def angle_of(v):
    return math.degrees(math.atan2(v[1], v[0]))


# --- Layout ------------------------------------------------------------------------------

def fwm_probe_layout(forward_pump="sigma+"):
    layout = Layout("FWM probe table (thesis frame)")
    _, hwp_deg, qwp_deg = pol.solve_waveplates(1 if forward_pump == "sigma+" else -1, 0.0)

    layout.add(Component(label="Science cell: 40 mm octagon, seals on the X axis", definition=Octagon_Cell()),
               position=(0, 0, 0), rotation=(0, 0, 0))
    layout.add(Component(label="Vacuum hardware along X (CAD side view)", definition=Vacuum_Keepout()),
               position=(0, 0, 0), rotation=(0, 0, 0))

    # Horizontal MOT axes (context). Each F beam enters at the valve end and travels towards its
    # retro at the source end (geometry.RETRO_DEG), where an HR-coated QWP returns it as B.
    for name in ("B", "A"):
        travel = geo.RETRO_DEG[name]
        start = -geo.INPUT_DISTANCE[name] * geo.unit_deg(travel)
        path = layout.add(BeamPath(label=f"MOT axis {name}: F in, B retro", wavelength=geo.WAVELENGTH_NM,
                                   waist=dim(geo.MOT_WAIST, "mm"), final_distance=dim(50, "mm")),
                          position=(*start, 0), rotation=(0, 0, travel))
        span = geo.INPUT_DISTANCE[name] + geo.RETRO_DISTANCE[name]
        path.add(mirror(f"MOT {name} retro: HR-coated QWP (one optic, [THESIS])", inch=2.0), beam_index=0b1,
                 distance=dim(span, "mm"), rotation=travel + 180)
        path.recompute()  # place each path's optics before the next path is traced

    # Side imaging (context): beam from +Y, camera optics at -Y [THESIS Sec. 7.5.1]
    imaging = layout.add(BeamPath(label="Old side-imaging beam (2 cm, from +Y)", wavelength=geo.WAVELENGTH_NM,
                                  waist=dim(geo.IMAGING_RADIUS, "mm"), final_distance=dim(80, "mm")),
                         position=(0, 450, 0), rotation=(0, 0, -90))
    imaging.add(lens("Side imaging lens 1, f = 75 mm achromat", 75), beam_index=0b1,
                distance=dim(450 + geo.CAMERA_LENS1, "mm"), rotation=-90)
    imaging.add(lens("Side imaging lens 2, f = 75 mm achromat", 75), beam_index=0b1,
                distance=dim(geo.CAMERA_LENS2 - geo.CAMERA_LENS1, "mm"), rotation=-90)
    imaging.recompute()
    layout.add(Component(label="Side camera GT2750 (placeholder box)", definition=Camera_Box()),
               position=(0, -geo.CAMERA_CHIP, 0), rotation=(0, 0, 0))

    # --- Probe: free-space beam -> power HWP + PBS -> PBS A -> HWP 22.5 -> PBS B -> QWP ->
    #     Galilean telescope -> M1 -> D-mirror -> cloud -> dump
    # PyOpticL renumbers a beam only where a cube really splits it (index i -> 2i transmitted,
    # 2i + 1 reflected). The H probe splits at the power PBS (set by the power HWP) and at PBS B
    # (45 deg after the HWP at 22.5 deg). PBS A passes it whole, so the index stays 0b10 there.
    arm = angle_of(geo.main_arm_direction())
    start_back = max(geo.ARM_PARTS.values()) + 40.0
    start = geo.arm_point(start_back)
    probe = layout.add(BeamPath(label="Probe (free space, 3 mm)", wavelength=geo.WAVELENGTH_NM,
                                waist=dim(geo.PROBE_INPUT_RADIUS, "mm"), polarization=linear_polarization(0),
                                power=geo.PROBE_SOURCE_POWER, final_distance=dim(60, "mm")),
                       position=(*start, 0), rotation=(0, 0, arm))
    order = sorted(geo.ARM_PARTS.items(), key=lambda kv: -kv[1])
    power_hwp = geo.power_hwp_deg()
    parts = {
        "lambda/2 (power)": (waveplate(f"Power HWP ({power_hwp:.1f} deg)", 0.5, power_hwp), 0b1),
        "PBS (power dump)": (pbs("Power PBS (reflection to a dump)"), 0b1),
        "PBS A (pick-off, PD FWM port)": (pbs("PBS A: pick-off, 4th port to PD FWM"), 0b10),
        "lambda/2 at 22.5 deg": (waveplate("HWP at 22.5 deg", 0.5, 22.5), 0b10),
        "PBS B (polariser, PD ref port)": (pbs("PBS B: polariser, reflection to PD ref"), 0b10),
        "lambda/4 (circular)": (waveplate(f"Probe QWP ({qwp_deg:+.0f} deg, same sigma as F)", 0.25, qwp_deg),
                                0b100),
        "telescope f = -75 mm": (lens("Telescope f = -75 mm", geo.TELESCOPE[0], 0.5), 0b100),
        "telescope f = +200 mm": (lens("Telescope f = +200 mm", geo.TELESCOPE[1]), 0b100),
    }
    placed = {}
    last = start_back
    for name, back in order:
        comp, index = parts[name]
        placed[name] = probe.add(comp, beam_index=index, distance=dim(last - back, "mm"), rotation=arm)
        last = back
    probe.add(Component(label="Dump: power PBS reflection", definition=Beam_Dump()), beam_index=0b11,
              distance=dim(40, "mm"), rotation=arm + geo.PBS_REFLECT_TURN)
    probe.add(Component(label="PD ref (probe power monitor)", definition=thorlabs.Photodetector_PDA10A2()),
              beam_index=0b101, distance=dim(geo.PD_OFFSET, "mm"), rotation=arm + geo.PBS_REFLECT_TURN)
    probe.add(mirror("M1 (1\")"), beam_index=0b100, distance=dim(last, "mm"),
              rotation=angle_of(geo.m1_normal()))
    # D-shaped mirror: a 1" disc offset so that its straight edge is 1.5 w from the probe, on the
    # MOT side. Hold it from the round side with a D-mirror mount.
    gap = geo.D_MIRROR_EDGE_GAP_W * geo.PROBE_WAIST
    probe.add(Component(label=f"D-mirror 1\" (edge {gap:.0f} mm from the probe, MOT side)",
                        definition=optics.Circular_Mirror(diameter=dim(1, "in"),
                                                          thickness=dim(geo.D_MIRROR_THICKNESS, "mm"))),
              beam_index=0b100, distance=dim(geo.M1_GAP, "mm"),
              rotation=angle_of(geo.d_mirror_normal()), offset=(dim(0.5, "in") - dim(gap, "mm"), 0))
    dump = geo.transmitted_dump()
    probe.add(Component(label="Dump: transmitted probe (before the axis-B input optics)", definition=Beam_Dump()),
              beam_index=0b100, distance=dim(float(np.linalg.norm(geo.d_mirror_centre()) + np.linalg.norm(dump)), "mm"),
              rotation=angle_of(geo.probe_direction()))
    probe.recompute()  # place the probe optics before the signal path looks for them

    # --- FWM signal: the phase conjugate of the probe at the cloud (complex conjugate Jones vector),
    # back along the probe path. The QWP turns it into H, so PBS B passes it whole (index 0b1). The
    # HWP at 22.5 deg turns it to 45 deg, and PBS A reflects half into its 4th port (0b11).
    at_cloud = [s.Proxy for s in probe.get_object().BeamSegments if s.Proxy.index == 0b100][-1]
    conjugate = np.conj(_normalize_jones_vector(at_cloud.polarization_jones))
    signal = layout.add(BeamPath(label="FWM conjugate (retraces the probe)", wavelength=geo.WAVELENGTH_NM,
                                 waist=dim(geo.PROBE_WAIST, "mm"), polarization=conjugate,
                                 power=geo.CONJUGATE_POWER, final_distance=dim(40, "mm")),
                        position=(0, 0, 0), rotation=(0, 0, angle_of(-geo.probe_direction())))
    signal.add(Component(label="PD FWM: lens, pinhole, DET36A/M at 100 kOhm",
                         definition=thorlabs.Photodetector_PDA10A2()),
               beam_index=0b11, distance=dim(geo.PD_OFFSET, "mm"), rotation=angle_of(-geo.main_arm_direction())
               + geo.PBS_REFLECT_TURN, after_object=placed["PBS A (pick-off, PD FWM port)"])
    signal.recompute()
    return layout


if __name__ == "__main__":
    fwm_probe_layout().recompute()
