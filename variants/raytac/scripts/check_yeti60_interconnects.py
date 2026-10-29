#!/usr/bin/env python3
"""Check continuous internal wires, mated housings and removable route guides.

No PCB/case geometry is modified. Circular sweeps are continuous BReps; sparse
polyline samples are not used as collision evidence. Run with the CAD runtime.
"""
import copy,hashlib,json,math,re
from pathlib import Path
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Pnt,gp_Dir,gp_Ax2,gp_Lin
from cad_geometry import load,bounds,intersection_volume
from check_yeti60_assembly import box,distance,move
from interconnect_geometry import line,s_bend,rounded_polyline,offset_path,sweep,validate,norm,sub
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'.assembly-work/interconnect';WORK.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def write_step(s,path):
    w=STEPControl_Writer();w.Transfer(s,STEPControl_AsIs);w.Write(str(path));text=re.sub(r"(FILE_NAME\('[^']*',')[^']*",r"\g<1>2000-01-01T00:00:00",path.read_text());path.write_text('\n'.join(l.rstrip() for l in text.splitlines())+'\n')
def check_hashes(mapping):
    for p,h in mapping.items():assert sha(ROOT/p)==h,'Stale interconnect input '+p

def usb_path(spec,connector,assembly,front_y):
    u=spec['usb'];a=read('mechanical/assembly-spec.json')['daughterboard'];sh=spec['sources']['SH'];r=u['radius'];start=tuple(connector['main_usb_wire_exit_case_mm']);q=(start[0]+1,start[1],start[2]);initial,end,_=s_bend(q,(1,0,0),u['high_z']-q[2],r)
    # The source C5 signal pad row is 1.45mm forward of the standard footprint origin.
    last=(75.0045+a['source_to_case_x_offset'],-(68.793+1.45)+a['source_to_case_y_offset']+sh['header_back_local_y']*-1-sh['mated_depth_reference'],a['pcb_bottom_z']+a['pcb_thickness']+u['daughterboard_exit_above_pcb'])
    first=rounded_polyline([end,(u['first_corner_x'],start[1],u['high_z']),(u['first_corner_x'],u['rear_y'],u['high_z']),(u['drop_x'],u['rear_y'],u['high_z']),(u['drop_x'],u['drop_y'],u['high_z'])],r)
    drop,drop_end,_=s_bend((u['drop_x'],u['drop_y'],u['high_z']),(0,-1,0),u['low_z']-u['high_z'],r)
    dz=last[2]-u['low_z'];run=math.sqrt(4*r*abs(dz)-dz*dz);ramp_start=(last[0],last[1]-u['end_straight']-run,u['low_z']);finish,ramp_end,_=s_bend(ramp_start,(0,1,0),dz,r)
    flat=rounded_polyline([drop_end,(u['drop_x'],front_y,u['low_z']),(last[0],front_y,u['low_z']),ramp_start],r)
    return [line(start,q)]+initial+first+drop+flat+finish+[line(ramp_end,last)]

def routes(spec,connector,assembly,fixed_front_y=None):
    lo,hi=spec['usb']['front_y_search'];target=spec['usb']['nominal_centerline_length']
    for _ in range(50 if fixed_front_y is None else 0):
        middle=(lo+hi)/2;p=usb_path(spec,connector,assembly,middle)
        if sum(x['length'] for x in p)>target:lo=middle
        else:hi=middle
    front=(lo+hi)/2 if fixed_front_y is None else fixed_front_y;usb=usb_path(spec,connector,assembly,front)
    assert abs(sum(x['length'] for x in usb)-target)<(1e-6 if fixed_front_y is None else spec['wire']['manufactured_free_length_tolerance'])
    b=spec['battery'];start=tuple(connector['main_battery_wire_exit_case_mm']);z=b['rear_z'];r=b['radius'];bb=assembly['battery_candidates'][0]['bounds_case_mm'];exit=tuple(bb[i]+b['pack_exit_local'][i] for i in range(3))
    lead,lead_end,_=s_bend(start,(0,1,0),z-start[2],r)
    first=rounded_polyline([lead_end,(start[0],b['rear_y'],z),(b['side_x'],b['rear_y'],z),(b['side_x'],b['drop_y'],z)],r)
    drop,end,_=s_bend((b['side_x'],b['drop_y'],z),(0,-1,0),exit[2]-z,r)
    battery=lead+first+drop+rounded_polyline([end,(b['side_x'],exit[1],exit[2]),exit],r)
    for p in [usb,battery]:validate(p)
    return {'usb':usb,'battery':battery},front

