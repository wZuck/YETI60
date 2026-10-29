#!/usr/bin/env python3
"""Build pinned YETI60 ZMK targets and record source/binary provenance."""
import argparse, hashlib, json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'zmkfirmware/zmk-build-arm@sha256:edb1c953438c6f720ddb79c3762f3972013b7fbbaf4fff3592fc869983e7afc5'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def record(address, kind, data):
    payload=bytes([len(data)])+address.to_bytes(2,'big')+bytes([kind])+data
    return ':'+(payload+bytes([-sum(payload)&255])).hex().upper()

def e73_hex(payload):
    lines=payload.decode().splitlines()
    assert lines[-1]==':00000001FF'
    # NFCPINS.PROTECT=0 releases P0.09/P0.10. Reserved bits remain erased.
    return ('\n'.join(lines[:-1]+[record(0,4,bytes.fromhex('1000')),
            record(0x120c,0,bytes.fromhex('FEFFFFFF')),lines[-1]])+'\n').encode()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, default=Path.home()/'.cache/yeti60-zmk-workspace')
    args = parser.parse_args(); workspace = args.workspace.resolve()
    if not (workspace/'zephyr').exists():
        raise SystemExit('Initialize the pinned west workspace described in firmware/target/README.md first')
    base = ['docker','run','--rm','-v',f'{workspace}:/work','-v',f'{ROOT}:/yeti','-w','/work',IMAGE]
    # Local --reference/--shared clones need their object stores at the same path.
    object_roots = set()
    for alternates in workspace.rglob('objects/info/alternates'):
        for path in alternates.read_text().splitlines():
            object_roots.add(Path(path).parents[2])
    for directory in sorted(object_roots):
        base[3:3] = ['-v', f'{directory}:{directory}:ro']
    assert sha(workspace/'config/west.yml') == sha(ROOT/'firmware/target/config/west.yml'), 'Workspace manifest differs from the committed lock'
    projects = subprocess.check_output(base+['west','list','-f','{path}|{revision}'],text=True).splitlines()
    revisions = {}
    for project in projects:
        name, locked = project.split('|')
        if name == 'config': continue
        directory = workspace/name
        assert not subprocess.check_output(['git','-C',str(directory),'status','--porcelain','--untracked-files=no']), 'Modified dependency: '+name
        revisions[name] = subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
        assert revisions[name] == locked, 'Dependency revision differs from lock: '+name
    assert revisions['zmk']=='0862fc0f8c864834007986efcaf52f292ea6d37d'
    records = {}
    for variant in ['normal','calibrator']:
        command = base+['west','build','-p','always','-s','zmk/app','-d',f'/yeti/.firmware-work/{variant}','-b','yeti60','--','-DZephyr_DIR=/work/zephyr/share/zephyr-package/cmake','-DZMK_CONFIG=/yeti/firmware/target/config','-DZMK_EXTRA_MODULES=/yeti/firmware/target','-DBOARD_ROOT=/yeti/firmware/target']
        if variant=='calibrator': command += ['-DEXTRA_CONF_FILE=/yeti/firmware/target/config/calibrator.conf','-DEXTRA_DTC_OVERLAY_FILE=/yeti/firmware/target/config/calibrator.overlay']
        work=ROOT/'.firmware-work';work.mkdir(exist_ok=True)
        with (work/(variant+'.log')).open('w') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        built=work/variant/'zephyr'; destination=ROOT/'firmware/releases'/variant;destination.mkdir(parents=True,exist_ok=True)
        for extension in ['hex','bin','elf']:
            payload = (built/('zmk.'+extension)).read_bytes()
            if extension == 'hex': payload = e73_hex(payload)
            (destination/('yeti60-e73.'+extension)).write_bytes(payload)
            obsolete=destination/('yeti60.'+extension)
            if obsolete.exists():obsolete.unlink()
        config=(built/'.config').read_text();tree=(built/'zephyr.dts').read_text()
        for option in ['CONFIG_NFCT_PINS_AS_GPIOS=y','CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC=y']:
            assert option in config,option
        assert 'CONFIG_SOC_DCDC_NRF52X=y' not in config and 'CONFIG_SOC_DCDC_NRF52X_HV=y' not in config
        reg1=tree.split('reg1: regulator@',1)[1].split('};',1)[0]
        assert 'regulator-initial-mode = < 0x0 >' in reg1
        records[variant]={'outputs':{str(p.relative_to(ROOT)):sha(p) for p in destination.glob('yeti60-e73.*')},'configuration_sha256':sha(built/'.config'),'devicetree_sha256':sha(built/'zephyr.dts'),
                          'E73_configuration':{'LF_clock':'internal-RC','REG1':'LDO','REG0_DCDC':False,'NFC_pins':'GPIO','HEX_NFCPINS_UICR':0xfffffffe}}
    sources=[*sorted((ROOT/'firmware/target').rglob('*')),*sorted((ROOT/'firmware/yeti60').glob('*.[ch]')),Path(__file__).resolve(),ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb']
    report={'status':'built','board':'yeti60','framework':'ZMK/Zephyr','container':IMAGE,'dependencies':revisions,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources if p.is_file() and p.suffix != '.md'},'variants':records,'physical_verification':False,'calibration_required':True,'flash_method':'SWD, application at 0x0; no UF2 bootloader assumed'}
    (ROOT/'docs/audit/yeti60-target-build.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Both YETI60 target variants built; physical validation remains pending')
if __name__=='__main__':main()
