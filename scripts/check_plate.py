#!/usr/bin/env python3
"""Check plate DXF and match its mirrored screw centres to source PCB holes.

Run with: uv run --with ezdxf python scripts/check_plate.py
"""
import hashlib
import json
import math
from pathlib import Path

import ezdxf
from ezdxf import bbox

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / "felk60/felk60_plate_hhkb.dxf"
    doc = ezdxf.readfile(path)
    audit = doc.audit()
    model = doc.modelspace()
    bounds = bbox.extents(model)
    polylines = list(model.query("LWPOLYLINE"))
    circles = list(model.query("CIRCLE"))
    def geometry_signature(document):
        signature = []
        for entity in document.modelspace():
            if entity.dxftype() == "CIRCLE":
                geometry = [*entity.dxf.center, entity.dxf.radius]
            elif entity.dxftype() == "LWPOLYLINE":
                geometry = [int(entity.closed), *[v for point in entity.get_points("xyseb") for v in point]]
            else:
                raise ValueError(f"Unreviewed DXF entity type: {entity.dxftype()}")
            signature.append([entity.dxftype(), entity.dxf.layer, [round(v, 9) for v in geometry]])
        return signature
    original_geometry = geometry_signature(doc)
    fixes = [{"code": int(f.code), "message": f.message} for f in audit.fixes]
    # Only dictionary ownership metadata repairs are authorized here. Do not
    # silently accept a geometry-affecting recovery as equivalent geometry.
    if audit.errors or any(f["code"] != 202 for f in fixes):
        raise ValueError("DXF needs repairs beyond the reviewed owner-handle metadata fix")
    normalized_path = ROOT / "mechanical/felk60_plate_hhkb.audited.dxf"
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(normalized_path)
    normalized = ezdxf.readfile(normalized_path)
    normalized_audit = normalized.audit()
    geometry_preserved = geometry_signature(normalized) == original_geometry
    if not geometry_preserved or normalized_audit.errors or normalized_audit.fixes:
        raise ValueError("Normalized plate DXF did not preserve geometry or audit cleanly")
    metadata = json.loads((ROOT / "docs/audit/pcb-metadata.json").read_text())
    board = next(b for b in metadata if b["source"].endswith("/EC60.kicad_pcb"))
    if board["source_sha256"] != hashlib.sha256((ROOT / board["source"]).read_bytes()).hexdigest():
        raise ValueError("Stale PCB metadata")
    holes = [{"ref": fp["reference"], **pad} for fp in board["footprints"]
             if fp["reference"].startswith("H") or fp["reference"] == "REF**"
             for pad in fp["drilled_pads"]]
    matches = []
    seen = set()
    for circle in circles:
        x, y = -circle.dxf.center.x, circle.dxf.center.y
        distances = [(math.hypot(x - h["xy_mm"][0], y - h["xy_mm"][1]), index)
                     for index, h in enumerate(holes)]
        distance, index = min(distances)
        if index in seen:
            raise ValueError("More than one plate circle matches a PCB hole")
        seen.add(index)
        matches.append({"plate_center_in_PCB_frame_mm": [x, y],
                        "plate_hole_diameter_mm": 2 * circle.dxf.radius,
                        "pcb_reference": holes[index]["ref"], "pcb_center_mm": holes[index]["xy_mm"],
                        "pcb_drill_mm": holes[index]["drill_mm"], "center_offset_mm": distance})
    valid_dxf = (doc.units == 4 and not audit.errors and geometry_preserved
                 and polylines and not any(not p.closed for p in polylines))
    # This is a correspondence check, not a tolerance/fastener acceptance limit.
    matched = len(matches) == len(holes) and max(m["center_offset_mm"] for m in matches) < 0.1
    report = {"status": "repaired-copy-geometry-and-hole-correspondence-checked-fit-unverified"
                         if valid_dxf and matched else "plate-check-failed",
              "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "pcb_source_sha256": board["source_sha256"],
              "units_mm": doc.units == 4, "DXF_audit_errors": len(audit.errors),
              "DXF_audit_fixes": len(audit.fixes), "polylines": len(polylines),
              "original_metadata_repairs": fixes,
              "normalized_copy": str(normalized_path.relative_to(ROOT)),
              "normalized_sha256": hashlib.sha256(normalized_path.read_bytes()).hexdigest(),
              "normalized_audit_errors": len(normalized_audit.errors),
              "normalized_audit_fixes": len(normalized_audit.fixes),
              "geometry_preserved_to_mm": 1e-9,
              "all_polylines_closed": all(p.closed for p in polylines),
              "screw_circles": len(circles), "PCB_mount_holes": len(holes),
              "size_mm": list(bounds.size), "transform": "PCB x = -DXF x; PCB y = DXF y",
              "max_center_offset_mm": max(m["center_offset_mm"] for m in matches),
              "hole_matches": matches,
              "unverified": ["thread specification and tolerance stack", "cutout-to-switch clearance",
                             "plate thickness (DXF is 2D; FELK60 specifies 1.2mm steel)",
                             "resin case, gasket compression and assembled interference"]}
    (ROOT / "docs/audit/plate.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(report["status"], "max center offset mm:", report["max_center_offset_mm"])
    if not valid_dxf or not matched:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
