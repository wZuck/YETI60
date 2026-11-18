#!/usr/bin/env python3
"""Bound current E73 retainers/complete films against this case and all nine leads.

No production release. Mating faces require measured finishing/bondline control;
this is not an assumption that independent raw print tolerances fit together.
"""
import argparse,copy,hashlib,json,math
from pathlib import Path
from itertools import combinations
from cad_geometry import load,bounds,intersection_volume
from check_yeti60_assembly import box,distance,move
from check_yeti60_interconnects import near,write_step
from check_e73_corner_harness import datums,bodies,pcb_solid,cut
from e73_corner_retention import build
from e73_retention_channels import capture,bond_areas
from e73_corner_harness_paths import envelope_wire
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/e73-hhkb-corner';WORK=ROOT/'.assembly-work/e73-corner/retention'
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def owners(item):
 owner=item.get('bond_pair');return set(owner if isinstance(owner,list)else [owner]if owner else [])
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--export',action='store_true');args=parser.parse_args();WORK.mkdir(parents=True,exist_ok=True)
 r=read('hardware/e73-hhkb-corner/audit/harness-study.json');assert r['status']=='continuous-wire-study-passed-guides-open'and not r['failures']
 for section in ['source_sha256','outputs']:
  for path,digest in r[section].items():assert sha(path)==digest,('Stale wire geometry',path)
 s=read('hardware/e73-corner-harness-spec.json');a=read('mechanical/assembly-spec.json');n=read('hardware/e73-hhkb-corner/audit/harness-native.json');ret=read('hardware/e73-corner-retention-spec.json');s['guides']=ret['guides'];tol=ret['tolerance_contract'];bottom,ex=datums(n,a,s);case=load(ROOT/a['geometry']['bottom']);top=load(ROOT/a['geometry']['top']);pack=box([228.25,-149.25,-9.65,313.75,-105.75,-4.35]);nominal,films=build(s,case,r['variants'][0]['routes'],ex,bottom);assert len(nominal)==16 and len(films)==17
 inputs=[BASE/'audit/harness-study.json',BASE/'audit/harness-native.json',ROOT/'hardware/e73-corner-retention-spec.json',ROOT/'hardware/e73-corner-harness-spec.json',ROOT/'mechanical/assembly-spec.json',ROOT/a['geometry']['bottom'],ROOT/a['geometry']['top'],ROOT/'scripts/e73_corner_retention.py',ROOT/'scripts/e73_retention_channels.py',ROOT/'scripts/check_e73_corner_harness.py',ROOT/'scripts/e73_corner_harness_paths.py',Path(__file__)]
 before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in inputs};failures=[];variants=[]
 for variant in r['variants']:
  delta=variant['pcb_bottom_shift_mm'];pcb=pcb_solid(bottom+delta,a['stack']['pcb_thickness']-delta);obs=bodies(n,a,s,bottom,delta);wire={(f,p):envelope_wire(path,.65)for f,paths in variant['routes'].items()for p,path in paths.items()};wide={(f,p):envelope_wire(path,.65+.5)for f,paths in variant['routes'].items()for p,path in paths.items()};items=[]
  for original in nominal+films:
   q=dict(original);q['shape']=move(q['shape'],z=delta)if q['mount'].startswith('PCB')else q['shape'];items.append(q)
  relative={(f,p):envelope_wire(path,.65+2*s['guides']['local_wire_position_allowance'])for f,paths in variant['routes'].items()for p,path in paths.items()}
  by_name={q['name']:q for q in items};records=[];pair_checks=[]
  for item in items:
   shape=item['shape'];bb=bounds(shape);film=item['category']=='retention-film'if 'category'in item else False;profile=tol['film_edge_error_L2_mm']if film else tol['guide_maximum_surface_point_error_L2_mm'];install=tol['guide_installed_datum_error_L2_mm'];owner='PCB'if item['mount'].startswith('PCB')else 'case'if item['mount']in ['case-floor','case-roof']and not film else None;clear={};interfaces=[]
   for name,obj in [('case',case),('top',top),('PCB',pcb),('pack',pack)]+list(obs.items()):
    if not near(bb,bounds(obj),1.5):continue
    if name==owner:
     if name=='PCB':face=bb[5]
     else:face=bb[5]if item['mount']=='case-roof'else bb[2]
     overlap=intersection_volume(shape,obj);assert overlap<1e-6,('Nominal mount intersection',item['name'],name,overlap)
     gap=distance(shape,obj);interfaces.append(dict(owner=name,nominal_bond_gap_mm=gap));cap=box([bb[0]-.8,bb[1]-.8,face-.65,bb[3]+.8,bb[4]+.8,face+.65]);obj=cut(obj,cap)
    gap=distance(shape,obj);error=profile+install+.002
    if name in ['case','top']:error+=math.sqrt(3)*tol['case_maximum_coordinate_error_each_axis_mm']
    elif name=='PCB'or name in obs:
     if not item['mount'].startswith('PCB'):error+=tol['PCB_installed_pose_Z_error_mm']+math.sqrt(3)*tol['case_maximum_coordinate_error_each_axis_mm']
    elif name=='pack'and item['mount'].startswith('PCB'):error+=tol['PCB_installed_pose_Z_error_mm']
    residual=gap-error;clear[name]=dict(nominal_gap_mm=gap,extra_error_mm=error,residual_mm=residual)
    if residual<tol['minimum_foreign_air_gap_mm']-1e-6:failures.append([delta,item['name'],name,residual])
   own=[];foreign=[]
   for (family,pin),solid in wire.items():
    if not near(bb,bounds(solid),1):continue
    if family==item['family']:
     overlap=intersection_volume(shape,solid);own.append(dict(pin=pin,overlap_mm3=overlap))
     if overlap>1e-6:failures.append([delta,item['name'],'own-insulation',pin,overlap])
    else:
     gap=distance(shape,wide[family,pin]);residual=gap-profile-install;foreign.append(dict(family=family,pin=pin,residual_mm=residual))
     if residual<.15-1e-6:failures.append([delta,item['name'],'other-wire',family,pin,residual])
   channels=[];bonding=[]
   if not film:
    channels=capture(item,relative,r['variants'][0]['routes'],s,delta)
    if not all(q['captured']for q in channels):failures.append([delta,item['name'],'wire-outside-channel',channels])
   else:
    bonding=bond_areas(item,by_name)
    if not all(q['bonded']for q in bonding):failures.append([delta,item['name'],'floating-or-unbonded-film',bonding])
   records.append(dict(channel_capture=channels,film_bond_areas=bonding,name=item['name'],mount=item['mount'],family=item['family'],bounds_case_mm=bb,clearances=clear,matched_interfaces=interfaces,own_wire_checks=own,foreign_wire_checks=foreign,film=film));print(delta,item['name'],'residual',round(min((v['residual_mm']for v in clear.values()),default=999),4),flush=True)
  for left,right in combinations(items,2):
   if not near(bounds(left['shape']),bounds(right['shape']),.3):continue
   intentional=right['name']in owners(left)or left['name']in owners(right)
   gap=distance(left['shape'],right['shape']);overlap=intersection_volume(left['shape'],right['shape'])if gap<1e-6 else 0
   if overlap>1e-6:failures.append([delta,'retainer-overlap',left['name'],right['name'],overlap])
   if not intentional and gap<.15+.2-1e-6:failures.append([delta,'retainer-gap',left['name'],right['name'],gap])
   pair_checks.append(dict(parts=[left['name'],right['name']],intentional_mating= intentional,gap_mm=gap,overlap_mm3=overlap))
  variants.append(dict(pcb_bottom_shift_mm=delta,parts=records,pair_checks=pair_checks))
 witness=move(nominal[0]['shape'],z=1.5);pcb=pcb_solid(bottom,a['stack']['pcb_thickness']);assert intersection_volume(witness,pcb)>1e-6,'Translated retainer failed to collide with PCB'
 relative={(f,p):envelope_wire(path,.85)for f,paths in r['variants'][0]['routes'].items()for p,path in paths.items()}
 bad=copy.deepcopy(s);bad['guides']['power_x'][1]=180;wrong,_=build(bad,case,r['variants'][0]['routes'],ex,bottom);part=next(q for q in wrong if q['name']=='PWR-R2');assert not all(q['captured']for q in capture(part,relative,r['variants'][0]['routes'],s)),'Empty misplaced guide was accepted'
 floating=dict(next(q for q in films if q['name']=='USB-R1-film'));bb=bounds(floating['shape']);floating['shape']=box([bb[0],bb[1],bb[2],bb[3],bb[4],bb[2]+s['guides']['retention_film_thickness']]);assert not all(q['bonded']for q in bond_areas(floating,{q['name']:q for q in nominal})),'Floating film was accepted'
 bad=copy.deepcopy(s);bad['guides']['retention_film_thickness']=.2;_,thick=build(bad,case,r['variants'][0]['routes'],ex,bottom);thick=next(q for q in thick if q['name']=='BAT-R1-film');residual=distance(thick['shape'],case)-tol['film_edge_error_L2_mm']-tol['guide_installed_datum_error_L2_mm']-math.sqrt(3)*tol['case_maximum_coordinate_error_each_axis_mm'];assert residual<.15,'Oversize tape was accepted'

 outputs={}
 if args.export:
  out=BASE/'mechanical/retention-review';out.mkdir(exist_ok=True)
  from OCP.BRepMesh import BRepMesh_IncrementalMesh
  from OCP.StlAPI import StlAPI_Writer
  for item in nominal+films:
   target=out/(item['name']+'.step');write_step(item['shape'],target);outputs[str(target.relative_to(ROOT))]=sha(str(target.relative_to(ROOT)))
   if item.get('category')!='retention-film':
    BRepMesh_IncrementalMesh(item['shape'],.01,False,.08,True).Perform();writer=StlAPI_Writer();writer.ASCIIMode=False;assert writer.Write(item['shape'],str(target.with_suffix('.stl')));outputs[str(target.with_suffix('.stl').relative_to(ROOT))]=sha(str(target.with_suffix('.stl').relative_to(ROOT)))
 assert all(sha(path)==digest for path,digest in before.items()),'Inputs changed during retention audit'
 report=dict(status='bounded-retainer-study-passed-service-and-process-open'if not failures else'retainer-study-failed',manufacturing_released=False,physical_verification=False,guide_count=16,film_piece_count=17,variants=variants,failures=failures,source_sha256=before,outputs=outputs,wrong_PCB_translation_rejected=True,wrong_power_station_rejected=True,floating_film_rejected=True,thick_film_rejected=True,limits=['Matched bonding faces and measured finished webs required; raw independent print errors are not assumed compatible','Film folds are nominal sharp construction; physical adhesion, cutting and static bends unqualified','Connected insertion/withdrawal and human tool access still open'])
 (WORK/'study.json').write_text(json.dumps(report,indent=2)+'\n');print('FAILURES',json.dumps(failures),flush=True)
 if failures:raise SystemExit(2)
 (BASE/'audit/retention-study.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
