#!/usr/bin/env python3
"""Remove only copper components having no pad or connected pour terminal.

Keep all one-ended, pad-connected unfinished routes and all GND stitching.
"""
import json,tempfile
from pathlib import Path
import pcbnew as pcb
from kicad_sexpr import loads,dumps,child
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840';path=BASE/'EC60-nRF52840.kicad_pcb'
board=pcb.LoadBoard(str(path));board.BuildConnectivity();conn=board.GetConnectivity()
def key(v):return v.m_Uuid.AsString()
items={key(v):v for v in list(board.GetTracks())+[p for f in board.GetFootprints() for p in f.Pads()]+list(board.Zones())}
seen=set();remove=set();groups=[]
for start in board.GetTracks():
    if key(start) in seen or start.GetNetname()=='GND':continue
    todo=[start];group=set();terminal=False
    while todo:
        item=todo.pop();k=key(item)
        if k in group:continue
        group.add(k);seen.add(k)
        if item.GetClass() in ('PAD','ZONE'):terminal=True
        for other in conn.GetConnectedItems(item):
            if other.GetNetCode()==start.GetNetCode() and key(other) in items:todo.append(items[key(other)])
    if not terminal:remove.update(group);groups.append({'net':start.GetNetname(),'items':len(group)})
x=loads(path.read_text());x[:]=[v for v in x if not(isinstance(v,list) and v[0] in ('segment','arc','via') and str(child(v,'uuid')[1]) in remove)]
path.write_text(dumps(x)+'\n')
(BASE/'orphan-copper-cleanup.json').write_text(json.dumps({'removed_items':len(remove),'groups':groups,'criterion':'no pad or copper-zone terminal; GND excluded'},indent=2)+'\n')
print('Removed',len(remove),'orphan copper primitives in',len(groups),'components')
