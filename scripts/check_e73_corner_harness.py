#!/usr/bin/env python3
"""Independent continuous-solid E73 harness study; never releases manufacturing."""
import argparse,hashlib,json,math
from pathlib import Path
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism,BRepPrimAPI_MakeCylinder
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.gp import gp_Vec,gp_Pnt,gp_Ax2,gp_Dir
from cad_geometry import load,bounds,intersection_volume
from check_yeti60_assembly import box,distance,move,wire
from check_yeti60_interconnects import write_step,near
from e73_corner_harness_paths import paths,paired_data,length,envelope_wire,sweep_wire
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'.assembly-work/e73-corner/harness';BASE=ROOT/'hardware/e73-hhkb-corner'
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def cut(a,b):
 op=BRepAlgoAPI_Cut(a,b);op.Build();assert op.IsDone()and BRepCheck_Analyzer(op.Shape()).IsValid();return op.Shape()
def datums(n,a,s):
 roles={'J4':{'1':'USB_FEED','2':'USB_DM','3':'USB_DP','4':'GND'},'J5':{'1':'USB_FEED','2':'GND'},'J1':{'1':'VBUS','4':'GND'},'J2':{'1':'BAT_CELL','2':'GND','3':'BAT_NTC'}}
 for ref,pins in roles.items():
  assert n['parts'][ref]['side']=='back',('Header side',ref)
  actual={q['pin']:q['net']for q in n['parts'][ref]['pads']}
  assert all(actual.get(pin)==net for pin,net in pins.items()),('Header pin contract',ref)
 bottom=a['stack']['plate_bottom_z']-a['stack']['pcb_to_plate_gap']-a['stack']['pcb_thickness'];ex={}
 # Recover actual connector frame from the ordered signal pads. For a back
 # header +local-Y (mating direction) is a counter-clockwise rotation of pad1->padN
 # in the right-handed case XY frame. SH signal row is local Y=-2.0.
 for ref,count in [('J1',4),('J2',3),('J4',4),('J5',2)]:
  p={q['pin']:q['xy_PCB_mm']for q in n['parts'][ref]['pads']if q['pin']in map(str,range(1,count+1))};first=p['1'];last=p[str(count)];t=((last[0]-first[0])/(count-1),-(last[1]-first[1])/(count-1));assert abs(math.hypot(*t)-1)<1e-6
  mating=(-t[1],t[0]);centre=((first[0]+last[0])/2,-(first[1]+last[1])/2)
  ex[ref]=[centre[i]+mating[i]*6.575 for i in range(2)]+[bottom-1.6]
 d=a['daughterboard'];ex['C5']=[75.0045+d['source_to_case_x_offset'],-(68.793+1.45)+d['source_to_case_y_offset']+1.675-6.25,d['pcb_bottom_z']+d['pcb_thickness']+1.4]
 b=a['battery'];ex['pack']=[b['bounds_xy'][0]+s['battery']['pack_exit_local'][0],b['bounds_xy'][1]+s['battery']['pack_exit_local'][1],b['top_z']-b['full_envelope_including_growth'][2]+s['battery']['pack_exit_local'][2]]
 return bottom,ex

