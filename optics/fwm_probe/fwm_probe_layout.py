"""PyOpticL layout of the FWM probe around the octagonal science cell.

Run inside FreeCAD with the PyOpticL workbench installed (see README.md):
    Macro > Macros... > fwm_probe_layout.py > Execute
or render it headless-with-GUI:
    FreeCAD.exe optics/fwm_probe/build_in_freecad.py

All positions come from geometry.py, and the waveplate angles come from
polarisation.py, so the CAD model matches the checked numbers. The MOT beams and the
imaging path are context only. Set their optic positions in geometry.py to the real
table before you use the model for clearance checks.
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np
import Part
import FreeCAD as App
from PyOpticL.beam_path import BeamPath, Stop, linear_polarization
from PyOpticL.layout import Component, Layout
from PyOpticL.library import optics, thorlabs
from PyOpticL.utils import Dimension as dim
from PyOpticL.utils import cylinder_shape

import geometry as geo
import polarisation as pol

IMAGING_BEAM_RADIUS = 5.0    # mm, ASSUMED: context only


# --- Custom part definitions -----------------------------------------------------------

def _octagon_prism(flat_to_flat, z0, height):
    """Octagonal prism with flats normal to 0, 45, 90, ... deg (faces 5, 6, 7, ...)."""
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
    """Science cell (thesis Sec. 4.1.4): 4 mm glass octagon, 40 mm square flats.
    Faces 4 and 8 carry the glass-to-metal seals, drawn with ASSUMED tube and flange sizes."""

    object_group = "optics"
    object_color = (0.6, 0.8, 0.9)
    object_transparency = 70

    def shape(self):
        w = geo.CELL_WALL
        outer = _octagon_prism(geo.CELL_FLAT_TO_FLAT, -geo.CELL_HEIGHT / 2, geo.CELL_HEIGHT)
        inner = _octagon_prism(geo.CELL_FLAT_TO_FLAT - 2 * w, -geo.CELL_HEIGHT / 2 + w, geo.CELL_HEIGHT - 2 * w)
        cell = outer.cut(inner)
        half = geo.CELL_FLAT_TO_FLAT / 2
        for face in geo.SEAL_FACES:
            angle = geo.FACE_ANGLE_DEG[face]
            tube = _along(angle, half - w, geo.SEAL_TUBE_LENGTH + w, geo.SEAL_TUBE_OD)
            bore = _along(angle, half - w - 1, geo.SEAL_TUBE_LENGTH + w + 2, geo.SEAL_TUBE_OD - 2 * w)
            flange = _along(angle, half + geo.SEAL_TUBE_LENGTH, geo.CF275_FLANGE_THICKNESS,
                            geo.CF275_FLANGE_OD)
            cell = cell.fuse(tube).fuse(flange).cut(bore)
        return cell


class Vacuum_Keepout:
    """ASSUMED keep-out volume for the vacuum system along the seal axis (faces 4-8):
    main chamber (6" spherical octagon via a reducer) one side, bellows + gate valve the other."""

    object_group = "optics"
    object_color = (0.9, 0.3, 0.3)
    object_transparency = 85

    def shape(self):
        start = geo.vacuum_keepout_start() + geo.CF275_FLANGE_THICKNESS
        parts = [_along(geo.FACE_ANGLE_DEG[f], start, geo.VACUUM_KEEPOUT_LENGTH,
                        2 * geo.VACUUM_KEEPOUT_RADIUS) for f in geo.SEAL_FACES]
        return parts[0].fuse(parts[1])


class Beam_Dump:
    """Small absorbing beam dump (terminates the beam)."""

    object_group = "optics"
    object_color = (0.1, 0.1, 0.1)

    def __init__(self, diameter=geo.PROBE_DUMP_DIAMETER, depth=10.0):
        self.diameter = diameter
        self.depth = depth

    def interfaces(self):
        return [Stop(position=(0, 0, 0), rotation=(0, 0, 0), diameter=dim(self.diameter, "mm"))]

    def shape(self):
        return cylinder_shape(diameter=self.diameter, height=self.depth,
                              position=(-self.depth, 0, 0), rotation=(0, 90, 0))


def half_inch_waveplate(label, retardance, angle):
    return Component(label=label, definition=optics.Circular_Waveplate(
        diameter=dim(0.5, "in"), retardance=retardance, fast_axis_angle=angle,
        mount_definition=thorlabs.Rotation_Mount_RSP05()))


def one_inch_waveplate(label, retardance, angle):
    return Component(label=label, definition=optics.Circular_Waveplate(
        diameter=dim(1, "in"), retardance=retardance, fast_axis_angle=angle,
        mount_definition=thorlabs.Rotation_Mount_RSP1()))


def one_inch_mirror(label):
    return Component(label=label, definition=optics.Circular_Mirror(
        diameter=dim(1, "in"), mount_definition=thorlabs.Mirror_Mount_KM100()))


def angle_of(v):
    return math.degrees(math.atan2(v[1], v[0]))


# --- Layout ------------------------------------------------------------------------------

def fwm_probe_layout(forward_pump='sigma+'):
    layout = Layout("FWM probe table")
    hwp_deg, qwp_deg = pol.solve_waveplates(-1 if forward_pump == 'sigma+' else 1, 0.0)[1:]

    layout.add(Component(label="Science cell: 40 mm octagon, seals on faces 4 and 8", definition=Octagon_Cell()),
               position=(0, 0, 0), rotation=(0, 0, 0))
    layout.add(Component(label="Vacuum system keep-out (ASSUMED radius)", definition=Vacuum_Keepout()),
               position=(0, 0, 0), rotation=(0, 0, 0))

    # MOT axis 1-5: forward pump F (+x), retro-reflected as the backward pump B (context)
    mot15 = layout.add(BeamPath(label="MOT beam 1-5: forward pump F, retro B", wavelength=geo.WAVELENGTH_NM,
                                waist=dim(11, "mm"), final_distance=dim(80, "mm")),
                       position=(geo.MOT_INPUT_QWP_X - 130, 0, 0), rotation=(0, 0, 0))
    mot15.add(one_inch_waveplate("MOT 1-5 input QWP (existing)", 0.25, 45), beam_index=0b1,
              distance=dim(130, "mm"), rotation=0)
    mot15.add(one_inch_waveplate("MOT 1-5 retro QWP (existing)", 0.25, 45), beam_index=0b1,
              distance=dim(geo.MOT_RETRO_QWP_X - geo.MOT_INPUT_QWP_X, "mm"), rotation=0)
    mot15.add(one_inch_mirror("MOT 1-5 retro mirror (existing)"), beam_index=0b1,
              distance=dim(geo.MOT_RETRO_MIRROR_X - geo.MOT_RETRO_QWP_X, "mm"), rotation=180)
    mot15.recompute()  # place each path's optics before the next path is traced

    # MOT axis 3-7 (context)
    mot37 = layout.add(BeamPath(label="MOT beam 3-7", wavelength=geo.WAVELENGTH_NM,
                                waist=dim(11, "mm"), final_distance=dim(80, "mm")),
                       position=(0, geo.MOT_INPUT_QWP_X - 130, 0), rotation=(0, 0, 90))
    mot37.add(one_inch_waveplate("MOT 3-7 input QWP (existing)", 0.25, 45), beam_index=0b1,
              distance=dim(130, "mm"), rotation=90)
    mot37.add(one_inch_waveplate("MOT 3-7 retro QWP (existing)", 0.25, 45), beam_index=0b1,
              distance=dim(geo.MOT_RETRO_QWP_X - geo.MOT_INPUT_QWP_X, "mm"), rotation=90)
    mot37.add(one_inch_mirror("MOT 3-7 retro mirror (existing)"), beam_index=0b1,
              distance=dim(geo.MOT_RETRO_MIRROR_X - geo.MOT_RETRO_QWP_X, "mm"), rotation=-90)
    mot37.recompute()

    # Side imaging 2-6 (context, beam size assumed)
    start = -350 / math.sqrt(2)
    imaging = layout.add(BeamPath(label="Side imaging 2-6 (context)", wavelength=geo.WAVELENGTH_NM,
                                  waist=dim(IMAGING_BEAM_RADIUS, "mm"), final_distance=dim(700, "mm")),
                         position=(start, start, 0), rotation=(0, 0, 45))
    imaging.recompute()

    # --- Probe: fibre -> HWP -> PBS -> 90:10 pick-off -> HWP -> QWP -> lens -> D-mirror -> cloud
    spot = geo.d_mirror_centre()
    fibre_xy = tuple(geo.fibre_position())
    arm = angle_of(geo.arm_direction())                        # -90 deg
    layout.add(Component(label="Probe fibre collimator", definition=thorlabs.Fiberport_PAF2A4A()),
               position=(*fibre_xy, 0), rotation=(0, 0, arm))
    probe = layout.add(BeamPath(label="Probe", wavelength=geo.WAVELENGTH_NM,
                                waist=dim(geo.PROBE_INPUT_RADIUS, "mm"),
                                polarization=linear_polarization(0), final_distance=dim(60, "mm")),
                       position=(*fibre_xy, 0), rotation=(0, 0, arm))

    pos = geo.ARM_POSITIONS
    probe.add(half_inch_waveplate("Probe input HWP (align fibre axis to PBS)", 0.5, 0), beam_index=0b1,
              distance=dim(pos['input HWP'], "mm"), rotation=arm)
    probe.add(Component(label="Probe PBS (clean-up polariser)",
                        definition=optics.Beamsplitter_Cube_on_Surface_Adapter(
                            side_length=dim(0.5, "in"), ref_polarization=90)),
              beam_index=0b1, distance=dim(pos['PBS (clean-up polariser)'] - pos['input HWP'], "mm"),
              rotation=arm)
    pickoff = probe.add(Component(label="Pick-off plate R:T 90:10 (non-polarising)",
                                  definition=optics.Circular_Sampler(
                                      diameter=dim(1, "in"), ref_ratio=0.9,
                                      mount_definition=thorlabs.Beamsplitter_Mount_B1G())),
                        beam_index=0b1,
                        distance=dim(pos['pick-off plate R:T 90:10'] - pos['PBS (clean-up polariser)'], "mm"),
                        rotation=45)
    probe.add(Component(label="Dump: forward probe reflection (90 %)", definition=Beam_Dump(10)),
              beam_index=0b11, distance=dim(geo.PICKOFF_DUMP_DISTANCE, "mm"), rotation=180)
    # after the pick-off plate, place the optics at table y (the plate lengthens the path)
    probe.add(half_inch_waveplate(f"Probe HWP ({hwp_deg:+.0f} deg)", 0.5, hwp_deg), beam_index=0b10,
              y_position=dim(geo.arm_y(pos['HWP']), "mm"), rotation=arm)
    probe.add(half_inch_waveplate(f"Probe QWP ({qwp_deg:+.0f} deg: circular, opposite to F)", 0.25, qwp_deg),
              beam_index=0b10, y_position=dim(geo.arm_y(pos['QWP']), "mm"), rotation=arm)
    lens_at = geo.lens_distance_from_fibre()
    probe.add(Component(label=f"Probe lens f = {geo.LENS_FOCAL_LENGTH:.0f} mm",
                        definition=optics.Spherical_Lens(diameter=dim(0.5, "in"),
                                                         focal_length=dim(geo.LENS_FOCAL_LENGTH, "mm"),
                                                         mount_definition=thorlabs.Lens_Mount_L05G())),
              beam_index=0b10, y_position=dim(geo.arm_y(lens_at), "mm"), rotation=arm)
    # D-shaped mirror: modelled as a 1/2 inch disc, offset so that its straight edge is
    # D_MIRROR_EDGE_GAP from the probe on the MOT side. Hold it with a D-mirror mount from the far side.
    probe.add(Component(label=f"Probe D-mirror (edge {geo.D_MIRROR_EDGE_GAP} mm from probe, MOT side)",
                        definition=optics.Circular_Mirror(diameter=dim(0.5, "in"),
                                                          thickness=dim(geo.D_MIRROR_THICKNESS, "mm"))),
              beam_index=0b10, y_position=dim(spot[1], "mm"),
              rotation=geo.rotation_deg(geo.d_mirror_normal()),
              offset=(dim(0.25, "in") - dim(geo.D_MIRROR_EDGE_GAP, "mm"), 0))
    probe.add(Component(label="Dump: transmitted probe (retro side)", definition=Beam_Dump()),
              beam_index=0b10, x_position=dim(geo.PROBE_DUMP_X, "mm"),
              rotation=angle_of(geo.probe_direction()) + 180)

    probe.recompute()  # place the probe optics before the signal path looks for them

    # --- FWM signal: phase conjugate of the probe, back along the probe path
    back = angle_of(-geo.probe_direction())
    signal = layout.add(BeamPath(label="FWM signal (conjugate, returns along the probe)",
                                 wavelength=geo.WAVELENGTH_NM, waist=dim(geo.probe_waist_at_cloud(), "mm"),
                                 final_distance=dim(40, "mm")),
                        position=(0, 0, 0), rotation=(0, 0, back))
    signal.add(Component(label="Signal photodiode (PDA10A2, beat note later)",
                         definition=thorlabs.Photodetector_PDA10A2()),
               beam_index=0b11, distance=dim(geo.PHOTODIODE_DISTANCE, "mm"), rotation=0,
               after_object=pickoff)
    signal.recompute()

    return layout


if __name__ == "__main__":
    fwm_probe_layout().recompute()
