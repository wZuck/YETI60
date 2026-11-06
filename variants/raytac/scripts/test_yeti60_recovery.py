#!/usr/bin/env python3
"""Exercise the actual CMake fingerprint and pinned ZMK gesture implementation."""
import hashlib,json,re,shutil,subprocess,sys,tempfile
from pathlib import Path
from yeti60_build_environment import workspace_path
from yeti60_calibration_contract import INPUTS,OPTIONS,version

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=workspace_path()
REV='0862fc0f8c864834007986efcaf52f292ea6d37d'
IMAGE='zmkfirmware/zmk-build-arm@sha256:edb1c953438c6f720ddb79c3762f3972013b7fbbaf4fff3592fc869983e7afc5'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    upstream=subprocess.check_output(['git','-C',str(WORKSPACE/'zmk'),'show',REV+':app/src/behaviors/behavior_tap_dance.c'],text=True)
    options=dict(zip(OPTIONS,['4','30','30000','y']))
    work=ROOT/'.firmware-work';work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='recovery-',dir=work) as folder:
        temp=Path(folder);baseline=temp/'baseline'
        for rel in INPUTS:
            target=baseline/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,target)
        fixture=baseline/'firmware/target/config/yeti60.keymap';shutil.copyfile(ROOT/'firmware/target/config/yeti60.keymap',fixture)
        cases=[]
        mutations=[('same',None,None),('scanner','firmware/target/src/scanner.c',('ADC_GAIN_1_6','ADC_GAIN_1_3')),
                   ('GPIO-mode','firmware/target/src/gpio_modes.h',('GPIO_DISCONNECTED','GPIO_INPUT')),
                   ('scan-control','firmware/target/src/scanner_control.c',('return -ENODEV;','return -EIO;')),
                   ('waveform','firmware/yeti60/core.c',('s->cfg.charge_us','s->cfg.discharge_us')),
                   ('calibration','firmware/yeti60/calibration.c',('6 * (sr > sp','1 * (sr > sp')),
                   ('header','firmware/yeti60/calibration.h',('128u','64u')),
                   ('keymap-only','firmware/target/config/yeti60.keymap',None),
                   ('effective-idle',None,None),('effective-gating',None,None)]
        base_version=version(baseline,options)
        for name,rel,needle in mutations:
            dest=temp/name;shutil.copytree(baseline,dest);opts=dict(options)
            if rel:
                file=dest/rel;text=file.read_text()
                if needle:
                    assert needle[0] in text;text=text.replace(needle[0],needle[1],1)
                else:text+='\n/* Keymap change without an analog change. */\n'
                file.write_text(text)
            if name=='effective-idle':opts[OPTIONS[1]]='60'
            if name=='effective-gating':opts[OPTIONS[3]]='n'
            wanted=version(dest,opts)
            assert (wanted==base_version)==(name in ['same','keymap-only'])
            cmake='include("/contract/baseline/firmware/target/calibration-contract.cmake")\n'
            cmake+='\n'.join('set('+key+' '+value+')' for key,value in opts.items())+'\n'
            cmake+='yeti60_calibration_contract("/contract/'+name+'" got)\n'
            cmake+='if(NOT got STREQUAL "'+wanted+'")\nmessage(FATAL_ERROR "Fingerprint mismatch: ${got}")\nendif()\n'
            (temp/(name+'.cmake')).write_text(cmake)
            cases.append((name,wanted))
        # One pinned container; no dependency checkout or source mutation.
        runner='import subprocess\n'
        runner+='\n'.join("subprocess.run(['cmake','-P','/contract/"+name+".cmake'],check=True)" for name,_ in cases)
        (temp/'run.py').write_text(runner)
        subprocess.run(['docker','run','--rm','--network','none','-v',str(temp)+':/contract:ro',IMAGE,'python3','/contract/run.py'],check=True)
        vendor=temp/'tapdance.c';vendor.write_text(upstream)
        for name in re.findall(r'^#include <([^>]+)>',upstream,re.M):
            header=temp/'includes'/name;header.parent.mkdir(parents=True,exist_ok=True);header.write_text('/* Host test shim supplies these interfaces. */\n')
        wrapper=temp/'test.c';wrapper.write_text('#include "tapdance_shim.h"\n#include "'+str(vendor)+'"\n#include "tapdance_cases.h"\n')
        binary=temp/'recovery'
        subprocess.run([shutil.which('clang'),'-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-const-variable','-Wno-unused-parameter','-Wno-sign-compare','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(temp/'includes'),'-I',str(ROOT/'tests/yeti60'),str(wrapper),'-o',str(binary)],check=True)
        result=subprocess.run([str(binary)],text=True,capture_output=True,check=True)
    files=[Path(__file__),ROOT/'scripts/yeti60_calibration_contract.py',ROOT/'scripts/yeti60_recovery_contract.py',ROOT/'tests/yeti60/tapdance_shim.h',ROOT/'tests/yeti60/tapdance_cases.h',ROOT/'firmware/target/config/yeti60.keymap',*[ROOT/p for p in INPUTS]]
    report=dict(status='passed',physical_verification=False,CMake_mutation_cases=[dict(case=n,version=v) for n,v in cases],
                native_gesture_output=result.stdout.strip(),upstream_revision=REV,upstream_tap_dance_sha256=hashlib.sha256(upstream.encode()).hexdigest(),
                execution='Actual CMake function in pinned build container; unmodified pinned ZMK tap-dance C with host timing/behavior interfaces under ASan/UBSan',
                not_verified=['Real Bluetooth pairing/unpair persistence or USB/HID delivery','Radio/RTOS analog sampling timing and actual key calibration'],
                source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files))})
    (ROOT/'docs/audit/firmware-recovery.json').write_text(json.dumps(report,indent=2)+'\n')
    print(result.stdout,end='');print('CMake calibration fingerprint mutation cases:',len(cases))


if __name__=='__main__':main()
