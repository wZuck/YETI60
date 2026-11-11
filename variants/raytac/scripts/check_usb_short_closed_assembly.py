#!/usr/bin/env python3
"""Continuous-solid nine-wire, closed-case and removable-guide acceptance.

Only candidate assets are written. Native shell outer faces, PCB, plate and
mount datums are retained; explicit internal cable and RF service reliefs are subtracted.
"""
import json,hashlib,math,re
from pathlib import Path
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepTools import BRepTools
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE,TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pnt,gp_Vec,gp_Ax2,gp_Dir
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from cad_geometry import load,bounds,intersection_volume
from check_yeti60_assembly import box,distance,move
from check_yeti60_interconnects import write_step,surface_z,conformal_base,grooves,near
from usb_short_harness import paths,paired_data,length,sweep_wire,envelope_wire
from build_yeti60_mechanical import rounded_box
from usb_short_model_contract import apply_model_envelopes
from usb_short_passive_contract import apply_passive_envelopes
from usb_short_battery_service import apply_envelope as apply_battery_service_envelope, POSITION
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/usb-short-route';OUT=BASE/'mechanical';WORK=ROOT/'.assembly-work/usb-short-closed';AUD=BASE/'audit'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def hashes(m):
    for p,h in m.items():assert sha(ROOT/p)==h,('Stale input',p)
def volume(s):
    p=GProp_GProps();BRepGProp.VolumeProperties_s(s,p);return abs(p.Mass())
def cut(a,b):
    op=BRepAlgoAPI_Cut(a,b);op.Build();assert op.IsDone() and BRepCheck_Analyzer(op.Shape()).IsValid();return op.Shape()
def external_faces(shape):
    result=[];faces=TopExp_Explorer(shape,TopAbs_FACE)
    while faces.More():
        f=TopoDS.Face(faces.Current());bb=bounds(f);surf=BRepAdaptor_Surface(f);u0,u1,v0,v1=BRepTools.UVBounds_s(f);p=gp_Pnt();du=gp_Vec();dv=gp_Vec();surf.D1((u0+u1)/2,(v0+v1)/2,p,du,dv);n=du.Crossed(dv)
        if n.Magnitude()>1e-9:
            n.Normalize()
            if f.Orientation()==TopAbs_REVERSED:n.Reverse()
            if (n.Z()<-.3 and bb[5]<-7) or (n.Y()>.3 and bb[4]>-96) or (n.X()>.3 and bb[3]>375) or (n.X()<-.3 and bb[0]<53):result.append(f)
        faces.Next()
    assert result;return result

