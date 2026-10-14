"""Build the FWM probe layout in FreeCAD, save it, and render top and isometric views.

Two ways to run it (see README.md, "Use it without Claude"):
    1. FreeCAD GUI: Macro > Macros... > set "User macros location" to this folder >
       select build_in_freecad.py > Execute.
    2. Command line: "C:\\Program Files\\FreeCAD 1.1\\bin\\FreeCAD.exe" optics\\fwm_probe\\build_in_freecad.py

Needs the PyOpticL workbench (FreeCAD Addon Manager), or set PYOPTICL_PATH to a clone of
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
            view = Gui.ActiveDocument.ActiveView
            view.viewTop()
            view.fitAll()
            view.saveImage(str(OUT / "fwm_probe_top.png"), 2400, 1600, "White")
            view.viewIsometric()
            view.fitAll()
            view.saveImage(str(OUT / "fwm_probe_iso.png"), 2400, 1600, "White")
        (OUT / "build_status.txt").write_text("OK\n")
        print(f"Saved {OUT / 'fwm_probe_table.FCStd'}")
    except Exception:
        (OUT / "build_status.txt").write_text(traceback.format_exc())
        traceback.print_exc()
    finally:
        if os.environ.get("FWM_BUILD_EXIT"):
            os._exit(0)


main()
