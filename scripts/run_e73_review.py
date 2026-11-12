#!/usr/bin/env python3
"""Reproduce E73 artifact, RF, USB and connector-service evidence.

A successful run means checks executed consistently; measured defects remain
HOLD in e73-readiness.json. --require-design returns 2 until those are closed.
"""
import argparse,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    if not __debug__:raise SystemExit('Review requires assertions enabled')
    parser=argparse.ArgumentParser()
    parser.add_argument('--reuse-artifact-audit',action='store_true',help='Require an already passing outcome and recheck current artifact integration instead of repeating native DRC/build-map generation')
    parser.add_argument('--require-design',action='store_true')
    args=parser.parse_args()
    native=[os.environ.get('KICAD_PYTHON','/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3')]
    uv=shutil.which('uv') or str(Path.home()/'.local/bin/uv')
    cad=[os.environ['YETI_CAD_PYTHON']] if 'YETI_CAD_PYTHON' in os.environ else [uv,'run','--python','3.14.7','--with-requirements',str(ROOT/'requirements-audit.txt'),'python']
    py=[sys.executable]
    stages=[]
    if args.reuse_artifact_audit:
        outcome=json.loads((ROOT/'docs/audit/outcome.json').read_text())
        assert outcome['checks_passed'] and all(x['state']=='passed' for x in outcome['stages']),'Run the artifact audit successfully first'
        stages.extend([('current-document-links',py+['scripts/check_project_docs.py']),('current-artifact-integration',py+['scripts/check_project_integration.py'])])
    else:stages.append(('full-artifact-audit',py+['scripts/run_audit.py','--baseline','HEAD']))
    stages.extend([
        ('RF-native-lands',native+['scripts/study_yeti60_rf_lands.py']),
        ('RF-case-tolerances',cad+['scripts/study_yeti60_rf_remediation.py']),
        ('RF-copper-projection',native+['scripts/screen_yeti60_interference.py']),
        ('RF-plate-projection',cad+['scripts/check_yeti60_antenna_plate.py']),
        ('USB-contact-paths',native+['scripts/check_yeti60_signal_paths.py']),
        ('USB-path-fault-tests',native+['tests/audit/test_signal_paths.py']),
        ('AFE-SPICE',py+['scripts/simulate_yeti60_interference.py']),
        ('interference-fault-tests',native+['tests/audit/test_interference.py']),
        ('PH-continuous-withdrawal',cad+['scripts/study_e73_service.py']),
        ('readiness-fault-tests',cad+['tests/audit/test_e73_readiness.py']),
        ('readiness-disposition',py+['scripts/review_e73_readiness.py']),
    ])
    records=[]
    for name,command in stages:
        print(name+': running',flush=True);start=time.monotonic()
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        record=dict(stage=name,state='passed' if result.returncode==0 else 'failed',exit_code=result.returncode,seconds=round(time.monotonic()-start,2))
        if result.returncode:record['output_tail']=(result.stdout+result.stderr)[-5000:]
        records.append(record);print(name+': '+record['state'],flush=True)
        if result.returncode:break
    passed=all(x['state']=='passed' for x in records) and len(records)==len(stages)
    report=dict(status='executed-design-hold' if passed else 'execution-failed',checks_executed_successfully=passed,stages=records,manufacturing_released=False,physical_verification=False,disposition='docs/audit/e73-readiness.json',artifact_audit_reused=args.reuse_artifact_audit)
    (ROOT/'docs/audit/e73-review-run.json').write_text(json.dumps(report,indent=2)+'\n')
    if not passed:return 1
    readiness=json.loads((ROOT/'docs/audit/e73-readiness.json').read_text())
    report['status']='executed-design-hold' if readiness['status']=='hold' else 'executed-design-checks-passed'
    (ROOT/'docs/audit/e73-review-run.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],flush=True)
    return 2 if args.require_design and readiness['status']=='hold' else 0
if __name__=='__main__':raise SystemExit(main())