def expand(bb,delta):return [x-delta for x in bb[:3]]+[x+delta for x in bb[3:]]
def near(a,b,margin):
    return all(a[i]<=b[i+3]+margin and b[i]<=a[i+3]+margin for i in range(3))
def surface_z(case,x,y,above=10):
    query=IntCurvesFace_ShapeIntersector();query.Load(case,1e-7);query.Perform(gp_Lin(gp_Pnt(x,y,above),gp_Dir(0,0,-1)),0,30)
    hits=[query.Pnt(i).Z() for i in range(1,query.NbPnt()+1)];assert hits;return max(hits)
def grooves(shape,x0,depth,y_positions,z,r):
    for y in y_positions:
        cutter=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x0-.01,y,z),gp_Dir(1,0,0)),r,depth+.02).Shape();op=BRepAlgoAPI_Cut(shape,cutter);op.Build();assert op.IsDone();shape=op.Shape()
    assert BRepCheck_Analyzer(shape).IsValid();return shape

def conformal_base(bb, case, bond_gap):
    op=BRepAlgoAPI_Cut(box(bb),move(case,0,0,bond_gap));op.Build()
    assert op.IsDone() and BRepCheck_Analyzer(op.Shape()).IsValid()
    return op.Shape()

def guides(spec,case,front_y):
    g=spec['guides'];result=[];data=[]
    for index,x in enumerate(g['rear_x']):
        y=g['rear_y'];d=g['rear_depth'];w=g['rear_width'];z=surface_z(case,x,y)
        samples=[surface_z(case,x+dx,y+dy) for dx in [-d/2,0,d/2] for dy in [-w/2,0,w/2]]
        lower=spec['battery']['rear_z'];upper=spec['usb']['high_z'];floor=min(samples)+g['base_bond_gap'];assert lower-g['groove_radius']-max(samples)-g['base_bond_gap']>=g['minimum_floor_web']
        base=grooves(conformal_base([x-d/2,y-w/2,floor,x+d/2,y+w/2,lower],case,g['base_bond_gap']),x-d/2,d,[y+v for v in spec['battery']['lateral_offsets']],lower,g['groove_radius'])
        bridge=box([x-d/2,y-w/2,lower+g['base_to_bridge_bond_gap'],x+d/2,y+w/2,upper]);bridge=grooves(bridge,x-d/2,d,[y+v for v in spec['battery']['lateral_offsets']],lower,g['groove_radius']);bridge=grooves(bridge,x-d/2,d,[y+v for v in spec['usb']['lateral_offsets']],upper,g['groove_radius'])
        for label,shape in [('base',base),('bridge',bridge)]:result.append((f'rear-{index+1}-{label}',shape))
        data.append({'station':f'rear-{index+1}','center_xy':[x,y],'floor_z':z,'floor_z_sample_range':[min(samples),max(samples)],'base_conforms_to_actual_case':True,'base_to_floor_bond_gap':g['base_bond_gap'],'lower_wire_z':lower,'upper_wire_z':upper,'retention_film_top_z':upper+spec['wire']['insulation_od_max']/2+g['retention_film_thickness']})
    x=g['front_x'];y=front_y;d=g['front_depth'];w=g['front_width'];floor=surface_z(case,x,y)+g['base_bond_gap'];z=spec['usb']['low_z'];assert z-g['groove_radius']-floor>=g['minimum_floor_web']
    shape=grooves(conformal_base([x-d/2,y-w/2,floor-.5,x+d/2,y+w/2,z],case,g['base_bond_gap']),x-d/2,d,[y+v for v in spec['usb']['lateral_offsets']],z,g['groove_radius']);result.append(('front-base',shape));data.append({'station':'front','center_xy':[x,y],'floor_z':floor-g['base_bond_gap'],'base_to_floor_bond_gap':g['base_bond_gap'],'wire_z':z})
    return result,data

