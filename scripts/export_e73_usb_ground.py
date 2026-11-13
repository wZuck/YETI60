#!/usr/bin/env python3
"""Export actual E73 repair ground shapes; KiCad Python, read-only PCB."""
import hashlib
import argparse
import json
from pathlib import Path
import pcbnew as pcb
from check_e73_usb_repair import usb_paths
from check_yeti60_signal_paths import centerline

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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pcb', type=Path, default=BASE / 'EC60-nRF52840.kicad_pcb')
    parser.add_argument('--output', type=Path, default=ROOT / '.assembly-work/e73-usb-ground.json')
    parser.add_argument('--skip-usb-paths', action='store_true', help='Export copper/models without legacy USB path assumptions')
    parser.add_argument('--model-ref', action='append', help='Footprint for native landing export; repeatable, defaults to J4/J5/C32')
    args = parser.parse_args()
    path = args.pcb.resolve()
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
    record['USB_all_copper'] = {net: {'tracks': [], 'pads': []} for net in ['USB_DM', 'USB_DP']}
    for track in board.GetTracks():
        net = track.GetNetname()
        if args.skip_usb_paths or net not in record['USB_all_copper']:
            continue
        assert track.GetClass() in ['PCB_TRACK', 'PCB_ARC'] and track.GetLayer() == pcb.B_Cu, 'Unexpected data layer/via'
        shape = pcb.SHAPE_POLY_SET()
        track.TransformShapeToPolygon(shape, pcb.B_Cu, 0, pcb.FromMM(.002), pcb.ERROR_INSIDE)
        record['USB_all_copper'][net]['tracks'].append({'UUID': track.m_Uuid.AsString(),
            'centerline': centerline(track), 'width_mm': pcb.ToMM(track.GetWidth()), 'polygons': polygons(shape)})
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if not args.skip_usb_paths and pad.GetNetname() in record['USB_all_copper']:
                record['USB_all_copper'][pad.GetNetname()]['pads'].append({
                    'ref': footprint.GetReference(), 'pin': pad.GetNumber(),
                    'polygons': polygons(pad.GetEffectivePolygon(pcb.B_Cu))})
    record['local_model_pads'] = {}
    record['local_model_Fab_bounds_native_XY_mm'] = {}
    model_refs=set(args.model_ref or ['J4','J5','C32'])
    for footprint in board.GetFootprints():
        ref = footprint.GetReference()
        if ref not in model_refs:
            continue
        assert abs(footprint.GetOrientationDegrees()/90-round(footprint.GetOrientationDegrees()/90))<1e-6,'Review rotated Fab-envelope extraction'
        points=[]
        for graphic in footprint.GraphicalItems():
            if graphic.GetClass()=='PCB_SHAPE' and graphic.GetLayer()==pcb.B_Fab:
                assert graphic.GetShape() in [pcb.SHAPE_T_SEGMENT,pcb.SHAPE_T_RECT],'Unsupported Fab curve requires review'
                points.extend([[pcb.ToMM(p.x),-pcb.ToMM(p.y)] for p in [graphic.GetStart(),graphic.GetEnd()]])
        assert points,('Missing nominal Fab geometry',ref)
        record['local_model_Fab_bounds_native_XY_mm'][ref]=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
        pads = []
        for pad in footprint.Pads():
            shape = pcb.SHAPE_POLY_SET()
            pad.TransformShapeToPolygon(shape, pcb.B_Cu, 0, pcb.FromMM(.002), pcb.ERROR_INSIDE)
            records = polygons(shape)
            for polygon in records:
                polygon['outer'] = [[x, -y] for x, y in polygon['outer']]
                polygon['holes'] = [[[x, -y] for x, y in hole] for hole in polygon['holes']]
            pads.append({'pin': pad.GetNumber(), 'polygons_native_XY_mm': records})
        record['local_model_pads'][ref] = pads
    assert set(record['local_model_pads'])==model_refs,'Requested landing footprint is missing'
    record['USB_paths'] = None if args.skip_usb_paths else usb_paths(board)
    record['kicad_version'] = pcb.GetBuildVersion()
    record['source_sha256'] = {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): sha(p)
                             for p in [path, Path(__file__), ROOT / 'scripts/check_e73_usb_repair.py',
                                       ROOT / 'scripts/check_yeti60_signal_paths.py', ROOT / 'mechanical/pcb-fabrication-spec.json']}
    assert sha(path) == before
    target = args.output.resolve()
    target.parent.mkdir(exist_ok=True, parents=True)
    target.write_text(json.dumps(record, separators=(',', ':')) + '\n')
    print('Read-only E73 ground extraction:', {k: len(v) for k, v in record['ground_copper'].items()})


if __name__ == '__main__':
    main()
