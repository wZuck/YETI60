#!/usr/bin/env python3
"""Verify acceptance evidence freshness; recorded design findings remain a hold."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def fresh(mapping,root=ROOT):
    for name,digest in mapping.items():
        assert sha(root/name)==digest,'Stale acceptance evidence: '+name


def validate(report):
    assert report['execution_status']=='completed'
    assert report['acceptance_status']=='hold'
    assert report['production_approved'] is False
    assert report['physical_test_performed'] is False
    assert report['field_solver_performed'] is False
    assert len(report['open_gates'])>=4
    assert set(report['variants'])=={'e73','raytac'}
    for record in report['variants'].values():
        assert record['CAD_checks_passed'] and record['firmware_build_and_host_checks_passed']
        assert record['physical_acceptance']=='not-run'
        assert record['RF_acceptance']=='hold'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--require-accepted',action='store_true');args=parser.parse_args()
    report=json.loads((ROOT/'docs/audit/acceptance.json').read_text());validate(report)
    fresh(report['source_sha256']);fresh(report['evidence_sha256']);fresh(report['outputs'])
    for filename in ['interference-layout.json','interference-analog.json','interference-plate.json']:
        data=json.loads((ROOT/'docs/audit'/filename).read_text());fresh(data['source_sha256']);fresh(data.get('outputs',{}))
        assert not data['physical_test_performed'] and not data['production_approved']
        for record in data.get('variants',{}).values():fresh(record.get('source_sha256',{}))
    print('Acceptance evidence current; CAD/build/model execution passed; RF design findings and physical acceptance remain ON HOLD.')
    return 2 if args.require_accepted else 0


if __name__=='__main__':raise SystemExit(main())