def build_case(spec,assembly,fit=None):
    fit=read(BASE/'mechanical-fit-spec.json') if fit is None else fit
    original=load(ROOT/'mechanical/generated/yeti60-bottom.step');case=original
    for key in ['case_pocket']:case=cut(case,box(spec[key]['bounds_case_mm']))
    before_service=case
    service=spec['case_service_relief']
    case=cut(case,rounded_box(service['bounds_case_mm'],service['corner_radius_mm']))
    service_removed=cut(before_service,case)
    plate=bounds(load(ROOT/'.assembly-work/plate.step'));guard=service['plate_bearing_XY_guard_mm']
    # Protect every ledge point inside the plate's XY envelope, including an
    # extra guard around its perimeter. No assertion of untouched ledges
    # outside the plate-bearing area is made for the through-height relief.
    bearing_guard=box([plate[0]-guard,plate[1]-guard,-25,plate[3]+guard,plate[4]+guard,25])
    assert intersection_volume(service_removed,bearing_guard)<1e-6,'Service relief erodes guarded plate bearing'
    assert volume(service_removed)>0,'Service relief removed no material'
    before_floor=case;floor=fit['switch_floor_relief']
    case=cut(case,rounded_box(floor['bounds_case_mm'],floor['corner_radius_mm']))
    floor_removed=cut(before_floor,case)
    assert volume(floor_removed)>0,'Switch relief removed no material'
    assert max(abs(a-b) for a,b in zip(bounds(original),bounds(case)))<1e-6,'Changed shell outer envelope'
    removed=cut(original,case);assert volume(removed)>0
    outer=external_faces(original);remaining=min(distance(removed,f) for f in outer);assert remaining-assembly['case']['linear_tolerance']>=spec['case_pocket']['minimum_remaining_wall_mm'],('Outer skin too thin',remaining)
    holes=[]
    for kind,axes,radius in [('M3',assembly['case']['top_screw_axes'],2.3),('M2',assembly['case']['daughterboard_screw_axes'],1.6)]:
        for x,y in axes:
            insert=assembly['case']['top_insert' if kind=='M3' else 'daughterboard_insert'];protected_radius=max(radius,(insert['bore_diameter']+insert['bore_tolerance'])/2)+assembly['case']['finished_bore_position_tolerance']+2;start=insert['bore_start_z'];end=start+(insert['bore_depth'] if kind=='M3' else -insert['bore_depth']);z0=min(start,end)-2;z1=max(start,end)+2
            protected=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,z0),gp_Dir(0,0,1)),protected_radius,z1-z0).Shape();v=intersection_volume(removed,protected);assert v<1e-6,('Insert support eroded',kind,x,y,v);holes.append({'kind':kind,'axis':[x,y],'protected_radius_mm':protected_radius,'protected_z_range_mm':[z0,z1],'removed_overlap_mm3':v})
    target=OUT/'yeti60-bottom-short-usb.step';write_step(case,target)
    BRepMesh_IncrementalMesh(case,.015,False,.08,True).Perform();stl=StlAPI_Writer();stl.ASCIIMode=False;assert stl.Write(case,str(target.with_suffix('.stl')))
    return case,{'original_bounds_case_mm':bounds(original),'new_bounds_case_mm':bounds(case),'removed_volume_mm3':volume(removed),'minimum_removed_to_selected_external_skin_mm':remaining,'case_linear_tolerance_mm':assembly['case']['linear_tolerance'],'minimum_remaining_skin_after_tolerance_mm':remaining-assembly['case']['linear_tolerance'],'external_skin_faces_checked':len(outer),'skin_selection':'Downward exterior faces below Z=-7; rear-facing faces reaching Y>-96; outer end faces; original trimmed BReps, conservative minimum distance','insert_supports':holes,'plate_bearing_guard_XY_mm':guard,'service_relief_removed_volume_mm3':volume(service_removed),'service_relief_to_guarded_plate_envelope_mm':distance(service_removed,bearing_guard),'through_height_service_relief_bounds_mm':service['bounds_case_mm'],'switch_floor_relief':{'bounds_case_mm':floor['bounds_case_mm'],'removed_volume_mm3':volume(floor_removed),'minimum_remaining_skin_after_tolerance_mm':min(distance(floor_removed,f) for f in outer)-assembly['case']['linear_tolerance']},'complete_service_path_qualified':False,'outputs':{str(p.relative_to(ROOT)):sha(p) for p in [target,target.with_suffix('.stl')]}}

def input_data(spec):
    assembly=read(ROOT/'docs/audit/yeti60-assembly.json');native=read(BASE/'audit/native-check.json');hashes(native['source_sha256']);assert native['audit_script_sha256']==sha(ROOT/'scripts/check_usb_short_route.py')
    source=read(ROOT/'.assembly-work/usb-short-audit/native-inputs.json');connectors=read(ROOT/'docs/audit/yeti60-interconnect-connectors.json');old=read(ROOT/'docs/audit/yeti60-interconnects.json');hashes(assembly['source_sha256'])
    bottom=assembly['nominal_stack']['pcb_bottom_z'];ex={}
    for h in source['new_headers']:
        ex[h['ref']]=[h['position'][0],-h['position'][1]+4.575,bottom-1.6]
    ex.update({'J1':connectors['main_usb_wire_exit_case_mm'],'J2':connectors['main_battery_wire_exit_case_mm'],'C5':old['centerline_recipes']['usb'][-1]['end'],'pack':old['centerline_recipes']['battery'][-1]['end']})
    ex['J2']=[POSITION[0],-POSITION[1]+spec['sources']['SH']['header_back_local_y']+spec['sources']['SH']['mated_depth_reference'],bottom-spec['battery']['main_exit_below_pcb']]
    # Explicit pin datums, including the two-to-four-position power fan-out.
    assert ex['J4'][:2]==[350.5,-108.925] and ex['J5'][:2]==[341,-112.925]
    assembly=apply_model_envelopes(apply_passive_envelopes(apply_battery_service_envelope(assembly),source))
    return assembly,source,ex

