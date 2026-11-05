#!/usr/bin/env python3
"""Run only current YETI60 checks; distinguish check failures from readiness.

Default exit 0 means the implemented checks passed, not production approval.
--require-production returns 2 while recorded hardware requirements remain open.
"""
import argparse,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AUD=ROOT/'docs/audit'; HW=ROOT/'hardware/ec60-nrf52840'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory():
    names=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
    files=[{'path':n,'bytes':(ROOT/n).stat().st_size,'sha256':sha(ROOT/n),'coverage':'inventoried-not-automatically-approved'} for n in sorted(set(names)) if n and (ROOT/n).is_file() and not n.startswith('docs/audit/')]
    (AUD/'source-inventory.json').write_text(json.dumps({'files':files,'excluded':'Git internals, ignored local state, upstream submodule contents, and audit outputs to avoid self-hashing','semantic_review_complete':False},indent=2)+'\n')
def main():
    if not __debug__:raise SystemExit('Audit requires assertions enabled')
    p=argparse.ArgumentParser();p.add_argument('--baseline',default='HEAD');p.add_argument('--refresh-renders',action='store_true');p.add_argument('--refresh-guide',action='store_true');p.add_argument('--require-production',action='store_true');a=p.parse_args()
    uv=shutil.which('uv') or str(Path.home()/'.local/bin/uv')
    kp=os.environ.get('KICAD_PYTHON','/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3')
    cad=[os.environ['YETI_CAD_PYTHON']] if 'YETI_CAD_PYTHON' in os.environ else [uv,'run','--with-requirements',str(ROOT/'requirements-audit.txt'),'python']
    py=[sys.executable]; native=[kp]
    cam=[uv,'run','--python','3.11','--with-requirements',str(ROOT/'requirements-cam.txt'),'python']
    stages=[]
    def add(name,runtime,script,args=(),deps=()):stages.append((name,runtime+['scripts/'+script,*args],list(deps)))
    add('schematic-current',py,'check_schematic_current.py')
    add('pin-contract',py,'check_single_nrf.py',deps=['schematic-current'])
    add('pcb-geometry-contract',native,'check_single_nrf_pcb.py',deps=['schematic-current'])
    add('ordinary-fabrication-contract',native,'check_yeti60_fabrication.py',deps=['pcb-geometry-contract'])
    stages.append(('ordinary-fabrication-fault-injection',native+['tests/audit/test_fabrication.py'],['ordinary-fabrication-contract']))
    add('pcb-native-drc',native,'audit_single_nrf.py',deps=['schematic-current'])
    add('RF-host-copper',native,'screen_yeti60_interference.py',deps=['pcb-native-drc'])
    stages.append(('RF-copper-fault-injection',native+['tests/audit/test_rf_copper.py'],['RF-host-copper']))
    add('connectivity-regression',native,'check_pcb_connectivity_regression.py',['--baseline',a.baseline],['pcb-native-drc'])
    add('C5-protected-IO',native,'check_yeti60_c5_protection.py')
    stages.append(('C5-protection-fault-injection',native+['tests/audit/test_c5_protection.py'],['C5-protected-IO']))
    add('USB-path-geometry',native,'check_yeti60_signal_paths.py',deps=['C5-protected-IO'])
    add('USB-reference-native',native,'export_yeti60_usb_reference.py',deps=['USB-path-geometry'])
    add('electrical-review',native,'check_yeti60_electrical.py',deps=['pin-contract'])
    add('firmware-pin-header',py,'generate_yeti60_pin_contract.py',['--check'],['pin-contract'])
    add('firmware-target-artifacts',py,'check_yeti60_target.py',deps=['firmware-pin-header'])
    add('firmware-recovery-contract',py,'test_yeti60_recovery.py',deps=['firmware-target-artifacts'])
    add('firmware-USB-event-policy',py,'test_yeti60_usb_events.py',deps=['firmware-target-artifacts'])
    add('firmware-GPIO-mode-policy',py,'test_yeti60_gpio_modes.py',deps=['firmware-target-artifacts'])
    add('firmware-scanner-control',py,'test_yeti60_scan_control.py',deps=['firmware-target-artifacts'])
    add('firmware-NVS-powercut-model',py,'test_yeti60_nvs_powercut.py',deps=['firmware-target-artifacts'])
    stages.append(('target-power-fault-injection',py+['tests/audit/test_target.py'],['firmware-target-artifacts']))
    add('firmware-calibration',py,'test_yeti60_calibration.py',deps=['firmware-pin-header'])
    add('firmware-simulation',py,'simulate_yeti60_firmware.py',deps=['firmware-pin-header'])
    add('analog-scan-waveform',cad,'study_yeti60_analog_waveform.py',deps=['firmware-simulation','firmware-target-artifacts'])
    add('firmware-plot',cad,'plot_yeti60_simulation.py',deps=['firmware-simulation'])
    add('mechanical-metadata',native,'export_yeti60_mechanical_metadata.py',deps=['pcb-geometry-contract'])
    add('daughterboard-native-cad',native,'export_yeti60_daughterboard.py')
    add('mechanical-design',cad,'build_yeti60_mechanical.py')
    add('plate-source',cad,'check_plate.py')
    add('plate-mount',cad,'check_yeti60_plate_mount.py',deps=['plate-source'])
    stages.append(('plate-mount-fault-injection',cad+['tests/audit/test_plate_mount.py'],['plate-mount']))
    add('key-mechanism-drawing',cad,'draw_yeti60_key_mechanism.py',deps=['plate-mount'])
    add('assembly-fit',cad,'check_yeti60_assembly.py',deps=['mechanical-metadata','plate-mount','mechanical-design'])
    add('interconnect-native-cad',py,'export_yeti60_interconnects.py',deps=['assembly-fit'])
    add('interconnect-fit',cad,'check_yeti60_interconnects.py',deps=['interconnect-native-cad','daughterboard-native-cad'])
    add('render-geometry',cad,'export_yeti60_render_meshes.py',deps=['assembly-fit','interconnect-fit'])
    add('interconnect-drawings',cad,'draw_yeti60_interconnects.py',deps=['render-geometry','interconnect-fit'])
    add('board-guidance',py,'check_yeti60_board_markings.py',deps=['pcb-geometry-contract'])
    add('purchase-bom',py,'export_yeti60_bom.py',deps=['pin-contract'])
    add('inventory-purchase-plan',py,'plan_yeti60_inventory.py',deps=['purchase-bom'])
    add('readme-materials',py,'check_yeti60_materials.py',deps=['inventory-purchase-plan'])
    add('illustration-native-map',native,'export_yeti60_build_map.py',deps=['purchase-bom','assembly-fit'])
    add('complete-exploded-sheet',cad,'draw_yeti60_complete_exploded.py',deps=['illustration-native-map','render-geometry'])
    add('plate-copper-firmware-map',cad,'check_yeti60_key_geometry.py',deps=['illustration-native-map'])
    stages.append(('plate-map-fault-injection',cad+['tests/audit/test_key_geometry.py'],['plate-copper-firmware-map']))
    guide_deps=['plate-copper-firmware-map','render-geometry']
    if a.refresh_renders or a.refresh_guide:
        add('illustration-regeneration',cad,'draw_yeti60_build_guide.py',deps=guide_deps)
        guide_deps=guide_deps+['illustration-regeneration']
    add('illustrated-build-guide',py,'check_yeti60_build_guide.py',deps=guide_deps)
    stages.append(('inventory-allocation-fault-injection',py+['tests/audit/test_inventory.py'],['inventory-purchase-plan']))
    add('fabrication-review-package',py,'export_yeti60_fabrication.py',deps=['purchase-bom','ordinary-fabrication-contract','pcb-native-drc'])
    add('power-calculation',py,'calculate_yeti60_power.py',deps=['pin-contract'])
    add('battery-pocket',cad,'study_yeti60_battery_pocket.py',deps=['assembly-fit'])
    add('cell-screening',cad,'screen_yeti60_batteries.py',deps=['battery-pocket'])
    add('prototype-research',cad,'study_yeti60_prototype.py',deps=['USB-reference-native','power-calculation','assembly-fit'])
    stages.append(('prototype-research-fault-injection',cad+['tests/audit/test_prototype_research.py'],['prototype-research']))
    add('assembly-drawings',cad,'draw_yeti60_assembly.py',deps=['render-geometry','battery-pocket','daughterboard-native-cad'])
    add('engineering-evidence',py,'check_yeti60_engineering.py',deps=['purchase-bom','power-calculation','cell-screening','assembly-drawings','interconnect-drawings'])
    stages.append(('engineering-fault-injection',py+['tests/audit/test_engineering.py'],['engineering-evidence']))
    if a.refresh_renders:
        add('pcb-renders',cad,'render_single_nrf.py',['--frames','72','--fps','24','--jobs','2'],deps=['pcb-native-drc'])
        add('assembly-renders',[uv,'run','--python','3.11','--with-requirements',str(ROOT/'requirements-render.txt'),'python'],'render_yeti60_assembly.py',deps=['render-geometry'])
    add('USB-repair-candidate-native',native,'check_usb_short_route.py')
    add('USB-repair-CAM-export',native,'export_usb_short_fabrication.py',deps=['USB-repair-candidate-native'])
    add('USB-repair-CAM-readback',cam,'check_usb_short_fabrication.py',deps=['USB-repair-CAM-export'])
    stages.append(('USB-repair-CAM-faults',cam+['tests/audit/test_usb_short_fabrication.py'],['USB-repair-CAM-readback']))
    stages.append(('USB-repair-passive-faults',py+['tests/audit/test_usb_short_passives.py'],['USB-repair-candidate-native']))
    stages.append(('USB-repair-power-faults',py+['tests/audit/test_usb_short_power.py'],['USB-repair-candidate-native']))
    stages.append(('USB-repair-F1-faults',py+['tests/audit/test_usb_short_fuse.py'],['USB-repair-candidate-native']))
    stages.append(('USB-repair-candidate-faults',native+['tests/audit/test_usb_short_route.py'],['USB-repair-candidate-native']))
    add('USB-repair-candidate-local-geometry',cad,'study_usb_short_route.py',deps=['USB-repair-candidate-native','assembly-fit'])
    stages.append(('USB-repair-ground-faults',cad+['tests/audit/test_usb_short_ground.py'],['USB-repair-candidate-local-geometry']))
    add('USB-repair-candidate-firmware',py,'check_usb_short_firmware.py',deps=['USB-repair-candidate-local-geometry'])
    add('USB-repair-inset-plate',cad,'build_usb_short_plate.py',deps=['USB-repair-candidate-firmware','assembly-fit'])
    add('USB-repair-closed-routes',cad,'check_usb_short_closed_assembly.py',deps=['USB-repair-candidate-firmware','interconnect-fit','USB-repair-inset-plate'])
    stages.append(('USB-repair-closed-route-faults',cad+['tests/audit/test_closed_harness.py'],['USB-repair-closed-routes']))
    add('USB-repair-printable-guides',cad,'export_usb_short_guides.py',deps=['USB-repair-closed-routes'])
    add('USB-repair-feed-budget',py,'calculate_usb_short_feed.py',deps=['USB-repair-closed-routes'])
    add('USB-repair-complete-assembly',cad,'export_usb_short_assembly.py',deps=['USB-repair-printable-guides'])
    add('USB-repair-rigid-extraction',cad,'check_usb_short_vertical_motion.py',deps=['USB-repair-complete-assembly'])
    stages.append(('USB-repair-rigid-extraction-faults',cad+['tests/audit/test_vertical_motion.py'],['USB-repair-rigid-extraction']))
    add('USB-repair-bounded-fit',cad,'check_usb_short_fit.py',deps=['USB-repair-rigid-extraction'])
    stages.append(('USB-repair-bounded-fit-faults',cad+['tests/audit/test_usb_short_fit.py'],['USB-repair-bounded-fit']))
    add('USB-repair-tolerance-diagnostic',cad,'study_usb_short_tolerances.py',deps=['USB-repair-bounded-fit-faults'])
    stages.append(('USB-repair-tolerance-evidence-faults',py+['tests/audit/test_usb_short_tolerances.py'],['USB-repair-tolerance-diagnostic']))
    add('USB-repair-native-surfaces',native,'export_usb_short_surfaces.py',deps=['USB-repair-candidate-native','USB-repair-complete-assembly'])
    add('USB-repair-surface-maps',cad,'paint_usb_short_surfaces.py',deps=['USB-repair-native-surfaces'])
    add('USB-repair-assembly-sheets',cad,'draw_usb_short_assembly.py',deps=['USB-repair-complete-assembly'])
    if a.refresh_renders:
        add('USB-repair-studio-renders',[uv,'run','--python','3.11','--with-requirements',str(ROOT/'requirements-render.txt'),'python'],'render_usb_short_assembly.py',deps=['USB-repair-surface-maps','USB-repair-assembly-sheets'])
    add('USB-repair-assembly-package',py,'check_usb_short_assembly_package.py',deps=['USB-repair-surface-maps','USB-repair-assembly-sheets','USB-repair-closed-route-faults','USB-repair-feed-budget','USB-repair-rigid-extraction-faults','USB-repair-tolerance-evidence-faults'])
    stages.append(('USB-repair-package-faults',py+['tests/audit/test_closed_package.py'],['USB-repair-assembly-package']))
    add('documentation',py,'check_project_docs.py')
    dependencies=[name for name,_,_ in stages]
    add('cross-domain-integration',py,'check_project_integration.py',deps=dependencies)
    stages.append(('integration-fault-injection',py+['tests/audit/test_integration.py'],['cross-domain-integration']))
    protected=[*HW.glob('*.kicad_sch'),*HW.glob('*.kicad_pcb'),*HW.glob('*.kicad_pro'),*HW.glob('*.kicad_sym'),*HW.glob('YAECKB.pretty/*.kicad_mod'),HW/'netlist.xml',HW/'components.json',HW/'pinmap.json',ROOT/'design-constraints.json',ROOT/'mechanical/felk60_plate_hhkb.plate-mount.dxf',*sorted((ROOT/'felk60').glob('*.step')),*sorted((ROOT/'firmware/yeti60').glob('*.[ch]'))]
    before={str(p.relative_to(ROOT)):sha(p) for p in protected}
    records=[];states={}
    for name,command,deps in stages:
        print(name+': running',flush=True);start=time.monotonic()
        if any(states[x]!='passed' for x in deps):record={'stage':name,'state':'skipped-dependency-failed'}
        else:
            try:
                r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
                record={'stage':name,'state':'passed' if r.returncode==0 else 'failed','exit_code':r.returncode}
                if r.returncode:record['output_tail']=(r.stdout+r.stderr)[-4000:]
            except OSError as e:record={'stage':name,'state':'failed','error':str(e)}
        record['seconds']=round(time.monotonic()-start,2);records.append(record);states[name]=record['state'];print(name+': '+record['state'],flush=True)
    changed=[n for n,h in before.items() if sha(ROOT/n)!=h]
    records.append({'stage':'design-inputs-unchanged','state':'failed' if changed else 'passed','changed':changed})
    okay=all(x['state']=='passed' for x in records)
    config=json.loads((ROOT/'design-constraints.json').read_text());pending=[x for x in config['open_requirements'] if x['status']!='closed']
    short_native=json.loads((ROOT/'hardware/usb-short-route/audit/native-check.json').read_text())
    for requirement in pending:
        if requirement['id']=='signal-interference':
            requirement['canonical_diagnostic_description']=requirement['description']
            requirement['description']='The repaired candidate has short mainboard USB routes and checked adjacent-ground coverage. Full harness impedance/return, actual USB eye and enclosed RF/EC acceptance remain open; the previous long-route canonical archive is held.'
    if short_native.get('power_layout_rework_open'):
        pending.append({'id':'USB-REPAIR-POWER-LAYOUT','status':'open','requirement':'Relocate/reroute the regulator power stage clear of the sensing guard and verify local output/feedback plus effective-capacitance layout','evidence':'hardware/usb-short-route/audit/native-check.json'})
    outcome={'status':'checks-passed-production-incomplete' if okay else 'checks-failed','checks_passed':okay,'production_approved':False,'stages':records,'open_requirements':pending,'scope':'Current single-nRF design, built ARM targets, host simulation, conditional mechanical/charging design and artifact provenance; no physical certification','inventory':'docs/audit/source-inventory.json'}
    outcome['candidate_first_article']={'entry':'hardware/usb-short-route/FIRST-ARTICLE.md',
        'CAM_package_verified':states.get('USB-repair-CAM-readback')=='passed',
        'CAM_fault_tests_passed':states.get('USB-repair-CAM-faults')=='passed',
        'manufacturing_order_released':False,'physical_acceptance':False,
        'sequence':'Supplier DFM before fabrication; pack confirmation before real-battery connection; physical acceptance after first-board fabrication. Enclosed service is a separate remaining requirement.',
        'previous_canonical_archive':'Held; not replaced or released by candidate file availability'}
    if states.get('USB-repair-tolerance-diagnostic')=='passed':
        tolerance=json.loads((ROOT/'hardware/usb-short-route/audit/tolerance-diagnostic.json').read_text())
        outcome['candidate_first_article']['combined_shell_tolerance_qualified']=tolerance['combined_tolerance_qualified']
        outcome['candidate_first_article']['tolerance_diagnostic']='hardware/usb-short-route/TOLERANCES.md'
        outcome['candidate_first_article']['baseline_interfaces_with_insufficient_known_reserve']=[r['interface'] for r in tolerance['directional_budgets'] if r['conditional_screen']=='insufficient']
        fitted=json.loads((ROOT/'hardware/usb-short-route/audit/tolerance-fit.json').read_text())
        outcome['candidate_first_article']['current_plate_switch_bounded_fit_passed']=fitted['plate_and_switch_bounded_envelopes_passed']
        outcome['candidate_first_article']['current_fit_entry']='hardware/usb-short-route/MECHANICAL-FIT.md'
    inventory();(AUD/'outcome.json').write_text(json.dumps(outcome,indent=2)+'\n')
    print(outcome['status'],flush=True)
    return 1 if not okay else (2 if a.require_production else 0)
if __name__=='__main__':raise SystemExit(main())
