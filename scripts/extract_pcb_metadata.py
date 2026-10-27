#!/usr/bin/env python3
"""Run with the Python bundled with KiCad (pcbnew is required)."""
import json
import hashlib
from pathlib import Path
import pcbnew

ROOT = Path(__file__).resolve().parents[1]


def point(p):
    return [pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)]


def extract(path):
    board = pcbnew.LoadBoard(str(path))
    bounds = board.GetBoardEdgesBoundingBox()
    settings = board.GetDesignSettings()
    footprints = []
    for fp in board.GetFootprints():
        footprints.append({"reference": fp.GetReference(), "value": fp.GetValue(),
                           "footprint": str(fp.GetFPID().GetLibItemName()),
                           "xy_mm": point(fp.GetPosition()),
                           "rotation_degrees": fp.GetOrientationDegrees(),
                           "layer": board.GetLayerName(fp.GetLayer()),
                           "attributes": fp.GetAttributes(),
                           "drilled_pads": [{"number": pad.GetNumber(),
                                             "xy_mm": point(pad.GetPosition()),
                                             "drill_mm": point(pad.GetDrillSize())}
                                            for pad in fp.Pads() if pad.GetDrillSize().x]})
    return {"source": str(path.relative_to(ROOT)),
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "board_thickness_mm": pcbnew.ToMM(settings.GetBoardThickness()),
            "copper_layer_count": board.GetCopperLayerCount(),
            "aux_origin_mm": point(settings.GetAuxOrigin()),
            "edge_bounding_box_including_stroke_mm": [pcbnew.ToMM(bounds.GetX()), pcbnew.ToMM(bounds.GetY()),
                                                       pcbnew.ToMM(bounds.GetWidth()), pcbnew.ToMM(bounds.GetHeight())],
            "footprints": footprints}


if __name__ == "__main__":
    result = [extract(path) for path in sorted((ROOT / "EC60/PCB").rglob("*.kicad_pcb"))]
    destination = ROOT / "docs/audit/pcb-metadata.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Extracted {len(result)} PCB files to {destination}")
