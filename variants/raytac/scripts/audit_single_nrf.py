#!/usr/bin/env python3
"""Fail-closed PCB audit: strict native DRC/parity and physical pin connectivity.

Run with KiCad Python. Global ignore severities are enabled in a scratch copy;
this audit never weakens or rewrites the design's actual rules.
"""
from collections import Counter
import hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as pcb
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840'
NAME='EC60-nRF52840';CLI=os.environ.get('KICAD_CLI','/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
project=BASE/(NAME+'.kicad_pro');project_hash=hashlib.sha256(project.read_bytes()).hexdigest()
config=json.loads(project.read_text());enabled=[]
for key,level in config['board']['design_settings']['rule_severities'].items():
    if level=='ignore':
        config['board']['design_settings']['rule_severities'][key]='error' if key=='footprint_type_mismatch' else 'warning';enabled.append(key)
with tempfile.TemporaryDirectory(prefix='yaeckb-strict-drc-') as folder:
    scratch=Path(folder)
    for p in BASE.glob('*.kicad_sch'):shutil.copyfile(p,scratch/p.name)
    shutil.copyfile(BASE/(NAME+'.kicad_pcb'),scratch/(NAME+'.kicad_pcb'))
    for name in ('sym-lib-table','fp-lib-table','YAECKB.kicad_sym'):shutil.copyfile(BASE/name,scratch/name)
    (scratch/'YAECKB.pretty').symlink_to((BASE/'YAECKB.pretty').resolve(),target_is_directory=True)
    (scratch/(NAME+'.kicad_pro')).write_text(json.dumps(config,indent=2)+'\n')
    result=subprocess.run([CLI,'pcb','drc','--all-track-errors','--schematic-parity','--severity-all','--refill-zones','--format','json','-o',str(scratch/'drc.json'),str(scratch/(NAME+'.kicad_pcb'))],capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stderr[-3000:])
    report=json.loads((scratch/'drc.json').read_text());(BASE/'DRC-strict.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if hashlib.sha256(project.read_bytes()).hexdigest()!=project_hash:raise ValueError('Audit changed project rules')
board=pcb.LoadBoard(str(BASE/(NAME+'.kicad_pcb')));board.BuildConnectivity();conn=board.GetConnectivity()
def uid(v):return v.m_Uuid.AsString()
items={uid(v):v for v in list(board.GetTracks())+[p for f in board.GetFootprints() for p in f.Pads()]+list(board.Zones())}
pads={(f.GetReference(),p.GetNumber()):p for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()}
cache={};next_group=0
for pad in pads.values():
    if uid(pad) in cache:continue
    todo=[pad];group=set()
    while todo:
        item=todo.pop();key=uid(item)
        if key in group:continue
        group.add(key)
        for other in conn.GetConnectedItems(item):
            if other.GetNetCode()==pad.GetNetCode() and uid(other) in items:todo.append(items[uid(other)])
    for key in group:cache[key]=next_group
    next_group+=1
xml=ET.parse(BASE/'netlist.xml').getroot()
critical=[];split_nets=[]
for net in xml.findall('./nets/net'):
    nodes=[(n.get('ref'),n.get('pin')) for n in net.findall('node')]
    if len(nodes)<2 or net.get('name')=='GND':continue
    reference=nodes[0]
    groups={}
    for node in nodes:
        pad=pads.get(node)
        groups.setdefault(cache.get(uid(pad)) if pad is not None else 'missing',[]).append('.'.join(node))
    if len(groups)>1:split_nets.append({'net':net.get('name'),'physical_components':list(groups.values())})
    for node in nodes[1:]:
        a,b=pads.get(reference),pads.get(node)
        critical.append({'net':net.get('name'),'from':'.'.join(reference),'to':'.'.join(node),
                         'physically_connected':a is not None and b is not None and cache[uid(a)]==cache[uid(b)]})
counts=Counter(v['type'] for v in report['violations'] if v['severity']=='error')
all_counts=Counter(v['type'] for v in report['violations'])
parity_errors=[v for v in report.get('schematic_parity',[]) if v.get('severity')=='error']
geometry_only=set(json.loads((BASE/'metadata-audit.json').read_text())['non_purchased_geometry_references'])|{'REF**'}
fp_refs={fp.m_Uuid.AsString():fp.GetReference() for fp in board.GetFootprints()}
missing_courtyards=[fp_refs.get(i['uuid'],'unknown') for v in report['violations'] if v['type']=='missing_courtyard' for i in v['items']]
manifest=json.loads((BASE/'frozen-footprints.json').read_text())
source_files=[BASE/(NAME+'.kicad_pcb'),project,BASE/'netlist.xml',BASE/'frozen-footprints.json',BASE/'YAECKB.kicad_sym']+list(BASE.glob('*.kicad_sch'))+[BASE/'YAECKB.pretty'/(v['id'].split(':')[-1]+'.kicad_mod') for v in manifest.values()]
summary={'status':('cad-checks-passed' if not counts and not parity_errors and not report['unconnected_items'] and all(x['physically_connected'] for x in critical) and not any(ref not in geometry_only for ref in missing_courtyards) and not any(v>=199 for v in all_counts.values()) else 'requires-routing-and-review'),'production_approved':False,'mcu_count':1,
    'source_sha256':{str(path.relative_to(BASE)):hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
    'enabled_previously_ignored_checks':enabled,'drc_errors_by_type':dict(counts),'schematic_parity_errors':len(parity_errors),
    'schematic_parity_by_type':dict(Counter(v['type'] for v in report.get('schematic_parity',[]))),
    'expected_noncomponent_courtyard_warnings':[ref for ref in missing_courtyards if ref in geometry_only],
    'unexpected_component_courtyard_warnings':[ref for ref in missing_courtyards if ref not in geometry_only],
    'unconnected_items':len(report['unconnected_items']),'warnings_by_type':dict(Counter(v['type'] for v in report['violations'] if v['severity']=='warning')),
    'potentially_truncated_categories':[k for k,v in all_counts.items() if v>=199],
    'physical_pin_pairs':critical,'failed_pin_pairs':sum(not x['physically_connected'] for x in critical),
    'split_nets':split_nets,
    'critical_paths':[{ 'from':'.'.join(a),'to':'.'.join(b),'connected':cache[uid(pads[a])]==cache[uid(pads[b])]} for a,b in [
        (('U6','1'),('U1','28')),(('U6','1'),('U1','30')),(('U5','8'),('U5','17')),(('U5','17'),('U1','1')),
        (('U6','4'),('L1','1')),(('U6','2'),('L1','2')),(('U1','20'),('U3','6')),
        (('J1','2'),('R30','1')),(('R30','2'),('U1','34')),(('J1','3'),('R31','1')),(('R31','2'),('U1','35')),
        (('U1','51'),('J3','2')),(('U1','53'),('J3','4'))]],
    'interference_simulation':'not_started_user_ordered_after_PCB_completion',
    'limits':['Ordinary JLC through-via process checked separately; no module via-in-pad or special fill/capping','DRC does not certify regulator stability, capacitor DC bias or thermal performance','C5 native electrical/mounting checks do not verify mating plug/harness serviceability or physical assembly','Normal/calibrator target builds verified separately; on-device USB/BLE and physical EC calibration untested']}
summary['failed_critical_paths']=sum(not x['connected'] for x in summary['critical_paths'])
if summary['failed_critical_paths']:summary['status']='requires-routing-and-review'
(BASE/'audit-current.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('physical_pin_pairs','source_sha256')},ensure_ascii=False,indent=2))
raise SystemExit(1 if summary['failed_critical_paths'] or counts or parity_errors or summary['unconnected_items'] or summary['failed_pin_pairs'] or summary['unexpected_component_courtyard_warnings'] or summary['potentially_truncated_categories'] else 0)
