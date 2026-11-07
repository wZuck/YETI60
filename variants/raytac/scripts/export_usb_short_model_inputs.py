#!/usr/bin/env python3
"""Read native pad landing bounds independently of the STEP model exporter."""
import hashlib
import json
from pathlib import Path
import pcbnew

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'
PCB = BASE / 'EC60-nRF52840.kicad_pcb'
OUT = ROOT / '.assembly-work/usb-short-models'


def main():
    board = pcbnew.LoadBoard(str(PCB))
    parts = {}
    for footprint in board.GetFootprints():
        if not footprint.Models():
            continue
        pads = []
        for pad in footprint.Pads():
            box = pad.GetBoundingBox()
            shape = pcbnew.SHAPE_POLY_SET()
            pad.TransformShapeToPolygon(shape, footprint.GetLayer(), 0,
                                        pcbnew.FromMM(.002), pcbnew.ERROR_INSIDE)
            def points(chain):
                return [[pcbnew.ToMM(chain.CPoint(i).x), -pcbnew.ToMM(chain.CPoint(i).y)]
                        for i in range(chain.PointCount())]
            polygons = [{'outer': points(shape.COutline(i)),
                         'holes': [points(shape.CHole(i, h)) for h in range(shape.HoleCount(i))]}
                        for i in range(shape.OutlineCount())]
            pads.append({'pin': pad.GetNumber(),
                         'is_npth': pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH,
                         'drill_mm': [pcbnew.ToMM(pad.GetDrillSize().x), pcbnew.ToMM(pad.GetDrillSize().y)],
                         'polygons_native_XY_mm': polygons,
                         'bbox_native_XY_mm': [pcbnew.ToMM(box.GetLeft()), -pcbnew.ToMM(box.GetBottom()),
                                               pcbnew.ToMM(box.GetRight()), -pcbnew.ToMM(box.GetTop())],
                         'center_native_XY_mm': [pcbnew.ToMM(pad.GetPosition().x), -pcbnew.ToMM(pad.GetPosition().y)]})
        parts[footprint.GetReference()] = {'pads': pads,
                                          'back': footprint.GetLayer() == pcbnew.B_Cu,
                                          'position_pcb_mm': [pcbnew.ToMM(footprint.GetPosition().x),
                                                              pcbnew.ToMM(footprint.GetPosition().y)],
                                          'angle_deg': footprint.GetOrientationDegrees()}
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'PCB_sha256': hashlib.sha256(PCB.read_bytes()).hexdigest(), 'parts': parts}
    (OUT / 'native-inputs.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Native pad landing bounds exported for', len(parts), 'footprints')


if __name__ == '__main__':
    main()
