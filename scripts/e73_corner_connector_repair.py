#!/usr/bin/env python3
"""Apply the bounded, source-bound J5 rotation after the frozen route replay.

The selected specification states the final pose. Its pre-repair pose exists
only to replay the already-reviewed route patch before this local change.
"""
import hashlib,json
from pathlib import Path
from kicad_sexpr import child,children,loads,dumps

def validate_patch(patch):
 assert patch['part']=='J5' and patch['expected_pose']==[335.5,117.5,0] and patch['final_pose']==[335.5,117.5,180]
 assert set(patch['allowed_nets'])=={'GND','USB_FEED','ROW_DRV4'}
 identifiers=set();via_count=0
 for text in patch['added']:
  q=loads(text);assert q[0]in['segment','via'];assert child(q,'net')[1]in patch['allowed_nets'];uid=str(child(q,'uuid')[1]);assert uid not in identifiers;identifiers.add(uid)
  points=[child(q,k)[1:3]for k in (['at']if q[0]=='via'else['start','end'])];x,y,X,Y=patch['repair_bounds_PCB_mm']
  assert all(x<=float(a)<=X and y<=float(b)<=Y for a,b in points),'Repair escaped its reviewed region'
  if q[0]=='via':
   via_count+=1;assert float(child(q,'size')[1])==.5 and float(child(q,'drill')[1])==.3
   assert child(q,'layers')[1:]==['F.Cu','B.Cu']
   assert all(child(child(q,'tenting'),side)[1]=='yes'for side in ['front','back'])
  else:
   assert child(q,'layer')[1]in['B.Cu','In1.Cu','In2.Cu'];assert float(child(q,'width')[1])>=(.127 if child(q,'net')[1]=='ROW_DRV4'else .25)
 assert via_count==patch['maximum_new_vias']==3
 assert len(patch['retired'])==12 and len({r['uuid']for r in patch['retired']})==12
 assert not identifiers.intersection(r['uuid']for r in patch['retired'])
 return patch

def apply(path,patch):
 import pcbnew as p
 validate_patch(patch);assert hashlib.sha256(path.read_bytes()).hexdigest()==patch['source_PCB_sha256'],'J5 repair targets a different routed baseline'
 tree=loads(path.read_text());nodes={str(child(q,'uuid')[1]):q for kind in ['segment','arc','via']for q in children(tree,kind)}
 for record in patch['retired']:
  q=nodes[record['uuid']];assert child(q,'net')[1]==record['net']in patch['allowed_nets'];assert hashlib.sha256(dumps(q).encode()).hexdigest()==record['sha256'];tree.remove(q)
 for text in patch['added']:
  q=loads(text);assert str(child(q,'uuid')[1])not in nodes;tree.append(q)
 path.write_text(dumps(tree)+'\n');b=p.LoadBoard(str(path));f=next(f for f in b.GetFootprints()if f.GetReference()==patch['part']);assert list(p.ToMM(f.GetPosition()))==patch['expected_pose'][:2]and f.GetOrientationDegrees()==patch['expected_pose'][2]and f.GetLayer()==p.B_Cu
 assert {q.GetNumber():q.GetNetname()for q in f.Pads()}=={'1':'USB_FEED','2':'GND','MP':''}
 f.SetOrientationDegrees(patch['final_pose'][2]);p.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();p.SaveBoard(str(path),b)
 return patch['retired']
