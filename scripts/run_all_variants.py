#!/usr/bin/env python3
"""Audit both module alternatives in one checkout and check feature parity."""
import argparse
import csv
import hashlib
import importlib.util
import json
import os,shutil
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OPTIONS={'e73':ROOT,'raytac':ROOT/'variants/raytac'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_archive(path, module):
    with zipfile.ZipFile(path) as archive:
        manifest=json.loads(archive.read('manifest.json'))
    assert manifest.get('controller_module')==module, 'Manufacturing archive belongs to a different module'
    assert manifest['copper_layers']==['F.Cu','In1.Cu','In2.Cu','B.Cu']
    assert manifest['blind_drill_hits']==0 and manifest['placement_parts']==76
    return {'module':module,'sha256':sha(path),'copper_layers':4,'blind_drill_hits':0,'placements':76}


def parity():
    """Check each current design; shared behavior does not require identical code."""
    read=lambda p:json.loads((ROOT/p).read_text())
    ray=ROOT/'variants/raytac'
    native=read('hardware/ec60-nrf52840/audit-current.json')
    assert native['status']=='cad-checks-passed' and native['mcu_count']==1
    assert not native['unconnected_items'] and not native['failed_ground_pairs']
    archive=verify_archive(ROOT/'hardware/fabrication/yeti60-e73-p2-dfm-review.zip','E73-2G4M08S1C')
    candidate=read('variants/raytac/hardware/usb-short-route/audit/native-check.json')
    assert candidate['status']=='native-candidate-checks-passed'
    assert candidate['strict_DRC_errors']==candidate['unconnected_items']==candidate['schematic_parity_items']==0
    cam=read('variants/raytac/hardware/usb-short-route/audit/fabrication-check.json')
    assert cam['status']=='candidate-CAM-native-roundtrip-passed' and not cam['manufacturing_released']
    # The candidate's split PTH/NPTH/CAM/stencil package has its own native
    # round-trip checker; a historical 76-part ZIP cannot qualify this board.
    uv=shutil.which('uv') or str(Path.home()/'.local/bin/uv')
    cam_runtime=[os.environ['YETI_CAM_PYTHON']] if 'YETI_CAM_PYTHON' in os.environ else [uv,'run','--python','3.11','--with-requirements',str(ray/'requirements-cam.txt'),'python']
    subprocess.run(cam_runtime+['scripts/check_usb_short_fabrication.py'],cwd=ray,check=True)
    for folder in [ROOT,ray]:
        policy=json.loads((folder/'docs/audit/usb-event-policy.json').read_text())
        assert policy['status']=='passed' and len(policy['cases'])==11
        assert policy['configuration_zero_rejected'] and policy['synchronous_disable_before_upstream_notification']
        for name,digest in policy['source_sha256'].items():assert sha(folder/name)==digest,'Stale USB policy: '+name
    subprocess.run([sys.executable,'scripts/check_usb_short_firmware.py'],cwd=ray,check=True)
    with (ray/'hardware/usb-short-route/mainboard-purchase.csv').open() as stream:
        purchases=list(csv.DictReader(stream))
    required=sum(int(r['Required']) for r in purchases)
    stock=sum(int(r['Planned stock use']) for r in purchases)
    buy=sum(int(r['Net purchase']) for r in purchases)
    assert required==stock+buy==cam['fitted_placements']==75
    inventory=read('docs/audit/yeti60-inventory.json')
    assert inventory['required_mainboard_parts']==inventory['planned_stock_parts']+inventory['net_purchase_parts']==76
    readiness=read('docs/audit/e73-readiness.json')
    assert not readiness['manufacturing_released'] and not readiness['physical_verification']
    return {'controllers_per_keyboard':1,'keys':60,'built_ARM_targets':4,
            'shared_USB_charge_and_wired_priority_policy':True,
            'feature_parity':False,
            'differences':['E73 retains the old 1.2 mm / 29-mount plate and seven-wire PH harness',
                           'Raytac current candidate uses C04/NiZ 1.6 mm / 28-mount plate and nine-wire SH3 harness',
                           'E73 scanner/storage fault and waveform improvements are not yet at Raytac parity'],
            'variants':{'e73':{'placements':76,'mounts':29,'stock_parts':inventory['planned_stock_parts'],'purchase_parts':inventory['net_purchase_parts'],'manufacturing_package':archive,'design_status':readiness['status']},
                        'raytac':{'placements':required,'mounts':28,'stock_parts':stock,'purchase_parts':buy,'manufacturing_package':'variants/raytac/hardware/usb-short-route/fabrication/yeti60-raytac-candidate-gerbers.zip','design_status':'candidate-physical-and-supplier-qualification-open'}}}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--refresh-renders',action='store_true')
    parser.add_argument('--refresh-guide',action='store_true')
    parser.add_argument('--check-existing',action='store_true',help='Verify current reports and integration without rerunning both full audits')
    parser.add_argument('--baseline',default='HEAD')
    args=parser.parse_args();results={}
    # CAD outputs are shared and deterministic; run variants sequentially.
    for name,folder in OPTIONS.items():
        command=[sys.executable,'scripts/run_audit.py','--baseline',args.baseline]
        if args.refresh_renders:command.append('--refresh-renders')
        if args.refresh_guide:command.append('--refresh-guide')
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
            subprocess.run([sys.executable,'tests/audit/test_variant_packages.py'],cwd=ROOT,check=True)
            # A later variant must not invalidate evidence for the earlier one.
            for name,folder in OPTIONS.items():
                subprocess.run([sys.executable,'scripts/check_project_integration.py'],cwd=folder,check=True)
        except (AssertionError,KeyError,FileNotFoundError,zipfile.BadZipFile,subprocess.CalledProcessError) as failure:
            okay=False;error=str(failure)
    for folder in OPTIONS.values():
        spec=importlib.util.spec_from_file_location('inventory',folder/'scripts/run_audit.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.inventory()
    report={'status':'both-variant-checks-passed-production-incomplete' if okay else 'variant-checks-failed',
            'mode':'existing-reports-and-current-integration' if args.check_existing else 'full-audits-and-current-integration',
            'production_approved':False,'variants':results,'feature_parity':agreement,'error':error,
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'tests/audit/test_variant_packages.py']},
            'outcome_sha256':{r['audit']:sha(ROOT/r['audit']) for r in results.values()},
            'scope':'Independent current E73 and Raytac candidate checks; recorded maturity differences are not feature parity or physical/RF/SI acceptance'}
    (ROOT/'docs/audit/variants.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],flush=True)
    return 0 if okay else 1


if __name__=='__main__':
    raise SystemExit(main())
