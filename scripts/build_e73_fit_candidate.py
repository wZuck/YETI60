#!/usr/bin/env python3
"""Build and inspect E73-only plate/floor repair; do not select it for production."""
import hashlib
import json
import math
from pathlib import Path
import ezdxf
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from shapely.geometry import Point
from cad_geometry import load, bounds, intersection_volume
from build_yeti60_mechanical import rounded_box, cut
from check_yeti60_interconnects import write_step
from check_yeti60_assembly import distance
from e73_fit_geometry import (profiles, internal_contract, build_shape,
    plate_envelope, switch_envelope, screen, gasket_coverage, volume, external_faces)

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/'mechanical/e73-fit-spec.json'
AUD=ROOT/'docs/audit/e73-fit-candidate.json'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes(items):
    for name,digest in items.items():assert sha(ROOT/name)==digest,('Stale input',name)

def inset_plate(doc,fit):
    p=fit['plate'];before=internal_contract(doc);rows=profiles(doc,p['profile_chord_mm'])
    old=rows[0][2];new=old.buffer(-p['outer_perimeter_inset_mm'],join_style='mitre')
    assert new.geom_type=='Polygon' and new.is_valid and new.area<old.area
    gaps=[]
    for _,_,poly in rows[1:]:
        assert new.contains(poly),'Inset reaches a key/stabilizer opening'
        gaps.append(new.exterior.distance(poly))
    for c in doc.modelspace().query('CIRCLE'):
        disk=Point(-c.dxf.center.x,-c.dxf.center.y).buffer(c.dxf.radius,quad_segs=128)
        assert new.contains(disk),'Inset reaches a mounting hole'
        gaps.append(new.exterior.distance(disk))
    assert min(gaps)>=p['minimum_edge_web_mm'],'Insufficient edge web'
    rows[0][1].set_points([(-x,-y,0,0,0) for x,y in list(new.exterior.coords)[:-1]],format='xyseb')
    rows[0][1].closed=True
    assert internal_contract(doc)==before,'Internal key/stabilizer/mount entities changed'
    return doc,dict(exterior_inset_mm=p['outer_perimeter_inset_mm'],unchanged_internal_entities=len(before),
                    minimum_edge_web_mm=min(gaps),original_area_mm2=old.area,candidate_area_mm2=new.area)

def insert_guards(removed,spec):
    rows=[]
    for kind,key,axes in [('M3','top_insert','top_screw_axes'),('M2','daughterboard_insert','daughterboard_screw_axes')]:
        i=spec['case'][key];r=(i['bore_diameter']+i['bore_tolerance'])/2+spec['case']['finished_bore_position_tolerance']+2
        start=i['bore_start_z'];end=start+i['bore_depth']*(1 if kind=='M3' else -1)
        z0=min(start,end)-2;z1=max(start,end)+2
        for x,y in spec['case'][axes]:
            guard=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,z0),gp_Dir(0,0,1)),r,z1-z0).Shape()
            overlap=intersection_volume(removed,guard)
            assert overlap<1e-6,('Insert support eroded',kind,x,y,overlap)
            rows.append(dict(kind=kind,axis_case_mm=[x,y],protected_radius_mm=r,protected_z_mm=[z0,z1],overlap_mm3=overlap))
    return rows

