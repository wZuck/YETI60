#!/usr/bin/env python3
"""Export and validate 16 removable guides, retention films and print-oriented STLs."""
import json,hashlib
from pathlib import Path
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf,gp_Ax1,gp_Pnt,gp_Dir,gp_Vec
from cad_geometry import load,bounds,intersection_volume
from check_yeti60_assembly import box,distance,move
from check_yeti60_interconnects import write_step,near
from check_usb_short_closed_assembly import input_data,obstacles,hashes
from usb_short_guides import build
from usb_short_harness import envelope_wire
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/usb-short-route';OUT=BASE/'mechanical/guides';WORK=ROOT/'.assembly-work/usb-short-closed'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    OUT.mkdir(parents=True,exist_ok=True);report=json.loads((BASE/'audit/closed-assembly.json').read_text());hashes(report['source_sha256']);spec=json.loads((BASE/'interconnect-spec.json').read_text());assembly,source,exits=input_data(spec);case=load(BASE/'mechanical/yeti60-bottom-short-usb.step');top=load(ROOT/'mechanical/generated/yeti60-top.step');nominal=report['nominal']['routes'];parts,films=build(spec,case,nominal,exits);records=[];render=[];outputs={};profile=json.loads((ROOT/'mechanical/pcb-fabrication-spec.json').read_text())
    for actual in [profile['CAD_finished_envelope_mm'],*profile['ordinary_thickness_acceptance_range_mm']]:
        delta=profile['CAD_finished_envelope_mm']-actual;obs=obstacles(assembly,source,delta);pack=box(assembly['battery_candidates'][0]['bounds_case_mm']);wiredata=report['nominal'] if delta==0 else None
        from usb_short_harness import paths,paired_data
        routes,centre=paths(spec,exits,delta);routes['usb'].update(paired_data(centre,spec)[0]);foreign={f:[envelope_wire(p,spec['wire']['insulation_od_max']+2*spec['wire']['case_and_route_position_allowance']) for p in wires.values()] for f,wires in routes.items()};own_nominal={f:[envelope_wire(p,spec['wire']['insulation_od_max']) for p in wires.values()] for f,wires in routes.items()}
        for part in parts:
            shift=delta if part['mount'].startswith('PCB') else 0;shape=move(part['shape'],z=shift);bb=bounds(shape);hits={}
            assert max(intersection_volume(shape,c) for c in [case,top,pack])<1e-6,(part['name'],'case/pack',actual)
            for label,q in obs:
                if near(bb,bounds(q),.2):
                    gap=distance(shape,q);hits[label]=gap;assert gap>=.15-1e-6,(part['name'],actual,label,gap)
            own_gap=min(distance(shape,q) for q in own_nominal[part['family']] if near(bb,bounds(q),.2))
            assert own_gap>=.05-1e-6,(part['name'],actual,'channel-to-insulation clearance',own_gap)
            for family,wires in foreign.items():
                if family==part['family']:continue
                for i,q in enumerate(wires):
                    if near(bb,bounds(q),.2):assert distance(shape,q)>=.15-1e-6,(part['name'],actual,'foreign harness',family,i,distance(shape,q))
            if delta==0:
                target=OUT/(part['name']+'.step');write_step(shape,target);outputs[str(target.relative_to(ROOT))]=sha(target);render.append({'name':part['name'],'path':str(target.relative_to(ROOT)),'sha256':sha(target),'category':'guide','color':'gray','group':'interconnect'})
                # STL orientation is explicit and independent of case coordinates.
                printable=shape;flipped=part['mount'].startswith('PCB') or part['mount']=='case-roof' or part['mount']=='removable-cover'
                if flipped:
                    tr=gp_Trsf();tr.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(1,0,0)),3.141592653589793);printable=BRepBuilderAPI_Transform(shape,tr,True).Shape()
                b=bounds(printable);printable=move(printable,-b[0],-b[1],-b[2]);BRepMesh_IncrementalMesh(printable,.005,False,.08,True).Perform();stl=StlAPI_Writer();stl.ASCIIMode=False;target=target.with_suffix('.stl');assert stl.Write(printable,str(target));outputs[str(target.relative_to(ROOT))]=sha(target)
                records.append({'name':part['name'],'quantity':1,'mount':part['mount'],'harness':part['family'],'datum_case_mm':part['datum_case_mm'],'bounds_case_mm':bb,'print_STL_bounds_mm':bounds(printable),'print_flip_about_X_deg':180 if flipped else 0,'STEP_preserves_case_coordinates':True,'bond_pair':part['bond_pair'],'nearest_retained_part_gap_mm':min(hits.values(),default=999),'minimum_channel_to_nominal_insulation_gap_mm':own_gap})
        for i,left in enumerate(parts):
            a=move(left['shape'],z=delta if left['mount'].startswith('PCB') else 0)
            for right in parts[:i]:
                b=move(right['shape'],z=delta if right['mount'].startswith('PCB') else 0)
                if near(bounds(a),bounds(b),.05):assert intersection_volume(a,b)<1e-6,(left['name'],right['name'],'guide collision',actual)
        for film in films:
            shift=delta if film['name'].startswith('PWR') else 0;shape=move(film['shape'],z=shift);bb=bounds(shape)
            assert max(intersection_volume(shape,c) for c in [case,top,pack])<1e-6,(film['name'],'film collision',actual)
            for label,q in obs:
                if near(bb,bounds(q),.2):assert distance(shape,q)>=.15-1e-6,(film['name'],label,actual,distance(shape,q))
            if delta==0:
                target=WORK/(film['name']+'.step');write_step(shape,target);render.append({k:v for k,v in film.items() if k!='shape'}|{'path':str(target.relative_to(ROOT)),'sha256':sha(target)})
        print('Guides/retention at thickness',actual,'passed',flush=True)
    assert len(records)==16
    inputs=[BASE/'audit/closed-assembly.json',BASE/'interconnect-spec.json',Path(__file__),ROOT/'scripts/usb_short_guides.py',ROOT/'scripts/usb_short_harness.py'];result={'status':'sixteen-guides-and-retention-passed','physical_verification':False,'parts':records,'part_count':16,'film_strips':len(films),'outputs':outputs,'render_parts':render,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in inputs},'printing':{'units':'mm','part_tolerance_mm':spec['guides']['guide_print_tolerance'],'minimum_floor_or_roof_web_mm':.3,'material':'Dimensionally qualified, post-cured tough engineering resin; deburr all channels','supports':'Keep support scars outside channels and bond datums; measure coupons before assembly'},'limits':['Adhesive retention and wire springback are physical acceptance items','Guide-to-case and guide-to-PCB bond interfaces intentionally use the specified tape gaps; non-bonded foreign parts are checked independently']}
    (BASE/'audit/guides.json').write_text(json.dumps(result,indent=2)+'\n');print('16 STEP/STL guide pairs exported')
if __name__=='__main__':main()