def case_study(s,a):
 original=load(ROOT/s['source_bottom']);case=original;cuts=[]
 for key in ['case_pocket']:
  cutter=box(s[key]['bounds_case_mm']);before=case;case=cut(case,cutter);cuts.append((key,cut(before,case)))
 # Same conservative selected exterior-face test as the existing Raytac
 # checker, reused as geometry only, with no inherited acceptance inputs.
 from OCP.TopExp import TopExp_Explorer
 from OCP.TopAbs import TopAbs_FACE,TopAbs_REVERSED
 from OCP.TopoDS import TopoDS
 from OCP.BRepAdaptor import BRepAdaptor_Surface
 from OCP.BRepTools import BRepTools
 from OCP.gp import gp_Vec
 outer=[];it=TopExp_Explorer(original,TopAbs_FACE)
 while it.More():
  f=TopoDS.Face(it.Current());bb=bounds(f);sf=BRepAdaptor_Surface(f);u,U,v,V=BRepTools.UVBounds_s(f);p=gp_Pnt();du=gp_Vec();dv=gp_Vec();sf.D1((u+U)/2,(v+V)/2,p,du,dv);normal=du.Crossed(dv)
  if normal.Magnitude()>1e-9:
   normal.Normalize()
   if f.Orientation()==TopAbs_REVERSED:normal.Reverse()
   if(normal.Z()<-.3 and bb[5]<-7)or(normal.Y()>.3 and bb[4]>-96)or(normal.X()>.3 and bb[3]>375)or(normal.X()<-.3 and bb[0]<53):outer.append(f)
  it.Next()
 removed=cut(original,case);skin=min(distance(removed,f)for f in outer)-a['case']['linear_tolerance'];guards=[]
 for kind,axes in [('M3',a['case']['top_screw_axes']),('M2',a['case']['daughterboard_screw_axes'])]:
  i=a['case']['top_insert'if kind=='M3'else'daughterboard_insert'];r=(i['bore_diameter']+i['bore_tolerance'])/2+a['case']['finished_bore_position_tolerance']+2;z=i['bore_start_z'];end=z+(i['bore_depth']if kind=='M3'else-i['bore_depth'])
  for x,y in axes:
   guard=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,min(z,end)-2),gp_Dir(0,0,1)),r,abs(end-z)+4).Shape();guards.append(dict(kind=kind,xy=[x,y],removed_overlap_mm3=intersection_volume(removed,guard)))
 report=dict(cut_skin=[dict(name=k,minimum_gap_mm=min(distance(q,f)for f in outer),nearest_face_bounds=bounds(min(outer,key=lambda f:distance(q,f))))for k,q in cuts],minimum_selected_skin_after_case_tolerance_mm=skin,required_skin_mm=2,selected_exterior_face_count=len(outer),insert_guards=guards,unchanged_outer_bounds=max(abs(x-y)for x,y in zip(bounds(original),bounds(case)))<1e-6)
 return case,report

def bodies(n,a,s,bottom,delta):
 out={};top=bottom+a['stack']['pcb_thickness'];limits=s['assembly_limits'];models=read('hardware/e73-hhkb-corner/audit/local-models.json')
 for ref,p in n['parts'].items():
  x,y,X,Y=p['bbox_PCB_mm'];height=limits.get(ref)
  if height is None:
   if ref.startswith('R'):height=limits['R']
   elif ref.startswith('C'):
    package=next((v for v in ['0402','0603','0805']if 'C_'+v in p['footprint']),None);assert package,('Unbounded capacitor package',ref);height=limits['C_'+package]
   else:raise ValueError(ref)
  if ref in models['parts']:
   q=models['parts'][ref]['nominal_model_and_Fab_union_bounds_native_mm'];x,y,X,Y=q[0],-q[4],q[3],-q[1]
  z,Z=(top-.15,top+height+.15)if p['side']=='front'else(bottom-height-.15,bottom+.15)
  out[ref]=box([x-.1,-Y-.1,z+delta,X+.1,-y+.1,Z+delta])
 for index,m in enumerate(n['mounts']):
  if m['ref']in a['pcb_fastener']['unused_pcb_mount_refs']:continue
  x,y=m['xy_PCB_mm'];y=-y;r=a['pcb_fastener']['washer_od_max']/2+.15;out['mount-'+str(index)]=box([x-r,y-r,bottom-1.9+delta,x+r,y+r,bottom+delta])
 d=a['daughterboard'];p=read('docs/audit/yeti60-daughterboard.json');assert sha(p['exported_step'])==p['exported_step_sha256'];out['C5']=move(load(ROOT/p['exported_step']),d['source_to_case_x_offset'],d['source_to_case_y_offset'],d['pcb_bottom_z'])
 for i,(x,y)in enumerate(a['case']['daughterboard_screw_axes']):out['C5-mount-'+str(i)]=box([x-2.1,y-2.1,-9.3038,x+2.1,y+2.1,-6.9])
 return out

