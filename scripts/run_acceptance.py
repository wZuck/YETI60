#!/usr/bin/env python3
"""Run both audits and reproducible interference screens, then record open gates."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone
from yeti60_acceptance_gates import design_and_pending_gates,summarize

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--refresh-guide',action='store_true')
    parser.add_argument('--check-existing-audits',action='store_true',help='Check existing full-audit evidence; always rerun interference screens')
    args=parser.parse_args()
    kp=os.environ.get('KICAD_PYTHON','/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3')
    cad=[os.environ['YETI_CAD_PYTHON']] if 'YETI_CAD_PYTHON' in os.environ else ['uv','run','--with-requirements','requirements-audit.txt','python']
    command=[sys.executable,'scripts/run_all_variants.py']
    if args.refresh_guide:command.append('--refresh-guide')
    if args.check_existing_audits:command.append('--check-existing')
    commands=[command,[kp,'scripts/study_yeti60_rf_lands.py'],
              cad+['scripts/study_yeti60_rf_remediation.py'],[kp,'scripts/screen_yeti60_interference.py'],
              [sys.executable,'scripts/simulate_yeti60_interference.py'],
              cad+['scripts/check_yeti60_antenna_plate.py'],[kp,'scripts/check_yeti60_signal_paths.py'],
              [kp,'tests/audit/test_signal_paths.py'],[kp,'tests/audit/test_interference.py']]
    executed=[]
    for command in commands:
        print('Running: '+' '.join(command),flush=True)
        subprocess.run(command,cwd=ROOT,check=True)
        executed.append({'command':command,'exit_code':0})
    variants={};evidence=[]
    for name,folder in [('e73',ROOT),('raytac',ROOT/'variants/raytac')]:
        outcome=folder/'docs/audit/outcome.json';board=folder/'hardware/ec60-nrf52840/audit-current.json'
        host=folder/'docs/audit/yeti60-firmware-simulation.json';target=folder/'docs/audit/yeti60-target-check.json'
        fit=folder/'docs/audit/yeti60-assembly.json';guide=folder/'docs/audit/yeti60-build-guide-check.json'
        result=json.loads(outcome.read_text());b=json.loads(board.read_text());h=json.loads(host.read_text())
        assert result['checks_passed'] and all(s['state']=='passed' for s in result['stages'])
        assert h['status']=='passed' and any('two sustained over-threshold' in line for line in h['output'])
        variants[name]={'CAD_checks_passed':True,'firmware_build_and_host_checks_passed':True,
                        'audit_stage_count':len(result['stages']),'DRC_errors':sum(b['drc_errors_by_type'].values()),
                        'unconnected_items':b['unconnected_items'],'DRC_warnings':b['warnings_by_type'],
                        'physical_signal_pairs':len(b['physical_pin_pairs']),
                        'RF_acceptance':'not-run','physical_acceptance':'not-run'}
        evidence += [outcome,board,host,target,fit,guide,folder/'docs/audit/integration.json',folder/'docs/audit/calibration.json']
    evidence += [ROOT/'docs/audit'/n for n in ['variants.json','interference-layout.json','interference-analog.json','interference-plate.json',
                                            'rf-remediation-candidate.json','rf-remediation-lands.json','USB-signal-paths.json']]
    sources=[Path(__file__),ROOT/'scripts/check_yeti60_acceptance.py',ROOT/'tests/audit/test_interference.py',
             ROOT/'scripts/yeti60_acceptance_gates.py',ROOT/'tests/audit/test_signal_paths.py',
             ROOT/'design-constraints.json',ROOT/'docs/testing/vendor-sources.json',
             *sorted((ROOT/'docs/testing').glob('*.md'))]
    outputs=[*sorted((ROOT/'docs/testing').glob('*.csv')),*sorted((ROOT/'docs/testing/images').glob('*'))]
    read=lambda n:json.loads((ROOT/'docs/audit'/n).read_text())
    gates=design_and_pending_gates(read('interference-layout.json'),read('interference-plate.json'),read('USB-signal-paths.json'),
                                 {name:json.loads(((ROOT if name=='e73' else ROOT/'variants/raytac')/'docs/audit/calibration.json').read_text()) for name in variants})
    for name,record in variants.items():
        record['RF_layout_acceptance']='passed' if all(g['state']=='passed' for g in gates if g['id'] in [name+'.antenna-host-copper',name+'.antenna-plate-projection']) else 'hold'
    report={'execution_status':'completed',**summarize(gates),'gates':gates,'field_solver_performed':False,
            'executed_at_UTC':datetime.now(timezone.utc).isoformat(),'commands':executed,'variants':variants,
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},
            'evidence_sha256':{str(p.relative_to(ROOT)):sha(p) for p in evidence},
            'outputs':{str(p.relative_to(ROOT)):sha(p) for p in outputs}}
    (ROOT/'docs/audit/acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
    subprocess.run([sys.executable,'scripts/check_yeti60_acceptance.py'],cwd=ROOT,check=True)
    # Inventory after all generated non-audit assets have their final contents.
    for folder in [ROOT,ROOT/'variants/raytac']:
        spec=importlib.util.spec_from_file_location('inventory',folder/'scripts/run_audit.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.inventory()
    return 0


if __name__=='__main__':raise SystemExit(main())
