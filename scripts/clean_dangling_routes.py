#!/usr/bin/env python3
"""Remove only native-DRC identified dangling copper; rerun DRC each round."""
import json,subprocess,tempfile
from pathlib import Path
import pcbnew as pcb
from kicad_sexpr import loads,dumps,child
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840';PATH=BASE/'EC60-nRF52840.kicad_pcb';CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
previous=BASE/'dangling-cleanup.json'
history=json.loads(previous.read_text()) if previous.exists() else {}
changes=history.get('removed',[])
last_snapshot=None;last_removed=[];blocked=[]
for iteration in range(201):
    with tempfile.TemporaryDirectory() as folder:
        p=Path(folder)/'drc.json';subprocess.run([CLI,'pcb','drc','--severity-all','--refill-zones','--format','json','-o',str(p),str(PATH)],check=True,capture_output=True)
        report=json.loads(p.read_text())
    if report['unconnected_items']:
        if last_snapshot is None:raise ValueError('Complete all routing before dangling cleanup')
        PATH.write_bytes(last_snapshot);changes=changes[:-len(last_removed)];blocked=last_removed
        print('RESTORED: removal opened a connection; trim the intermediate junction manually',flush=True)
        break
    if iteration==200:break
    ids={i['uuid'] for v in report['violations'] if v['type'] in ('track_dangling','via_dangling') for i in v['items']}
    doc=loads(PATH.read_text());removed=[v for v in doc if isinstance(v,list) and v[0] in ('segment','arc','via') and str(child(v,'uuid')[1]) in ids]
    if not removed:break
    last_snapshot=PATH.read_bytes();last_removed=[str(child(v,'uuid')[1]) for v in removed]
    print('PRUNE',iteration,len(removed),flush=True);changes.extend(str(child(v,'uuid')[1]) for v in removed)
    doc[:]=[v for v in doc if v not in removed];PATH.write_text(dumps(doc)+'\n')
B=pcb.LoadBoard(str(PATH));pcb.ZONE_FILLER(B).Fill(B.Zones());pcb.SaveBoard(str(PATH),B,True)
(BASE/'dangling-cleanup.json').write_text(json.dumps({**history,'removed':changes,'blocked_candidates':blocked,'requires_connectivity_regression':True},indent=2)+'\n')