def main():
    spec=read('mechanical/interconnect-spec.json');assembly=read('docs/audit/yeti60-assembly.json');connectors=read('docs/audit/yeti60-interconnect-connectors.json');daughter=read('docs/audit/yeti60-daughterboard.json');check_hashes(assembly['source_sha256']);check_hashes(connectors['source_sha256'])
    assert daughter['SH_model_offset_xyz_mm']==[0,-1.45,0]
    assert spec['usb']['pin_map']=={str(i):str(i) for i in range(1,5)} and spec['battery']['pin_map']=={'1':'PACK+','2':'PACK-','3':'NTC'}
    assert spec['wire']['insulation_od_max']<=.8 and spec['sources']['PH']['contact']=='SPH-004T-P0.5S'
    paths,front_y=routes(spec,connectors,assembly);case=load(ROOT/'mechanical/generated/yeti60-bottom.step');top=load(ROOT/'mechanical/generated/yeti60-top.step');pcb=load(ROOT/'.assembly-work/pcb-placed.step');pack=box(assembly['battery_candidates'][0]['bounds_case_mm']);cases=[case,top];od=spec['wire']['insulation_od_max'];allow=spec['wire']['case_and_route_position_allowance'];gap=spec['wire']['minimum_air_gap_after_allowance'];bodies={};nominal={};report_wires={};outputs={};render=[];obstacles=[]
    for p in assembly['component_envelopes']:obstacles.append((p['ref'],box(p['bounds_case_mm']),p['bounds_case_mm']))
    for i,h in enumerate(assembly['mounting_hole_matches']):
        x,y=h['pcb_center_case_mm'];head_radius=read('mechanical/assembly-spec.json')['pcb_fastener']['washer_od_max']/2+.15;bb=[x-head_radius,y-head_radius,-3.9,x+head_radius,y+head_radius,-2];obstacles.append(('PCB-fastener-'+str(i),box(bb),bb))
    a=read('mechanical/assembly-spec.json')['daughterboard'];udb=move(load(ROOT/daughter['exported_step']),a['source_to_case_x_offset'],a['source_to_case_y_offset'],a['pcb_bottom_z']);obstacles.append(('C5-complete-board',udb,bounds(udb)))
    for i,(x,y) in enumerate(read('mechanical/assembly-spec.json')['case']['daughterboard_screw_axes']):
        bb=[x-2.1,y-2.1,-9.3038,x+2.1,y+2.1,-6.9];obstacles.append(('C5-fastener-'+str(i),box(bb),bb))
    for name,path in paths.items():
        records=[]
        for i,offset in enumerate(spec[name]['lateral_offsets'],1):
            wire_path=offset_path(path,offset);radius=min(p['radius'] for p in wire_path if p['kind']=='arc');assert radius>=spec['wire']['minimum_static_bend_radius']
            shape=sweep(wire_path,od);enlarged=sweep(wire_path,od+2*allow);bb=bounds(enlarged);owner='J1' if name=='usb' else 'J2';clearances={}
            for label,other,other_bb in obstacles:
                if label==owner or not near(bb,other_bb,1):continue
                d=distance(enlarged,other);clearances[label]=d;assert d>=gap-1e-6,(name,i,'obstacle',label,d)
            case_d=[distance(enlarged,c) for c in cases];assert min(case_d)>=gap-1e-6,(name,i,'case',case_d)
            assert max(intersection_volume(enlarged,c) for c in cases)<1e-6
            assert distance(enlarged,pcb)>=gap-1e-6
            pack_overlap=intersection_volume(shape,pack);assert pack_overlap<1e-6,(name,i,'pack',pack_overlap)
            key=name+'-'+str(i);nominal[key]=shape;bodies[key]=enlarged;out=WORK/(key+'.step');write_step(shape,out);outputs[str(out.relative_to(ROOT))]=sha(out);render.append({'name':key,'path':str(out.relative_to(ROOT)),'sha256':sha(out),'category':'wire','color':spec[name]['colors'][str(i)]})
            records.append({'pin':i,'color':spec[name]['colors'][str(i)],'free_length_mm':sum(p['length'] for p in wire_path),'minimum_bend_radius_mm':radius,'wire_exit_start_case_mm':list(wire_path[0]['start']),'wire_exit_end_case_mm':list(wire_path[-1]['end']),'nominal_bounds_case_mm':bounds(shape),'minimum_expanded_case_gap_mm':min(case_d),'minimum_expanded_obstacle_gap_mm':min(clearances.values(),default=999),'expanded_obstacle_gaps_mm':clearances,'pack_overlap_mm3':pack_overlap})
        report_wires[name]=records
    # Different harnesses need independent position allowance; parallel wires
    # within one harness are constrained by the comb pitch and may touch insulation.
    cross_gaps=[distance(bodies['usb-'+str(i)],bodies['battery-'+str(j)]) for i in range(1,5) for j in range(1,4)];assert min(cross_gaps)>=gap-1e-6,('harness crossing',min(cross_gaps))
    sh=spec['sources']['SH'];ph=spec['sources']['PH'];sx,sy,sz=connectors['main_usb_wire_exit_case_mm'];px,py,pz=connectors['main_battery_wire_exit_case_mm'];ux,uy,uz=paths['usb'][-1]['end'];ubottom=a['pcb_bottom_z']+a['pcb_thickness'];plug_boxes={'main-SH':[sx-sh['housing_depth'],sy-sh['housing_width']/2,-5.1,sx,sy+sh['housing_width']/2,-2.1],'main-PH':[px-ph['housing_width']/2,py-ph['housing_depth'],-7.5,px+ph['housing_width']/2,py,-2],'C5-SH':[ux-sh['housing_width']/2,uy,ubottom,ux+sh['housing_width']/2,uy+sh['housing_depth'],ubottom+3.1]};plug_data=[]
    for label,bb in plug_boxes.items():
        enlarged=box(expand(bb,spec['plug_envelope_allowance']));d=min(distance(enlarged,c) for c in cases);assert d>=gap
        skip='J2' if label=='main-PH' else 'J1' if label=='main-SH' else 'C5-complete-board'
        for other,obj,obb in obstacles:
            if other==skip or not near(bounds(enlarged),obb,1):continue
            assert distance(enlarged,obj)>=gap-1e-6,(label,other,distance(enlarged,obj))
        shape=box(bb);assert intersection_volume(shape,pcb)<1e-6,(label,'main PCB overlap');out=WORK/('housing-'+label.lower()+'.step');write_step(shape,out);outputs[str(out.relative_to(ROOT))]=sha(out);render.append({'name':label,'path':str(out.relative_to(ROOT)),'sha256':sha(out),'category':'mating-housing','color':'ivory'});plug_data.append({'name':label,'bounds_case_mm':bb,'minimum_expanded_case_gap_mm':d,'geometry':'Conservative complete envelope; intentional overlap with its mating header excluded'})
    print('Wires and housing envelopes passed; constructing conformal guides',flush=True)
    guide_shapes,guide_data=guides(spec,case,front_y);published={}
    public=ROOT/'mechanical/generated/interconnect-guides';public.mkdir(exist_ok=True)
    for label,shape in guide_shapes:
        bb=bounds(shape);overlaps=[intersection_volume(shape,c) for c in cases];assert max(overlaps)<1e-6,(label,'case overlap',overlaps,bb)
        assert distance(shape,pcb)>=gap
        for ref,obj,obb in obstacles:
            if near(bb,obb,gap):assert distance(shape,obj)>=gap-1e-6,(label,ref,distance(shape,obj))
        for wire in nominal.values():
            if near(bb,bounds(wire),0):assert intersection_volume(shape,wire)<1e-6,('Guide pinches nominal wire',label)
        out=WORK/(label+'.step');write_step(shape,out);outputs[str(out.relative_to(ROOT))]=sha(out);render.append({'name':label,'path':str(out.relative_to(ROOT)),'sha256':sha(out),'category':'guide','color':'gray'})
        # Published parts retain case coordinates; no hidden reorientation/scaling.
        target=public/(label+'.step');target.write_bytes(out.read_bytes());published[str(target.relative_to(ROOT))]=sha(target)
        BRepMesh_IncrementalMesh(shape,.005,False,.08,True).Perform();stl=StlAPI_Writer();stl.ASCIIMode=False;target=public/(label+'.stl');assert stl.Write(shape,str(target));published[str(target.relative_to(ROOT))]=sha(target)
    thickness_checks=[]
    profile=read('mechanical/pcb-fabrication-spec.json')
    for actual in profile['ordinary_thickness_acceptance_range_mm']:
        delta=profile['CAD_finished_envelope_mm']-actual
        moved=copy.deepcopy(connectors)
        for field in ['main_usb_wire_exit_case_mm','main_battery_wire_exit_case_mm']:moved[field][2]+=delta
        variant,_=routes(spec,moved,assembly,front_y);smallest=999.;largest_length_change=0.;variant_bodies={}
        for name,path in variant.items():
            for i,offset in enumerate(spec[name]['lateral_offsets'],1):
                conductor=offset_path(path,offset);enlarged=sweep(conductor,od+2*allow);bb=bounds(enlarged)
                smallest=min(smallest,*(distance(enlarged,c) for c in cases))
                assert min(distance(enlarged,c) for c in cases)>=gap-1e-6,('PCB thickness wire/case',actual,name,i)
                assert distance(enlarged,move(pcb,z=delta))>=gap-1e-6
                owner='J1' if name=='usb' else 'J2'
                for label,obj,obb in obstacles:
                    if label==owner:continue
                    dz=0 if label.startswith('C5') else delta
                    shifted=[v+(dz if k in [2,5] else 0) for k,v in enumerate(obb)]
                    if near(bb,shifted,1):assert distance(enlarged,move(obj,z=dz))>=gap-1e-6,('PCB thickness obstacle',actual,name,i,label)
                length_change=abs(sum(p['length'] for p in conductor)-report_wires[name][i-1]['free_length_mm']);largest_length_change=max(largest_length_change,length_change)
                assert length_change<=spec['wire']['manufactured_free_length_tolerance']
                variant_bodies[name+'-'+str(i)]=enlarged
        assert min(distance(variant_bodies['usb-'+str(i)],variant_bodies['battery-'+str(j)]) for i in range(1,5) for j in range(1,4))>=gap-1e-6
        for label,bb in plug_boxes.items():
            dz=0 if label=='C5-SH' else delta;shifted=[v+(dz if k in [2,5] else 0) for k,v in enumerate(bb)]
            assert min(distance(box(expand(shifted,spec['plug_envelope_allowance'])),c) for c in cases)>=gap-1e-6
        thickness_checks.append({'finished_pcb_thickness_mm':actual,'main_connector_z_shift_mm':delta,'minimum_expanded_wire_case_gap_mm':smallest,'maximum_required_free_length_change_mm':largest_length_change,'fixed_guide_positions':True})
    sources=['mechanical/interconnect-spec.json','mechanical/assembly-spec.json','docs/audit/yeti60-assembly.json','docs/audit/yeti60-daughterboard.json','docs/audit/yeti60-interconnect-connectors.json','mechanical/generated/yeti60-bottom.step','mechanical/generated/yeti60-top.step','scripts/check_yeti60_interconnects.py','scripts/interconnect_geometry.py','scripts/cad_geometry.py','mechanical/pcb-fabrication-spec.json']
    report={'status':'controlled-route-geometry-passed','production_approved':False,'source_sha256':{p:sha(ROOT/p) for p in sources},'generated_step_sha256':outputs,'published_guide_sha256':published,'wire_diameter_max_mm':od,'radial_case_and_route_allowance_mm':allow,'minimum_air_gap_after_allowance_mm':gap,'usb_front_y_mm':front_y,'wires':report_wires,'minimum_expanded_harness_to_harness_gap_mm':min(cross_gaps),'mated_housings':plug_data,'guide_stations':guide_data,'ordinary_board_thickness_checks':thickness_checks,'render_parts':render,'centerline_recipes':paths,'case_modification_required':False,'assumptions':['All wires are held flat in the named grooves and preformed route; free bundling is not qualified','Lead exit Z datums and actual harness tolerances require supplier confirmation','No strain, springback, fatigue, pull-out or SI/RF certification'],'not_verified':spec['not_verified']}
    (ROOT/'docs/audit/yeti60-interconnects.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['status','minimum_expanded_harness_to_harness_gap_mm','case_modification_required']},indent=2))
if __name__=='__main__':main()
