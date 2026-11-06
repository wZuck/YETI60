#!/usr/bin/env python3
"""Verify target source provenance, ARM linkage and complete Intel HEX records."""
import hashlib,json,struct,re,subprocess
from pathlib import Path
from yeti60_build_environment import workspace_path
from yeti60_calibration_contract import version
from yeti60_hid_contract import linked_hid_layout,verify_summary
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def usb_callback_linkage(elf):
    """Decode linked Thumb BL targets, rather than trusting source/flags alone."""
    shoff=struct.unpack_from('<I',elf,32)[0];stride,count=struct.unpack_from('<HH',elf,46)
    sections=[struct.unpack_from('<IIIIIIIIII',elf,shoff+i*stride) for i in range(count)]
    symbols={}
    for section in sections:
        if section[1]!=2:continue
        strings=sections[section[6]];names=elf[strings[4]:strings[4]+strings[5]]
        for at in range(section[4],section[4]+section[5],section[9]):
            name,value,size,info,other,index=struct.unpack_from('<IIIBBH',elf,at)
            symbols[names[name:names.find(b'\0',name)].decode(errors='replace')]=(value,size,index)
    def calls(name):
        value,size,index=symbols[name];section=sections[index];start=value&~1
        offset=section[4]+start-section[3];code=elf[offset:offset+size];targets=[]
        for at in range(0,len(code)-3,2):
            hi,lo=struct.unpack_from('<HH',code,at)
            if hi&0xf800!=0xf000 or lo&0xd000!=0xd000:continue
            sign=(hi>>10)&1;i1=1^((lo>>13)&1)^sign;i2=1^((lo>>11)&1)^sign
            delta=(sign<<24)|(i1<<23)|(i2<<22)|((hi&0x3ff)<<12)|((lo&0x7ff)<<1)
            if sign:delta-=1<<25
            targets.append((start+at+4+delta)&~1)
        return targets
    assert (symbols['__wrap_usb_enable'][0]&~1) in calls('zmk_usb_init'),'ZMK USB init bypasses charger callback wrapper'
    assert (symbols['usb_enable'][0]&~1) in calls('__wrap_usb_enable'),'USB wrapper bypasses original legacy stack'
    assert 'usb_status' in symbols and symbols['usb_status'][1]>0,'Charger USB event callback not linked'
    return {'ZMK_init_calls_wrapper':True,'wrapper_calls_original_stack':True,'charger_event_callback_linked':True,'method':'ARM ELF symbol table and decoded Thumb BL targets'}

def usb_configuration_power(elf):
    # Read the linked legacy descriptor section, including both target variants.
    shoff=struct.unpack_from('<I',elf,32)[0]
    stride,count=struct.unpack_from('<HH',elf,46)
    sections=[struct.unpack_from('<IIIIIIIIII',elf,shoff+i*stride) for i in range(count)]
    symbols={}
    for section in sections:
        if section[1]!=2:continue
        strings=sections[section[6]];names=elf[strings[4]:strings[4]+strings[5]]
        for at in range(section[4],section[4]+section[5],section[9]):
            name,value,size,info,other,index=struct.unpack_from('<IIIBBH',elf,at)
            symbols[names[name:names.find(b'\0',name)].decode(errors='replace')]=(value,index)
    start,index=symbols['__usb_descriptor_start'];end,end_index=symbols['__usb_descriptor_end']
    assert index==end_index and index<len(sections)
    section=sections[index];at=section[4]+start-section[3]
    data=elf[at:at+end-start];powers=[];offset=0
    while offset+2<=len(data) and data[offset]:
        size,kind=data[offset:offset+2];assert size>=2 and offset+size<=len(data)
        if kind==2:
            assert size==9
            powers.append(data[offset+8]*2)
        offset+=size
    assert powers==[500],'USB descriptor must request 500 mA: '+str(powers)
    return powers[0]

