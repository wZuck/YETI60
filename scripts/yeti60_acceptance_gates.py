#!/usr/bin/env python3
"""Separate verifiable design gates from absent hardware/supplier evidence."""


def summarize(gates):
    assert gates and len({g['id'] for g in gates})==len(gates)
    assert all(g['scope'] in ['design','qualification','physical','supplier'] for g in gates)
    assert all(g['state'] in ['passed','failed','open','not-run'] for g in gates)
    design=[g for g in gates if g['scope']=='design']
    assert design
    design_passed=all(g['state']=='passed' for g in design)
    accepted=all(g['state']=='passed' for g in gates)
    return {'acceptance_status':'accepted' if accepted else 'hold',
            'design_review_status':'passed' if design_passed else 'hold',
            'ready_for_engineering_first_article':design_passed,
            'production_approved':accepted,
            'physical_test_performed':any(g['scope']=='physical' and g['state'] in ['passed','failed'] for g in gates),
            'open_gate_ids':[g['id'] for g in gates if g['state']!='passed'],
            'open_gates':[g['description'] for g in gates if g['state']!='passed']}


def design_and_pending_gates(layout,plate,paths,calibration):
    gates=[]
    def add(ident,scope,state,description):gates.append({'id':ident,'scope':scope,'state':state,'description':description})
    for name in ['e73','raytac']:
        copper=layout['variants'][name]
        clean=all(v['GND_union_mm2']+v['non_GND_union_mm2']<=.001 for v in copper['layers'])
        add(name+'.antenna-host-copper','design','passed' if clean else 'failed',
            name+': host copper must clear the declared antenna screen on every layer; E73 region remains provisional')
        clear=plate['variants'][name]['metal_plate_projection_mm2']<=1e-6
        add(name+'.antenna-plate-projection','design','passed' if clear else 'failed',
            name+': metal plate must clear the declared antenna projection; proximity still needs physical RF validation')
        data=paths['variants'][name]
        short=all(data[n]['ESD_branch_to_main_path_mm']<=5 for n in ['positive','negative'])
        add(name+'.USB-protection-branches','design','passed' if short else 'failed',
            name+': TVS signal branches must be <=5mm under the imposed project layout target')
        add(name+'.guarded-calibration','design','passed' if calibration[name]['status']=='passed' else 'failed',
            name+': guarded per-key calibration must pass the native sanitizer regression suite')
        add(name+'.USB-SI','qualification','open',name+': full cable/C5/pair impedance, return continuity and USB eye remain unqualified')
        for ident,description in [('functional','Flash/readback, 60 keys, USB/BLE transport and host cycle tests'),
                                  ('RF-noise','Final-enclosure range, coexistence and per-key interference margins'),
                                  ('power-thermal','Power transients, charging, temperature interruption and runtime'),
                                  ('mechanical','Actual donor stack, resin, fasteners, plug and harness acceptance')]:
            add(name+'.physical-'+ident,'physical','not-run',name+': '+description+'; no physical unit exists')
    add('supplier-battery','supplier','open','Supplier-signed complete pack, corrected cell limits and independent thermal-protection evidence required')
    add('manufacturer-DFM','supplier','open','Fabricator/assembler review and ordinary-process first-article inspection required')
    return gates
