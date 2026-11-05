#!/usr/bin/env python3
"""Build pinned YETI60 ZMK targets and record source/binary provenance."""
import argparse, hashlib, json, subprocess, re, sys
from yeti60_calibration_contract import configuration, version
from yeti60_recovery_contract import check_recovery_dts
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'zmkfirmware/zmk-build-arm@sha256:edb1c953438c6f720ddb79c3762f3972013b7fbbaf4fff3592fc869983e7afc5'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, default=Path.home()/'.cache/yeti60-zmk-workspace')
    args = parser.parse_args(); workspace = args.workspace.resolve()
    sys.path.insert(0,str(workspace/'zephyr/scripts/dts/python-devicetree/src'))
    from devicetree import dtlib
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
            if extension == 'hex': payload = payload.replace(b'\r\n', b'\n')
            (destination/('yeti60-raytac.'+extension)).write_bytes(payload)
            obsolete=destination/('yeti60.'+extension)
            if obsolete.exists():obsolete.unlink()
        options=configuration((built/'.config').read_text())
        commands=json.loads((work/variant/'compile_commands.json').read_text())
        scanners=[c for c in commands if c['file'].endswith('/firmware/target/src/scanner.c')]
        assert len(scanners)==1
        match=re.search(r'-DYETI_CALIBRATION_VERSION=(0x[0-9a-f]{8})\b',scanners[0]['command'])
        assert match and match.group(1)==version(ROOT,options),'Linked scan calibration contract differs'
        config_text=(built/'.config').read_text()
        assert 'CONFIG_ZMK_BLE_CLEAR_BONDS_ON_START=y' not in config_text
        clock_hz=int(re.search(r'^CONFIG_SYS_CLOCK_HW_CYCLES_PER_SEC=(\d+)$',config_text,re.M).group(1))
        queue_size=int(re.search(r'^CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE=(\d+)$',config_text,re.M).group(1))
        assert queue_size==128 and 'CONFIG_ATOMIC_OPERATIONS_BUILTIN=y' in config_text
        assert '# CONFIG_NVS_DATA_CRC is not set' in config_text,'Global NVS CRC changes need a settings migration review'
        records[variant]={'outputs':{str(p.relative_to(ROOT)):sha(p) for p in destination.glob('yeti60-raytac.*')},'configuration_sha256':sha(built/'.config'),'devicetree_sha256':sha(built/'zephyr.dts'),
                         'calibration_version':match.group(1),'calibration_scan_configuration':options,'diagnostic_clock_hz':clock_hz,'kscan_event_queue_size':queue_size,'builtin_atomics':True,'calibration_record_bytes':308,'global_NVS_data_CRC':False,
                         'recovery_binding':check_recovery_dts(dtlib.DT(str(built/'zephyr.dts')))}
    assert records['normal']['calibration_version']==records['calibrator']['calibration_version'],'Normal and calibrator thresholds would be incompatible'
    sources=[*sorted((ROOT/'firmware/target').rglob('*')),*sorted((ROOT/'firmware/yeti60').glob('*.[ch]')),Path(__file__).resolve(),ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb']
    sources += [ROOT/'scripts/yeti60_calibration_contract.py',ROOT/'scripts/yeti60_recovery_contract.py']
    report={'status':'built','board':'yeti60','framework':'ZMK/Zephyr','container':IMAGE,'dependencies':revisions,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources if p.is_file() and p.suffix != '.md'},'variants':records,'physical_verification':False,'calibration_required':True,'flash_method':'SWD, application at 0x0; no UF2 bootloader assumed'}
    (ROOT/'docs/audit/yeti60-target-build.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Both YETI60 target variants built; physical validation remains pending')
if __name__=='__main__':main()
