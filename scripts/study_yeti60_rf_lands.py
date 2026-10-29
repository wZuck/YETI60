#!/usr/bin/env python3
"""Read-only native land support check for the proposed RF wing placements."""
import hashlib
import json
from pathlib import Path
import pcbnew as pcb

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def rectangle(bb):
    x,y,X,Y=bb;poly=pcb.SHAPE_POLY_SET();poly.NewOutline()
    for a,b in [(x,y),(X,y),(X,Y),(x,Y)]:poly.Append(pcb.FromMM(a),pcb.FromMM(b))
    return poly


def main():
    specpath=ROOT/'mechanical/rf-remediation.json';spec=json.loads(specpath.read_text())
    records={};sources=[specpath,Path(__file__)]
    for name,folder in [('e73',ROOT),('raytac',ROOT/'variants/raytac')]:
        path=folder/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb';sources.append(path)
        rules=json.loads(path.with_suffix('.kicad_pro').read_text())
        rule=rules['board']['design_settings']['rules']['min_copper_edge_clearance']
        assert rule==spec['minimum_native_copper_to_edge']
        allowance=rule+spec['additional_fabrication_outline_allowance']
        sources.append(path.with_suffix('.kicad_pro'))
        before=sha(path);board=pcb.LoadBoard(str(path))
        outline=pcb.SHAPE_POLY_SET();assert board.GetBoardPolygonOutlines(outline,False)
        outline.BooleanAdd(rectangle(spec['proposed_PCB_wing_XY']))
        module=next(f for f in board.GetFootprints() if f.GetReference()=='U1')
        pose=spec['placements'][name];module.SetOrientationDegrees(pose['rotation_deg'])
        module.SetPosition(pcb.VECTOR2I(*[pcb.FromMM(v) for v in pose['origin_PCB_XY']]))
        margins=[];pads=[]
        for pad in module.Pads():
            outside=pcb.SHAPE_POLY_SET();outside.BooleanSubtract(pad.GetEffectivePolygon(pcb.B_Cu),outline)
            assert outside.Area()<1, (name,pad.GetNumber(),'land outside proposed board')
            bb=pad.GetBoundingBox();bounds=[pcb.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]
            enlarged=rectangle([bounds[0]-allowance,bounds[1]-allowance,bounds[2]+allowance,bounds[3]+allowance])
            outside=pcb.SHAPE_POLY_SET();outside.BooleanSubtract(enlarged,outline)
            assert outside.Area()<1, (name,pad.GetNumber(),'less than native copper-to-edge plus fabrication allowance')
            margin=spec['proposed_PCB_wing_XY'][2]-bounds[2];margins.append(margin)
            pads.append({'number':pad.GetNumber(),'net':pad.GetNetname(),'copper_bbox_mm':bounds})
        assert sha(path)==before
        records[name]={'land_count':len(pads),'all_lands_supported':True,'native_copper_edge_rule_mm':rule,
                       'fabrication_allowance_mm':spec['additional_fabrication_outline_allowance'],
                       'combined_conservative_edge_allowance_passed':True,
                       'minimum_right_edge_margin_mm':min(margins),'pads':pads,'source_mutated':False}
    report={'status':'candidate-land-support-passed-native-routing-pending','candidate_only':True,
            'production_approved':False,'physical_verification':False,'variants':records,
            'limits':['Original outline plus proposed rectangular wing only; corner fillets must preserve these margins',
                      'No routing, DRC, intercomponent collision or solder-joint strength acceptance'],
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources}}
    (ROOT/'docs/audit/rf-remediation-lands.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({name:{k:v for k,v in r.items() if k!='pads'} for name,r in records.items()},indent=2))


if __name__=='__main__':main()