def obstacles(assembly,source,delta=0):
    result=[]
    for p in assembly['component_envelopes']:
        if p['ref'] not in ['R30','R31']:result.append((p['ref'],move(box(p['bounds_case_mm']),z=delta)))
    for i,h in enumerate(assembly['mounting_hole_matches']):
        x,y=h['pcb_center_case_mm'];result.append(('PCB-mount-'+str(i),box([x-2.1,y-2.1,-3.9+delta,x+2.1,y+2.1,-2+delta])))
    daughter=read(ROOT/'docs/audit/yeti60-daughterboard.json');s=read(ROOT/'mechanical/assembly-spec.raytac.json')['daughterboard'];result.append(('C5',move(load(ROOT/daughter['exported_step']),s['source_to_case_x_offset'],s['source_to_case_y_offset'],s['pcb_bottom_z'])))
    for i,(x,y) in enumerate(read(ROOT/'mechanical/assembly-spec.raytac.json')['case']['daughterboard_screw_axes']):result.append(('C5-mount-'+str(i),box([x-2.1,y-2.1,-9.3038,x+2.1,y+2.1,-6.9])))
    return result

def evaluate(spec,assembly,source,exits,case,delta=0,publish=False):
    route,centre=paths(spec,exits,delta);data,twists=paired_data(centre,spec);route['usb'].update(data);top=load(ROOT/'mechanical/generated/yeti60-top.step');pcb=move(load(ROOT/'.assembly-work/pcb-placed.step'),z=delta);pack=box(assembly['battery_candidates'][0]['bounds_case_mm']);obs=obstacles(assembly,source,delta);records={};shapes={};renders=[];exports={};gap=spec['wire']['minimum_air_gap_after_allowance']
    for family,wires in route.items():
        records[family]=[]
        for pin,path in wires.items():
            shape=envelope_wire(path,spec['wire']['insulation_od_max']+2*spec['wire']['case_and_route_position_allowance']);shapes[family,pin]=shape;bb=bounds(shape);clear={label:distance(shape,q) for label,q in [('bottom',case),('top',top),('PCB',pcb)]};owner={'usb':'J4','power':'J5','battery':'J2'}[family]
            for label,q in obs:
                if label==owner or (family=='power' and label=='J1') or not near(bb,bounds(q),1):continue
                clear[label]=distance(shape,q)
            if family!='battery':clear['pack']=distance(shape,pack)
            assert min(clear.values())>=gap-1e-6,(delta,family,pin,'clearance',min(clear.items(),key=lambda a:a[1]))
            radii=[p['radius'] if p['kind']=='arc' else p['curvature_radius_lower_bound_mm'] for p in path if p['kind']!='line'];assert min(radii)>=4-1e-6,(family,pin,'minimum radius',min(radii))
            row={'pin':pin,'free_length_mm':length(path),'minimum_design_bend_radius_mm':min(radii),'wire_exit_start_case_mm':path[0]['start'],'wire_exit_end_case_mm':path[-1]['end'],'expanded_envelope_bounds_case_mm':bb,'minimum_expanded_gap_mm':min(clear.values()),'expanded_gaps_mm':clear};records[family].append(row)
            if publish:
                nominal=sweep_wire(path,spec['wire']['insulation_od_max']);target=WORK/(family+'-'+pin+'.step');write_step(nominal,target);exports[str(target.relative_to(ROOT))]=sha(target);renders.append({'name':family+'-'+pin,'path':str(target.relative_to(ROOT)),'sha256':sha(target),'color':spec[family]['colors'][pin],'category':'wire','group':'interconnect'})
    crossings=[]
    for left,right in [('usb','power'),('usb','battery'),('power','battery')]:
        v=min((distance(a,b),i,j) for i,a in shapes.items() if i[0]==left for j,b in shapes.items() if j[0]==right);assert v[0]>=gap-1e-6,('Independent harness collision',delta,left,right,v);crossings.append({'families':[left,right],'minimum_expanded_gap_mm':v[0],'wires':[v[1],v[2]]})
    # Actual source/target pin positions, not a cable-colour assumption.
    assert all(abs(route['usb'][pin][0]['start'][0]-(exits['J4'][0]-1.5+int(pin)-1))<1e-6 for pin in ['1','2','3','4'])
    assert all(abs(route['usb'][pin][-1]['end'][0]-(exits['C5'][0]-1.5+int(pin)-1))<1e-6 for pin in ['1','2','3','4'])
    assert abs(route['power']['1'][-1]['end'][1]-(exits['J1'][1]+1.5))<1e-6 and abs(route['power']['2'][-1]['end'][1]-(exits['J1'][1]-1.5))<1e-6
    for pin,offset in zip(['1','2','3'],spec['battery']['header_lateral_offsets']):
        assert max(abs(a-b) for a,b in zip(route['battery'][pin][0]['start'],[exits['J2'][0]-offset,exits['J2'][1],exits['J2'][2]+delta]))<1e-6, 'SH3 battery pin-order mismatch'
    skew=abs(length(route['usb']['2'])-length(route['usb']['3']));assert skew<1
    return {'pcb_z_shift_mm':delta,'wires':records,'crossings':crossings,'USB_geometric_pair_skew_mm':skew,'twist_sections':twists,'routes':route,'render_parts':renders,'generated_step_sha256':exports},shapes,pcb,obs,pack

