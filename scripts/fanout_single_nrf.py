#!/usr/bin/env python3
"""Place checked through-via escapes beside unfinished nRF IO pads.

Vias stay out of SMT pad copper. Native DRC must still run after zone refill.
"""
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as pcb
from configure_single_nrf_rules import nrf_nets
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840'
path=BASE/'EC60-nRF52840.kicad_pcb'
board=pcb.LoadBoard(str(path));board.BuildConnectivity();conn=board.GetConnectivity()
u=board.FindFootprintByReference('U1');fine=set(nrf_nets())
doc=ET.parse(BASE/'netlist.xml').getroot()
expected={net.get('name'):{(n.get('ref'),n.get('pin')) for n in net.findall('node')} for net in doc.findall('./nets/net')}
layers=(pcb.F_Cu,pcb.In1_Cu,pcb.In2_Cu,pcb.B_Cu)
items=[]
for fp in board.GetFootprints():
    for pad in fp.Pads():
        for layer in layers:
            if pad.IsOnLayer(layer):items.append((pad,pad.GetEffectiveShape(layer),layer))
for track in board.GetTracks():
    for layer in layers:
        if track.IsOnLayer(layer):items.append((track,track.GetEffectiveShape(layer),layer))
keepouts=[z for fp in board.GetFootprints() for z in fp.Zones()]
steps=sorted(((x*.2,y*.2) for x in range(-14,15) for y in range(-14,15) if .55<=math.hypot(x*.2,y*.2)<=2.85),key=lambda p:math.hypot(*p))

def component(pad):
    seen=set();todo=[pad];result=[]
    while todo:
        item=todo.pop();key=item.m_Uuid.AsString()
        if key in seen:continue
        seen.add(key);result.append(item)
        for other in conn.GetConnectedItems(item):
            if other.GetNetCode()==pad.GetNetCode():todo.append(other)
    return result

def legal(pad,point):
    via=pcb.SHAPE_CIRCLE(point,pcb.FromMM(.25))
    line=pcb.SHAPE_SEGMENT(pad.GetPosition(),point,pcb.FromMM(.127))
    for item,shape,layer in items:
        same=item.GetNetCode()==pad.GetNetCode()
        clearance=.15 if item.GetNetname() in fine else .2
        if isinstance(item,pcb.PAD) and item.GetAttribute()==pcb.PAD_ATTRIB_NPTH:clearance=.85
        if not same and pcb.SHAPE.Collide(via,shape,pcb.FromMM(clearance)):return False
        if isinstance(item,pcb.PAD) and item.GetAttribute()==pcb.PAD_ATTRIB_SMD and pcb.SHAPE.Collide(via,shape,pcb.FromMM(.05)):return False
        if layer==pcb.B_Cu and not same and pcb.SHAPE.Collide(line,shape,pcb.FromMM(clearance)):return False
    for zone in keepouts:
        if zone.GetDoNotAllowVias() and zone.Outline().Collide(via,0):return False
        if zone.GetDoNotAllowTracks() and zone.GetLayerSet().Contains(pcb.B_Cu) and zone.Outline().Collide(line,0):return False
    return True

for pad in u.Pads():
    net=pad.GetNetname()
    if net not in fine or net.startswith('unconnected-'):continue
    connected=component(pad)
    pads={(pcb.Cast_to_PAD(a).GetParentFootprint().GetReference(),pcb.Cast_to_PAD(a).GetNumber()) for a in connected if a.GetClass()=='PAD'}
    if expected[net]<=pads or any(a.GetClass()=='PCB_VIA' for a in connected):continue
    found=None
    for dx,dy in steps:
        q=pcb.VECTOR2I(pad.GetPosition().x+pcb.FromMM(dx),pad.GetPosition().y+pcb.FromMM(dy))
        if legal(pad,q):found=q;break
    if found is None:
        print('NO ESCAPE',pad.GetNumber(),net,flush=True);continue
    via=pcb.PCB_VIA(board);via.SetPosition(found);via.SetWidth(pcb.FromMM(.5));via.SetDrill(pcb.FromMM(.3))
    via.SetViaType(pcb.VIATYPE_THROUGH);via.SetLayerPair(pcb.F_Cu,pcb.B_Cu);via.SetNet(pad.GetNet());board.Add(via)
    track=pcb.PCB_TRACK(board);track.SetStart(pad.GetPosition());track.SetEnd(found);track.SetWidth(pcb.FromMM(.127));track.SetLayer(pcb.B_Cu);track.SetNet(pad.GetNet());board.Add(track)
    for layer in layers:items.append((via,via.GetEffectiveShape(layer),layer))
    items.append((track,track.GetEffectiveShape(),pcb.B_Cu))
    print('ESCAPE',pad.GetNumber(),net,[pcb.ToMM(found.x),pcb.ToMM(found.y)],flush=True)
    board.BuildConnectivity();conn=board.GetConnectivity()
pcb.SaveBoard(str(path),board)
