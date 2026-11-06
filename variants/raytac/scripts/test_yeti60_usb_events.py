#!/usr/bin/env python3
"""Exercise actual charger adapter with the unmodified pinned ZMK USB callback."""
import hashlib,json,re,shutil,subprocess,tempfile
from pathlib import Path
from yeti60_build_environment import workspace_path
ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=workspace_path()
REV='0862fc0f8c864834007986efcaf52f292ea6d37d'
CASES=['normal','not-ready','enable-fault']+['init-fault-'+str(i) for i in range(3)]+['write-fault-'+str(i) for i in range(5)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    source=subprocess.check_output(['git','-C',str(WORKSPACE/'zmk'),'show',REV+':app/src/usb.c'],text=True)
    with tempfile.TemporaryDirectory(prefix='yeti-usb-events-') as folder:
        temp=Path(folder);upstream=temp/'usb.c';upstream.write_text(source)
        for name in re.findall(r'^#include <([^>]+)>',source,re.M):
            if (ROOT/'tests/yeti60/stubs'/name).exists():continue
            header=temp/'includes'/name;header.parent.mkdir(parents=True,exist_ok=True);header.write_text('/* Host interfaces supplied by usb_upstream_shim.h. */\n')
        wrapper=temp/'test.c';wrapper.write_text('#include "usb_upstream_shim.h"\n#include "'+str(upstream)+'"\n')
        binary=temp/'usb-events'
        subprocess.run([shutil.which('clang'),'-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',
                        '-DCONFIG_USB_MAX_POWER=250','-DYETI_PINNED_USB','-I',str(ROOT/'tests/yeti60/stubs'),'-I',str(temp/'includes'),'-I',str(ROOT/'tests/yeti60'),
                        '-I',str(ROOT/'firmware/target/src'),'-I',str(ROOT/'firmware/yeti60'),str(ROOT/'firmware/target/src/usb_policy.c'),str(wrapper),str(ROOT/'tests/yeti60/usb_policy.c'),'-o',str(binary)],check=True)
        records=[]
        for case in CASES:
            result=subprocess.run([str(binary),case],text=True,capture_output=True,check=True)
            records.append(dict(case=case,output=result.stdout.strip()))
    files=[Path(__file__),ROOT/'firmware/target/src/usb_policy.c',ROOT/'firmware/target/src/usb_policy.h',ROOT/'firmware/target/src/scanner.c',ROOT/'firmware/target/CMakeLists.txt',ROOT/'firmware/yeti60/board_pins.h',ROOT/'tests/yeti60/usb_policy.c',ROOT/'tests/yeti60/usb_upstream_shim.h',*sorted((ROOT/'tests/yeti60/stubs').rglob('*.h'))]
    report=dict(status='passed',physical_verification=False,upstream_revision=REV,upstream_usb_sha256=hashlib.sha256(source.encode()).hexdigest(),cases=records,
                execution='Actual target charger adapter and complete unmodified pinned ZMK USB status source, host GPIO/workqueue doubles under ASan/UBSan',
                synchronous_disable_before_upstream_notification=True,configuration_zero_rejected=True,GPIO_fault_latched=True,unintended_external_ILIM_mode_rejected=True,
                not_verified=['Physical USB bus requests, driver scheduling/interrupt latency and suspend current','Physical GPIO or charger failures, input transients and charge temperatures','Real USB/BLE endpoints and full stack concurrency'],
                source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files))})
    (ROOT/'docs/audit/usb-event-policy.json').write_text(json.dumps(report,indent=2)+'\n')
    for record in records:print(record['case']+': '+record['output'])
if __name__=='__main__':main()
