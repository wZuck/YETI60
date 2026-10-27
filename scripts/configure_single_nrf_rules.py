#!/usr/bin/env python3
"""Set explicit 0.127mm nRF IO breakout rules; bulk wiring stays at 0.2mm."""
import copy,json
from pathlib import Path
import xml.etree.ElementTree as ET
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840'

def nrf_nets():
    doc=ET.parse(BASE/'netlist.xml').getroot()
    return sorted(n.get('name') for n in doc.findall('./nets/net') if n.get('name') not in ('GND','+3.3V','USB_5V') and any(p.get('ref')=='U1' for p in n.findall('node')))

def configure(path):
    config=json.loads(path.read_text())
    config['board']['design_settings']['rules']['min_track_width']=.127
    config['board']['design_settings']['rules']['min_via_diameter']=.5
    config['board']['design_settings']['rules']['min_through_hole_diameter']=.3
    classes=config['net_settings']['classes']
    classes[:]=[c for c in classes if c['name']!='NRF_IO']
    fine=copy.deepcopy(classes[0]);fine.update(name='NRF_IO',clearance=.15,track_width=.127,via_diameter=.5,via_drill=.3,priority=0)
    classes.append(fine)
    config['net_settings']['netclass_patterns']=[{'netclass':'NRF_IO','pattern':n} for n in nrf_nets()]
    path.write_text(json.dumps(config,indent=2)+'\n')

if __name__=='__main__':
    for name in ('EC60-nRF52840.kicad_pro','EC60-nRF52840.unrouted.kicad_pro'):
        path=BASE/name
        if path.exists():configure(path)
