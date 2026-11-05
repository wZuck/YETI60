#!/usr/bin/env python3
"""Continuous nominal rigid extraction, conditional on disconnected leads.

Exact planar-face prisms cover the entire PCB/plate translation; conservative
boxes cover fitted parts and PCB-mounted guides. This does not qualify cable
release, parked loose plugs, tools, key mechanisms or finished-case tolerances.
"""
import hashlib
import json
from pathlib import Path
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Vec
from cad_geometry import load, bounds, intersection_volume
from check_yeti60_assembly import box, distance
from check_usb_short_closed_assembly import hashes
from usb_short_harness import sweep_wire

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/usb-short-route'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())


def planar_sweep(shape, travel):
    bb=bounds(shape);faces=TopExp_Explorer(shape,TopAbs_FACE);choices=[]
    while faces.More():
        face=TopoDS.Face(faces.Current());fb=bounds(face)
        if abs(fb[2]-bb[2])<1e-6 and abs(fb[5]-bb[2])<1e-6:
            area=GProp_GProps();BRepGProp.SurfaceProperties_s(face,area)
            choices.append((area.Mass(),face))
        faces.Next()
    assert choices,'No planar base face for rigid sweep'
    face=max(choices,key=lambda item:item[0])[1]
    result=BRepPrimAPI_MakePrism(face,gp_Vec(0,0,bb[5]-bb[2]+travel)).Shape()
    prop=GProp_GProps();BRepGProp.VolumeProperties_s(result,prop)
    if prop.Mass()<0:result.Reverse()
    assert BRepCheck_Analyzer(result).IsValid()
    return result


def swept_box(bb,travel):
    result=bb[:];result[5]+=travel
    return box(result)


def case_check(case, moving):
    rows=[]
    for name,shape in moving:
        volume=intersection_volume(case,shape)
        assert volume<1e-6,('Rigid extraction hits bottom',name,volume)
        rows.append({'part':name,'intersection_mm3':volume,'minimum_nominal_gap_mm':distance(case,shape)})
    return rows


def limiting_points(case,moving):
    result=[]
    for name,shape in moving:
        if name not in ['plate-exact-planar-footprint','SW100']:continue
        query=BRepExtrema_DistShapeShape(case,shape);query.Perform();assert query.IsDone()
        pairs=[]
        for i in range(1,min(query.NbSolution(),5)+1):
            p,q=query.PointOnShape1(i),query.PointOnShape2(i)
            pairs.append({'case':[p.X(),p.Y(),p.Z()],'moving':[q.X(),q.Y(),q.Z()]})
        result.append({'part':name,'nominal_gap_mm':query.Value(),'nearest_point_pairs_case_mm':pairs})
    return result


def rear_clip_screen(spec, pcb, fixed):
    allowance=spec['guides']['PCB_service_XY_allowance']+spec['guides']['service_mount_position_allowance']+spec['guides']['guide_print_tolerance']+spec['guides']['case_print_wall_tolerance']
    rows=[]
    for name,shape in fixed:
        if name.startswith('USB-R'):
            gap=distance(pcb,shape)
            assert gap-allowance>=.15-1e-6,('Rear clip blocks PCB tolerance corridor',name,gap,allowance)
            rows.append({'part':name,'nominal_PCB_sweep_gap_mm':gap,'summed_allowance_mm':allowance,'remaining_gap_mm':gap-allowance})
    return rows


