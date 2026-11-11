#!/usr/bin/env python3
"""Read-only feasibility proof for an outboard antenna wing and internal relief."""
import hashlib
import json
from pathlib import Path
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Pnt,gp_Dir,gp_Lin
from cad_geometry import load,bounds,intersection_volume
from check_yeti60_assembly import build_plate,box,distance
from build_yeti60_mechanical import rounded_box,cut

ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    specpath=ROOT/'mechanical/rf-remediation.json';spec=json.loads(specpath.read_text())
    assemblypath=ROOT/'mechanical/assembly-spec.json';assembly=json.loads(assemblypath.read_text())
    shell=ROOT/'mechanical/generated/yeti60-bottom.step';bottom=load(shell)
    top=load(ROOT/'mechanical/generated/yeti60-top.step')
    cavity=spec['bottom_relief_case_XYZ'];candidate=cut(bottom,rounded_box(cavity,spec['bottom_relief_corner_radius']))
    before=bounds(bottom);after=bounds(candidate)
    assert max(abs(a-b) for a,b in zip(before,after))<1e-6
    plate,_=build_plate(assembly['stack']['plate_bottom_z'])
    case_tol=assembly['case']['linear_tolerance'];records={}
    xy_allowance=spec['PCB_position_XY_allowance']+spec['module_placement_XY_allowance']
    z_allowance=assembly['stack']['spacer_length_tolerance']
    for name,part in spec['placements'].items():
        x0,y0,x1,y1=part['body_with_XY_tolerance_PCB']
        body=box([x0-xy_allowance,-y1-xy_allowance,part['worst_bottom_Z']-z_allowance,x1+xy_allowance,-y0+xy_allowance,-2+z_allowance])
        overlap=[intersection_volume(body,c) for c in [candidate,top]]
        gap=min(distance(body,c) for c in [candidate,top])
        assert max(overlap)<1e-6 and gap-case_tol>=spec['minimum_component_gap_after_case_tolerance']
        x0,y0,x1,y1=part['antenna_projection_PCB']
        projection=box([x0,-y1,4.2062,x1,-y0,5.4062])
        assert intersection_volume(projection,plate)<1e-6
        lateral=distance(projection,plate)
        assert lateral>3
        records[name]={'case_overlap_mm3':overlap,'minimum_component_case_gap_mm':gap,
                       'gap_after_case_tolerance_mm':gap-case_tol,'antenna_plate_projection_overlap_mm3':0,
                       'antenna_plate_lateral_gap_mm':lateral,'applied_to_native_PCB':spec.get('native_implemented',False)}
    x0,y0,x1,y1=spec['proposed_PCB_wing_XY']
    radius=spec['PCB_wing_corner_radius']
    # A conservative box includes the concave corner extensions as well as
    # convex corners removed by milling. Inflate XY independently of Z.
    x_allowance=spec['additional_fabrication_outline_allowance']+spec['PCB_position_XY_allowance']
    wing=box([x0-x_allowance,-y1-radius-x_allowance,-2.1538-z_allowance,x1+x_allowance,-y0+radius+x_allowance,-.3938+z_allowance])
    nominal_wing=box([x0,-y1-radius,-2.,x1,-y0+radius,-.3938])
    nominal_wing_gap=min(distance(nominal_wing,c) for c in [candidate,top])
    assert nominal_wing_gap>=spec['minimum_nominal_board_gap']
    wing_gap=min(distance(wing,c) for c in [candidate,top])
    assert max(intersection_volume(wing,c) for c in [candidate,top])<1e-6
    assert wing_gap-case_tol>=spec['minimum_board_gap_after_tolerances']
    # Sample the original outer underside inside the flat pocket footprint.
    # This samples floor web only; it is not a full structural/thin-wall analysis.
    floor=[];r=spec['bottom_relief_corner_radius']
    for i in range(17):
        for j in range(35):
            x=cavity[0]+r+(cavity[3]-cavity[0]-2*r)*i/16
            y=cavity[1]+r+(cavity[4]-cavity[1]-2*r)*j/34
            query=IntCurvesFace_ShapeIntersector();query.Load(candidate,1e-7)
            query.Perform(gp_Lin(gp_Pnt(x,y,-30),gp_Dir(0,0,1)),0,40)
            hits=sorted(query.Pnt(k).Z() for k in range(1,query.NbPnt()+1))
            if len(hits)>=2 and hits[0]<cavity[2]-1e-5:
                floor.append(cavity[2]-hits[0])
    assert floor and min(floor)-2*case_tol>=spec['minimum_floor_after_case_tolerance']
    sources=[specpath,assemblypath,shell,ROOT/'mechanical/generated/yeti60-top.step',
             ROOT/'mechanical/felk60_plate_hhkb.audited.dxf',ROOT/'scripts/build_yeti60_mechanical.py',
             ROOT/'scripts/check_yeti60_assembly.py',ROOT/'scripts/cad_geometry.py',Path(__file__)]
    report={'status':'implemented-RF-geometry-tolerance-screen-passed' if spec.get('native_implemented',False) else 'candidate-geometric-feasibility-passed-native-implementation-pending',
            'production_approved':False,'physical_verification':False,'candidate_only':not spec.get('native_implemented',False),
            'external_case_bounds_unchanged':True,'nominal_wing_case_gap_mm':nominal_wing_gap,'variants':records,'wing_case_gap_mm':wing_gap,
            'wing_gap_after_case_profile_allowance_mm':wing_gap-case_tol,
            'PCB_position_XY_allowance_mm':spec['PCB_position_XY_allowance'],
            'module_placement_XY_allowance_mm':spec['module_placement_XY_allowance'],
            'PCB_outline_allowance_mm':spec['additional_fabrication_outline_allowance'],
            'PCB_stack_Z_allowance_mm':z_allowance,
            'case_profile_allowance_per_surface_mm':case_tol,
            'floor_samples':len(floor),'minimum_sampled_floor_web_mm':min(floor),
            'minimum_sampled_floor_web_after_case_tolerance_mm':min(floor)-2*case_tol,
            'scope':'Conditional BRep screen, not native PCB, RF, strength or manufacturing approval',
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources}}
    (ROOT/'docs/audit/rf-remediation-candidate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))


if __name__=='__main__':main()
