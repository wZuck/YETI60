#!/usr/bin/env python3
"""Build and host-check the E73 corner firmware in an isolated project root.

Normal publication requires a routed native PCB. --prepare-only verifies the
candidate pin contract and prepares the workspace without publishing images.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from yeti60_build_environment import workspace_path, require_workspace

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'hardware/e73-hhkb-corner'
WORK = ROOT/'.assembly-work/e73-corner/firmware-build'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_sources(report):
    for name,digest in report['source_sha256'].items():
        assert sha(ROOT/name)==digest, ('Stale design evidence',name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,default=workspace_path())
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--development-build',action='store_true',help='Build and test only in ignored workspace; never publish images')
    args=parser.parse_args()
    if not args.prepare_only:
        # Fail before compilation if the documented audit runtime is missing.
        import numpy, matplotlib  # noqa: F401
    workspace=args.workspace.expanduser().resolve()
    require_workspace(workspace,ROOT/'firmware/target/config/west.yml')
    native_path=BASE/'audit/placement-check.json'
    native=json.loads(native_path.read_text());verify_sources(native)
    assert not (args.prepare_only and args.development_build)
    if not args.prepare_only and not args.development_build:
        assert native['electrical_routing_complete'], 'Finish native routing before publishing candidate firmware'
        for name in ['USB-reference','corner-fit']:
            report=json.loads((BASE/'audit'/f'{name}.json').read_text());verify_sources(report)
            if name=='USB-reference':assert report['checks_passed'] and report['whole_ground_network_connected']
            else:assert report['status']=='bounded-corner-body-proxies-passed-harness-and-RF-open'
    copied={}
    def copy(source,target):
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        copied[str(source.relative_to(ROOT))]=sha(source)
    copied[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
    copied['requirements-audit.txt']=sha(ROOT/'requirements-audit.txt')
    for rel in ['firmware/target','firmware/yeti60','tests/yeti60','tests/audit']:
        for source in sorted((ROOT/rel).rglob('*')):
            local=source.relative_to(ROOT/rel)
            if not source.is_file() or any(q in ['third_party','__pycache__','.git']for q in local.parts):continue
            copy(source,WORK/rel/local)
    actions=['build_yeti60_firmware.py','check_yeti60_target.py','simulate_yeti60_firmware.py',
             'test_yeti60_calibration.py','test_yeti60_usb_events.py','test_yeti60_recovery.py',
             'test_yeti60_gpio_modes.py','test_yeti60_scan_control.py','test_yeti60_key_pipeline.py',
             'test_yeti60_nvs_powercut.py','study_yeti60_analog_waveform.py','check_yeti60_firmware_suite.py']
    # Copy the actual local import closure. Unrelated routing edits must not
    # invalidate a firmware build or become false firmware source evidence.
    pending=actions+['generate_yeti60_pin_contract.py'];seen=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        seen.add(name);source=ROOT/'scripts'/name;copy(source,WORK/'scripts'/name)
        for node in ast.walk(ast.parse(source.read_text())):
            names=([node.module]if isinstance(node,ast.ImportFrom)and node.module else
                   [q.name for q in node.names]if isinstance(node,ast.Import)else [])
            for module in names:
                local=module.split('.')[0]+'.py'
                if (ROOT/'scripts'/local).is_file():pending.append(local)
    destination=WORK/'hardware/ec60-nrf52840'
    for source in BASE.iterdir():
        if source.is_file() and source.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym','.xml','.json']:
            copy(source,destination/source.name)
    copy(ROOT/'hardware/ec60-nrf52840/pinmap.json',destination/'pinmap.json')
    from yeti60_calibration_contract import INPUTS
    for rel in INPUTS:
        if rel.startswith('mechanical/'):copy(ROOT/rel,WORK/rel)
    copy(ROOT/'docs/testing/analog-waveform-inputs.json',WORK/'docs/testing/analog-waveform-inputs.json')
    (WORK/'docs/audit').mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,YETI60_ZMK_WORKSPACE=str(workspace))
    subprocess.run([sys.executable,str(WORK/'scripts/generate_yeti60_pin_contract.py'),'--check'],check=True,env=env)
    if args.prepare_only:
        result=dict(status='pin-contract-prepared-no-firmware-built',manufacturing_released=False,
            physical_verification=False,firmware_built=False,native_routing_complete=native['electrical_routing_complete'],
            unconnected_items=native['unconnected_items'],source_sha256=copied,
            native_evidence_sha256=sha(native_path),workspace=str(WORK.relative_to(ROOT)))
        (WORK/'preflight.json').write_text(json.dumps(result,indent=2)+'\n')
        print(result['status']);return
    for name in actions:
        print('Running '+name,flush=True)
        subprocess.run([sys.executable,str(WORK/'scripts'/name)],check=True,env=env)
    for name in ['test_target.py','test_firmware_suite.py']:
        subprocess.run([sys.executable,str(WORK/'tests/audit'/name)],check=True,env=env)
    for name,digest in copied.items():assert sha(ROOT/name)==digest,('Source changed during build',name)
    if args.development_build:
        result=dict(status='development-normal-calibrator-built-host-suite-passed',
            manufacturing_released=False,physical_verification=False,firmware_published=False,
            native_routing_complete=native['electrical_routing_complete'],
            source_sha256=copied,native_evidence_sha256=sha(native_path),
            source_PCB_sha256=copied[str((BASE/'EC60-nRF52840.kicad_pcb').relative_to(ROOT))])
        (WORK/'development-build.json').write_text(json.dumps(result,indent=2)+'\n')
        print(result['status']);return
    published=BASE/'firmware';published.mkdir(exist_ok=True)
    outputs={};evidence={}
    for variant in ['normal','calibrator']:
        for ext in ['hex','bin']:
            source=WORK/'firmware/releases'/variant/('yeti60-e73.'+ext)
            target=published/'releases'/variant/source.name
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
            outputs[str(target.relative_to(ROOT))]=sha(target)
    names=['yeti60-target-build','yeti60-target-check','yeti60-firmware-simulation','calibration',
           'gpio-mode-policy','scan-control','key-pipeline','nvs-powercut','firmware-recovery',
           'analog-waveform','usb-event-policy','firmware-suite']
    for name in names:
        source=WORK/'docs/audit'/f'{name}.json';target=published/f'{name}.json'
        shutil.copyfile(source,target);evidence[str(target.relative_to(ROOT))]=sha(target)
    result=dict(status='candidate-normal-calibrator-built-host-suite-passed',physical_verification=False,manufacturing_released=False,
        canonical_releases_modified=False,source_sha256=copied,published_outputs=outputs,evidence=evidence,
        native_evidence_sha256=sha(native_path),source_PCB_sha256=sha(BASE/'EC60-nRF52840.kicad_pcb'),
        original_report_path_basis='Copied evidence paths are relative to the isolated firmware-build root; map canonical PCB/netlist paths to this corner candidate. ELF files remain in the ignored build root.',
        limits=['Host and linked-binary checks only; no physical USB/BLE/EC, battery, thermal or range acceptance'])
    (published/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'])


if __name__=='__main__':main()
