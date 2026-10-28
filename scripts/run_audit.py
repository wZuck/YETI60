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
    p=argparse.ArgumentParser();p.add_argument('--baseline',default='HEAD');p.add_argument('--refresh-renders',action='store_true');p.add_argument('--require-production',action='store_true');a=p.parse_args()
    uv=shutil.which('uv') or str(Path.home()/'.local/bin/uv')
    kp=os.environ.get('KICAD_PYTHON','/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3')
    cad=[os.environ['YETI_CAD_PYTHON']] if 'YETI_CAD_PYTHON' in os.environ else [uv,'run','--with-requirements',str(ROOT/'requirements-audit.txt'),'python']
    py=[sys.executable]; native=[kp]
    stages=[]
    def add(name,runtime,script,args=(),deps=()):stages.append((name,runtime+['scripts/'+script,*args],list(deps)))
    add('schematic-current',py,'check_schematic_current.py')
    add('pin-contract',py,'check_single_nrf.py',deps=['schematic-current'])
    add('pcb-geometry-contract',native,'check_single_nrf_pcb.py',deps=['schematic-current'])
    add('pcb-native-drc',native,'audit_single_nrf.py',deps=['schematic-current'])
    add('connectivity-regression',native,'check_pcb_connectivity_regression.py',['--baseline',a.baseline],['pcb-native-drc'])
    add('electrical-review',native,'check_yeti60_electrical.py',deps=['pin-contract'])
    add('firmware-pin-header',py,'generate_yeti60_pin_contract.py',['--check'],['pin-contract'])
    add('firmware-simulation',py,'simulate_yeti60_firmware.py',deps=['firmware-pin-header'])
    add('firmware-plot',cad,'plot_yeti60_simulation.py',deps=['firmware-simulation'])
    add('mechanical-metadata',native,'export_yeti60_mechanical_metadata.py',deps=['pcb-geometry-contract'])
    add('plate-source',cad,'check_plate.py')
    add('assembly-fit',cad,'check_yeti60_assembly.py',deps=['mechanical-metadata','plate-source'])
    add('render-geometry',cad,'export_yeti60_render_meshes.py',deps=['assembly-fit'])
    if a.refresh_renders:
        add('pcb-renders',cad,'render_single_nrf.py',deps=['pcb-native-drc'])
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
    outcome={'status':'checks-passed-production-incomplete' if okay else 'checks-failed','checks_passed':okay,'production_approved':False,'stages':records,'open_requirements':pending,'scope':'Current single-nRF design, host core, conditional mechanical fit and artifact provenance; no target or physical certification','inventory':'docs/audit/source-inventory.json'}
    inventory();(AUD/'outcome.json').write_text(json.dumps(outcome,indent=2)+'\n')
    print(outcome['status'],flush=True)
    return 1 if not okay else (2 if a.require_production else 0)
if __name__=='__main__':raise SystemExit(main())