def main():
    p=ROOT/'docs/audit/yeti60-target-build.json';build=json.loads(p.read_text())
    assert build['status']=='built' and build['board']=='yeti60'
    assert set(build['variants'])=={'normal','calibrator'}
    workspace=workspace_path()
    att_header=subprocess.check_output(['git','-C',str(workspace/'zephyr'),'show',build['dependencies']['zephyr']+':subsys/bluetooth/host/att_internal.h'],text=True)
    minimum_mtu=int(re.search(r'^#define BT_ATT_DEFAULT_LE_MTU\s+(\d+)$',att_header,re.M).group(1))
    assert minimum_mtu==23
    for name,h in build['source_sha256'].items():assert sha(ROOT/name)==h,'Stale firmware source: '+name
    details={}
    for variant,record in build['variants'].items():
        assert record['diagnostic_clock_hz']==32768,'Requalify the documented diagnostic clock resolution'
        assert record['kscan_event_queue_size']==128 and record['builtin_atomics']
        assert record['calibration_record_bytes']==308 and not record['global_NVS_data_CRC']
        assert record['calibration_version']==version(ROOT,record['calibration_scan_configuration'])
        recovery=record['recovery_binding']
        assert recovery['window_ms']==400 and recovery['single_tap']==recovery['hold']=='none'
        assert recovery['clears']=='selected BLE profile only' and recovery['base_Backspace_preserved']
        assert not recovery['calibration_settings_erase_binding']
        for name,h in record['outputs'].items():assert sha(ROOT/name)==h,'Changed firmware output: '+name
        folder=ROOT/'firmware/releases'/variant;elf=(folder/'yeti60-raytac.elf').read_bytes()
        assert elf[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<H',elf,18)[0]==40,'Not a 32-bit ARM ELF'
        for symbol in [b'yeti_target_usb_poll\0',b'yeti_cal_thresholds\0',b'yeti_calibration_checksum\0',b'yeti_scan\0',b'bt_enable\0',b'zmk_hog_send_keyboard_report\0',b'zmk_usb_get_status\0']:
            assert symbol in elf,'Missing target implementation: '+str(symbol)
        assert len((folder/'yeti60-raytac.bin').read_bytes())<0xf0000
        offset=0;seen=set();ended=False
        for line in (folder/'yeti60-raytac.hex').read_text().splitlines():
            assert not ended and line.startswith(':')
            data=bytes.fromhex(line[1:]);assert len(data)==data[0]+5 and sum(data)%256==0,'Invalid HEX checksum'
            count,address,kind=data[0],int.from_bytes(data[1:3],'big'),data[3]
            if kind==0:
                for address in range(offset+address,offset+address+count):
                    assert address<0xf0000 or 0x10001000<=address<0x10002000,'HEX overwrites storage or invalid address'
                    assert address not in seen,'Overlapping HEX data';seen.add(address)
            elif kind==4:offset=int.from_bytes(data[4:6],'big')<<16
            elif kind==2:offset=int.from_bytes(data[4:6],'big')<<4
            elif kind==1:ended=True
            else:assert kind in [3,5],'Unsupported HEX record'
        assert ended and seen
        hid=linked_hid_layout(elf,minimum_mtu);verify_summary(hid)
        details[variant]={'arm_elf':True,'hex_checksums':'passed','programmed_bytes':len(seen),'settings_partition_preserved':True,'USB_configuration_mA':usb_configuration_power(elf),'USB_callback_linkage':usb_callback_linkage(elf),'HID_linked_layout':hid,'diagnostic_clock_hz':record['diagnostic_clock_hz'],'kscan_event_queue_size':record['kscan_event_queue_size'],'builtin_atomics':record['builtin_atomics']}
    assert len({v['calibration_version'] for v in build['variants'].values()})==1
    report={'status':'passed','variants':details,'build_manifest_sha256':sha(p),'physical_verification':False,'calibration_contract_version':build['variants']['normal']['calibration_version'],'recovery_binding':build['variants']['normal']['recovery_binding']}
    report['verification_recipe_sha256']={str(path.relative_to(ROOT)):sha(path) for path in [Path(__file__).resolve(),ROOT/'scripts/yeti60_hid_contract.py']}
    report['pinned_ATT_header_sha256']=hashlib.sha256(att_header.encode()).hexdigest()
    (ROOT/'docs/audit/yeti60-target-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
