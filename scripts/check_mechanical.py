#!/usr/bin/env python3
"""Inspect original STEP solids and the FELK60 plate DXF without altering them.

Run with: uv run --with cadquery-ocp --with ezdxf python scripts/check_mechanical.py
This checks source geometry, not resin printability or final assembly clearance.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

import ezdxf
from ezdxf import bbox
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL
from OCP.TopExp import TopExp_Explorer

ROOT = Path(__file__).resolve().parents[1]


def count(shape, kind):
    explorer = TopExp_Explorer(shape, kind)
    total = 0
    while explorer.More():
        total += 1
        explorer.Next()
    return total


def inspect_step(path):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise ValueError(f"STEP read failed: {path}")
    if reader.TransferRoots() < 1:
        raise ValueError(f"No transferable STEP roots: {path}")
    shape = reader.OneShape()
    if shape.IsNull():
        raise ValueError(f"Null STEP shape: {path}")
    bounds = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, bounds, False, False)
    lower, upper = bounds.CornerMin(), bounds.CornerMax()
    values = (lower.X(), lower.Y(), lower.Z(), upper.X(), upper.Y(), upper.Z())
    volume = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, volume)
    return {"path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "brep_valid": BRepCheck_Analyzer(shape).IsValid(),
            "solids": count(shape, TopAbs_SOLID), "shells": count(shape, TopAbs_SHELL),
            "bounds_mm": list(values),
            "size_mm": [values[i + 3] - values[i] for i in range(3)],
            "volume_mm3": volume.Mass()}


def inspect_dxf(path):
    doc = ezdxf.readfile(path)
    audit = doc.audit()
    space = doc.modelspace()
    bounds = bbox.extents(space)
    polylines = list(space.query("LWPOLYLINE"))
    circles = list(space.query("CIRCLE"))
    return {"path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "units": doc.units, "units_are_mm": doc.units == 4,
            "entities": dict(Counter(e.dxftype() for e in space)),
            "audit_errors": len(audit.errors), "audit_fixes": len(audit.fixes),
            "open_polylines": sum(not p.closed for p in polylines),
            "size_mm": list(bounds.size),
            "circle_diameters_mm": sorted({round(2 * e.dxf.radius, 6) for e in circles}),
            "coordinate_note": "DXF X is mirrored relative to positive-X EC60 PCB coordinates; assembly transform must be explicit"}


def main():
    steps = [inspect_step(p) for p in sorted((ROOT / "felk60").glob("*.step"))]
    if not steps:
        raise ValueError("No FELK60 STEP files found")
    original_dxf = inspect_dxf(ROOT / "felk60/felk60_plate_hhkb.dxf")
    plate_report = json.loads((ROOT / "docs/audit/plate.json").read_text())
    dxf = inspect_dxf(ROOT / plate_report["normalized_copy"])
    if (plate_report["source_sha256"] != original_dxf["sha256"] or
            plate_report["normalized_sha256"] != dxf["sha256"]):
        raise ValueError("Stale repaired DXF verification; rerun check_plate.py")
    valid = (all(v["brep_valid"] and v["solids"] > 0 and v["volume_mm3"] > 0 for v in steps)
             and dxf["units_are_mm"] and not dxf["audit_errors"]
             and not dxf["audit_fixes"] and not dxf["open_polylines"])
    report = {"status": "BRep-and-repaired-DXF-valid-assembly-unverified" if valid else "source-geometry-check-failed",
              "step": steps, "original_plate_dxf": original_dxf, "checked_plate_dxf": dxf,
              "unverified": ["top/bottom/PCB/plate assembly transforms and interference",
                             "resin inserts, wall thickness, shrinkage, supports and print orientation",
                             "battery/module/connector envelopes and antenna keepout",
                             "final production STL watertight mesh and physical fit"]}
    destination = ROOT / "docs/audit/mechanical.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
