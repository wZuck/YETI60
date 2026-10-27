#!/usr/bin/env python3
"""Repair small clearance violations while keeping the existing signal routes.

Use native copper/hole checks; only short IO escapes may neck to the existing
0.127mm class minimum. Otherwise try <=0.05mm translations of the same segment.
Pin-to-pin connectivity must be compared with the checkpoint afterward.
"""
from pathlib import Path
import json,math
import pcbnew as pcb
from configure_single_nrf_rules import nrf_nets
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840';path=BASE/'EC60-nRF52840.kicad_pcb'
board=pcb.LoadBoard(str(path));fine=set(nrf_nets());items=list(board.GetTracks())+[p for f in board.GetFootprints() for p in f.Pads()]
by_id={i.m_Uuid.AsString():i for i in items};report=json.loads((BASE/'DRC-routed.json').read_text());changes=[];selected={}
for v in report['violations']:
 if v['severity']!='error':continue
 for value in v['items']:
  item=by_id.get(value['uuid'])
  if item and item.GetClass()=='PCB_TRACK':selected[value['uuid']]=item

def legal(track):
 layer=track.GetLayer();shape=track.GetEffectiveShape();net=track.GetNetname();clear=.15 if net in fine else .2
 for other in items:
  if other is track or other.GetNetname()==net or not other.IsOnLayer(layer):continue
  gap=max(clear,.15 if other.GetNetname() in fine else .2)
  if other.GetClass()=='PAD' and other.GetAttribute()==pcb.PAD_ATTRIB_NPTH:gap=.85
  if other.GetClass()=='PCB_VIA':gap=max(gap,.25-(pcb.ToMM(other.GetWidth(layer))-pcb.ToMM(other.GetDrillValue()))/2)
  if shape.Collide(other.GetEffectiveShape(layer),pcb.FromMM(gap)):return False
 return True
for key,track in selected.items():
 a,b=track.GetStart(),track.GetEnd();width=track.GetWidth();net=track.GetNetname();done=False
 if net in fine and width>pcb.FromMM(.127) and track.GetLength()<pcb.FromMM(3):
  track.SetWidth(pcb.FromMM(.127))
  if legal(track):changes.append({'net':net,'action':'local IO neck','width_mm':.127});done=True
  else:track.SetWidth(width)
 if not done:
  for distance in (.005,.01,.02,.025,.03,.04,.05):
   for dx,dy in ((0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)):
    d=pcb.VECTOR2I(pcb.FromMM(dx*distance),pcb.FromMM(dy*distance));track.SetStart(a+d);track.SetEnd(b+d)
    if legal(track):changes.append({'net':net,'action':'segment offset','dx_mm':dx*distance,'dy_mm':dy*distance});done=True;break
   if done:break
  if not done:track.SetStart(a);track.SetEnd(b)
 print('FIXED' if done else 'UNRESOLVED',net,key,flush=True)
board.BuildConnectivity();pcb.ZONE_FILLER(board).Fill(board.Zones());pcb.SaveBoard(str(path),board,True)
(BASE/'small-clearance-repairs.json').write_text(json.dumps({'changes':changes,'rules_weakened':False,'requires_DRC_and_connectivity_comparison':True},indent=2)+'\n')
