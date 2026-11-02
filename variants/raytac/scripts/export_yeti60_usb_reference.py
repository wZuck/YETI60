#!/usr/bin/env python3
"""Read-only native copper extraction for the Raytac USB reference screen."""
import hashlib
import json
from pathlib import Path
import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polygons(shape):
    def points(chain):
        return [[pcb.ToMM(chain.CPoint(i).x), pcb.ToMM(chain.CPoint(i).y)]
                for i in range(chain.PointCount())]
    return [{'outer': points(shape.COutline(i)),
             'holes': [points(shape.CHole(i, h)) for h in range(shape.HoleCount(i))]}
            for i in range(shape.OutlineCount())]


def main():
    path = ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'
    before = sha(path)
    board = pcb.LoadBoard(str(path))
    layers = {}
    for layer in [pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu]:
        shapes = []
        for zone in board.Zones():
            if zone.IsOnLayer(layer) and not zone.GetIsRuleArea() and zone.GetNetname() == 'GND':
                shapes.extend(polygons(zone.GetFilledPolysList(layer)))
        for footprint in board.GetFootprints():
            for pad in footprint.Pads():
                if pad.IsOnLayer(layer) and pad.GetNetname() == 'GND':
                    shapes.extend(polygons(pad.GetEffectivePolygon(layer)))
        for track in board.GetTracks():
            if track.IsOnLayer(layer) and track.GetNetname() == 'GND':
                shape = pcb.SHAPE_POLY_SET()
                track.TransformShapeToPolygon(shape, layer, 0, pcb.FromMM(.002), pcb.ERROR_INSIDE)
                shapes.extend(polygons(shape))
        layers[board.GetLayerName(layer)] = shapes
    vias = [{'xy': [pcb.ToMM(t.GetPosition().x), pcb.ToMM(t.GetPosition().y)],
             'diameter_mm': pcb.ToMM(t.GetWidth(pcb.F_Cu))}
            for t in board.GetTracks() if isinstance(t, pcb.PCB_VIA) and t.GetNetname() == 'GND']
    record = {'ground_copper': layers, 'ground_through_vias': vias,
              'polygon_error_mm': .002,
              'scope': 'Filled zones plus ground pads/tracks/vias; pad/via drill voids are not resolved by all native effective-shape APIs',
              'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [path, Path(__file__)]}}
    assert sha(path) == before
    target = ROOT/'.assembly-work/usb-reference-inputs.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(record, separators=(',', ':'))+'\n')
    print('Read-only USB reference extraction:', {k: len(v) for k, v in layers.items()}, 'ground vias:', len(vias))


if __name__ == '__main__':
    main()
