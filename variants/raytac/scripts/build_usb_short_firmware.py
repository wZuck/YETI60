#!/usr/bin/env python3
"""Rebuild candidate firmware in isolation; preserve canonical releases untouched."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/usb-short-route';WORK=ROOT/'.assembly-work/usb-short-build'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--host-tests-only',action='store_true',help='Recheck existing ARM sources/artifacts, rerun host tests and republish evidence without compilation');args=parser.parse_args()
    native=json.loads((BASE/'audit/native-check.json').read_text());geometry=json.loads((BASE/'audit/geometry-check.json').read_text())
    assert native['status']=='native-candidate-checks-passed' and geometry['status']=='local-header-fit-and-reference-passed'
    for p,h in native['source_sha256'].items():assert sha(ROOT/p)==h,'Stale native evidence: '+p
    for p,h in geometry['source_sha256'].items():assert sha(ROOT/p)==h,'Stale geometry evidence: '+p
    # The firmware uses the locked west workspace, not the documentation link
    # target/third_party/zmk. Never copy a Git checkout's metadata into provenance.
    upstream=WORK/'firmware/target/third_party'
    if upstream.is_symlink():upstream.unlink()
    elif upstream.exists():shutil.rmtree(upstream)
    for rel in ['firmware/target','firmware/yeti60','tests/yeti60']:
        ignore=shutil.ignore_patterns('third_party','__pycache__') if rel=='firmware/target' else shutil.ignore_patterns('__pycache__')
        shutil.copytree(ROOT/rel,WORK/rel,dirs_exist_ok=True,ignore=ignore)
    dest=WORK/'hardware/ec60-nrf52840';dest.mkdir(parents=True,exist_ok=True)
    for p in BASE.iterdir():
        if p.is_file() and p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym','.json','.xml']:shutil.copyfile(p,dest/p.name)
    shutil.copyfile(ROOT/'hardware/ec60-nrf52840/pinmap.json',dest/'pinmap.json')
    scripts=['build_yeti60_firmware.py','generate_yeti60_pin_contract.py','check_yeti60_target.py','simulate_yeti60_firmware.py','test_yeti60_calibration.py','test_yeti60_gpio_modes.py','test_yeti60_scan_control.py','test_yeti60_key_pipeline.py','test_yeti60_nvs_powercut.py','yeti60_key_pipeline_contract.py','yeti60_scan_control_contract.py','yeti60_nvs_contract.py','yeti60_host_atomics.py','yeti60_calibration_contract.py','yeti60_recovery_contract.py'];(WORK/'scripts').mkdir(exist_ok=True);(WORK/'docs/audit').mkdir(parents=True,exist_ok=True)
    for name in scripts:shutil.copyfile(ROOT/'scripts'/name,WORK/'scripts'/name)
    actions=[('generate_yeti60_pin_contract.py',['--check'])]
    if not args.host_tests_only:actions.append(('build_yeti60_firmware.py',[]))
    # The checker rejects changed firmware/board inputs or altered existing images
    # before host-only publication. This mode cannot bless a stale ARM build.
    actions.extend((name,[]) for name in ['check_yeti60_target.py','simulate_yeti60_firmware.py','test_yeti60_calibration.py','test_yeti60_gpio_modes.py','test_yeti60_scan_control.py','test_yeti60_key_pipeline.py','test_yeti60_nvs_powercut.py'])
    for name,options in actions:subprocess.run([sys.executable,str(WORK/'scripts'/name),*options],check=True)
    pub=BASE/'firmware';pub.mkdir(exist_ok=True);build=json.loads((WORK/'docs/audit/yeti60-target-build.json').read_text());outputs={};not_published={}
    for variant in ['normal','calibrator']:
        for ext in ['hex','bin','elf']:
            rel=Path('firmware/releases')/variant/('yeti60-raytac.'+ext);source=WORK/rel
            if ext=='elf':not_published[str(rel)]={'sha256':sha(source),'reason':'Retained in ignored build workspace; checked by target checker; rebuild for debugging'};continue
            target=pub/'releases'/variant/source.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);outputs[str(target.relative_to(ROOT))]=sha(target)
    evidence={}
    for source,name in [('yeti60-target-build.json','build.json'),('yeti60-target-check.json','target-check.json'),('yeti60-firmware-simulation.json','simulation.json'),('calibration.json','calibration.json'),('gpio-mode-policy.json','gpio-mode-policy.json'),('scan-control.json','scan-control.json'),('key-pipeline.json','key-pipeline.json'),('nvs-powercut.json','nvs-powercut.json'),('yeti60-firmware-trace.csv','trace.csv')]:
        target=pub/name;shutil.copyfile(WORK/'docs/audit'/source,target);evidence[str(target.relative_to(ROOT))]=sha(target)
    sources={}
    for rel,h in build['source_sha256'].items():
        target='hardware/usb-short-route/EC60-nRF52840.kicad_pcb' if rel=='hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb' else rel
        assert sha(ROOT/target)==h,('Build input drifted',target);sources[target]=h
    sources['hardware/usb-short-route/netlist.xml']=sha(BASE/'netlist.xml');sources['scripts/build_usb_short_firmware.py']=sha(Path(__file__))
    result={'status':'candidate-normal-and-calibrator-built-and-host-checked','physical_verification':False,'canonical_releases_modified':False,'source_sha256':sources,'published_outputs':outputs,'evidence':evidence,'unpublished_build_outputs':not_published,'original_report_path_basis':'All paths inside copied build/target/simulation/calibration reports are relative to the ignored .assembly-work/usb-short-build directory; this manifest maps published files to the canonical variant root','native_acceptance_sha256':sha(BASE/'audit/native-check.json'),'local_geometry_acceptance_sha256':sha(BASE/'audit/geometry-check.json')}
    (pub/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');print('Candidate normal/calibrator HEX and BIN published locally; no physical execution claimed')
if __name__=='__main__':main()