def main():
    OUT.mkdir(exist_ok=True);WORK.mkdir(parents=True,exist_ok=True);spec=read(BASE/'interconnect-spec.json');assembly,source,exits=input_data(spec);case,case_report=build_case(spec,read(ROOT/'mechanical/assembly-spec.raytac.json'))
    result,shapes,pcb,obs,pack=evaluate(spec,assembly,source,exits,case,publish=True);print('Nominal nine-wire routes passed',flush=True)
    variants=[];profile=read(ROOT/'mechanical/pcb-fabrication-spec.json')
    for thickness in profile['ordinary_thickness_acceptance_range_mm']:
        d=profile['CAD_finished_envelope_mm']-thickness;r,_,_,_,_=evaluate(spec,assembly,source,exits,case,d);change=max(abs(w['free_length_mm']-next(q['free_length_mm'] for q in result['wires'][f] if q['pin']==w['pin'])) for f,rs in r['wires'].items() for w in rs);assert change<=.5,('Harness length tolerance',thickness,change);variants.append({'pcb_thickness_mm':thickness,'maximum_free_length_change_mm':change,'minimum_expanded_gap_mm':min(w['minimum_expanded_gap_mm'] for rs in r['wires'].values() for w in rs),'crossings':r['crossings']});print('Thickness',thickness,'passed',flush=True)
    sources=[BASE/'interconnect-spec.json',BASE/'EC60-nRF52840.kicad_pcb',BASE/'audit/native-check.json',ROOT/'docs/audit/yeti60-assembly.json',ROOT/'docs/audit/yeti60-daughterboard.json',ROOT/'docs/audit/yeti60-interconnect-connectors.json',ROOT/'docs/audit/yeti60-interconnects.json',ROOT/'mechanical/generated/yeti60-bottom.step',ROOT/'mechanical/generated/yeti60-top.step',ROOT/'mechanical/assembly-spec.raytac.json',ROOT/'mechanical/pcb-fabrication-spec.json',Path(__file__),ROOT/'scripts/usb_short_harness.py',ROOT/'scripts/usb_short_passive_contract.py',ROOT/'scripts/usb_short_model_contract.py',ROOT/'scripts/usb_short_battery_service.py',BASE/'audit/native-models.json',ROOT/'scripts/interconnect_geometry.py',ROOT/'scripts/check_yeti60_interconnects.py',ROOT/'scripts/build_yeti60_mechanical.py',ROOT/'scripts/cad_geometry.py']
    sources.append(BASE/'mechanical-fit-spec.json')
    report={'status':'nine-wire-closed-case-routes-passed','physical_verification':False,'manufacturing_released':False,'case':case_report,'connector_exits_case_mm':exits,'nominal':result,'ordinary_thickness_checks':variants,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},'limits':['One internal rear relief is required; the original unmodified bottom is not this assembly','Spline twist sweeps are render/manufacturing geometry; collision proof uses conservative full pair tubes on twist sections','Internal conductor order is constrained by the guides; insulation contact within the twisted pair is intentional','No actual wire springback, crimp pull-out, resin shrinkage, RF/USB eye or battery supplier qualification']}
    (AUD/'closed-assembly.json').write_text(json.dumps(report,indent=2)+'\n');print('Closed case routing report written')
if __name__=='__main__':main()
