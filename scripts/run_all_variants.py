#!/usr/bin/env python3
"""Audit both module alternatives in one checkout and check feature parity."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
OPTIONS={'e73':ROOT,'raytac':ROOT/'variants/raytac'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parity():
    records={}
    for name,folder in OPTIONS.items():
        read=lambda p:json.loads((folder/p).read_text())
        with (folder/'hardware/bom/mainboard.csv').open() as source:
            parts=list(csv.DictReader(source))
        records[name]={'parts':parts,'keys':read('docs/audit/yeti60-key-geometry.json'),
                       'fit':read('docs/audit/yeti60-assembly.json'),
                       'inventory':read('docs/audit/yeti60-inventory.json'),
                       'board':read('hardware/ec60-nrf52840/audit-current.json')}
        assert records[name]['board']['mcu_count']==1 and not records[name]['board']['unconnected_items']
        assert records[name]['board']['status']=='cad-checks-passed'
    a,b=records['e73'],records['raytac']
    assert [r for r in a['parts'] if r['References']!='U1']==[r for r in b['parts'] if r['References']!='U1'], 'Non-module BOM diverged'
    assert a['fit']['mounting_hole_matches']==b['fit']['mounting_hole_matches'], 'Mounting geometry diverged'
    assert a['fit']['active_key_positions']==b['fit']['active_key_positions'], 'Plate/key layout diverged'
    assert a['fit']['selected_battery']==b['fit']['selected_battery'], 'Shared battery specification diverged'
    for option in [a,b]:
        assert option['inventory']['planned_stock_parts']==10 and option['inventory']['net_purchase_parts']==66
        assert len(option['keys']['matches'])==60
    return {'controllers_per_keyboard':1,'keys':60,'mounts':29,'non_module_BOM_identical':True,
            'shared_case_and_battery':True,'stock_use_per_selected_keyboard':10,'mainboard_to_buy':66}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--refresh-renders',action='store_true')
    parser.add_argument('--check-existing',action='store_true',help='Verify current reports and integration without rerunning both full audits')
    parser.add_argument('--baseline',default='52b8d56be0b162c7f9585936349c08ddcb7c338f')
    args=parser.parse_args();results={}
    # CAD outputs are shared and deterministic; run variants sequentially.
    for name,folder in OPTIONS.items():
        command=[sys.executable,'scripts/run_audit.py','--baseline',args.baseline]
        if args.refresh_renders:command.append('--refresh-renders')
        if args.check_existing:
            outcome=json.loads((folder/'docs/audit/outcome.json').read_text())
            code=0 if outcome['checks_passed'] and all(s['state']=='passed' for s in outcome['stages']) else 1
            print(name+': checking current evidence',flush=True)
        else:
            print(name+': full audit',flush=True)
            code=subprocess.run(command,cwd=folder).returncode
        results[name]={'exit_code':code,'audit':str((folder/'docs/audit/outcome.json').relative_to(ROOT))}
    okay=all(r['exit_code']==0 for r in results.values());agreement=None;error=None
    if okay:
        try:
            agreement=parity()
            # A later variant must not invalidate evidence for the earlier one.
            for name,folder in OPTIONS.items():
                subprocess.run([sys.executable,'scripts/check_project_integration.py'],cwd=folder,check=True)
        except (AssertionError,subprocess.CalledProcessError) as failure:
            okay=False;error=str(failure)
    for folder in OPTIONS.values():
        spec=importlib.util.spec_from_file_location('inventory',folder/'scripts/run_audit.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.inventory()
    report={'status':'both-variant-checks-passed-production-incomplete' if okay else 'variant-checks-failed',
            'mode':'existing-reports-and-current-integration' if args.check_existing else 'full-audits-and-current-integration',
            'production_approved':False,'variants':results,'feature_parity':agreement,'error':error,
            'source_sha256':{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},
            'outcome_sha256':{r['audit']:sha(ROOT/r['audit']) for r in results.values()},
            'scope':'Both complete designs in this branch; no physical acceptance or RF/SI certification'}
    (ROOT/'docs/audit/variants.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],flush=True)
    return 0 if okay else 1


if __name__=='__main__':
    raise SystemExit(main())
