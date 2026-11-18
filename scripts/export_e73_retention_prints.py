#!/usr/bin/env python3
"""Export measured local-mm print meshes and separate film cutting templates.

Rigid transforms only. Assembly STEP coordinates are retained separately from
STL files placed at the origin for fabrication. Films are cut, never printed.
"""
import csv,hashlib,html,json,math,struct
from pathlib import Path
import numpy as np
import ezdxf
from OCP.gp import gp_Trsf,gp_Ax1,gp_Pnt,gp_Dir
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.TopoDS import TopoDS_Compound
from OCP.BRep import BRep_Builder
from cad_geometry import load,bounds
from e73_fit_geometry import volume
from check_yeti60_assembly import move
from check_yeti60_interconnects import write_step
from e73_corner_retention import build
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/e73-hhkb-corner';OUT=BASE/'mechanical/retention'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def mesh(shape,target):
 BRepMesh_IncrementalMesh(shape,.008,False,.08,True).Perform();writer=StlAPI_Writer();writer.ASCIIMode=False;assert writer.Write(shape,str(target));data=target.read_bytes();n=struct.unpack_from('<I',data,80)[0];assert len(data)==84+n*50;pts=np.array([struct.unpack_from('<9f',data,84+i*50+12)for i in range(n)]).reshape(-1,3,3);bb=np.concatenate([pts.min(axis=(0,1)),pts.max(axis=(0,1))]);expected=np.array(bounds(shape));assert np.max(np.abs(bb-expected))<.012;v=abs(np.einsum('ij,ij->i',pts[:,0],np.cross(pts[:,1],pts[:,2])).sum()/6);assert abs(v/volume(shape)-1)<.015;return dict(triangles=n,mesh_bounds_mm=bb.tolist(),mesh_volume_mm3=float(v),STEP_volume_mm3=volume(shape))
