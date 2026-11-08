"""Build the FWM probe layout in FreeCAD, save it, and render top and isometric views.

Two ways to run it (see README.md, "Use it without Claude"):
    1. FreeCAD GUI: Macro > Macros... > set "User macros location" to this folder >
       select build_in_freecad.py > Execute.
    2. Command line: "C:\\Program Files\\FreeCAD 1.1\\bin\\FreeCAD.exe" optics\\fwm_probe\\build_in_freecad.py

Writes the renders fwm_probe_top.png and fwm_probe_iso.png next to this file, on a dark
background with lighter part colours (BACKGROUND and dark_theme below). Needs the PyOpticL
workbench (FreeCAD Addon Manager), or set PYOPTICL_PATH to a clone of
https://github.com/UMassIonTrappers/PyOpticL. Writes to optics/fwm_probe/output/.
You can run it again after you edit geometry.py: it reloads the modules each time.
"""
import importlib
import json
import os
import sys
import traceback
from pathlib import Path

try:
    HERE = Path(__file__).resolve().parent
except NameError:  # some FreeCAD versions run macros without __file__
    HERE = Path(os.environ.get("FWM_PROBE_DIR", Path.cwd()))
OUT = HERE / "output"
if os.environ.get("PYOPTICL_PATH"):
    sys.path.insert(0, os.environ["PYOPTICL_PATH"])
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import FreeCAD as App

DOC_NAME = "fwm_probe_table"

# Render theme (the saved FCStd keeps the PyOpticL colours). PyOpticL draws 780 nm as a dark red
# and mounts as dark grey, which disappear on a dark background, so the renders lighten them.
BACKGROUND = "#00273d"
BEAM_COLOR = (1.0, 0.36, 0.36)       # #ff5c5c, contrast 5:1 on the background
DARK_PART_COLOR = (0.72, 0.74, 0.78)  # mounts, dumps, camera (any grey darker than 0.35)
OPTIC_COLOR = (0.65, 0.72, 1.0)      # PyOpticL optics (0.5, 0.5, 0.8)
VACUUM_COLOR, VACUUM_TRANSPARENCY = (0.85, 0.87, 0.92), 80   # Vacuum_Keepout, not red like the beams


def beam_report(doc):
    rows = []
    for obj in doc.Objects:
        proxy = getattr(obj, "Proxy", None)
        if proxy is None or type(proxy).__name__ != "BeamPath":
            continue
        for seg in obj.BeamSegments:
            p = seg.Proxy.get_global_position()
            d = seg.Proxy.get_global_direction()
            rows.append(dict(path=obj.Label, index=seg.Proxy.index,
                             start=[round(float(v), 3) for v in p],
                             direction=[round(float(v), 5) for v in d],
                             length=round(seg.Distance.Value, 3), power=round(seg.Power.Value, 4),
                             start_object=seg.StartObject.Label if seg.StartObject else None,
                             end_object=seg.EndObject.Label if seg.EndObject else None))
    return rows


def dark_theme(doc):
    """Recolour the view objects for the dark render. Call after the FCStd is saved."""
    import fwm_probe_layout
    for obj in doc.Objects:
        view = getattr(obj, "ViewObject", None)
        if view is None or not hasattr(view, "ShapeColor"):
            continue
        proxy = type(getattr(obj, "Proxy", None)).__name__
        color = tuple(view.ShapeColor[:3])

        def near(ref):
            return all(abs(c - x) < 0.02 for c, x in zip(color, ref))
        if hasattr(obj, "StartObject") or proxy == "BeamPath":
            view.ShapeColor = BEAM_COLOR
        elif near(fwm_probe_layout.Vacuum_Keepout.object_color):
            view.ShapeColor = VACUUM_COLOR
            view.Transparency = VACUUM_TRANSPARENCY
        elif max(color) < 0.35 and max(color) - min(color) < 0.05:
            view.ShapeColor = DARK_PART_COLOR
        elif near((0.5, 0.5, 0.8)):
            view.ShapeColor = OPTIC_COLOR


def main():
    OUT.mkdir(exist_ok=True)
    try:
        # load the latest edits to the design files (FreeCAD keeps old imports in memory)
        import geometry
        import polarisation
        import fwm_probe_layout
        for module in (geometry, polarisation, fwm_probe_layout):
            importlib.reload(module)

        print("\n--- geometry.py clearance checks ---")
        geometry.report()

        # start from an empty document each time
        if DOC_NAME in App.listDocuments():
            App.closeDocument(DOC_NAME)
        doc = App.newDocument(DOC_NAME)
        App.setActiveDocument(DOC_NAME)

        layout = fwm_probe_layout.fwm_probe_layout()
        layout.recompute()
        doc.recompute()
        (OUT / "beam_segments.json").write_text(json.dumps(beam_report(doc), indent=1))
        doc.saveAs(str(OUT / "fwm_probe_table.FCStd"))
        if App.GuiUp:
            import FreeCADGui as Gui
            dark_theme(doc)
            view = Gui.ActiveDocument.ActiveView
            view.viewTop()
            view.fitAll()
            view.saveImage(str(HERE / "fwm_probe_top.png"), 2400, 1600, BACKGROUND)
            view.viewIsometric()
            view.fitAll()
            view.saveImage(str(HERE / "fwm_probe_iso.png"), 2400, 1600, BACKGROUND)
        (OUT / "build_status.txt").write_text("OK\n")
        print(f"Saved {OUT / 'fwm_probe_table.FCStd'}")
    except Exception:
        (OUT / "build_status.txt").write_text(traceback.format_exc())
        traceback.print_exc()
    finally:
        if os.environ.get("FWM_BUILD_EXIT"):
            os._exit(0)


main()
