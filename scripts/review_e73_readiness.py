#!/usr/bin/env python3
"""Combine current E73 checks without equating software success with release."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AUD=ROOT/'docs/audit'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gates(cad,target,events,layout,paths,assembly,service,outcome,firmware,tolerances):
    result=[]
    def add(name,state,details):result.append(dict(id=name,state=state,details=details))
    add('native-PCB','passed' if cad['status']=='cad-checks-passed' and not cad['failed_ground_pairs'] and not cad['failed_pin_pairs'] and not cad['unconnected_items'] and len(cad['physical_pin_pairs'])==270 and len(cad['ground_pin_pairs'])==142 else 'failed',
        dict(signal_pairs=len(cad['physical_pin_pairs']),ground_pairs=len(cad['ground_pin_pairs']),opens=cad['unconnected_items']))
    add('matched-firmware','passed' if target['status']=='passed' else 'failed',target['variants'])
    complete=firmware['status']=='passed' and not firmware['physical_verification'] and firmware['E73_GPIO_ADC_RC_LDO_NFC_preserved'] and (firmware['active_keys'],firmware['event_queue'],firmware['CRC_record_bytes'],firmware['NVS_cut_trials'])==(60,128,308,14795)
    add('scanner-calibration-storage-models','passed' if complete else 'failed',firmware)
    add('USB-event-charging-policy','passed' if events['status']=='passed' and len(events['cases'])==11 and events['configuration_zero_rejected'] else 'failed',
        dict(cases=len(events['cases']),GPIO1_CE_N=True,physical_verification=False))
    clean=all(x['GND_union_mm2']+x['non_GND_union_mm2']<=.001 for x in layout['layers'])
    add('antenna-projection','passed' if clean else 'failed','Provisional E73 antenna-end band only; vendor numeric keepout and real RF remain open')
    lengths={name:paths[name]['ESD_branch_to_main_path_mm'] for name in ['positive','negative']}
    add('USB-protection-branches','passed' if all(isinstance(v,(int,float)) and 0<=v<=5 for v in lengths.values()) else 'failed',dict(actual_mm=lengths,project_maximum_mm=5))
    correct_plate=abs(assembly['nominal_stack']['plate_thickness_mm']-1.6)<1e-6 and len(assembly['mounting_hole_matches'])==28
    mechanism=assembly.get('mechanism_contract',{})
    qualified=correct_plate and mechanism.get('status')=='drawing-based-plate-mount-contract-passed' and mechanism.get('active_key_centers_preserved')==60 and mechanism.get('installed_mount_sets')==28 and mechanism.get('plate_stabilizer_pairs')==3 and mechanism.get('unused_pcb_mount_refs')==['H26']
    add('NiZ-plate-mounted-stabilizers','passed' if qualified else 'failed',dict(dimensions_match_target=correct_plate,geometry_port_qualified=qualified,contract=mechanism,physical_fit_verified=False))
    sufficient=all(r['optimistic_remaining_gap_mm']>=r['project_minimum_air_gap_mm'] and not r['unquantified_terms'] for r in tolerances['directional_budgets'])
    add('mechanical-tolerance-budget','passed' if sufficient and tolerances['combined_tolerance_qualified'] else 'failed',tolerances['directional_budgets'])
    add('battery-plug-service','passed' if service['status']=='passed' else 'failed',service['checks'])
    add('full-artifact-audit','passed' if outcome['checks_passed'] else 'failed',dict(passed=sum(x['state']=='passed' for x in outcome['stages']),total=len(outcome['stages'])))
    add('closed-harness-and-power-layout','open','E73 retains its original seven-wire route and long USB PCB paths; Raytac nine-wire/SH3/power-layout acceptance cannot be inherited')
    add('battery-supplier-and-DFM','open','Protected 1S 1600 mAh pack envelope 85 x 43 x 4.8 mm; supplier corrected limits, independent thermal protection and ordinary-process DFM are not accepted')
    add('physical-functional-RF-thermal-mechanical','not-run','USB/BLE, 60 keys, charging, analog margins, RF, actual NiZ fit and battery safety require hardware')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--require-design',action='store_true');a=p.parse_args()
    names=['integration.json','outcome.json','yeti60-target-check.json','yeti60-target-build.json','usb-event-policy.json','interference-layout.json','USB-signal-paths.json','yeti60-assembly.json','e73-service-motion.json','firmware-suite.json','e73-tolerance-diagnostic.json']
    data={n:json.loads((AUD/n).read_text()) for n in names}
    # Fail on obsolete evidence, even when the resulting disposition is HOLD.
    for name in ['usb-event-policy.json','interference-layout.json','USB-signal-paths.json','yeti60-assembly.json','e73-service-motion.json','yeti60-target-build.json','e73-tolerance-diagnostic.json']:
        for key,value in data[name].get('source_sha256',{}).items():assert sha(ROOT/key)==value,('Stale E73 evidence',name,key)
    cadpath=ROOT/'hardware/ec60-nrf52840/audit-current.json';cad=json.loads(cadpath.read_text())
    for name,value in cad['source_sha256'].items():assert sha(cadpath.parent/name)==value,('Stale native CAD',name)
    for variant in data['USB-signal-paths.json']['variants'].values():
        for name,value in variant['source_sha256'].items():assert sha(ROOT/name)==value,('Stale USB board',name)
    build=data['yeti60-target-build.json']
    assert data['yeti60-target-check.json']['build_manifest_sha256']==sha(AUD/'yeti60-target-build.json'),'Stale target check'
    for variant in build['variants'].values():
        for name,value in variant['outputs'].items():assert sha(ROOT/name)==value,('Stale firmware output',name)
    from check_yeti60_firmware_suite import verify as verify_firmware_suite
    assert data['firmware-suite.json']==verify_firmware_suite(),'Stale firmware suite summary'
    rows=gates(cad,data['yeti60-target-check.json'],data['usb-event-policy.json'],data['interference-layout.json']['variants']['e73'],data['USB-signal-paths.json']['variants']['e73'],data['yeti60-assembly.json'],data['e73-service-motion.json'],data['outcome.json'],data['firmware-suite.json'],data['e73-tolerance-diagnostic.json'])
    blocked=[x['id'] for x in rows if x['state']!='passed']
    report=dict(module='E73-2G4M08S1C',status='hold' if blocked else 'design-checks-passed',gates=rows,open_gate_ids=blocked,
                production_approved=False,manufacturing_released=False,physical_verification=False,
                existing_daughterboard='Keep existing UDB-C-JSH C5; no daughterboard PCB change',
                evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in [cadpath,*[AUD/n for n in names]]},
                source_sha256={'scripts/review_e73_readiness.py':sha(Path(__file__))})
    (AUD/'e73-readiness.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 2 if a.require_design and blocked else 0
if __name__=='__main__':raise SystemExit(main())
