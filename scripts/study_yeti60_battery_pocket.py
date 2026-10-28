#!/usr/bin/env python3
"""Build an optional interior-only recess and measure actual BRep wall clearance."""
import hashlib,json,math,re
from pathlib import Path
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder,BRepPrimAPI_MakeBox
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.GeomAbs import GeomAbs_Plane
from OCP.TopAbs import TopAbs_FACE,TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pnt
from cad_geometry import load,bounds,intersection_volume
from check_yeti60_assembly import box,distance
from build_yeti60_mechanical import cut,write,cylinder
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rounded_box(b,r):
 x,y,z,X,Y,Z=b;s=box([x+r,y,z,X-r,Y,Z])
 for a in [box([x,y+r,z,X,Y-r,Z])]+[cylinder(cx,cy,z,r,Z-z) for cx in [x+r,X-r] for cy in [y+r,Y-r]]:
  op=BRepAlgoAPI_Fuse(s,a);op.Build();assert op.IsDone();s=op.Shape()
 return s

def main():
 path=ROOT/'mechanical/battery-pocket-study.json';spec=json.loads(path.read_text());source=ROOT/'mechanical/generated/yeti60-bottom.step';s=load(source);top=load(ROOT/'mechanical/generated/yeti60-top.step');tool=rounded_box(spec['pocket_bounds_case_mm'],spec['pocket_corner_radius_mm']);result=cut(s,tool)
 n=0;ex=TopExp_Explorer(result,TopAbs_SOLID)
 while ex.More():n+=1;ex.Next()
 assert n==1 and BRepCheck_Analyzer(result).IsValid();assert max(abs(a-b) for a,b in zip(bounds(s),bounds(result)))<1e-6
 # The exterior underside is the large 7-degree planar face, not the flat inner floor.
 ex=TopExp_Explorer(s,TopAbs_FACE);candidates=[]
 while ex.More():
  f=TopoDS.Face(ex.Current());surf=BRepAdaptor_Surface(f);bb=bounds(f)
  if surf.GetType()==GeomAbs_Plane:
   d=surf.Plane().Axis().Direction()
   if abs(d.Z())>.9 and .10<abs(d.Y())<.15 and bb[3]-bb[0]>300 and bb[4]-bb[1]>80:
    g=GProp_GProps();BRepGProp.SurfaceProperties_s(f,g);candidates.append((g.Mass(),f,surf.Plane()))
  ex.Next()
 assert candidates,'No unique large exterior underside plane found'
 _,outer,plane=max(candidates,key=lambda x:x[0]);pb=spec['pocket_bounds_case_mm'];floor=box([pb[0],pb[1],pb[2],pb[3],pb[4],pb[2]+.001]);wall=distance(floor,outer)
 assert wall-spec['floor_tolerance_allowance_mm']>=spec['required_remaining_wall_mm']
 pack=box(spec['pack_bounds_case_mm']);pack_overlap=[intersection_volume(pack,c) for c in [result,top]];assert max(pack_overlap)<1e-6
 tol=spec['pack_xy_and_case_tolerance_allowance_mm'];eb=spec['pack_bounds_case_mm'].copy()
 for i in [0,1]:eb[i]-=tol;eb[i+3]+=tol
 expanded_pack=box(eb);expanded_overlap=[intersection_volume(expanded_pack,c) for c in [result,top]];assert max(expanded_overlap)<1e-6,'Pack XY placement/case tolerance hits pocket corner'
 fit=json.loads((ROOT/'docs/audit/yeti60-assembly.json').read_text());component_hits=[p['ref'] for p in fit['component_envelopes'] if intersection_volume(pack,box(p['bounds_case_mm']))>1e-6];assert not component_hits
 fastener_distances=[]
 for h in fit['mounting_hole_matches']:
  x,y=h['pcb_center_case_mm'];head=cylinder(x,y,fit['nominal_stack']['pcb_bottom_z']-1.9,3,1.9);fastener_distances.append(distance(pack,head));assert intersection_volume(pack,head)<1e-6
 # An exact BRep common checks the cutter against insert/service datums, not a grid approximation.
 assembly=json.loads((ROOT/'mechanical/assembly-spec.json').read_text());protected=[]
 for axes,r in [(assembly['case']['top_screw_axes'],5),(assembly['case']['daughterboard_screw_axes'],4)]:
  for x,y in axes:protected.append(intersection_volume(tool,cylinder(x,y,-25,r,40)))
 assert max(protected)<1e-6
 write(result,'yeti60-bottom-battery-pocket.step');out=ROOT/'mechanical/generated/yeti60-bottom-battery-pocket.step';props=GProp_GProps();BRepGProp.VolumeProperties_s(s,props);before=props.Mass();BRepGProp.VolumeProperties_s(result,props);removed=before-props.Mass();assert removed>0
 report={'status':'optional-pocket-geometric-checks-passed','production_approved':False,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [path,source,ROOT/'mechanical/generated/yeti60-top.step',ROOT/'mechanical/assembly-spec.json',ROOT/'docs/audit/yeti60-assembly.json',Path(__file__).resolve(),ROOT/'scripts/cad_geometry.py',ROOT/'scripts/build_yeti60_mechanical.py',ROOT/'scripts/check_yeti60_assembly.py']},'output':str(out.relative_to(ROOT)),'output_sha256':sha(out),'external_bounds_mm':bounds(result),'case_scale':[1,1,1],'solid_count':n,'removed_volume_mm3':removed,'pocket_bounds_case_mm':pb,'pack_bounds_case_mm':spec['pack_bounds_case_mm'],'pack_max_envelope_mm':spec['pack_max_envelope_mm'],'pack_case_overlap_mm3':pack_overlap,'expanded_pack_xy_tolerance_mm':tol,'expanded_pack_case_overlap_mm3':expanded_overlap,'component_envelope_collisions':component_hits,'minimum_pack_to_fastener_envelope_mm':min(fastener_distances),'minimum_remaining_wall_normal_mm':wall,'remaining_wall_after_tolerance_mm':wall-spec['floor_tolerance_allowance_mm'],'wall_method':'Exact minimum BRep distance between conservative full rectangular pocket-floor region and original large sloping exterior underside face; includes rounded-pocket corners conservatively','underside_plane':{'normal':[plane.Axis().Direction().X(),plane.Axis().Direction().Y(),plane.Axis().Direction().Z()],'point':[plane.Location().X(),plane.Location().Y(),plane.Location().Z()]},'insert_keepouts_removed_volume_mm3':max(protected),'not_verified':spec['not_verified']}
 (ROOT/'docs/audit/yeti60-battery-pocket.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['status','removed_volume_mm3','minimum_remaining_wall_normal_mm','remaining_wall_after_tolerance_mm','minimum_pack_to_fastener_envelope_mm']},indent=2))
if __name__=='__main__':main()
