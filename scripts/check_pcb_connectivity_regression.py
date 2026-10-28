#!/usr/bin/env python3
"""Verify PCB repairs preserve previously connected schematic pin pairs."""
import pcbnew as p,json,subprocess,tempfile,argparse,hashlib
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
baseline_xml=E.fromstring(subprocess.check_output(['git','show',revision+':hardware/ec60-nrf52840/netlist.xml'],cwd=base))
current_xml=E.parse(hw/'netlist.xml').getroot()
pair_contract={}
for document in [baseline_xml,current_xml]:
 for net in document.findall('./nets/net'):
  if net.get('name')=='GND':continue
  nodes=[(v.get('ref'),v.get('pin')) for v in net.findall('node')]
  for a,b in combinations(sorted(nodes),2):pair_contract[(a,b)]=net.get('name')
added=[]
for (a,b),name in pair_contract.items():
 now=a in after and b in after and after[a]==after[b]
 item={'net':name,'a':a,'b':b}
 if a not in before or b not in before:
  added.append({**item,'connected':now});continue
 was=before[a]==before[b]
 if was and not now:regress.append(item)
 if now and not was:improve.append(item)
result={'reference_commit':revision,'regressed_pairs':regress,'improved_pairs':improve,'new_component_pairs':added,'scope':'Union of baseline and current non-GND schematic pad pairs; missing new pads do not count as old regressions. Current native audit verifies every new pair and GND.','source_sha256':{str(q.relative_to(base)):hashlib.sha256(q.read_bytes()).hexdigest() for q in [hw/'EC60-nRF52840.kicad_pcb',hw/'netlist.xml',Path(__file__).resolve()]}}
(hw/'connectivity-changes.json').write_text(json.dumps(result,indent=2)+'\n')
from collections import Counter
print('Regressions',Counter(v['net'] for v in regress));print('Improvements',Counter(v['net'] for v in improve))

folder.cleanup()
raise SystemExit(1 if regress else 0)
