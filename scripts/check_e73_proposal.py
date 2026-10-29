#!/usr/bin/env python3
"""Validate the E73 pin proposal and reference footprint, not a routed design."""
import hashlib
import json
from pathlib import Path
import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'hardware/module-options/e73.json'
    data=json.loads(path.read_text())
    pins={p['number']:p for p in data['pins']}
    assert set(pins)==set(range(1,44)) and data['controller_count_per_board']==1
    assert sum(p['location']=='outer' for p in pins.values())==28
    connected=[p for p in pins.values() if p['proposed_net']]
    assert len(connected)==32
    bottom=sorted(p['number'] for p in connected if p['location']=='bottom')
    assert bottom==[12,24,28,32,34]
    roles={p['proposed_net']:p for p in connected if p['proposed_net'] not in ['GND','+3.3V']}
    required=['ROW_DRV'+str(i) for i in range(5)]+['AMUX_SEL_'+str(i) for i in range(3)]+[
        'APLEX_EN_PIN_0','APLEX_EN_PIN_1','APLEX_OUT_PIN_0','ADC','BAT_ADC','BAT_MEAS_EN','AFE_EN',
        'CHG_EN1','CHG_EN2','CHG_CE_N','CHG_N','PGOOD_N','STATUS_LED']
    gpio=[roles[r]['soc_function'] for r in required]
    assert len(gpio)==len(set(gpio))==21 and all(n.startswith('P') for n in gpio)
    assert roles['ADC']['soc_function']=='P0.28' and roles['BAT_ADC']['soc_function']=='P0.05'
    for role,number in [('SWDIO',37),('SWDCLK',39),('RESET_N',26),('USB_5V',27),('USB_DM',29),('USB_DP',31)]:
        assert roles[role]['number']==number
    assert all(pins[n]['proposed_net']=='+3.3V' for n in [19,23])
    assert all(pins[n]['proposed_net']=='GND' for n in [5,21,24]) and pins[25]['proposed_net'] is None
    footprint=ROOT/data['footprint_output']
    assert hashlib.sha256(footprint.read_bytes()).hexdigest()==data['footprint_sha256']
    module=pcb.FootprintLoad(str(footprint.parent),'E73-2G4M08S1C')
    pads={int(p.GetNumber()):p for p in module.Pads()}
    assert set(pads)==set(pins)
    for number,pad in pads.items():
        assert [pcb.ToMM(pad.GetPosition().x),pcb.ToMM(pad.GetPosition().y)]==pins[number]['vendor_land_center_mm']
        assert [pcb.ToMM(pad.GetSize().x),pcb.ToMM(pad.GetSize().y)]==pins[number]['vendor_land_size_mm']
    assert not data['production_approved']
    report={'status':'pin-proposal-and-reference-footprint-checked-not-PCB-validation',
            'module':data['module'],'controller_count_per_board':1,'assigned_GPIO_functions':21,
            'connected_outer_lands':27,'connected_bottom_lands':bottom,
            'PCB_routed':False,'E73_firmware_built':False,'production_approved':False,
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [path,footprint,Path(__file__)]}}
    (ROOT/'docs/audit/e73-pin-proposal.json').write_text(json.dumps(report,indent=2)+'\n')
    print('21 GPIO functions unique; USB/SWD/power pins and 43 vendor lands match. PCB and firmware not validated yet.')


if __name__=='__main__':
    main()