def main():
 r=read('hardware/e73-hhkb-corner/audit/retention-study.json');assert r['status']=='bounded-retainer-study-passed-service-and-process-open'and not r['failures']
 for section in ['source_sha256','outputs']:
  for name,digest in r[section].items():assert sha(ROOT/name)==digest,('Stale retainer evidence',name)
 s=read('hardware/e73-corner-harness-spec.json');ret=read('hardware/e73-corner-retention-spec.json');s['guides']=ret['guides'];a=read('mechanical/assembly-spec.json');wire=read('hardware/e73-hhkb-corner/audit/harness-study.json');case=load(ROOT/a['geometry']['bottom']);guides,films=build(s,case,wire['variants'][0]['routes'],wire['connector_exits_case_mm']);OUT.mkdir(exist_ok=True);(OUT/'print').mkdir(exist_ok=True);(OUT/'assembly-reference').mkdir(exist_ok=True);rows=[];outputs={};builder=BRep_Builder();plate=TopoDS_Compound();builder.MakeCompound(plate)
 for index,q in enumerate(guides):
  source=BASE/'mechanical/retention-review'/(q['name']+'.step');shape=load(source);flip=q['mount']!='case-floor';transform=gp_Trsf()
  if flip:transform.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(1,0,0)),math.pi);shape=BRepBuilderAPI_Transform(shape,transform,True).Shape()
  bb=bounds(shape);translation=[-v for v in bb[:3]];local=move(shape,*translation);target=OUT/'print'/(q['name']+'.stl');record=mesh(local,target);assert abs(volume(local)/volume(load(source))-1)<1e-6
  # A separate, spaced layout is a convenience file, not an extra part.
  placed=move(local,(index%4)*10,(index//4)*9,0);builder.Add(plate,placed);write_step(load(source),OUT/'assembly-reference'/(q['name']+'.step'));outputs[str(target.relative_to(ROOT))]=sha(target)
  rows.append(dict(name=q['name'],quantity=1,family=q['family'],mount=q['mount'],datum_case_mm=q['datum_case_mm'],source_assembly_STEP=str(source.relative_to(ROOT)),source_sha256=sha(source),X_rotation_deg=180 if flip else 0,local_translation_mm=translation,scaled=False,local_STL=str(target.relative_to(ROOT)),**record))
 target=OUT/'print/ALL-16-GUIDES-ONE-EACH.stl';mesh(plate,target);outputs[str(target.relative_to(ROOT))]=sha(target);write_step(plate,OUT/'print/ALL-16-GUIDES-ONE-EACH.step')
 cuts=[]
 for q in films:
  source=BASE/'mechanical/retention-review'/(q['name']+'.step');write_step(load(source),OUT/'assembly-reference'/(q['name']+'.step'))
  bb=bounds(q['shape']);width=bb[3]-bb[0]
  if q['folded_strap']:
   # Oversize blanks are folded on the actual part and trimmed to the STEP
   # envelope. This is not a claimed exact neutral-axis bend development.
   span=bb[4]-bb[1]-2*q['film_thickness_mm'];leg=bb[5]-bb[2];length=span+2*leg+1.0;allowance=.5
  else:
   if 'USB-F'in q['name']:width=bb[4]-bb[1]
   length=bb[5]-bb[2];allowance=0
  cuts.append(dict(name=q['name'],quantity=1,blank_width_mm=round(width,3),blank_length_mm=round(length,3),trim_allowance_each_end_mm=allowance,folded=q['folded_strap'],total_thickness_max_mm=q['film_thickness_mm'],assembly_bounds_case_mm=bb))
 for zh in [False,True]:
  suffix='.zh-CN'if zh else'';target=OUT/('parts'+suffix+'.csv')
  with target.open('w',newline='')as f:
   w=csv.writer(f,lineterminator='\n');w.writerow(['零件','数量','制造方式','文件／说明']if zh else['Part','Quantity','Process','File / instructions'])
   for q in rows:w.writerow([q['name'],1,'绝缘刚性支架，尺寸及薄壁须检验'if zh else'Rigid insulating guide; inspect dimensions and webs','print/'+q['name']+'.stl'])
   for q in cuts:w.writerow([q['name'],1,'聚酰亚胺胶带裁片，禁止打印'if zh else'Cut polyimide tape; do not print',f'{q["blank_width_mm"]} x {q["blank_length_mm"]} mm'+('，折后按 STEP 修剪'if zh and q['folded']else'; fold and trim to STEP'if q['folded']else'')])
  outputs[str(target.relative_to(ROOT))]=sha(target)
  width,height=110,95;body=[]
  for i,q in enumerate(cuts):
   x=5+(i%4)*27;y=7+(i//4)*16;body.append(f'<rect x="{x}" y="{y}" width="{q["blank_length_mm"]}" height="{q["blank_width_mm"]}" fill="none" stroke="#244738" stroke-width="0.15"/><text x="{x}" y="{y+q["blank_width_mm"]+3}" font-size="2">{html.escape(q["name"])}</text>')
  body.append('<path d="M5 92h50" stroke="#244738" stroke-width="0.2"/><text x="58" y="93" font-size="2.4">50 mm</text>');target=OUT/('film-blanks'+suffix+'.svg');target.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" height="{height}mm" viewBox="0 0 {width} {height}"><title>'+('胶膜下料参考，折后按装配包络修剪'if zh else'Film blanks; fold and trim to assembly envelope')+'</title>'+''.join(body)+'</svg>\n');outputs[str(target.relative_to(ROOT))]=sha(target)
 report=dict(status='local-mm-rigid-mesh-and-film-blank-exports-passed',manufacturing_released=False,physical_verification=False,rigid_parts=rows,film_blanks=cuts,source_sha256={str(p.relative_to(ROOT)):sha(p)for p in [BASE/'audit/retention-study.json',BASE/'audit/harness-study.json',ROOT/'hardware/e73-corner-retention-spec.json',ROOT/'scripts/e73_corner_retention.py',Path(__file__)]},outputs=outputs,limits=['STL origin/orientation changed by rigid transforms only; assembly STEP retains case coordinates','ALL-16 is one copy of every rigid guide, not a seventeenth part','Film SVG blanks require actual folding, trimming and incoming-thickness inspection; sharp CAD folds are explanatory'])
 # Include every actual generated file, including local STEP references.
 report['outputs']={str(p.relative_to(ROOT)):sha(p)for p in sorted(OUT.rglob('*'))if p.is_file()and p.name!='.DS_Store'}
 (BASE/'audit/retention-prints.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':main()
