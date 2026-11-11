#!/usr/bin/env python3
"""Exercise pinned ZMK matrix/keymap/HID functions with resolved ARM bindings."""
import csv,hashlib,json,re,shutil,subprocess,sys,tempfile
from pathlib import Path
from yeti60_build_environment import workspace_path
ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=workspace_path()
REV='0862fc0f8c864834007986efcaf52f292ea6d37d'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def function(source,name,signature=None):
    match=re.search(r'^[^;{}\n]*\b'+name+r'\([^;{}]*?\)\s*\{',source,re.M)
    assert match,name
    start=source.index('{',match.start());end=start+1;depth=1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return (signature if signature else source[match.start():start])+source[start:end]+'\n'
def main():
    from yeti60_key_pipeline_contract import verify
    manifest=ROOT/'docs/audit/yeti60-target-build.json';build=json.loads(manifest.read_text())
    assert build['dependencies']['zmk']==REV
    sys.path.insert(0,str(WORKSPACE/'zephyr/scripts/dts/python-devicetree/src'))
    from devicetree.dtlib import DT
    compiled={};maps={};configs={}
    for variant,record in build['variants'].items():
        folder=ROOT/'.firmware-work'/variant/'zephyr'
        assert sha(folder/'zephyr.dts')==record['devicetree_sha256']
        assert sha(folder/'.config')==record['configuration_sha256']
        dt=DT(str(folder/'zephyr.dts'));layers=[]
        for child in dt.get_node('/keymap').nodes.values():
            value=child.props['bindings'].value
            cells=[int.from_bytes(value[i:i+4],'big') for i in range(0,len(value),4)];bindings=[];at=0
            while at<len(cells):
                node=dt.phandle2node[cells[at]];count=node.props['#binding-cells'].to_num()
                bindings.append([node.props['compatible'].to_string(),*cells[at+1:at+1+count]])
                at+=1+count
            assert len(bindings)==60
            layers.append(bindings)
        assert len(layers)==2
        compiled[variant]=layers
        matrix=dt.label2node['matrix_transform'];maps[variant]=matrix.props['map'].to_nums()
        assert matrix.props['rows'].to_num()==5 and matrix.props['columns'].to_num()==15
        assert all(matrix.props[name].to_num()==0 for name in ['row-offset','col-offset'] if name in matrix.props)
        configs[variant]=dict(re.findall(r'^(CONFIG_[A-Z0-9_]+)=(.*)$',(folder/'.config').read_text(),re.M))
    assert compiled['normal']==compiled['calibrator'] and maps['normal']==maps['calibrator']
    options=['CONFIG_ZMK_HID_REPORT_TYPE_HKRO','CONFIG_ZMK_HID_REPORT_TYPE_NKRO','CONFIG_ZMK_HID_KEYBOARD_REPORT_SIZE','CONFIG_ZMK_HID_CONSUMER_REPORT_SIZE','CONFIG_ZMK_HID_CONSUMER_REPORT_USAGES_FULL','CONFIG_ZMK_USB_BOOT','CONFIG_ZMK_HID_SEPARATE_MOD_RELEASE_REPORT','CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE']
    cfg={key:configs['normal'].get(key,'n') for key in options}
    assert all({key:configs[v].get(key,'n') for key in options}==cfg for v in configs)
    assert cfg['CONFIG_ZMK_HID_REPORT_TYPE_HKRO']=='y' and cfg['CONFIG_ZMK_HID_KEYBOARD_REPORT_SIZE']=='6'
    assert cfg['CONFIG_ZMK_USB_BOOT']=='n' and cfg['CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE']=='128'
    source_names=['app/src/hid.c','app/src/hid_listener.c','app/src/keymap.c','app/src/matrix_transform.c','app/src/physical_layouts.c','app/src/behaviors/behavior_key_press.c','app/src/behaviors/behavior_momentary_layer.c','app/src/behaviors/behavior_bt.c']
    header_names=['app/include/zmk/keys.h','app/include/zmk/hid.h','app/include/zmk/events/keycode_state_changed.h','app/include/dt-bindings/zmk/keys.h','app/include/dt-bindings/zmk/hid_usage.h','app/include/dt-bindings/zmk/hid_usage_pages.h','app/include/dt-bindings/zmk/modifiers.h','app/include/dt-bindings/zmk/bt.h']
    vendor={name:subprocess.check_output(['git','-C',str(WORKSPACE/'zmk'),'show',REV+':'+name],text=True) for name in source_names+header_names}
    parts=[]
    transforms=vendor['app/src/matrix_transform.c']
    parts.append(transforms[transforms.index('struct zmk_matrix_transform {'):transforms.index('/* the transform')])
    parts.append(function(transforms,'zmk_matrix_transform_row_column_to_position'))
    keymap=vendor['app/src/keymap.c']
    for name in ['set_layer_state','zmk_keymap_layer_default','zmk_keymap_layer_active_with_state','zmk_keymap_layer_activate','zmk_keymap_layer_deactivate']:
        parts.append(function(keymap,name))
    parts.append(function(keymap,'zmk_keymap_get_layer_binding_at_idx','static const struct zmk_behavior_binding *zmk_keymap_get_layer_binding_at_idx(zmk_keymap_layer_id_t layer_id, uint16_t binding_idx) '))
    for name in ['zmk_keymap_apply_position_state','zmk_keymap_position_state_changed']:
        parts.append(function(keymap,name))
    mo=vendor['app/src/behaviors/behavior_momentary_layer.c']
    parts.append(function(mo,'mo_keymap_binding_pressed'));parts.append(function(mo,'mo_keymap_binding_released'))
    kp=vendor['app/src/behaviors/behavior_key_press.c']
    parts.append(function(kp,'on_keymap_binding_pressed'));parts.append(function(kp,'on_keymap_binding_released'))
    bt=vendor['app/src/behaviors/behavior_bt.c']
    for name in ['on_keymap_binding_pressed','on_keymap_binding_released']:
        parts.append(function(bt,name).replace(name,name.replace('on_','bt_'),1))
    listener=vendor['app/src/hid_listener.c']
    for name in ['hid_listener_keycode_pressed','hid_listener_keycode_released']:parts.append(function(listener,name))
    physical=vendor['app/src/physical_layouts.c']
    parts.append(function(physical,'zmk_physical_layout_kscan_callback'));parts.append(function(physical,'zmk_physical_layouts_kscan_process_msgq'))
    actual='\n'.join(parts)
    with (ROOT/'firmware/target/calibration-keys.csv').open(newline='') as stream:keys=list(csv.DictReader(stream))
    assert len(keys)==60
    lookup=[0]*75
    for position,value in enumerate(maps['normal']):
        row,col=value>>8,value&255
        assert row==int(keys[position]['row']) and col==int(keys[position]['column'])
        lookup[row*15+col]=position+1
    assert len([v for v in lookup if v])==60
    data=['static const uint32_t lookup[75]={'+','.join(map(str,lookup))+'};']
    data.append('static const uint16_t matrix_cells[60]={'+','.join(map(str,maps['normal']))+'};')
    rows=[]
    for layer in compiled['normal']:
        rows.append('{'+','.join('{'+json.dumps(b[0])+','+str(b[1] if len(b)>1 else 0)+','+str(b[2] if len(b)>2 else 0)+'}' for b in layer)+'}')
    data.append('static const struct zmk_behavior_binding zmk_keymap[2][60]={'+','.join(rows)+'};')
    expectations=[]
    for key in keys:
        tokens=key['key_binding'].split()
        assert tokens[0] in ['&kp','&mo']
        expectations.append(tokens[1] if tokens[0]=='&kp' else '0')
    data.append('static const uint32_t expected_base[60]={'+','.join(expectations)+'};')
    with tempfile.TemporaryDirectory(prefix='yeti-key-pipeline-') as folder:
        temp=Path(folder);include=temp/'include'
        for name in ['zephyr/kernel.h','zephyr/logging/log.h','zmk/hid.h']:
            path=include/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('/* Host interfaces are declared by pipeline.c. */\n')
        for path in header_names:
            if path.endswith('/hid.h') or '/events/' in path:continue
            target=include/path.removeprefix('app/include/');target.parent.mkdir(parents=True,exist_ok=True);target.write_text(vendor[path])
        hid=vendor['app/include/zmk/hid.h']
        structs=hid[hid.index('struct zmk_hid_keyboard_report_body {'):hid.index('#if IS_ENABLED(CONFIG_ZMK_POINTING)',hid.index('struct zmk_hid_keyboard_report_body {'))]
        (temp/'hid_structs.inc').write_text(structs)
        event=vendor['app/include/zmk/events/keycode_state_changed.h']
        event=event[event.index('struct zmk_keycode_state_changed {'):].replace('ZMK_EVENT_DECLARE(zmk_keycode_state_changed);','static int raise_zmk_keycode_state_changed(struct zmk_keycode_state_changed event);')
        (temp/'keycode_event.inc').write_text(event)
        (temp/'config.inc').write_text('\n'.join('#define '+key+' '+('1' if value=='y' else '0' if value=='n' else value) for key,value in cfg.items())+'\n')
        (temp/'bindings.inc').write_text('\n'.join(data)+'\n')
        fixture=ROOT/'tests/yeti60/key_pipeline.c'
        def compile_case(name,functions=actual,hid_source=vendor['app/src/hid.c']):
            (temp/'functions.inc').write_text(functions);(temp/'hid.c').write_text(hid_source)
            binary=temp/name
            subprocess.run([shutil.which('clang'),'-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-Wno-unused-function','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(include),'-I',str(temp),str(fixture),'-o',str(binary)],check=True)
            return binary
        binary=compile_case('good');cases=[]
        for name in ['base','fn','layer-release-order','rollover','unused','all-release']:
            result=subprocess.run([str(binary),name],text=True,capture_output=True)
            assert result.returncode==0,(name,result.stdout,result.stderr)
            cases.append({'case':name,**json.loads(result.stdout)})
        mutants=[]
        for name,functions,hid_source,case in [
            ('wrong-transform',actual.replace('return val - INDEX_OFFSET;','return (val - INDEX_OFFSET + 1) % 60;'),vendor['app/src/hid.c'],'base'),
            ('drop-layer-snapshot',actual.replace('zmk_keymap_active_behavior_layer[position] = _zmk_keymap_layer_state;','zmk_keymap_active_behavior_layer[position] = 0;'),vendor['app/src/hid.c'],'fn'),
            ('release-on-current-layer',actual.replace('if (pressed) {\n        zmk_keymap_active_behavior_layer[position]', 'if (true) {\n        zmk_keymap_active_behavior_layer[position]'),vendor['app/src/hid.c'],'layer-release-order'),
            ('omit-HID-release',actual,vendor['app/src/hid.c'].replace('deselect_keyboard_usage(code);','/* injected missing release */'),'base')]:
            assert functions!=actual or hid_source!=vendor['app/src/hid.c'],name
            bad=compile_case(name,functions,hid_source);result=subprocess.run([str(bad),case],text=True,capture_output=True)
            assert result.returncode!=0 and 'Assertion' in result.stderr,(name,result.stdout,result.stderr)
            mutants.append({'case':name,'exit_code':result.returncode,'assertion':result.stderr.strip().splitlines()[-1].replace(str(temp),'<host-test>')})
    files=[Path(__file__),ROOT/'scripts/yeti60_key_pipeline_contract.py',fixture,ROOT/'firmware/target/config/yeti60.keymap',ROOT/'firmware/target/calibration-keys.csv']
    report={'status':'passed','physical_verification':False,'upstream_revision':REV,
            'upstream_sha256':{name:hashlib.sha256(body.encode()).hexdigest() for name,body in vendor.items()},
            'execution':'Actual pinned matrix lookup, physical-layout callback/queue consumer, keymap layer selection, kp/mo/BT-command handlers, keycode conversion, HID listener and complete hid.c; modeled dispatch/event/queue/endpoint interfaces under ASan/UBSan',
            'not_verified':['ADC/scanner-to-queue execution is covered separately by scanner tests','Real Zephyr workqueue timing, USB or BLE packet delivery, host interpretation and transport switching','Tap-dance timing and actual BT profile/bond operations are covered separately; BLE operations are mocks and the dance router only records invocations'],
            'target_build_manifest_sha256':sha(manifest),'compiled_maps':maps,'compiled_bindings':compiled,
            'compiled_variants':{name:{'configuration_sha256':record['configuration_sha256'],'devicetree_sha256':record['devicetree_sha256']} for name,record in build['variants'].items()},
            'resolved_HID_configuration':cfg,'positive_cases':cases,'rejected_mutants':mutants,
            'source_sha256':{str(path.relative_to(ROOT)):sha(path) for path in files}}
    verify(report,build,sha(manifest))
    (ROOT/'docs/audit/key-pipeline.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'cases':cases,'rejected_mutants':len(mutants)},indent=2))
if __name__=='__main__':main()
