#!/usr/bin/env python3
"""Check current PCB/case fit and a provisional battery envelope; build render geometry.

Run with requirements-audit.txt. Z assumptions and proxy heights are explicit.
No claim of qualified switch/dome/keycap/battery manufacturing tolerances.
"""
import hashlib,json,math,subprocess
from pathlib import Path
import ezdxf
from ezdxf.path import make_path
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace,BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism,BRepPrimAPI_MakeBox
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Pnt,gp_Vec,gp_Trsf
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from cad_geometry import load,bounds,intersection_volume
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'.assembly-work';WORK.mkdir(exist_ok=True)
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def move(shape,x=0,y=0,z=0):
    t=gp_Trsf();t.SetTranslation(gp_Vec(x,y,z));return BRepBuilderAPI_Transform(shape,t,True).Shape()
def box(bb):return BRepPrimAPI_MakeBox(gp_Pnt(*bb[:3]),bb[3]-bb[0],bb[4]-bb[1],bb[5]-bb[2]).Shape()
def distance(a,b):
    d=BRepExtrema_DistShapeShape(a,b);d.Perform();assert d.IsDone();return d.Value()
def wire(points,ccw):
    pts=[]
    for p in points:
        if not pts or math.dist(p,pts[-1])>1e-8:pts.append(p)
    if math.dist(pts[0],pts[-1])<1e-8:pts.pop()
    area=sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(pts,pts[1:]+pts[:1]))
    if (area>0)!=ccw:pts.reverse()
    builder=BRepBuilderAPI_MakePolygon()
    for x,y,z in pts:builder.Add(gp_Pnt(x,y,z))
    builder.Close();return builder.Wire()
def write_step(shape,path):
    w=STEPControl_Writer();w.Transfer(shape,STEPControl_AsIs);w.Write(str(path))
def build_plate(z):
    doc=ezdxf.readfile(ROOT/'mechanical/felk60_plate_hhkb.audited.dxf');profiles=[];centers=[]
    for e in doc.modelspace().query('LWPOLYLINE'):
        points=[(-v.x,-v.y,z) for v in make_path(e).flattening(.002)]
        xs=[p[0] for p in points];ys=[p[1] for p in points];area=(max(xs)-min(xs))*(max(ys)-min(ys));profiles.append((area,points))
        sx,sy=max(xs)-min(xs),max(ys)-min(ys)
        if abs(sy-14)<.01 and (abs(sx-14.6)<.01 or abs(sx-32)<.01):centers.append({'x':(min(xs)+max(xs))/2,'y':(min(ys)+max(ys))/2,'cutout_width':sx})
    profiles.sort(key=lambda a:-a[0]);face=BRepBuilderAPI_MakeFace(wire(profiles[0][1],True))
    for _,pts in profiles[1:]:face.Add(wire(pts,False))
    # Screw circles are also tessellated to <=0.002 mm sagitta.
    for c in doc.modelspace().query('CIRCLE'):
        n=max(64,math.ceil(math.pi/math.acos(1-.002/c.dxf.radius)));pts=[(-c.dxf.center.x+c.dxf.radius*math.cos(2*math.pi*i/n),-c.dxf.center.y+c.dxf.radius*math.sin(2*math.pi*i/n),z) for i in range(n)];face.Add(wire(pts,False))
    assert face.IsDone();shape=BRepPrimAPI_MakePrism(face.Face(),gp_Vec(0,0,1.2)).Shape();assert BRepCheck_Analyzer(shape).IsValid();assert len(centers)==60,len(centers)
    return shape,sorted(centers,key=lambda c:(-c['y'],c['x']))
