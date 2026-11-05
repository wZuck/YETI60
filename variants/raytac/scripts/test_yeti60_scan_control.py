#!/usr/bin/env python3
"""Run actual scanner shell, owner loop, fault cleanup and lifecycle atomics."""
import hashlib,json,re,shutil,subprocess,tempfile
from pathlib import Path
from yeti60_host_atomics import prepare, REV
ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=Path.home()/'.cache/yeti60-zmk-workspace'
ZMK_REV='0862fc0f8c864834007986efcaf52f292ea6d37d'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def function(source,name):
    match=re.search(r'^static (?:int|void)(?: __unused)? '+name+r'\(',source,re.M)
    assert match,name
    brace=source.index('{',match.start());depth=1;end=brace+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[match.start():end]+'\n'
def main():
    scanner=ROOT/'firmware/target/src/scanner.c';source=scanner.read_text()
    control=ROOT/'firmware/target/src/scanner_control.c';original=control.read_text()
    config=ROOT/'firmware/target/config/yeti60.conf'
    queue_size=int(re.search(r'^CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE=(\d+)$',config.read_text(),re.M).group(1))
    vendor=subprocess.check_output(['git','-C',str(WORKSPACE/'zmk'),'show',ZMK_REV+':app/src/physical_layouts.c'],text=True)
    cases=['offline','parser','queue','queue-burst','fault-race','cleanup','worker-ADC','worker-GPIO','worker-GPIO-capture','worker-disabled-GPIO','worker-calibration']
    positive=[];negative=[]
    with tempfile.TemporaryDirectory(prefix='yeti-scan-control-') as folder:
        temp=Path(folder);upstream=prepare(WORKSPACE,temp)
        (temp/'zmk_kscan_callback.inc').write_text(function(vendor,'zmk_physical_layout_kscan_callback'))
        (temp/'zmk_event_types.inc').write_text(vendor[vendor.index('#define ZMK_KSCAN_EVENT_STATE_PRESSED'):vendor.index('static struct zmk_kscan_msg_processor')])
        (temp/'scanner_globals.inc').write_text(source[source.index('static struct yeti_core core;'):source.index('static int load_calibration(')])
        def build(name,body=source,policy=original,capacity=queue_size):
            (temp/'queue_contract.h').write_text('#define CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE '+str(capacity)+'\n')
            for function_name,include in [('command','command'),('fault_shutdown','fault'),('run','run')]:
                (temp/('scanner_'+include+'.inc')).write_text(function(body,function_name))
            file=temp/'scanner_control.c';file.write_text(policy);binary=temp/name
            subprocess.run([shutil.which('clang'),'-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-variable','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(temp),'-I',str(ROOT/'firmware/target/src'),'-I',str(ROOT/'firmware/yeti60'),str(file),str(ROOT/'firmware/yeti60/core.c'),str(ROOT/'firmware/yeti60/calibration.c'),str(ROOT/'tests/yeti60/scanner_control.c'),'-o',str(binary)],check=True)
            return binary
        binary=build('good')
        for name in cases:
            run=subprocess.run([str(binary),name],text=True,capture_output=True)
            assert run.returncode==0,(name,run.stdout,run.stderr)
            positive.append(dict(case=name,output=run.stdout.strip()))
        mutations=[
            ('accept-offline',source,original.replace('return -ENODEV;','return 0;'),'offline'),
            ('accept-fault-mutation',source,original.replace('if (state == Y_SCAN_FAULT && mutation(action))','if (false)'),'fault-race'),
            ('omit-consumer-recheck',source,original.replace('if (action && mutation(action) && yeti_scan_state() != Y_SCAN_RUNNING)','if (false)'),'fault-race'),
            ('overwrite-pending',source,original.replace('return atomic_cas(&pending, 0, action) ? 0 : -EBUSY;','atomic_set(&pending, action); return 0;'),'queue'),
            ('omit-key-release',source.replace('callback(scan_device, row, col, false);','(void)0;'),original,'cleanup'),
            ('omit-fault-poweroff',source.replace('(void)yeti_power(&core, false);','(void)0;'),original,'cleanup'),
            ('publish-fault-frame',source.replace('if (err || io_fault) {','if (err) {'),original,'worker-GPIO-capture'),
            ('short-event-queue',source,original,'queue-burst',4)]
        for mutation in mutations:
            name,body,policy,case=mutation[:4];capacity=mutation[4] if len(mutation)>4 else queue_size
            assert body!=source or policy!=original or capacity!=queue_size,name
            bad=build(name,body,policy,capacity);run=subprocess.run([str(bad),case],text=True,capture_output=True)
            assert run.returncode!=0 and 'Assertion' in run.stderr,(name,run.stdout,run.stderr)
            negative.append(dict(case=name,exit_code=run.returncode,output=run.stderr.strip()[-600:]))
    files=[Path(__file__),ROOT/'scripts/yeti60_host_atomics.py',scanner,control,config,ROOT/'firmware/target/src/scanner_control.h',ROOT/'tests/yeti60/scanner_control.c',*[ROOT/('firmware/yeti60/'+n) for n in ['core.c','core.h','board_pins.h','calibration.c','calibration.h']]]
    report=dict(status='passed',physical_verification=False,execution='Verbatim production shell, worker loop and shutdown; actual lifecycle module, core, calibration and pinned Zephyr builtin atomics; modeled ADC/GPIO/sleep/settings/kscan interfaces under ASan/UBSan',
                positive_cases=positive,rejected_mutants=negative,active_keys_checked=60,inactive_positions_rejected=15,capture_frames_per_key=128,upstream_revision=REV,upstream_sha256=upstream,ZMK_revision=ZMK_REV,ZMK_physical_layouts_sha256=hashlib.sha256(vendor.encode()).hexdigest(),event_queue_capacity=queue_size,undrained_burst_events_checked=120,
                not_verified=['Actual RTOS scheduling/preemption or hardware memory ordering on Cortex-M4','Real ADC/GPIO failures, USB/BLE HID release delivery, flash writes or battery operation'],source_sha256={str(p.relative_to(ROOT)):sha(p) for p in files})
    (ROOT/'docs/audit/scan-control.json').write_text(json.dumps(report,indent=2)+'\n')
    for case in positive:print(case['output'])
    print('Scanner lifecycle/worker mutants rejected:',len(negative))
if __name__=='__main__':main()
