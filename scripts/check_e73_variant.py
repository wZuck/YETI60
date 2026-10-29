#!/usr/bin/env python3
"""Check E73-specific vendor lands, pin identities and target configuration.

Native DRC, connectivity, firmware linkage and assembly are separate checks.
"""
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT/'hardware/ec60-nrf52840'


def verify_pin_contract(profile, component, pinmap):
    expected = {str(p['number']): p['proposed_net'] for p in profile['pins'] if p['proposed_net']}
    assert component['value'] == pinmap['module'] == 'E73-2G4M08S1C', 'Wrong module variant'
    assert component['pins'] == pinmap['module_pin_nets'] == expected, 'E73 module pin assignment mismatch'
    signals = [p['soc_function'] for p in profile['pins'] if p['proposed_net'] and p['soc_function'].startswith('P')]
    assert len(signals) == len(set(signals)) == 22  # 21 GPIO functions and P0.18 reset.
    assert [p['number'] for p in profile['pins'] if p['proposed_net'] and p['location']=='bottom'] == [12,24,28,32,34]
    assert expected['4']=='ADC' and expected['15']=='BAT_ADC'
    assert all(expected[str(n)] == '+3.3V' for n in [19,23])
    assert expected['27']=='USB_5V' and '25' not in expected
    return expected


def verify_lands(module, profile, pcb):
    pads = {int(p.GetNumber()): p for p in module.Pads()}
    assert set(pads) == set(range(1,44)), 'E73 must retain all 43 vendor lands'
    assert module.IsFlipped(), 'E73 belongs on component side B.Cu'
    angle = math.radians(module.GetOrientationDegrees())
    ox,oy = [pcb.ToMM(v) for v in [module.GetPosition().x,module.GetPosition().y]]
    for reference in profile['pins']:
        pad = pads[reference['number']]
        x,y = reference['vendor_land_center_mm']
        expected = [ox+math.cos(angle)*x-math.sin(angle)*y,oy-math.sin(angle)*x-math.cos(angle)*y]
        actual = [pcb.ToMM(pad.GetPosition().x),pcb.ToMM(pad.GetPosition().y)]
        assert math.dist(actual,expected)<2e-6, 'Changed E73 vendor land position'
        assert [pcb.ToMM(pad.GetSize().x),pcb.ToMM(pad.GetSize().y)] == reference['vendor_land_size_mm'], 'Changed E73 vendor land size'
        target_angle = (module.GetOrientationDegrees()-reference['vendor_land_angle_deg'])%360
        assert abs((pad.GetOrientationDegrees()-target_angle+180)%360-180)<1e-6, 'Changed E73 vendor land rotation'
        net = reference['proposed_net']
        assert pad.GetNetname()==net if net else pad.GetNetname().startswith('unconnected-'), 'Incorrect E73 pad net'


def main():
    import pcbnew as pcb
    profile_path=ROOT/'hardware/module-options/e73.json'
    profile=json.loads(profile_path.read_text())
    component=json.loads((HW/'components.json').read_text())['U1']
    pinmap=json.loads((HW/'pinmap.json').read_text())
    verify_pin_contract(profile,component,pinmap)
    xml=ET.parse(HW/'netlist.xml').getroot()
    symbol=next(p for p in xml.findall('./libparts/libpart') if p.get('part')=='E73-2G4M08S1C')
    names={p.get('num'):p.get('name') for p in symbol.findall('./pins/pin')}
    assert names == {str(p['number']):p['soc_function'] for p in profile['pins']}, 'Symbol differs from vendor pin identities'
    board=pcb.LoadBoard(str(HW/'EC60-nRF52840.kicad_pcb'))
    module=next(f for f in board.GetFootprints() if f.GetReference()=='U1')
    verify_lands(module,profile,pcb)
    dts=ROOT/'firmware/target/boards/yeti/yeti60/yeti60.dts'
    conf=ROOT/'firmware/target/boards/yeti/yeti60/yeti60_defconfig'
    assert 'NRF5X_REG_MODE_LDO' in dts.read_text()
    assert all(v in conf.read_text() for v in ['CONFIG_NFCT_PINS_AS_GPIOS=y','CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC=y'])
    files=[profile_path,HW/'components.json',HW/'pinmap.json',HW/'netlist.xml',HW/'EC60-nRF52840.kicad_pcb',dts,conf,Path(__file__)]
    report={'status':'e73-module-contract-passed','module':'E73-2G4M08S1C','vendor_lands':43,'connected_bottom_lands':[12,24,28,32,34],
            'REG1_mode':'LDO','NFC_pins':'GPIO','scan_ADC_AIN':4,'battery_ADC_AIN':3,'production_approved':False,
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
            'scope':'Vendor pin and pad geometry plus source configuration; DRC, linked firmware and assembly checked separately'}
    (ROOT/'docs/audit/yeti60-e73-variant.json').write_text(json.dumps(report,indent=2)+'\n')
    print('E73: 43 vendor lands, all pin identities, current nets, RC clock and LDO configuration agree')


if __name__=='__main__':
    main()
