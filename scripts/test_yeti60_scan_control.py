#!/usr/bin/env python3
"""Run actual scanner shell, owner loop, fault cleanup and lifecycle atomics."""
import hashlib,json,re,shutil,subprocess,sys,tempfile
from pathlib import Path
from yeti60_build_environment import workspace_path
from yeti60_host_atomics import prepare, REV
ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=workspace_path()
ZMK_REV='0862fc0f8c864834007986efcaf52f292ea6d37d'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def function(source,name):
    match=re.search(r'^(?:static )?(?:int|void)(?: __unused)? '+name+r'\(',source,re.M)
    assert match,name
    brace=source.index('{',match.start());depth=1;end=brace+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[match.start():end]+'\n'
def main():
    from yeti60_scan_control_contract import verify
    scanner=ROOT/'firmware/target/src/scanner.c';source=scanner.read_text()
    control=ROOT/'firmware/target/src/scanner_control.c';original=control.read_text()
    config=ROOT/'firmware/target/config/yeti60.conf';build_path=ROOT/'docs/audit/yeti60-target-build.json'
    build=json.loads(build_path.read_text());normal=build['variants']['normal']
    assert build['dependencies']['zmk']==ZMK_REV and build['dependencies']['zephyr']==REV
    target_folder=ROOT/'.firmware-work/normal/zephyr';dts_path=target_folder/'zephyr.dts'
    assert sha(dts_path)==normal['devicetree_sha256'] and sha(target_folder/'.config')==normal['configuration_sha256']
    sys.path.insert(0,str(WORKSPACE/'zephyr/scripts/dts/python-devicetree/src'))
    from devicetree.dtlib import DT
    dt=DT(str(dts_path));matrix=dt.label2node['matrix_transform']
    encoded=matrix.props['map'].to_nums();positions=[(value>>8,value&255) for value in encoded]
    assert matrix.props['rows'].to_num()==5 and matrix.props['columns'].to_num()==15
    assert len(set(positions))==len(positions)==60 and all(r<5 and c<15 for r,c in positions)
    board_dts=ROOT/'firmware/target/boards/yeti/yeti60/yeti60.dts'
    region=re.search(r'map\s*=\s*<([\s\S]*?)>;',board_dts.read_text()).group(1)
    source_positions=[tuple(map(int,p)) for p in re.findall(r'RC\(\s*(\d+)\s*,\s*(\d+)\s*\)',region)]
    assert positions==source_positions,'Compiled transform order differs from the board source/physical-map contract'
    compiled_variants={}
    for name,record in build['variants'].items():
        variant_folder=ROOT/'.firmware-work'/name/'zephyr';variant_dts=variant_folder/'zephyr.dts'
        assert sha(variant_dts)==record['devicetree_sha256'] and sha(variant_folder/'.config')==record['configuration_sha256']
        node=DT(str(variant_dts)).label2node['matrix_transform']
        mapped=[(value>>8,value&255) for value in node.props['map'].to_nums()]
        assert node.props['rows'].to_num()==5 and node.props['columns'].to_num()==15 and mapped==positions
        assert record['calibration_version']==normal['calibration_version']
        assert record['calibration_scan_configuration']==normal['calibration_scan_configuration']
        compiled_variants[name]={'positions':mapped,'devicetree_sha256':sha(variant_dts),'configuration_sha256':sha(variant_folder/'.config')}
    masks=[0]*5
    for row,col in positions:masks[row]|=1<<col
    source_masks=[int(item.strip(),0) for item in re.search(r'active\[5\]\s*=\s*\{([^}]+)',source).group(1).split(',') if item.strip()]
    assert masks==source_masks,'Scanner active positions differ from the compiled matrix transform'
    options=normal['calibration_scan_configuration']
    assert options=={'CONFIG_YETI60_ACTIVE_SCAN_MS':'4','CONFIG_YETI60_IDLE_SCAN_MS':'30','CONFIG_YETI60_IDLE_AFTER_MS':'30000','CONFIG_YETI60_AFE_IDLE_GATING':'y'},'Requalify the idle test for changed scan options'
    queue_size=normal['kscan_event_queue_size']
    assert queue_size==int(re.search(r'^CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE=(\d+)$',config.read_text(),re.M).group(1))
    vendor=subprocess.check_output(['git','-C',str(WORKSPACE/'zmk'),'show',ZMK_REV+':app/src/physical_layouts.c'],text=True)
    settings_source=subprocess.check_output(['git','-C',str(WORKSPACE/'zephyr'),'show',REV+':subsys/settings/src/settings.c'],text=True)
    transform_header=subprocess.check_output(['git','-C',str(WORKSPACE/'zmk'),'show',ZMK_REV+':app/include/dt-bindings/zmk/matrix_transform.h'],text=True)
    assert '#define KT_ROW(item) (item >> 8)' in transform_header and '#define KT_COL(item) (item & 0xFF)' in transform_header
    dispatch=function(settings_source,'settings_call_set_handler')
    cases=['offline','parser','queue','queue-burst','fault-race','cleanup','worker-ADC','worker-GPIO','worker-GPIO-capture','worker-disabled-GPIO','load-reject','settings-dispatch','worker-load','worker-idle-shorttap','worker-calibration']
    positive=[];negative=[];idle_details=None;short_tap_details=None
    core_original=(ROOT/'firmware/yeti60/core.c').read_text()
    with tempfile.TemporaryDirectory(prefix='yeti-scan-control-') as folder:
        temp=Path(folder);upstream=prepare(WORKSPACE,temp)
        (temp/'zmk_kscan_callback.inc').write_text(function(vendor,'zmk_physical_layout_kscan_callback'))
        (temp/'zmk_event_types.inc').write_text(vendor[vendor.index('#define ZMK_KSCAN_EVENT_STATE_PRESSED'):vendor.index('static struct zmk_kscan_msg_processor')])
        (temp/'scanner_globals.inc').write_text(source[source.index('static struct yeti_core core;'):source.index('static int load_calibration(')])
        def compile_case(name,body=source,policy=original,capacity=queue_size,dispatcher=dispatch,core_body=core_original):
            (temp/'settings_dispatch.inc').write_text(dispatcher)
            macros={**{key:('1' if value=='y' else value) for key,value in options.items()},'CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE':str(capacity),'CONFIG_SYS_CLOCK_HW_CYCLES_PER_SEC':str(normal['diagnostic_clock_hz']),'YETI_CALIBRATION_VERSION':normal['calibration_version']}
            (temp/'queue_contract.h').write_text('\n'.join('#define '+key+' '+value for key,value in macros.items())+'\n')
            for function_name,include in [('load_calibration','load'),('command','command'),('fault_shutdown','fault'),('run','run')]:
                (temp/('scanner_'+include+'.inc')).write_text(function(body,function_name))
            file=temp/'scanner_control.c';file.write_text(policy);binary=temp/name
            (temp/'core.c').write_text(core_body)
            subprocess.run([shutil.which('clang'),'-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-variable','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(temp),'-I',str(ROOT/'firmware/target/src'),'-I',str(ROOT/'firmware/yeti60'),str(file),str(temp/'core.c'),str(ROOT/'firmware/yeti60/calibration.c'),str(ROOT/'tests/yeti60/scanner_control.c'),'-o',str(binary)],check=True)
            return binary
        binary=compile_case('good')
        for name in cases:
            run=subprocess.run([str(binary),name],text=True,capture_output=True)
            assert run.returncode==0,(name,run.stdout,run.stderr)
            positive.append(dict(case=name,output=run.stdout.strip()))
            if name=='worker-calibration':
                idle_details=json.loads(next(line for line in run.stdout.splitlines() if line.startswith('{')))
            if name=='worker-idle-shorttap':
                short_tap_details=json.loads(next(line for line in run.stdout.splitlines() if line.startswith('{')))
        mutations=[
            ('accept-offline',source,original.replace('return -ENODEV;','return 0;'),'offline'),
            ('accept-fault-mutation',source,original.replace('if (state == Y_SCAN_FAULT && mutation(action))','if (false)'),'fault-race'),
            ('omit-consumer-recheck',source,original.replace('if (action && mutation(action) && yeti_scan_state() != Y_SCAN_RUNNING)','if (false)'),'fault-race'),
            ('overwrite-pending',source,original.replace('return atomic_cas(&pending, 0, action) ? 0 : -EBUSY;','atomic_set(&pending, action); return 0;'),'queue'),
            ('omit-key-release',source.replace('callback(scan_device, row, col, false);','(void)0;'),original,'cleanup'),
            ('omit-fault-poweroff',source.replace('(void)yeti_power(&core, false);','(void)0;'),original,'cleanup'),
            ('publish-fault-frame',source.replace('if (err || io_fault) {','if (err) {'),original,'worker-GPIO-capture'),
            ('short-event-queue',source,original,'queue-burst',4),
            ('omit-record-length',source.replace('if (len != sizeof(saved))','if (len == (size_t)-1)'),original,'load-reject'),
            ('omit-record-validation',source.replace('!yeti_calibration_valid(&value, YETI_CALIBRATION_VERSION)','false'),original,'load-reject'),
            ('accept-short-read',source.replace('read(arg, &value, sizeof(value)) != sizeof(value)','read(arg, &value, sizeof(value)) < 0'),original,'load-reject'),
            ('omit-save-checksum',source.replace('candidate.crc32 = yeti_calibration_checksum(&candidate);','candidate.crc32 = 0;'),original,'worker-calibration'),
            ('omit-pending-wake',source.replace('if (any_key || changed || pending || calibration_mode) {','(void)pending;\n      if (any_key || changed || calibration_mode) {'),original,'worker-idle-shorttap')]
        for mutation in mutations:
            name,body,policy,case=mutation[:4];capacity=mutation[4] if len(mutation)>4 else queue_size
            assert body!=source or policy!=original or capacity!=queue_size,name
            bad=compile_case(name,body,policy,capacity);run=subprocess.run([str(bad),case],text=True,capture_output=True)
            assert run.returncode!=0 and 'Assertion' in run.stderr,(name,run.stdout,run.stderr)
            negative.append(dict(case=name,exit_code=run.returncode,output=run.stderr.strip()[-600:]))
            if case=='worker-idle-shorttap':
                negative[-1]['observed']=json.loads(next(line for line in run.stdout.splitlines() if line.startswith('{')))
        mutant=dispatch.replace('/* Ignoring the error */\n\t\t\trc = 0;','/* Injected propagation */\n\t\t\treturn rc;')
        assert mutant!=dispatch
        binary=compile_case('propagate-calibration-load-error',dispatcher=mutant)
        run=subprocess.run([str(binary),'settings-dispatch'],text=True,capture_output=True)
        assert run.returncode!=0 and 'Assertion' in run.stderr,run.stderr
        negative.append(dict(case='propagate-calibration-load-error',exit_code=run.returncode,output=run.stderr.strip()[-600:]))
        lower_unused=source.replace('candidate.low[r][c] = 4094;','candidate.low[r][c] = 4093;').replace('candidate.high[r][c] = 4095;','candidate.high[r][c] = 4094;')
        inclusive=core_original.replace('samples[r][c] > s->cfg.high[r][c]','samples[r][c] >= s->cfg.high[r][c]')
        bypass_debounce=core_original.replace('>= s->cfg.debounce_frames','>= 1u')
        for name,body,core_body,case in [('lower-unused-thresholds',lower_unused,core_original,'worker-calibration'),('inclusive-high-threshold',source,inclusive,'worker-calibration'),('bypass-debounce',source,bypass_debounce,'worker-idle-shorttap')]:
            assert body!=source or core_body!=core_original,name
            binary=compile_case(name,body=body,core_body=core_body)
            run=subprocess.run([str(binary),case],text=True,capture_output=True)
            assert run.returncode!=0 and 'Assertion' in run.stderr,(name,run.stdout,run.stderr)
            negative.append(dict(case=name,exit_code=run.returncode,output=run.stderr.strip()[-600:]))
            if case=='worker-idle-shorttap':
                negative[-1]['observed']=json.loads(next(line for line in run.stdout.splitlines() if line.startswith('{')))
    files=[Path(__file__),ROOT/'scripts/yeti60_host_atomics.py',ROOT/'scripts/yeti60_scan_control_contract.py',scanner,control,config,board_dts,ROOT/'firmware/target/src/scanner_control.h',ROOT/'tests/yeti60/scanner_control.c',*[ROOT/('firmware/yeti60/'+n) for n in ['core.c','core.h','board_pins.h','calibration.c','calibration.h']]]
    report=dict(status='passed',physical_verification=False,execution='Verbatim production shell, worker loop and shutdown; actual lifecycle module, core, calibration and pinned Zephyr builtin atomics; modeled ADC/GPIO/sleep/settings/kscan interfaces under ASan/UBSan',
                positive_cases=positive,rejected_mutants=negative,active_keys_checked=60,inactive_positions_rejected=15,capture_frames_per_key=128,upstream_revision=REV,upstream_sha256=upstream,ZMK_revision=ZMK_REV,ZMK_physical_layouts_sha256=hashlib.sha256(vendor.encode()).hexdigest(),event_queue_capacity=queue_size,undrained_burst_events_checked=120,
                calibration_record_bytes=308,legacy_record_bytes_rejected=304,settings_dispatch_sha256=hashlib.sha256(settings_source.encode()).hexdigest(),
                target_build_manifest_sha256=sha(build_path),resolved_devicetree_sha256=sha(dts_path),resolved_configuration_sha256=sha(target_folder/'.config'),compiled_matrix_active_masks=masks,compiled_matrix_positions=positions,compiled_variant_maps=compiled_variants,compiled_transform_header_sha256=hashlib.sha256(transform_header.encode()).hexdigest(),scan_configuration=options,inactive_idle=idle_details,idle_short_tap=short_tap_details,
                not_verified=['Actual RTOS scheduling/preemption or hardware memory ordering on Cortex-M4','Real ADC/GPIO failures, USB/BLE HID release delivery, flash writes or battery operation'],source_sha256={str(p.relative_to(ROOT)):sha(p) for p in files})
    verify(report,build,sha(build_path))
    (ROOT/'docs/audit/scan-control.json').write_text(json.dumps(report,indent=2)+'\n')
    for case in positive:print(case['output'])
    print('Scanner lifecycle/worker mutants rejected:',len(negative))
if __name__=='__main__':main()
