#!/usr/bin/env python3
"""Read actual KiCad pads, fab outlines and electrode shapes for build diagrams."""
import csv
import hashlib
import json
from pathlib import Path
import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / 'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'
OUT = ROOT / '.assembly-work/build-map.json'


def xy(point):
    return [pcb.ToMM(point.x), pcb.ToMM(point.y)]


def polygons(shape):
    return [[xy(shape.COutline(i).CPoint(j)) for j in range(shape.COutline(i).PointCount())]
            for i in range(shape.OutlineCount())]


def main():
    board = pcb.LoadBoard(str(BOARD))
    outline = pcb.SHAPE_POLY_SET()
    assert board.GetBoardPolygonOutlines(outline, False)
    with (ROOT / 'hardware/bom/mainboard.csv').open() as source:
        rows = list(csv.DictReader(source))
    fitted = {ref for row in rows if int(row['Quantity']) for ref in row['References'].split(', ')}
    assert len(fitted) == 76
    parts, electrodes, holes = {}, {}, []
    for footprint in board.GetFootprints():
        ref = footprint.GetReference()
        if ref == 'REF**' or ref.startswith('H'):
            holes.extend({'at': xy(p.GetPosition()), 'drill': xy(p.GetDrillSize())}
                         for p in footprint.Pads() if p.GetDrillSize().x)
        if ref.startswith('SW') and ref not in ('SW1', 'SW100'):
            electrodes[ref] = {'at': xy(footprint.GetPosition()),
                               'pads': [{'net': p.GetNetname(), 'polygons': polygons(p.GetEffectivePolygon(pcb.F_Cu))}
                                        for p in footprint.Pads() if p.IsOnLayer(pcb.F_Cu)],
                               'polygons': [poly for p in footprint.Pads() if p.IsOnLayer(pcb.F_Cu)
                                            for poly in polygons(p.GetEffectivePolygon(pcb.F_Cu))]}
        if ref not in fitted | {'J3', 'JP1'}:
            continue
        pads, fab, paste = [], [], []
        for pad in footprint.Pads():
            if pad.IsOnLayer(pcb.B_Paste):
                paste.extend(polygons(pad.GetEffectivePolygon(pcb.B_Paste)))
            if not pad.IsOnLayer(pcb.B_Cu):
                continue
            pads.append({'number': pad.GetNumber(), 'net': pad.GetNetname(),
                         'at': xy(pad.GetPosition()), 'drill': xy(pad.GetDrillSize()),
                         'polygons': polygons(pad.GetEffectivePolygon(pcb.B_Cu))})
        for item in footprint.GraphicalItems():
            if not isinstance(item, pcb.PCB_SHAPE) or item.GetLayer() != pcb.B_Fab:
                continue
            shape = item.GetShape()
            if shape == pcb.SHAPE_T_SEGMENT:
                fab.append({'kind': 'line', 'points': [xy(item.GetStart()), xy(item.GetEnd())]})
            elif shape == pcb.SHAPE_T_RECT:
                a, b = xy(item.GetStart()), xy(item.GetEnd())
                fab.append({'kind': 'line', 'points': [a, [b[0], a[1]], b, [a[0], b[1]], a]})
            elif shape == pcb.SHAPE_T_CIRCLE:
                fab.append({'kind': 'circle', 'center': xy(item.GetCenter()), 'radius': pcb.ToMM(item.GetRadius())})
            elif shape == pcb.SHAPE_T_ARC:
                fab.append({'kind': 'arc', 'points': [xy(item.GetStart()), xy(item.GetArcMid()), xy(item.GetEnd())]})
            elif shape == pcb.SHAPE_T_POLY:
                fab.extend({'kind': 'line', 'points': poly + [poly[0]]} for poly in polygons(item.GetPolyShape()))
        assert footprint.IsFlipped(), 'Build view assumes all fitted parts are on B.Cu: ' + ref
        parts[ref] = {'value': footprint.GetValue(), 'at': xy(footprint.GetPosition()),
                      'pads': pads, 'fab': fab, 'paste': paste, 'fitted': ref in fitted}
    assert (len(electrodes), len(holes), len(parts)) == (74, 29, 78), (len(electrodes), len(holes), len(parts))
    result = {'pcb_source': str(BOARD.relative_to(ROOT)), 'pcb_sha256': hashlib.sha256(BOARD.read_bytes()).hexdigest(),
              'export_recipe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'coordinate_frame': 'Native PCB: X left-to-right and Y rear-to-front from sensing face',
              'outline': polygons(outline), 'holes': holes, 'parts': parts, 'electrodes': electrodes,
              'fitted_references': sorted(fitted), 'do_not_fit': ['JP1'], 'probe_only': ['J3']}
    daughter_path = ROOT / 'hardware/usb-daughterboard/upstream/UDB.kicad_pcb'
    daughter = pcb.LoadBoard(str(daughter_path))
    daughter_outline = pcb.SHAPE_POLY_SET()
    assert daughter.GetBoardPolygonOutlines(daughter_outline, False)
    daughter_parts = {}
    for footprint in daughter.GetFootprints():
        ref = footprint.GetReference()
        if ref not in {'J1', 'J2', 'R1', 'R2', 'U1', 'D1', 'F1'}:
            continue
        assert not footprint.IsFlipped()
        bb = footprint.GetBoundingBox(False, False)
        daughter_parts[ref] = {
            'at': xy(footprint.GetPosition()), 'value': footprint.GetValue(),
            'bbox': [pcb.ToMM(bb.GetLeft()), pcb.ToMM(bb.GetTop()), pcb.ToMM(bb.GetRight()), pcb.ToMM(bb.GetBottom())],
            'pads': [{'number': p.GetNumber(), 'net': p.GetNetname(), 'at': xy(p.GetPosition()),
                      'polygons': polygons(p.GetEffectivePolygon(pcb.F_Cu))}
                     for p in footprint.Pads() if p.IsOnLayer(pcb.F_Cu)],
        }
    assert len(daughter_parts) == 7 and daughter.GetCopperLayerCount() == 4
    result['daughterboard'] = {'parts': daughter_parts, 'outline': polygons(daughter_outline),
                              'source': str(daughter_path.relative_to(ROOT)),
                              'source_sha256': hashlib.sha256(daughter_path.read_bytes()).hexdigest()}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, separators=(',', ':')) + '\n')
    print('Read-only assembly map: 76 fitted sites, JP1 DNP, J3 probe pads, 74 electrodes, 29 holes')


if __name__ == '__main__':
    main()
