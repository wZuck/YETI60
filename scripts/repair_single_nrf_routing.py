#!/usr/bin/env python3
"""Rip up only new routes implicated by KiCad DRC; retain original EC copper."""
import json
from pathlib import Path
import shutil
import sys
from kicad_sexpr import loads,dumps,child
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840'
NAME='EC60-nRF52840'
if len(sys.argv)>1:
    original=loads(Path(sys.argv[1]).read_text())
    protected={str(child(v,'uuid')[1]) for v in original if isinstance(v,list) and v[0] in ('segment','arc','via')}
else:
    protected=set(json.loads((BASE/'retained-copper.json').read_text())['uuids'])
current=loads((BASE/(NAME+'.kicad_pcb')).read_text())
report=json.loads((BASE/'DRC-routed.json').read_text())
bad={i['uuid'] for v in report['violations'] if v['severity']=='error' for i in v['items'] if i['uuid'] not in protected}
removed=[v for v in current if isinstance(v,list) and v[0] in ('segment','arc','via') and str(child(v,'uuid')[1]) in bad]
current[:]=[v for v in current if not any(v is r for r in removed)]
(BASE/(NAME+'.unrouted.kicad_pcb')).write_text(dumps(current)+'\n')
shutil.copyfile(BASE/(NAME+'.kicad_pro'),BASE/(NAME+'.unrouted.kicad_pro'))
print('Removed',len(removed),'new tracks/vias; original EC routes retained')
