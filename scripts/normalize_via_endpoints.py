#!/usr/bin/env python3
"""Normalize existing via contacts; move no pads/vias and require full DRC afterward."""
from pathlib import Path
import json,math,tempfile
import pcbnew as pcb
from kicad_sexpr import loads,dumps,child
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840';path=BASE/'EC60-nRF52840.kicad_pcb'
board=pcb.LoadBoard(str(path));items={v.m_Uuid.AsString():v for v in board.GetTracks()}
report=json.loads((BASE/'DRC-strict.json').read_text());changes=[];remove=set()
for violation in report['violations']:
 if violation['type']!='track_not_centered_on_via':continue
 pair=[items.get(i['uuid']) for i in violation['items']]
 track=next((i for i in pair if i is not None and i.GetClass()=='PCB_TRACK'),None)
 via=next((i for i in pair if i is not None and i.GetClass()=='PCB_VIA'),None)
 if track is None or via is None or track.GetNetCode()!=via.GetNetCode():continue
 point=via.GetPosition()
 for getter,setter in ((track.GetStart,track.SetStart),(track.GetEnd,track.SetEnd)):
  old=getter();d=math.hypot(old.x-point.x,old.y-point.y)
  radius=via.GetWidth(track.GetLayer())/2
  contained=d+track.GetWidth()/2<=radius-pcb.FromMM(.005)
  if d>0 and (d<=pcb.FromMM(.001) or contained):setter(point);changes.append(d/1e6)
 if track.GetStart()==track.GetEnd():remove.add(track.m_Uuid.AsString())
with tempfile.TemporaryDirectory(prefix='yaeckb-endpoint-snap-') as folder:
 tmp=Path(folder)/'board.kicad_pcb';pcb.SaveBoard(str(tmp),board,True);doc=loads(tmp.read_text())
 doc[:]=[v for v in doc if not(isinstance(v,list) and v[0]=='segment' and str(child(v,'uuid')[1]) in remove)];tmp.write_text(dumps(doc)+'\n');board=pcb.LoadBoard(str(tmp))
board.BuildConnectivity();pcb.ZONE_FILLER(board).Fill(board.Zones());pcb.SaveBoard(str(path),board,True)
(BASE/'via-contact-normalization.json').write_text(json.dumps({'snapped_endpoints':len(changes),'maximum_displacement_mm':max(changes,default=0),'removed_zero_length_tracks':len(remove),'pads_and_vias_moved':False,'larger_corrections':'endpoint lies inside same-net via copper; full route must be rechecked for clearance and connectivity'},indent=2)+'\n')
print('Snapped',len(changes),'endpoints; max displacement',max(changes,default=0),'mm')
