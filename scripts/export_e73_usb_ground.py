#!/usr/bin/env python3
"""Export actual E73 repair ground shapes; KiCad Python, read-only PCB."""
import hashlib
import json
from pathlib import Path
import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/e73-usb-repair'
LAYERS = [pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def polygons(shape):
    def points(chain):
        return [[pcb.ToMM(chain.CPoint(i).x), pcb.ToMM(chain.CPoint(i).y)]
                for i in range(chain.PointCount())]
    return [{'outer': points(shape.COutline(i)),
             'holes': [points(shape.CHole(i, h)) for h in range(shape.HoleCount(i))]}
            for i in range(shape.OutlineCount())]


def main():
    path = BASE / 'EC60-nRF52840.kicad_pcb'
    before = sha(path)
    board = pcb.LoadBoard(str(path))
    record = {'ground_copper': {}, 'ground_vertical_connectors': [],
              'ground_through_vias': [], 'physical_verification': False,
              'polygon_error_mm': .002,
              'limitation': 'Polygon approximation and connectivity only; drill voids may not be represented by every effective-shape API'}
    for layer in LAYERS:
        shapes = []
        for zone in board.Zones():
            if zone.IsOnLayer(layer) and not zone.GetIsRuleArea() and zone.GetNetname() == 'GND':
                shapes.extend(polygons(zone.GetFilledPolysList(layer)))
        for f in board.GetFootprints():
            for pad in f.Pads():
                if pad.IsOnLayer(layer) and pad.GetNetname() == 'GND':
                    shapes.extend(polygons(pad.GetEffectivePolygon(layer)))
        for track in board.GetTracks():
            if track.IsOnLayer(layer) and track.GetNetname() == 'GND':
                shape = pcb.SHAPE_POLY_SET()
                track.TransformShapeToPolygon(shape, layer, 0, pcb.FromMM(.002), pcb.ERROR_INSIDE)
                shapes.extend(polygons(shape))
        record['ground_copper'][board.GetLayerName(layer)] = shapes
    for track in board.GetTracks():
        if isinstance(track, pcb.PCB_VIA) and track.GetNetname() == 'GND':
            shape = pcb.SHAPE_POLY_SET()
            track.TransformShapeToPolygon(shape, pcb.F_Cu, 0, pcb.FromMM(.002), pcb.ERROR_INSIDE)
            record['ground_vertical_connectors'].append({'UUID': track.m_Uuid.AsString(), 'by_layer':
                {board.GetLayerName(l): polygons(shape) for l in LAYERS if track.IsOnLayer(l)}})
            record['ground_through_vias'].append({'xy': [pcb.ToMM(track.GetPosition().x), pcb.ToMM(track.GetPosition().y)]})
    for f in board.GetFootprints():
        for pad in f.Pads():
            if pad.GetAttribute() == pcb.PAD_ATTRIB_PTH and pad.GetNetname() == 'GND':
                record['ground_vertical_connectors'].append({'UUID': pad.m_Uuid.AsString(), 'by_layer':
                    {board.GetLayerName(l): polygons(pad.GetEffectivePolygon(l)) for l in LAYERS if pad.IsOnLayer(l)}})
    record['source_sha256'] = {str(p.relative_to(ROOT)): sha(p) for p in [path, Path(__file__)]}
    assert sha(path) == before
    target = ROOT / '.assembly-work/e73-usb-ground.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(record, separators=(',', ':')) + '\n')
    print('Read-only E73 ground extraction:', {k: len(v) for k, v in record['ground_copper'].items()})


if __name__ == '__main__':
    main()
