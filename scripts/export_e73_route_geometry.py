#!/usr/bin/env python3
"""Read-only native geometry for constrained incremental signal routing."""
import hashlib
import argparse
import json
from pathlib import Path
import pcbnew as p
from export_e73_usb_ground import polygons

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/e73-hhkb-corner'
LAYERS=[p.F_Cu,p.In1_Cu,p.In2_Cu,p.B_Cu]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pcb',type=Path,default=BASE/'EC60-nRF52840.kicad_pcb')
    parser.add_argument('--output',type=Path,default=ROOT/'.assembly-work/e73-corner/route-geometry.json')
    args=parser.parse_args();path=args.pcb.resolve()
    project=path.with_suffix('.kicad_pro');rules=json.loads(project.read_text())['net_settings']
    assert not rules.get('netclass_assignments'), 'Review explicit class assignments before routing'
    assert not path.with_suffix('.kicad_dru').exists(), 'Review custom rules before routing'
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    before=sha(path);b=p.LoadBoard(str(path))
    records=[]
    for f in b.GetFootprints():
        for pad in f.Pads():
            layers=[l for l in LAYERS if pad.IsOnLayer(l)]
            records.append(dict(UUID=pad.m_Uuid.AsString(),kind='pad',reference=f.GetReference(),pin=pad.GetNumber(),
                net=pad.GetNetname(),SMD=pad.GetAttribute()==p.PAD_ATTRIB_SMD,
                drill_mm=list(p.ToMM(pad.GetDrillSize())),point=list(p.ToMM(pad.GetPosition())),
                local_clearance_mm=p.ToMM(max(pad.GetLocalClearance() or 0,f.GetLocalClearance() or 0)),
                by_layer={b.GetLayerName(l):polygons(pad.GetEffectivePolygon(l))for l in layers}))
    for t in b.GetTracks():
        shapes={}
        for l in LAYERS:
            if t.IsOnLayer(l):
                poly=p.SHAPE_POLY_SET();t.TransformShapeToPolygon(poly,l,0,p.FromMM(.001),p.ERROR_OUTSIDE)
                shapes[b.GetLayerName(l)]=polygons(poly)
        records.append(dict(UUID=t.m_Uuid.AsString(),kind='via' if isinstance(t,p.PCB_VIA)else 'trace',
            net=t.GetNetname(),point=list(p.ToMM(t.GetStart())),end=list(p.ToMM(t.GetEnd())),by_layer=shapes,
            via_drill_mm=p.ToMM(t.GetDrillValue()) if isinstance(t,p.PCB_VIA) else None))
    keepouts=[]
    for z in b.Zones():
        if z.GetIsRuleArea():
            keepouts.append(dict(name=z.GetZoneName(),tracks=z.GetDoNotAllowTracks(),vias=z.GetDoNotAllowVias(),
                layers=[b.GetLayerName(l)for l in LAYERS if z.IsOnLayer(l)],polygons=polygons(z.Outline())))
    mask=[]
    for f in b.GetFootprints():
        for g in f.GraphicalItems():
            if g.GetLayer()==p.B_Mask:
                poly=p.SHAPE_POLY_SET();g.TransformShapeToPolygon(poly,p.B_Mask,0,p.FromMM(.001),p.ERROR_OUTSIDE)
                mask.extend(polygons(poly))
    outline=p.SHAPE_POLY_SET();assert b.GetBoardPolygonOutlines(outline,False)
    result=dict(copper=records,keepouts=keepouts,B_mask_openings=mask,outline=polygons(outline),
        pcb_source=str(path.relative_to(ROOT)),pcb_sha256=before,net_rules=rules,
        source_sha256={str(f.relative_to(ROOT)):sha(f)for f in [path,project,Path(__file__),ROOT/'scripts/export_e73_usb_ground.py']},
        physical_verification=False,manufacturing_released=False,polygon_error_mm=.001)
    assert sha(path)==before,'Routing extraction modified PCB'
    target=args.output.resolve();target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('Actual copper primitives:',len(records),'Keepouts:',len(keepouts))


if __name__=='__main__':main()
