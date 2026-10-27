#!/usr/bin/env python3
"""Verify PCB repairs preserve previously connected schematic pin pairs."""
import pcbnew as p,json,subprocess,tempfile,argparse
from pathlib import Path
from itertools import combinations
import xml.etree.ElementTree as E
parser=argparse.ArgumentParser();parser.add_argument('--baseline',required=True);args=parser.parse_args()
base=Path(__file__).resolve().parents[1];hw=base/'hardware/ec60-nrf52840'
revision=subprocess.check_output(['git','rev-parse','--verify',args.baseline+'^{commit}'],cwd=base,text=True).strip()
folder=tempfile.TemporaryDirectory(prefix='yaeckb-connectivity-baseline-');old=Path(folder.name)/'baseline.kicad_pcb'
old.write_bytes(subprocess.check_output(['git','show',revision+':hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'],cwd=base))
def groups(path):
 b=p.LoadBoard(str(path));b.BuildConnectivity();c=b.GetConnectivity();items={x.m_Uuid.AsString():x for x in list(b.GetTracks())+[v for f in b.GetFootprints() for v in f.Pads()]};labels={};out={};count=0
 for f in b.GetFootprints():
  for pad in f.Pads():
   if pad.GetNetname()=='GND':continue
   k=pad.m_Uuid.AsString()
   if k not in labels:
    todo=[pad];seen=set()
    while todo:
     a=todo.pop();ak=a.m_Uuid.AsString()
     if ak in seen:continue
     seen.add(ak);labels[ak]=count
     todo.extend(items[v.m_Uuid.AsString()] for v in c.GetConnectedItems(a) if v.GetNetCode()==pad.GetNetCode() and v.m_Uuid.AsString() in items)
    count+=1
   out[(f.GetReference(),pad.GetNumber())]=labels[k]
 return out
before=groups(old);after=groups(hw/'EC60-nRF52840.kicad_pcb');regress=[];improve=[]
for net in E.parse(hw/'netlist.xml').findall('./nets/net'):
 if net.get('name')=='GND':continue
 nodes=[(v.get('ref'),v.get('pin')) for v in net.findall('node')]
 for a,b in combinations(nodes,2):
  was=before[a]==before[b];now=after[a]==after[b]
  item={'net':net.get('name'),'a':a,'b':b}
  if was and not now:regress.append(item)
  if now and not was:improve.append(item)
result={'reference_commit':revision,'regressed_pairs':regress,'improved_pairs':improve,'scope':'all non-GND schematic pad pairs; GND checked by native DRC and explicit supply checks'}
(hw/'connectivity-changes.json').write_text(json.dumps(result,indent=2)+'\n')
from collections import Counter
print('Regressions',Counter(v['net'] for v in regress));print('Improvements',Counter(v['net'] for v in improve))

folder.cleanup()
raise SystemExit(1 if regress else 0)
