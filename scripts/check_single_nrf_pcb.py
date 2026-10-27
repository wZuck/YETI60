#!/usr/bin/env python3
"""Validate native PCB netlist parity and retained mechanical/electrode geometry.

Use KiCad's Python. Pass a PCB path, or check the canonical routed review board.
This does not replace ERC, DRC, assembly fit or interference simulation.
"""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/ec60-nrf52840'

def require(ok, message):
    if not ok: raise ValueError(message)

def pad_geometry(p):
    q = p.GetPosition()
    shape = p.GetEffectivePolygon(pcb.F_Cu)
    # Compare physical electrode outlines, including exact polygon vertices.
    return (p.GetNumber(), q.x, q.y, p.GetOrientationDegrees(), shape.Format())

def outline(board):
    items=list(board.GetDrawings())
    for fp in board.GetFootprints():items.extend(fp.GraphicalItems())
    result=[]
    for item in items:
        if item.GetLayer()!=pcb.Edge_Cuts or not isinstance(item,pcb.PCB_SHAPE):continue
        start,end=item.GetStart(),item.GetEnd()
        mid=item.GetArcMid() if item.GetShape()==pcb.SHAPE_T_ARC else pcb.VECTOR2I(0,0)
        result.append((int(item.GetShape()),start.x,start.y,end.x,end.y,mid.x,mid.y,item.GetWidth()))
    return sorted(result)

def main():
    path = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else BASE/'EC60-nRF52840.kicad_pcb'
    source = pcb.LoadBoard(str(ROOT/'EC60/PCB/EC60_PCB/EC60.kicad_pcb'))
    target = pcb.LoadBoard(str(path))
    actual = {f.GetReference():f for f in target.GetFootprints()}
    document = ET.parse(BASE/'netlist.xml').getroot()
    rules=json.loads(path.with_suffix('.kicad_pro').read_text())
    require(rules['board']['design_settings']['rules']['min_track_width']==.127,'Project rule contract overwritten')
    require(any(c['name']=='NRF_IO' and c['clearance']==.15 for c in rules['net_settings']['classes']),'nRF IO class missing')
    expected = {(n.get('ref'),n.get('pin')):net.get('name') for net in document.findall('./nets/net') for n in net.findall('node')}
    for comp in document.findall('./components/comp'):
        ref = comp.get('ref')
        require(ref in actual, 'Missing PCB footprint '+ref)
        require(actual[ref].GetValue()==comp.findtext('value'),'Component value mismatch '+ref)
        actual_id=str(actual[ref].GetFPID().GetLibNickname())+':'+str(actual[ref].GetFPID().GetLibItemName())
        require(actual_id==comp.findtext('footprint'),'Footprint ID mismatch '+ref)
        seen = set()
        for pad in actual[ref].Pads():
            key = ref,pad.GetNumber()
            if key in expected:
                require(pad.GetNetname()==expected[key], 'PCB net mismatch '+str(key))
                seen.add(key)
        require({k for k in expected if k[0]==ref} <= seen, 'Missing PCB pin '+ref)
    electrodes=0
    for fp in source.GetFootprints():
        if not str(fp.GetFPID().GetLibItemName()).startswith('ecs_pad_'):continue
        current=actual[fp.GetReference()]
        require(fp.GetPosition()==current.GetPosition(), 'Moved electrode '+fp.GetReference())
        a=sorted(pad_geometry(p) for p in fp.Pads() if p.GetNumber() in ('1','2','3') and p.GetNetname()!='GND' and p.IsOnLayer(pcb.F_Cu))
        b=sorted(pad_geometry(p) for p in current.Pads() if p.GetNumber() in ('1','2','3') and p.GetNetname()!='GND' and p.IsOnLayer(pcb.F_Cu))
        require(a==b, 'Changed electrode copper '+fp.GetReference())
        electrodes+=1
    require(source.GetCopperLayerCount()==target.GetCopperLayerCount()==4,'Layer stack mismatch')
    require(source.GetDesignSettings().GetBoardThickness()==target.GetDesignSettings().GetBoardThickness(),'Board thickness changed')
    require(outline(source)==outline(target),'Changed board outline')
    for ref in ('REF**',):
        a=next(f for f in source.GetFootprints() if f.GetReference()==ref)
        ap=sorted((p.GetPosition().x,p.GetPosition().y,p.GetDrillSize().x,p.GetDrillSize().y) for p in a.Pads())
        bp=sorted((p.GetPosition().x,p.GetPosition().y,p.GetDrillSize().x,p.GetDrillSize().y) for p in actual[ref].Pads())
        require(ap==bp,'Changed mounting holes')
    display_path=str(path.relative_to(ROOT)) if ROOT in path.parents else str(path)
    result={'pcb':display_path,'netlist_parity':'pass','electrode_footprints_preserved':electrodes,'mounting_holes':'pass','copper_layers':4,'interference_simulation':'not_started'}
    (BASE/'pcb-contract-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
