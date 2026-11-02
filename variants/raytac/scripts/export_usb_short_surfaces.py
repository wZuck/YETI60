#!/usr/bin/env python3
"""Read-only native outer copper/mask polygons for assembly illustrations."""
import hashlib
import json
from pathlib import Path
import pcbnew as pcb
from export_yeti60_usb_reference import polygons

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path = BASE / 'EC60-nRF52840.kicad_pcb'
    before = sha(path)
    board = pcb.LoadBoard(str(path))
    outline = pcb.SHAPE_POLY_SET()
    assert board.GetBoardPolygonOutlines(outline, False)
    surfaces = {}
    for name, layer, mask in [('front', pcb.F_Cu, pcb.F_Mask), ('back', pcb.B_Cu, pcb.B_Mask)]:
        copper, openings = [], []
        for zone in board.Zones():
            if zone.IsOnLayer(layer) and not zone.GetIsRuleArea():
                copper += polygons(zone.GetFilledPolysList(layer))
        for f in board.GetFootprints():
            for pad in f.Pads():
                if pad.IsOnLayer(layer):
                    copper += polygons(pad.GetEffectivePolygon(layer))
                if pad.IsOnLayer(mask):
                    openings += polygons(pad.GetEffectivePolygon(mask))
        for track in board.GetTracks():
            if track.IsOnLayer(layer):
                shape = pcb.SHAPE_POLY_SET()
                track.TransformShapeToPolygon(shape, layer, 0, pcb.FromMM(.002), pcb.ERROR_INSIDE)
                copper += polygons(shape)
        surfaces[name] = dict(copper=copper, pad_mask_openings=openings)
    result = dict(outline=polygons(outline), surfaces=surfaces, source_sha256={
        str(p.relative_to(ROOT)): sha(p) for p in [path, Path(__file__), ROOT / 'scripts/export_yeti60_usb_reference.py']},
        scope='Native copper and pad effective-mask geometry for visual appearance only; finish, mask expansion, via tenting and silkscreen are not manufacturing outputs')
    target = ROOT / '.assembly-work/usb-short-assembly/surfaces.json'
    target.write_text(json.dumps(result, separators=(',', ':')))
    assert sha(path) == before
    print('Native outer surface extraction:', {k: len(v['copper']) for k, v in surfaces.items()})


if __name__ == '__main__':
    main()
