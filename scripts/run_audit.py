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
    files=[{'path':n,'bytes':(ROOT/n).stat().st_size,'sha256':sha(ROOT/n),'coverage':'inventoried-not-automatically-approved'} for n in sorted(set(names)) if n and (ROOT/n).is_file() and '/docs/audit/' not in '/'+n]
    (AUD/'source-inventory.json').write_text(json.dumps({'files':files,'excluded':'Git internals, ignored local state, upstream submodule contents, and audit outputs to avoid self-hashing','semantic_review_complete':False},indent=2)+'\n')
def main():
    if not __debug__:raise SystemExit('Audit requires assertions enabled')
    p=argparse.ArgumentParser();p.add_argument('--baseline',default='HEAD');p.add_argument('--refresh-renders',action='store_true');p.add_argument('--refresh-guide',action='store_true');p.add_argument('--require-production',action='store_true');a=p.parse_args()
    uv=shutil.which('uv') or str(Path.home()/'.local/bin/uv')
    kp=os.environ.get('KICAD_PYTHON','/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3')
    cad=[os.environ['YETI_CAD_PYTHON']] if 'YETI_CAD_PYTHON' in os.environ else [uv,'run','--with-requirements',str(ROOT/'requirements-audit.txt'),'python']
    py=[sys.executable]; native=[kp]
    stages=[]
    def add(name,runtime,script,args=(),deps=()):stages.append((name,runtime+['scripts/'+script,*args],list(deps)))
    add('schematic-current',py,'check_schematic_current.py')
    add('pin-contract',py,'check_single_nrf.py',deps=['schematic-current'])
    add('e73-vendor-reference',native,'check_e73_reference.py')
    add('e73-module-contract',native,'check_e73_variant.py',deps=['pin-contract','e73-vendor-reference'])
    stages.append(('e73-pin-fault-injection',py+['tests/audit/test_e73.py'],['e73-module-contract']))
    add('pcb-geometry-contract',native,'check_single_nrf_pcb.py',deps=['schematic-current'])
    add('ordinary-fabrication-contract',native,'check_yeti60_fabrication.py',deps=['pcb-geometry-contract'])
    stages.append(('ordinary-fabrication-fault-injection',native+['tests/audit/test_fabrication.py'],['ordinary-fabrication-contract']))
    add('pcb-native-drc',native,'audit_single_nrf.py',deps=['schematic-current'])
    add('connectivity-regression',native,'check_pcb_connectivity_regression.py',['--baseline',a.baseline],['pcb-native-drc'])
    add('electrical-review',native,'check_yeti60_electrical.py',deps=['pin-contract'])
    add('firmware-pin-header',py,'generate_yeti60_pin_contract.py',['--check'],['pin-contract'])
    add('firmware-target-artifacts',py,'check_yeti60_target.py',deps=['firmware-pin-header'])
    stages.append(('target-power-fault-injection',py+['tests/audit/test_target.py'],['firmware-target-artifacts']))
    add('firmware-simulation',py,'simulate_yeti60_firmware.py',deps=['firmware-pin-header'])
    add('firmware-plot',cad,'plot_yeti60_simulation.py',deps=['firmware-simulation'])
    add('mechanical-metadata',native,'export_yeti60_mechanical_metadata.py',deps=['pcb-geometry-contract'])
    add('daughterboard-native-cad',native,'export_yeti60_daughterboard.py')
    add('mechanical-design',cad,'build_yeti60_mechanical.py')
    add('plate-source',cad,'check_plate.py')
    add('assembly-fit',cad,'check_yeti60_assembly.py',deps=['mechanical-metadata','plate-source','mechanical-design'])
    add('interconnect-native-cad',py,'export_yeti60_interconnects.py',deps=['assembly-fit'])
    add('interconnect-fit',cad,'check_yeti60_interconnects.py',deps=['interconnect-native-cad','daughterboard-native-cad'])
    add('render-geometry',cad,'export_yeti60_render_meshes.py',deps=['assembly-fit','interconnect-fit'])
    add('interconnect-drawings',cad,'draw_yeti60_interconnects.py',deps=['render-geometry','interconnect-fit'])
    add('board-guidance',py,'check_yeti60_board_markings.py',deps=['pcb-geometry-contract'])
    add('purchase-bom',py,'export_yeti60_bom.py',deps=['pin-contract'])
    add('inventory-purchase-plan',py,'plan_yeti60_inventory.py',deps=['purchase-bom'])
    add('readme-materials',py,'check_yeti60_materials.py',deps=['inventory-purchase-plan'])
    add('illustration-native-map',native,'export_yeti60_build_map.py',deps=['purchase-bom','assembly-fit'])
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
    add('assembly-drawings',cad,'draw_yeti60_assembly.py',deps=['render-geometry','battery-pocket','daughterboard-native-cad'])
    add('engineering-evidence',py,'check_yeti60_engineering.py',deps=['purchase-bom','power-calculation','cell-screening','assembly-drawings','interconnect-drawings'])
    stages.append(('engineering-fault-injection',py+['tests/audit/test_engineering.py'],['engineering-evidence']))
    if a.refresh_renders:
        add('pcb-renders',cad,'render_single_nrf.py',['--frames','72','--fps','24','--jobs','2'],deps=['pcb-native-drc'])
        add('assembly-renders',[uv,'run','--python','3.11','--with-requirements',str(ROOT/'requirements-render.txt'),'python'],'render_yeti60_assembly.py',deps=['render-geometry'])
    add('documentation',py,'check_project_docs.py')
    dependencies=[name for name,_,_ in stages]
    add('cross-domain-integration',py,'check_project_integration.py',deps=dependencies)
    stages.append(('integration-fault-injection',py+['tests/audit/test_integration.py'],['cross-domain-integration']))
    protected=[*HW.glob('*.kicad_sch'),*HW.glob('*.kicad_pcb'),*HW.glob('*.kicad_pro'),*HW.glob('*.kicad_sym'),*HW.glob('YAECKB.pretty/*.kicad_mod'),HW/'netlist.xml',HW/'components.json',HW/'pinmap.json',ROOT/'design-constraints.json',ROOT/'mechanical/felk60_plate_hhkb.audited.dxf',*sorted((ROOT/'felk60').glob('*.step')),*sorted((ROOT/'firmware/yeti60').glob('*.[ch]'))]
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
    outcome={'status':'checks-passed-production-incomplete' if okay else 'checks-failed','checks_passed':okay,'production_approved':False,'stages':records,'open_requirements':pending,'scope':'Current single-nRF design, built ARM targets, host simulation, conditional mechanical/charging design and artifact provenance; no physical certification','inventory':'docs/audit/source-inventory.json'}
    inventory();(AUD/'outcome.json').write_text(json.dumps(outcome,indent=2)+'\n')
    print(outcome['status'],flush=True)
    return 1 if not okay else (2 if a.require_production else 0)
if __name__=='__main__':raise SystemExit(main())
