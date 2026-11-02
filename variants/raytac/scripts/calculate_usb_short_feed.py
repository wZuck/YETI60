#!/usr/bin/env python3
"""Bound the revised feed cable; distinguish vendor limits from imposed targets."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/usb-short-route'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path=BASE/'audit/closed-assembly.json';closed=json.loads(path.read_text())
    wires={family:{w['pin']:w for w in rows} for family,rows in closed['nominal']['wires'].items()}
    selected=[('usb','1'),('usb','4'),('power','1'),('power','2')]
    length=sum(wires[f][p]['free_length_mm'] for f,p in selected)/1000
    length_max=length+4*.0005
    # Eight engaged power contacts: positive/return at C5, J4, J5 and J1.
    # JST SH eSH.pdf p1 specifies initial 20 mOhm, post-environment 40 mOhm.
    scenarios=[]
    for name,wire_limit,contact in [('initial-20C-target',.25,.020),('aged-60C-target',.30,.040)]:
        resistance=length_max*wire_limit+8*contact
        for current in [.1,.5]:
            scenarios.append(dict(scenario=name,current_A=current,wire_R_limit_ohm_per_m=wire_limit,
                contact_R_limit_ohm=contact,loop_R_ohm=resistance,drop_V=current*resistance,
                distributed_harness_loss_W=current*current*resistance))
    budgets=[]
    hot=next(s for s in scenarios if s['scenario']=='aged-60C-target' and s['current_A']==.5)
    for start in [4.75,5.0,5.25]:
        available=start-hot['drop_V']-4.63
        budgets.append(dict(C5_SH_board_pad_voltage_V=start,charger_input_target_V=4.63,
            remaining_voltage_after_harness_V=available,remaining_mainboard_R_budget_ohm=available/.5,
            interpretation='No full-current margin even before mainboard losses' if available<0 else 'Budget for mainboard fuse, copper and other series losses; not proven available'))
    data=dict(status='conditional-feed-budget-calculated-not-qualified',physical_verification=False,
        selected_wire_legs=selected,nominal_copper_length_m=length,maximum_exit_to_exit_length_m=length_max,
        length_tolerance_per_wire_mm=.5,engaged_power_contact_count=8,scenarios=scenarios,budgets=budgets,
        return_topology='The native PCB ground plane connects J1/J4/J5 ground in parallel with the black power jumper. The eight-contact series model intentionally ignores that parallel plane; it is a pessimistic harness-path screen, not the actual solved current distribution.',
        imposed_not_vendor_guaranteed={'wire_resistance_20C_ohm_per_m_max':.25,'wire_resistance_60C_ohm_per_m_max':.30,
            'meaning':'Procurement/test targets for an unselected actual wire. Include crimp extensions, splice/crimp resistance and length tolerance in the measured finished loop; the wire-exit model omits internal lead lengths.'},
        sources={'JST_SH_contact_resistance':{'url':'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf','page':1,'initial_max_ohm':.020,'after_environment_max_ohm':.040},
                 'BQ24074_USB_input_DPM':{'url':'https://www.ti.com/lit/ds/symlink/bq24074.pdf','revision':'N','page':12,'threshold_min_typ_max_V':[4.35,4.5,4.63]}},
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [path,Path(__file__)]},
        not_included=['External USB cable, USB-C contact and C5 input fuse losses before the C5 SH PCB pad',
                      'Mainboard input fuse resistance/temperature derating, PCB copper and regulator losses',
                      'Unspecified crimp extensions/contact processing, actual wire resistance and USB signal quality'],
        conclusion='Do not promise the programmed charge rate. Qualify the final fuse/wire and measure U5 IN/OUT and MCU VBUS under load; input DPM may reduce current while USB typing remains required.')
    (BASE/'audit/feed-budget.json').write_text(json.dumps(data,indent=2)+'\n')
    print('Feed round-trip length m:',length,'Aged/hot imposed-target drop at 500mA V:',hot['drop_V'])


if __name__=='__main__':main()