def main():
    spec=read(BASE/'interconnect-spec.json');travel=spec['case_service_relief']['vertical_extraction_mm']
    assembly=read(BASE/'audit/assembly.json');guides=read(BASE/'audit/guides.json')
    hashes(assembly['source_sha256']);hashes(guides['source_sha256']);hashes(guides['outputs'])
    case=load(BASE/'mechanical/yeti60-bottom-short-usb.step')
    pcb=planar_sweep(load(ROOT/'.assembly-work/pcb-placed.step'),travel)
    moving=[('PCB-exact-planar-footprint',pcb),('plate-exact-planar-footprint',planar_sweep(load(ROOT/assembly['plate_geometry']),travel))]
    moving += [(p['ref'],swept_box(p['bounds_case_mm'],travel)) for p in assembly['component_envelopes']]
    moving += [(p['name'],swept_box(p['bounds_case_mm'],travel)) for p in assembly['mated_housings'] if p['owner'] in ['J1','J5']]
    for i,p in enumerate(assembly['mounting_hole_matches']):
        x,y=p['pcb_center_case_mm'];moving.append(('stack-hardware-'+str(i+1),swept_box([x-2.1,y-2.1,-3.9,x+2.1,y+2.1,assembly['nominal_stack']['plate_bottom_z']],travel)))
    fixed=[]
    for part in guides['render_parts']:
        shape=load(ROOT/part['path'])
        if part['name'].startswith('PWR'):
            moving.append((part['name'],swept_box(bounds(shape),travel)))
        else:fixed.append((part['name'],shape))
    closed=read(BASE/'audit/closed-assembly.json')
    for pin,path in closed['nominal']['routes']['power'].items():
        # A single whole-harness box falsely fills the high straight run
        # with the low crossover/fan-out height. Bound primitives separately.
        for i,piece in enumerate(path,1):
            moving.append(('power-'+pin+'/segment-'+str(i),swept_box(bounds(sweep_wire([piece],spec['wire']['insulation_od_max'])),travel)))
    rows=case_check(case,moving)
    # Only clip/PCB clearance is tolerance-screened here. A nominal 0.2 mm
    # clip overhang used to evade static checks but is inadequate for service.
    clip_rows=rear_clip_screen(spec,pcb,fixed)
    for name,shape in fixed:
        for moving_name,sweep in moving:
            bb,bq=bounds(shape),bounds(sweep)
            if any(bb[i]>bq[i+3] or bq[i]>bb[i+3] for i in range(3)):continue
            assert intersection_volume(shape,sweep)<1e-6,('Rigid extraction hits fixed guide',moving_name,name)
    old=load(ROOT/'mechanical/generated/yeti60-bottom.step')
    regression={'unrelieved_PCB_sweep_intersection_mm3':intersection_volume(old,pcb),
        'unrelieved_module_sweep_intersection_mm3':intersection_volume(old,next(s for n,s in moving if n=='U1'))}
    assert regression['unrelieved_PCB_sweep_intersection_mm3']>1
    assert regression['unrelieved_module_sweep_intersection_mm3']>1
    sources=[Path(__file__),BASE/'interconnect-spec.json',BASE/'audit/assembly.json',BASE/'audit/guides.json',BASE/'audit/closed-assembly.json',BASE/'mechanical/yeti60-bottom-short-usb.step',ROOT/'.assembly-work/pcb-placed.step',ROOT/assembly['plate_geometry'],ROOT/'mechanical/generated/yeti60-bottom.step',ROOT/'scripts/cad_geometry.py',ROOT/'scripts/check_yeti60_assembly.py',ROOT/'scripts/usb_short_harness.py']
    report={'status':'nominal-disconnected-rigid-extraction-passed','physical_verification':False,'manufacturing_released':False,'complete_service_path_qualified':False,
        'translation_mm':[0,0,travel],'moving_envelopes':rows,'rear_clip_tolerance_screen':clip_rows,'baseline_regression':regression,'limiting_nominal_features':limiting_points(case,moving),
        'scope':'Continuous vertical translation of nominal PCB/plate, fitted mainboard envelopes, 28 stack hardware envelopes, PCB power jumper and its plugs/guides; case-top removed; USB/battery disconnected and parked outside motion envelope',
        'not_qualified':['USB/battery plug unmating, flexible-wire deformation and loose-plug parking','Actual caps, housings, domes and stabilizer moving envelopes','Combined plate/component/case tolerance motion; reported nominal gaps are not tolerance approval','Tool access, adhesion, resin/supplier first article and physical operation'],
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources}}
    (BASE/'audit/vertical-motion.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Nominal disconnected extraction passed for',len(moving),'moving envelopes; complete service remains open',flush=True)


if __name__=='__main__':main()
