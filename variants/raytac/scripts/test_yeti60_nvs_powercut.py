#!/usr/bin/env python3
"""Exercise pinned NVS recovery on a bounded NOR model; no NVMC execution."""
import hashlib,json,re,shutil,subprocess,sys,tempfile
from pathlib import Path
from yeti60_build_environment import workspace_path
from yeti60_host_atomics import prepare
from test_yeti60_scan_control import function
from yeti60_nvs_contract import verify
ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=workspace_path()
REV='10ba6d0cb38bc3d258775d27982f707599320085'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    build_path=ROOT/'docs/audit/yeti60-target-build.json';build=json.loads(build_path.read_text())
    assert build['dependencies']['zephyr']==REV
    for rel,digest in build['source_sha256'].items():
        assert sha(ROOT/rel)==digest,('Stale compiled source',rel)
    record=build['variants']['normal'];folder=ROOT/'.firmware-work/normal/zephyr'
    config_path=folder/'.config';dts_path=folder/'zephyr.dts'
    assert sha(config_path)==record['configuration_sha256'] and sha(dts_path)==record['devicetree_sha256']
    config=config_path.read_text()
    for option in ['CONFIG_NVS','CONFIG_SETTINGS_NVS']:
        assert option+'=y' in config
    for option in ['CONFIG_NVS_DATA_CRC','CONFIG_NVS_LOOKUP_CACHE','CONFIG_NVS_INIT_BAD_MEMORY_REGION','CONFIG_SOC_FLASH_NRF_EMULATE_ONE_BYTE_WRITE_ACCESS']:
        assert option+'=y' not in config
    def number(name):return int(re.search(r'^'+name+r'=(\d+)$',config,re.M).group(1))
    sys.path.insert(0,str(WORKSPACE/'zephyr/scripts/dts/python-devicetree/src'))
    from devicetree.dtlib import DT
    dt=DT(str(dts_path));flash=dt.label2node['flash0'];storage=dt.label2node['storage_partition']
    offset,partition_bytes=storage.props['reg'].to_nums()
    erase=flash.props['erase-block-size'].to_num();write=flash.props['write-block-size'].to_num()
    sector=erase*number('CONFIG_SETTINGS_NVS_SECTOR_SIZE_MULT')
    sectors=min(number('CONFIG_SETTINGS_NVS_SECTOR_COUNT'),partition_bytes//sector)
    assert (offset,partition_bytes,sector,sectors,write)==(0xf0000,0x10000,4096,8,4)
    paths=['subsys/fs/nvs/nvs.c','subsys/fs/nvs/nvs_priv.h','include/zephyr/fs/nvs.h','lib/crc/crc8_sw.c','lib/crc/crc32_sw.c','subsys/settings/src/settings_nvs.c','drivers/flash/soc_flash_nrf.c']
    upstream={p:subprocess.check_output(['git','-C',str(WORKSPACE/'zephyr'),'show',REV+':'+p],text=True) for p in paths}
    cases=[];negative=[]
    with tempfile.TemporaryDirectory(prefix='yeti-nvs-powercut-') as directory:
        temp=Path(directory);include=temp/'include'
        atomic_hashes=prepare(WORKSPACE,include)
        (include/'scanner_load.inc').write_text(function((ROOT/'firmware/target/src/scanner.c').read_text(),'load_calibration'))
        for path in ['zephyr/drivers/flash.h','zephyr/sys/crc.h','zephyr/logging/log.h','zephyr/kernel.h','zephyr/device.h','zephyr/toolchain.h']:
            target=include/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('/* Interfaces supplied by forced nvs_shim.h include. */\n')
        for source,target in [('subsys/fs/nvs/nvs.c','nvs.c'),('subsys/fs/nvs/nvs_priv.h','nvs_priv.h'),('include/zephyr/fs/nvs.h','include/zephyr/fs/nvs.h'),('lib/crc/crc8_sw.c','crc8.c'),('lib/crc/crc32_sw.c','crc32.c')]:
            path=temp/target;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(upstream[source])
        (include/'nvs_profile.h').write_text('\n'.join('#define '+key+' '+str(value) for key,value in dict(NVS_OFFSET=offset,SECTOR_BYTES=sector,SECTOR_COUNT=sectors,WRITE_BYTES=write,CALIBRATION_VERSION=record['calibration_version']).items())+'\n')
        binary=temp/'powercut'
        command=[shutil.which('clang'),'-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-variable','-Wno-sign-compare','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-include',str(ROOT/'tests/yeti60/nvs_shim.h'),'-I',str(include),'-I',str(ROOT/'tests/yeti60'),'-I',str(ROOT/'firmware/yeti60'),str(temp/'nvs.c'),str(temp/'crc8.c'),str(temp/'crc32.c'),str(ROOT/'firmware/yeti60/calibration.c'),str(ROOT/'tests/yeti60/nvs_powercut.c'),'-o',str(binary)]
        subprocess.run(command,check=True)
        for scenario in ['first-save','rewrite','legacy-replacement','garbage-collection','recovery-cut']:
            result=subprocess.run([str(binary),scenario],text=True,capture_output=True)
            assert result.returncode==0,(scenario,result.stdout,result.stderr)
            details=json.loads(result.stdout.splitlines()[-1]);cases.append(details)
            print(result.stdout,end='',flush=True)
        original=upstream['subsys/fs/nvs/nvs.c']
        payload='\trc = nvs_flash_data_wrt(fs, data, len, true);\n\tif (rc) {\n\t\treturn rc;\n\t}\n'
        assert original.count(payload)==1
        metadata_first=original.replace(payload,'').replace('\trc = nvs_flash_ate_wrt(fs, &entry);',
            '\trc = nvs_flash_ate_wrt(fs, &entry);\n\tif (rc) return rc;\n\trc = nvs_flash_data_wrt(fs, data, len, true);')
        lost_sentinel=original.replace('(wlk_prev_addr == gc_prev_addr) && gc_ate.len',
            '(wlk_prev_addr == gc_prev_addr) && gc_ate.len && gc_ate.id != 10')
        for name,mutant,scenario in [('commit-before-payload',metadata_first,'rewrite'),('omit-live-GC-sentinel',lost_sentinel,'garbage-collection')]:
            assert mutant!=original,name
            (temp/'nvs.c').write_text(mutant);subprocess.run(command,check=True)
            result=subprocess.run([str(binary),scenario],text=True,capture_output=True)
            assert result.returncode!=0 and 'Assertion' in result.stderr,(name,result.stdout,result.stderr)
            negative.append(dict(case=name,exit_code=result.returncode,output=result.stderr.strip()[-600:]))
    files=[Path(__file__),ROOT/'scripts/yeti60_host_atomics.py',ROOT/'scripts/test_yeti60_scan_control.py',ROOT/'scripts/yeti60_nvs_contract.py',ROOT/'tests/yeti60/nvs_shim.h',ROOT/'tests/yeti60/nvs_powercut.c',ROOT/'firmware/target/src/scanner.c',ROOT/'firmware/yeti60/calibration.c',ROOT/'firmware/yeti60/calibration.h',ROOT/'firmware/yeti60/board_pins.h',ROOT/'firmware/target/config/west.yml']
    report=dict(status='passed',physical_verification=False,execution='Unmodified pinned Zephyr NVS/public-private headers, CRC/atomic code, actual target calibration loader under ASan/UBSan; modeled sequential NOR word writes/partial page erases, mutexes and reboot; no NVMC, RTOS, BLE or electrical power execution',
        cases=cases,total_cut_trials=sum(c['trials'] for c in cases),
        rejected_mutants=negative,post_recovery_resave_verified=True,opaque_unrelated_sentinel_preserved=True,
        profile=dict(partition_offset=offset,partition_bytes=partition_bytes,sector_bytes=sector,sectors=sectors,NVS_bytes=sector*sectors,write_bytes=write,global_NVS_CRC=False,calibration_version=record['calibration_version']),
        cut_patterns=['before next four-byte unit','first byte of unit','first two bytes','first three bytes','selected 0x55 bits','selected 0xaa bits','after final commit before acknowledgement'],
        target_build_manifest_sha256=sha(build_path),resolved_configuration_sha256=sha(config_path),resolved_devicetree_sha256=sha(dts_path),
        upstream_revision=REV,upstream_sha256={**atomic_hashes,**{p:hashlib.sha256(data.encode()).hexdigest() for p,data in upstream.items()}},
        recovery_cut_seed='0x55 selected-bit cut midway through one dirty-page erase; second cut swept through every modeled recovery unit',
        not_verified=['Arbitrary erase/program bit ordering, unbounded successive cuts, real NVMC timing/voltage or flash endurance','Complete settings name allocation/backend operations or actual Bluetooth bonds/HID','Physical battery/charger brownout, radio-synchronized flash scheduling or on-device recovery'],
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in files})
    verify(report,build,sha(build_path))
    (ROOT/'docs/audit/nvs-powercut.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Modeled NVS cut/recovery trials passed:',report['total_cut_trials'])
    print('Rejected NVS ordering/GC mutants:',len(negative))
if __name__=='__main__':main()