def pcb_solid(bottom,thickness):
 outline=read('.assembly-work/e73-corner/copper.json')['outline'];assert len(outline)==1;q=outline[0];face=BRepBuilderAPI_MakeFace(wire([(x,-y,bottom)for x,y in q['outer']],True))
 for h in q['holes']:face.Add(wire([(x,-y,bottom)for x,y in h],False))
 return BRepPrimAPI_MakePrism(face.Face(),gp_Vec(0,0,thickness)).Shape()

def portal(point,tangent,depth=1.0,width=1.0):
 # Bounded launch/termination exception only: any return of the cable to its
 # owning header elsewhere still collides. The port is declared in report.
 p=list(point);q=[p[i]+tangent[i]*depth for i in range(3)];return box([min(p[i],q[i])-width for i in range(3)]+[max(p[i],q[i])+width for i in range(3)])

def evaluate(s,n,a,ex,bottom,case,delta=0,export=False):
 route,centre=paths(s,ex,delta);data,twists=paired_data(centre,s);route['usb'].update(data);obs=bodies(n,a,s,bottom,delta);top=load(ROOT/a['geometry']['top']);pcb=pcb_solid(bottom+delta,a['stack']['pcb_thickness']-delta);b=a['battery'];pack=box([b['bounds_xy'][0]-.25,b['bounds_xy'][1]-.25,b['top_z']-4.8-.25,b['bounds_xy'][2]+.25,b['bounds_xy'][3]+.25,b['top_z']+.25]);result=[];shapes={};portals=[]
 # Mated SHR housings: conservative boxes, header overlap intentional.
 for ref,count,axis in [('J4',4,(-1,0)),('J5',2,(0,1)),('J2',3,(0,1)),('J1',4,(1,0)),('C5',4,(0,-1))]:
  p=list(ex[ref]);p[2]+=delta if ref!='C5'else 0
  if ref!='C5':
   pads={q['pin']:q['xy_PCB_mm']for q in n['parts'][ref]['pads']};q=pads['1'];r=pads[str(count)];axis=((r[1]-q[1])/(count-1),(r[0]-q[0])/(count-1))
  width=count+1;depth=5;xx,yy=(depth,width)if axis[0]else(width,depth);cx=p[0]-axis[0]*depth/2;cy=p[1]-axis[1]*depth/2;z0=p[2]-1.5;z1=p[2]+1.5;obs['plug-'+ref]=box([cx-xx/2,cy-yy/2,z0,cx+xx/2,cy+yy/2,z1])
 for family,wires in route.items():
  for pin,path in wires.items():
   shape=envelope_wire(path,s['wire']['insulation_od_max']+2*s['wire']['case_and_route_position_allowance']);shapes[family,pin]=shape;bb=bounds(shape);clear={};owner={'usb':'J4','power':'J5','battery':'J2'}[family];target={'usb':'C5','power':'J1','battery':'pack'}[family];from interconnect_geometry import tangent
   p1=portal(path[0]['start'],tangent(path[0],False));p2=portal(path[-1]['end'],tangent(path[-1],True));portals.append(dict(family=family,pin=pin,start_bounds=bounds(p1),end_bounds=bounds(p2)))
   for name,obj in [('bottom',case),('top',top),('PCB',pcb),('pack',pack)]+list(obs.items()):
    if not near(bb,bounds(obj),1):continue
    if name in [owner,'plug-'+owner]:obj=cut(obj,p1)
    if name in [target,'plug-'+target]:obj=cut(obj,p2)
    gap=distance(shape,obj);clear[name]=gap
   radii=[p.get('radius',p.get('curvature_radius_lower_bound_mm',1e9))for p in path if p['kind']!='line'];v=dict(family=family,pin=pin,free_length_mm=length(path),minimum_bend_radius_mm=min(radii),clearances_mm=clear,start=path[0]['start'],end=path[-1]['end']);result.append(v)
   if export:write_step(sweep_wire(path,.8),WORK/(family+'-'+pin+'.step'))
   from OCP.BRepExtrema import BRepExtrema_DistShapeShape
   d=BRepExtrema_DistShapeShape(shape,case);d.Perform();point=d.PointOnShape2(1);v['nearest_case_point_mm']=[point.X(),point.Y(),point.Z()]
   print(delta,family,pin,round(v['free_length_mm'],3),'min',sorted(clear.items(),key=lambda q:q[1])[:3], 'case_point',v['nearest_case_point_mm'],flush=True)
 crossings=[]
 for left,right in [('usb','power'),('usb','battery'),('power','battery')]:
  d,i,j=min((distance(q,r),i,j)for i,q in shapes.items()if i[0]==left for j,r in shapes.items()if j[0]==right)
  q=BRepExtrema_DistShapeShape(shapes[i],shapes[j]);q.Perform();point=q.PointOnShape1(1);witness=[point.X(),point.Y(),point.Z()];crossings.append(dict(families=[left,right],gap_mm=d,wires=[i,j],witness_mm=witness));print('cross',delta,left,right,d,witness,flush=True)
 internal=[]
 from itertools import combinations
 # Per-harness relative-position allowance differs from the globally shared
 # route envelope. Only the twisted data pair deliberately touches insulation.
 local={key:envelope_wire(route[key[0]][key[1]],s['wire']['insulation_od_max']+2*s['wire']['relative_non_twisted_position_allowance_mm'])for key in shapes}
 for family in route:
  for i,j in combinations(route[family],2):
   if family=='usb'and {i,j}=={'2','3'}:continue
   left,right=local[family,i],local[family,j];gap=distance(left,right);overlap=intersection_volume(left,right)if gap<1e-6 else 0
   internal.append(dict(family=family,pins=[i,j],relative_envelope_gap_mm=gap,overlap_mm3=overlap));assert overlap<1e-6,('Same-harness insulation intersection',family,i,j,overlap)
 skew=abs(length(route['usb']['2'])-length(route['usb']['3']));assert skew<1
 # Bind each physical start/end to the actual native pad order, independently
 # of the path generator's lateral-offset convention.
 for family,ref in [('usb','J4'),('power','J5'),('battery','J2')]:
  p=n['parts'][ref];pads={q['pin']:q for q in p['pads']};count=len(route[family]);first=pads['1']['xy_PCB_mm'];last=pads[str(count)]['xy_PCB_mm'];direction=[(last[0]-first[0])/(count-1),-(last[1]-first[1])/(count-1)]
  for pin,path in route[family].items():
   offset=int(pin)-(count+1)/2;expected=[ex[ref][i]+direction[i]*offset for i in range(2)]+[ex[ref][2]+delta];assert math.dist(path[0]['start'],expected)<1e-6,('Wrong native wire order',family,pin)
 for pin,path in route['usb'].items():assert math.dist(path[-1]['end'],[ex['C5'][0]+int(pin)-2.5,ex['C5'][1],ex['C5'][2]])<1e-6
 assert math.dist(route['power']['1'][-1]['end'],[ex['J1'][0],ex['J1'][1]+1.5,ex['J1'][2]+delta])<1e-6
 assert math.dist(route['power']['2'][-1]['end'],[ex['J1'][0],ex['J1'][1]-1.5,ex['J1'][2]+delta])<1e-6
 return dict(pcb_bottom_shift_mm=delta,internal_conductor_checks=internal,USB_geometric_pair_skew_mm=skew,wires=result,crossings=crossings,twists=twists,portals=portals,routes=route)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--export',action='store_true');parser.add_argument('--thickness',action='store_true');parser.add_argument('--publish',action='store_true');args=parser.parse_args();WORK.mkdir(parents=True,exist_ok=True);s=read('hardware/e73-corner-harness-spec.json');a=read('mechanical/assembly-spec.json');n=read('hardware/e73-hhkb-corner/audit/harness-native.json')
 for path,digest in n['source_sha256'].items():assert sha(path)==digest,('Stale native map',path)
 if args.publish:(BASE/'audit/harness-study.json').unlink(missing_ok=True)
 inputs=[ROOT/'hardware/e73-corner-harness-spec.json',ROOT/'mechanical/assembly-spec.json',ROOT/'mechanical/pcb-fabrication-spec.json',BASE/'EC60-nRF52840.kicad_pcb',BASE/'audit/harness-native.json',BASE/'audit/local-models.json',ROOT/s['source_bottom'],ROOT/a['geometry']['top'],ROOT/'docs/audit/yeti60-daughterboard.json',Path(__file__),ROOT/'scripts/e73_corner_harness_paths.py',ROOT/'scripts/interconnect_geometry.py',ROOT/'scripts/cad_geometry.py',ROOT/'scripts/check_yeti60_assembly.py',ROOT/'scripts/check_yeti60_interconnects.py']
 before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in inputs}
 for path,digest in read('hardware/e73-hhkb-corner/audit/local-models.json')['source_sha256'].items():assert sha(path)==digest,('Stale connector model',path)
 bottom,ex=datums(n,a,s);print('exits',ex,flush=True);case,cr=case_study(s,a);print('case',json.dumps(cr),flush=True);results=[evaluate(s,n,a,ex,bottom,case,export=args.export)]
 if args.thickness or args.publish:
  for t in read('mechanical/pcb-fabrication-spec.json')['ordinary_thickness_acceptance_range_mm']:results.append(evaluate(s,n,a,ex,bottom,case,a['stack']['pcb_thickness']-t))
 failures=[]
 if cr['minimum_selected_skin_after_case_tolerance_mm']<2:failures.append('case-skin')
 if any(q['removed_overlap_mm3']>1e-6 for q in cr['insert_guards']):failures.append('insert-support')
 if not cr['unchanged_outer_bounds']:failures.append('outer-envelope')
 for r in results:
  for w in r['wires']:
   for name,gap in w['clearances_mm'].items():
    required=.15+(math.sqrt(3)*.15+.002 if name in ['bottom','top']else 0)
    if gap<required-1e-6:failures.append([r['pcb_bottom_shift_mm'],w['family'],w['pin'],name,gap,required])
   if w['minimum_bend_radius_mm']<4-1e-6:failures.append(['bend',w['family'],w['pin']])
  for cross in r['crossings']:
   if cross['gap_mm']<.15-1e-6:failures.append(['cross',r['pcb_bottom_shift_mm'],cross])
 report=dict(status='continuous-wire-study-passed-guides-open'if not failures else'continuous-wire-study-failed',manufacturing_released=False,physical_verification=False,connector_exits_case_mm=ex,case=cr,variants=results,failures=failures,source_sha256=before)
 assert all(sha(path)==digest for path,digest in before.items()),'Harness source changed during evaluation'
 (WORK/'study.json').write_text(json.dumps(report,indent=2)+'\n');print('FAILURES',json.dumps(failures),flush=True)
 if failures:raise SystemExit(2)
 if args.publish:
  from OCP.BRepMesh import BRepMesh_IncrementalMesh
  from OCP.StlAPI import StlAPI_Writer
  out=BASE/'mechanical';out.mkdir(exist_ok=True);target=out/'yeti60-e73-corner-bottom-m04.step';write_step(case,target);BRepMesh_IncrementalMesh(case,.025,False,.08,True).Perform();writer=StlAPI_Writer();writer.ASCIIMode=False;assert writer.Write(case,str(target.with_suffix('.stl')))
  report['outputs']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [target,target.with_suffix('.stl')]}
  report['limits']=['Continuous sweeps and conservative body/plug boxes only; guide/film retention not accepted yet','Wire OD includes incoming tolerance; supplier bend/crimp compatibility requires confirmation','Case exterior and insert guards screened, not structural FEA','No physical assembly, USB signal integrity, RF/EC or battery thermal qualification']
  (BASE/'audit/harness-study.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
