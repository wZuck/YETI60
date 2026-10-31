#!/usr/bin/env python3
"""Verify acceptance evidence freshness; recorded design findings remain a hold."""
import argparse
import hashlib
import json
from pathlib import Path
from yeti60_acceptance_gates import summarize,design_and_pending_gates

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def fresh(mapping,root=ROOT):
    for name,digest in mapping.items():
        assert sha(root/name)==digest,'Stale acceptance evidence: '+name


def validate(report):
    assert report['execution_status']=='completed'
    expected=summarize(report['gates'])
    for key,value in expected.items():assert report[key]==value,'Acceptance state does not match evidence gates: '+key
    assert report['field_solver_performed'] is False
    assert set(report['variants'])=={'e73','raytac'}
    for record in report['variants'].values():
        assert record['CAD_checks_passed'] and record['firmware_build_and_host_checks_passed']
        if not report['physical_test_performed']:
            assert record['physical_acceptance']=='not-run' and record['RF_acceptance']=='not-run'
        if report['production_approved']:
            assert record['physical_acceptance']=='passed' and record['RF_acceptance']=='passed'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--require-accepted',action='store_true');parser.add_argument('--require-design',action='store_true');args=parser.parse_args()
    report=json.loads((ROOT/'docs/audit/acceptance.json').read_text());validate(report)
    fresh(report['source_sha256']);fresh(report['evidence_sha256']);fresh(report['outputs'])
    for filename in ['interference-layout.json','interference-analog.json','interference-plate.json',
                     'rf-remediation-candidate.json','rf-remediation-lands.json','USB-signal-paths.json']:
        data=json.loads((ROOT/'docs/audit'/filename).read_text());fresh(data['source_sha256']);fresh(data.get('outputs',{}))
        assert not data.get('physical_test_performed',data.get('physical_verification',False)) and not data['production_approved']
        for record in data.get('variants',{}).values():fresh(record.get('source_sha256',{}))
    for folder in [ROOT,ROOT/'variants/raytac']:
        data=json.loads((folder/'docs/audit/calibration.json').read_text())
        assert data['status']=='passed' and not data['physical_verification']
        fresh(data['source_sha256'],folder)
    read=lambda name:json.loads((ROOT/'docs/audit'/name).read_text())
    gates=design_and_pending_gates(read('interference-layout.json'),read('interference-plate.json'),read('USB-signal-paths.json'),
                                 {name:json.loads(((ROOT if name=='e73' else ROOT/'variants/raytac')/'docs/audit/calibration.json').read_text()) for name in ['e73','raytac']})
    assert report['gates']==gates,'Gate states differ from current test evidence'
    print('Acceptance evidence current; design review: '+report['design_review_status']+'; final acceptance: '+report['acceptance_status']+'. Physical and supplier evidence is separate.')
    return 2 if (args.require_accepted and report['acceptance_status']!='accepted') or (args.require_design and report['design_review_status']!='passed') else 0


if __name__=='__main__':raise SystemExit(main())
