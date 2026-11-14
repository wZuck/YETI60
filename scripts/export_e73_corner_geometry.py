#!/usr/bin/env python3
"""Export actual copper and reference geometry with polygon holes preserved."""
import argparse
import hashlib
import json
from pathlib import Path
import pcbnew as pcb
from export_e73_usb_ground import polygons

ROOT = Path(__file__).resolve().parents[1]
LAYERS = [pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pcb', type=Path, default=ROOT/'hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pcb')
    parser.add_argument('--output', type=Path, default=ROOT/'.assembly-work/e73-corner/copper.json')
    args = parser.parse_args()
    args.pcb=args.pcb.resolve();args.output=args.output.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = sha(args.pcb)
    board = pcb.LoadBoard(str(args.pcb))
    record = dict(ground_copper={}, ground_vertical_connectors=[], ground_through_vias=[],
                  B_blockers=[], USB_copper={}, ground_anchors={}, B_mask_openings=[], physical_verification=False, polygon_error_mm=.001)
    outline = pcb.SHAPE_POLY_SET()
    assert board.GetBoardPolygonOutlines(outline, False)
    record['outline'] = polygons(outline)
    for layer in LAYERS:
        shapes = []
        for z in board.Zones():
            if not z.GetIsRuleArea() and z.IsOnLayer(layer) and z.GetNetname() == 'GND':
                shapes.extend(polygons(z.GetFilledPolysList(layer)))
        for f in board.GetFootprints():
            for p in f.Pads():
                if p.IsOnLayer(layer) and p.GetNetname() == 'GND':
                    shapes.extend(polygons(p.GetEffectivePolygon(layer)))
        for t in board.GetTracks():
            if t.IsOnLayer(layer) and t.GetNetname() == 'GND':
                poly = pcb.SHAPE_POLY_SET()
                t.TransformShapeToPolygon(poly, layer, 0, pcb.FromMM(.001), pcb.ERROR_INSIDE)
                shapes.extend(polygons(poly))
        record['ground_copper'][board.GetLayerName(layer)] = shapes
    for f in board.GetFootprints():
        for g in f.GraphicalItems():
            if g.GetLayer() == pcb.B_Mask:
                poly = pcb.SHAPE_POLY_SET()
                g.TransformShapeToPolygon(poly, pcb.B_Mask, 0, pcb.FromMM(.001), pcb.ERROR_OUTSIDE)
                shapes = polygons(poly)
                record['B_mask_openings'].extend(shapes)
                # Bare clamp-contact regions must not expose USB copper.
                record['B_blockers'].extend(shapes)
        for p in f.Pads():
            if p.GetNetname() == 'GND' and f.GetReference() == 'J4':
                record['ground_anchors'][f.GetReference()+'.'+p.GetNumber()] = dict(xy=list(pcb.ToMM(p.GetPosition())),layer='B.Cu')
            if p.IsOnLayer(pcb.B_Cu) and p.GetNetname() not in ['USB_DM', 'USB_DP']:
                record['B_blockers'].extend(polygons(p.GetEffectivePolygon(pcb.B_Cu)))
            if p.GetNetname() in ['USB_DM', 'USB_DP']:
                record['USB_copper'].setdefault(p.GetNetname(), []).append(dict(kind='pad', reference=f.GetReference(), pin=p.GetNumber(),
                    by_layer={board.GetLayerName(l):polygons(p.GetEffectivePolygon(l)) for l in LAYERS if p.IsOnLayer(l)}))
            if p.GetAttribute() == pcb.PAD_ATTRIB_PTH and p.GetNetname() == 'GND':
                record['ground_vertical_connectors'].append(dict(UUID=p.m_Uuid.AsString(), by_layer={board.GetLayerName(l):polygons(p.GetEffectivePolygon(l)) for l in LAYERS if p.IsOnLayer(l)}))
    for t in board.GetTracks():
        poly = pcb.SHAPE_POLY_SET()
        if t.IsOnLayer(pcb.B_Cu) and t.GetNetname() not in ['USB_DM', 'USB_DP']:
            t.TransformShapeToPolygon(poly, pcb.B_Cu, 0, pcb.FromMM(.001), pcb.ERROR_OUTSIDE)
            record['B_blockers'].extend(polygons(poly))
        if t.GetNetname() in ['USB_DM', 'USB_DP']:
            row = dict(UUID=t.m_Uuid.AsString(), kind='via' if isinstance(t,pcb.PCB_VIA) else 'trace',
                       by_layer={}, start=list(pcb.ToMM(t.GetStart())), end=list(pcb.ToMM(t.GetEnd())))
            for layer in LAYERS:
                if t.IsOnLayer(layer):
                    q = pcb.SHAPE_POLY_SET()
                    t.TransformShapeToPolygon(q, layer, 0, pcb.FromMM(.001), pcb.ERROR_INSIDE)
                    row['by_layer'][board.GetLayerName(layer)] = polygons(q)
            record['USB_copper'].setdefault(t.GetNetname(), []).append(row)
        if isinstance(t,pcb.PCB_VIA) and t.GetNetname() == 'GND':
            poly = pcb.SHAPE_POLY_SET()
            t.TransformShapeToPolygon(poly, pcb.F_Cu, 0, pcb.FromMM(.001), pcb.ERROR_INSIDE)
            record['ground_vertical_connectors'].append(dict(UUID=t.m_Uuid.AsString(), by_layer={board.GetLayerName(l):polygons(poly) for l in LAYERS if t.IsOnLayer(l)}))
            record['ground_through_vias'].append(dict(xy=list(pcb.ToMM(t.GetPosition()))))
    paths = [args.pcb, ROOT/'hardware/e73-corner-spec.json', Path(__file__), ROOT/'scripts/export_e73_usb_ground.py']
    record['source_sha256'] = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    assert sha(args.pcb) == before
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(record,separators=(',',':'))+'\n')
    print('Exported native reference copper, blockers and USB copper; source unchanged')


if __name__ == '__main__':
    main()