def main():
    meta=json.loads((ROOT/'docs/audit/yeti60-pcb-mechanical-metadata.json').read_text());pcbpath=ROOT/meta['source'];assert sha(pcbpath)==meta['source_sha256']
    bottom=load(ROOT/'felk60/felk60_bottom.step');top=load(ROOT/'felk60/felk60_top_hhkb.step')
    subprocess.run([CLI,'pcb','export','step','--board-only','--user-origin','0x0mm','-f','-o',str(WORK/'pcb-body.step'),str(pcbpath)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    body=load(WORK/'pcb-body.step');native_bounds=bounds(body);native_thickness=native_bounds[5]-native_bounds[2]
    faces=TopExp_Explorer(body,TopAbs_FACE);base_face=None;largest=0
    while faces.More():
        f=TopoDS.Face(faces.Current());bb=bounds(f)
        if abs(bb[2])<1e-6 and abs(bb[5])<1e-6:
            prop=GProp_GProps();BRepGProp.SurfaceProperties_s(f,prop)
            if prop.Mass()>largest:base_face=f;largest=prop.Mass()
        faces.Next()
    assert base_face is not None
    # KiCad STEP body excludes outer copper/mask; use a conservative envelope
    # extruded to the declared finished thickness without stretching XY.
    body=BRepPrimAPI_MakePrism(base_face,gp_Vec(0,0,meta['pcb_thickness_mm'])).Shape()
    prop=GProp_GProps();BRepGProp.VolumeProperties_s(body,prop)
    if prop.Mass()<0:body.Reverse()
    assert BRepCheck_Analyzer(body).IsValid()
    # FELK60 ledges are 3.19 and 6.39. 2mm gaskets at the documented 50%
    # compression leave 1mm + 1.2mm plate + 1mm in the 3.2mm gap.
    plate_bottom=4.19;plate,keys=build_plate(plate_bottom);write_step(plate,WORK/'plate.step')
    plate_collision=[intersection_volume(plate,s) for s in (bottom,top)]
    nominal_gap=4.6 # Explicit provisional PCB-top to plate-bottom distance.
    pcb_top=plate_bottom-nominal_gap;shift=pcb_top-meta['pcb_thickness_mm'];placed=move(body,z=shift);write_step(placed,WORK/'pcb-placed.step')
    pcb_collisions=[intersection_volume(placed,s) for s in (bottom,top)];pcb_distances=[distance(placed,s) for s in (bottom,top)]
    envelopes=[];hits=[]
    for part in meta['parts']:
        if not part['back']:continue
        x0,y0,x1,y1=part.get('physical_body_bbox_pcb_mm') or part['xy_courtyard_and_graphics_bbox_pcb_mm'];height=part['height_envelope_mm'];bb=[x0,-y1,shift-height,x1,-y0,shift];s=box(bb)
        volumes=[intersection_volume(s,c) for c in (bottom,top)];entry={**part,'bounds_case_mm':bb,'collision_volume_mm3':volumes,'min_case_distance_mm':min(distance(s,c) for c in (bottom,top))};envelopes.append(entry)
        if max(volumes)>1e-5:hits.append(entry)
    # Hole correspondence is not a manufacturing tolerance approval.
    hole_matches=[];used=set()
    dxf=ezdxf.readfile(ROOT/'mechanical/felk60_plate_hhkb.audited.dxf')
    for circle in dxf.modelspace().query('CIRCLE'):
        center=(-circle.dxf.center.x,circle.dxf.center.y)
        choices=[(math.dist(center,h['center_pcb_mm']),i,h) for i,h in enumerate(meta['mount_holes']) if i not in used]
        offset,i,h=min(choices,key=lambda v:v[0]);used.add(i)
        hole_matches.append({'pcb_ref':h['ref'],'center_offset_mm':offset,'plate_pilot_diameter_mm':2*circle.dxf.radius,'pcb_min_clearance_diameter_mm':min(h['drill_mm']),'nominal_M2_radial_margin_before_tolerances_mm':min(h['drill_mm'])/2-1-offset})
    assert len(hole_matches)==len(meta['mount_holes'])==29
    assert max(h['center_offset_mm'] for h in hole_matches)<.1
    # Current board and component envelopes at several plausible stack gaps.
    sweep=[]
    for gap in (4.0,4.3,4.6,4.9,5.2):
        z=plate_bottom-gap-meta['pcb_thickness_mm'];shape=move(body,z=z);sweep.append({'pcb_to_plate_gap_mm':gap,'pcb_bottom_z':z,'pcb_case_overlap_mm3':[intersection_volume(shape,c) for c in (bottom,top)],'flat_floor_pack_thickness_budget_mm':round(z-.5-(-5.91+.5),3)})
    # Free XY cells below the board, with insulation and fastener exclusions.
    step=1.;xmin,xmax=74,354;ymin,ymax=-197,-105;W,H=int(xmax-xmin),int(ymax-ymin)
    free=[[True]*W for _ in range(H)];exclusions=[]
    for e in envelopes:
        bb=e['bounds_case_mm'];exclusions.append([bb[0]-1,bb[1]-1,bb[3]+1,bb[4]+1])
    for h in meta['mount_holes']:
        x,y=h['center_pcb_mm'];exclusions.append([x-3,-y-3,x+3,-y+3])
    for y in range(H):
        for x in range(W):
            xx,yy=xmin+x+.5,ymin+y+.5
            if any(a<=xx<=c and b<=yy<=d for a,b,c,d in exclusions):free[y][x]=False
    # 0.5mm each above/below, before allocating actual pack swelling/protection.
    pack_height=math.floor((shift-.5-(-5.91+.5))*10)/10
    candidates=[]
    for width,height in [(60,30),(50,30),(50,20),(40,30),(40,20),(30,20)]:
        found=None
        for j in range(H-height+1):
            for i in range(W-width+1):
                if all(all(row[i:i+width]) for row in free[j:j+height]):found=[xmin+i,ymin+j,shift-.5-pack_height,xmin+i+width,ymin+j+height,shift-.5];break
            if found:break
        if found:
            s=box(found);v=[intersection_volume(s,c) for c in (bottom,top)];candidates.append({'bounds_case_mm':found,'size_mm':[width,height,pack_height],'case_overlap_mm3':v,'envelope_must_include_swelling_and_protection':True,'component_xy_and_fastener_keepouts_clear':True,'bottom_case_distance_mm':distance(s,bottom),'top_insulation_gap_mm':.5,'status':'provisional-pack-envelope-not-a-selected-battery'})
    report={'status':'conditional-fit-review','source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [pcbpath,ROOT/'felk60/felk60_bottom.step',ROOT/'felk60/felk60_top_hhkb.step',ROOT/'mechanical/felk60_plate_hhkb.audited.dxf']},'verification_recipe_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(),ROOT/'scripts/cad_geometry.py',ROOT/'scripts/export_yeti60_mechanical_metadata.py']},'mechanical_metadata_sha256':sha(ROOT/'docs/audit/yeti60-pcb-mechanical-metadata.json'),'pcb_frame_to_case':'X=PCB_X; Y=-PCB_Y; Z=export_Z+pcb_bottom_z','nominal_stack':{'bottom_gasket_ledge_z':3.19,'top_gasket_ledge_z':6.39,'compressed_gasket_each_mm':1.,'plate_bottom_z':plate_bottom,'plate_thickness_mm':1.2,'pcb_to_plate_gap_mm':nominal_gap,'pcb_top_z':pcb_top,'pcb_bottom_z':shift,'pcb_gap_basis':'PROVISIONAL parameter; Topre dome/housing/standoff stack is not dimensionally qualified'},'mounting_hole_matches':hole_matches,'max_hole_center_offset_mm':max(h['center_offset_mm'] for h in hole_matches),'min_M2_radial_margin_before_tolerances_mm':min(h['nominal_M2_radial_margin_before_tolerances_mm'] for h in hole_matches),'power_switch_access':'SW100 remains internal; no external actuator opening or extension is defined','plate_profile_chord_error_mm':.002,'active_key_positions':keys,'native_step_substrate_body_thickness_mm':native_thickness,'finished_board_envelope_thickness_mm':meta['pcb_thickness_mm'],'finished_envelope_basis':'Native STEP bottom face extruded to declared finished copper/mask thickness; conservative full board envelope','pcb_case_overlap_mm3':pcb_collisions,'pcb_case_distances_mm':pcb_distances,'plate_case_overlap_mm3':plate_collision,'component_envelopes':envelopes,'colliding_envelopes':[e['ref'] for e in hits],'pcb_gap_sweep':sweep,'battery_candidates':candidates,'not_verified':['Final switch/dome/fastener PCB-to-plate gap and tolerances','Actual battery/protection/NTC, swelling/insulation, cable bend and daughterboard envelope','J2 mating plug and current component height assumptions except sourced Raytac and JST body heights','Resin insert conversion and print shrinkage; original M3 metal-thread pilots are retained','Generic keycap shapes in renders are illustrative, not qualified OEM CAD']}
    (ROOT/'docs/audit/yeti60-assembly.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'PCB_overlap':pcb_collisions,'PCB_distance':pcb_distances,'plate_overlap':plate_collision,'colliding_envelopes':report['colliding_envelopes'],'battery_candidates':len(candidates)},indent=2))
    if max(pcb_collisions+plate_collision)>1e-5 or hits or any(max(c['case_overlap_mm3'])>1e-5 for c in candidates):
        raise SystemExit('Assembly geometry has collisions; inspect report')
if __name__=='__main__':main()