def main():
    fit=read(SPEC);assert fit['revision']=='YETI60-E73-FIT-M01' and not fit['canonical_selection_changed']
    assembly=read(ROOT/'docs/audit/yeti60-assembly.json');hashes(assembly['source_sha256'])
    spec=read(ROOT/'mechanical/assembly-spec.json');fabrication=read(ROOT/'mechanical/pcb-fabrication-spec.json')
    assert assembly['nominal_stack']['plate_thickness_mm']==1.6
    selected=[ROOT/'mechanical/felk60_plate_hhkb.plate-mount.dxf',ROOT/'mechanical/generated/yeti60-bottom.step',ROOT/'mechanical/generated/yeti60-top.step',ROOT/'mechanical/assembly-spec.json',ROOT/'mechanical/yeti60-key-mechanism.e73.json']
    selected_before={str(p.relative_to(ROOT)):sha(p) for p in selected}
    source=ROOT/fit['plate']['source'];doc,plate_proof=inset_plate(ezdxf.readfile(source),fit)
    out=ROOT/fit['plate']['output'];out.parent.mkdir(exist_ok=True)
    ezdxf.options.write_fixed_meta_data_for_testing=True;doc.saveas(out)
    saved=ezdxf.readfile(out);assert internal_contract(saved)==internal_contract(ezdxf.readfile(source))
    shape=build_shape(saved,assembly['nominal_stack']['plate_bottom_z'],1.6);plate_step=ROOT/fit['plate']['step'];write_step(shape,plate_step)
    original=load(ROOT/'mechanical/generated/yeti60-bottom.step');top=load(ROOT/'mechanical/generated/yeti60-top.step')
    floor=fit['switch_floor_relief'];bottom=cut(original,rounded_box(floor['bounds_case_mm'],floor['corner_radius_mm']))
    removed=cut(original,bottom);assert volume(removed)>1e-6
    assert max(abs(a-b) for a,b in zip(bounds(original),bounds(bottom)))<1e-6,'Case outer bounds changed'
    skin=external_faces(original);remaining=min(distance(removed,f) for f in skin)-math.sqrt(3)*fit['case_maximum_coordinate_error_each_axis_mm']-fit['geometric_computation_guard_mm']
    assert remaining>=floor['minimum_remaining_wall_mm'],'Switch relief leaves too little exterior wall'
    supports=insert_guards(removed,spec)
    path=ROOT/fit['bottom_output'];write_step(bottom,path)
    BRepMesh_IncrementalMesh(bottom,.015,False,.08,True).Perform();stl=StlAPI_Writer();stl.ASCIIMode=False;assert stl.Write(bottom,str(path.with_suffix('.stl')))
    env=plate_envelope(saved,fit,assembly['nominal_stack'])
    interfaces=[screen(bottom,env,fit,'plate-bottom-static'),screen(top,env,fit,'plate-top-static')]
    part=next(p for p in assembly['component_envelopes'] if p['ref']=='SW100')
    switch,terms=switch_envelope(part,fit,spec,fabrication);interfaces.append(screen(bottom,switch,fit,'SW100-bottom'))
    gaskets=gasket_coverage(saved,fit,{'lower':bottom,'upper':top})
    assert selected_before=={str(p.relative_to(ROOT)):sha(p) for p in selected},'Canonical selection changed during candidate build'
    dependencies=[Path(__file__),ROOT/'scripts/e73_fit_geometry.py',ROOT/'scripts/build_yeti60_mechanical.py',ROOT/'scripts/check_yeti60_assembly.py',ROOT/'scripts/check_yeti60_interconnects.py',ROOT/'scripts/cad_geometry.py',SPEC,ROOT/'docs/audit/yeti60-assembly.json',ROOT/'mechanical/pcb-fabrication-spec.json',*selected]
    report=dict(status='e73-bounded-plate-switch-repair-candidate-passed',canonical_selection_changed=False,manufacturing_released=False,physical_verification=False,complete_keyboard_tolerance_qualified=False,
        plate=plate_proof,interfaces=interfaces,switch_budget=terms,gasket_bearing_checks=gaskets,
        lower_shell_repair=dict(removed_volume_mm3=volume(removed),original_bounds_case_mm=bounds(original),candidate_bounds_case_mm=bounds(bottom),selected_exterior_faces_checked=len(skin),minimum_removed_to_selected_skin_after_coordinate_allowance_mm=remaining,minimum_required_wall_mm=floor['minimum_remaining_wall_mm'],insert_supports=supports),
        selected_sources_unchanged=selected_before,
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in dependencies},outputs={str(p.relative_to(ROOT)):sha(p) for p in [out,plate_step,path,path.with_suffix('.stl')]},
        remaining=['Select candidate in the canonical assembly and calibration fingerprint, then rebuild both firmware targets and all dependent checks/drawings/renders', 'Continuous whole-PCB installation/removal and complete flexible harness/service movement', 'All other part/fastener tolerances, received NiZ/stabilizer dimensions, foam force/creep and resin/insert strength', 'Actual power/USB/BLE/charge/thermal/RF acceptance'])
    AUD.write_text(json.dumps(report,indent=2)+'\n')
    print('E73 M01 plate/floor candidate passed; canonical assembly unchanged; minimum residual',min(r['remaining_air_gap_mm'] for r in interfaces),flush=True)
if __name__=='__main__':main()
