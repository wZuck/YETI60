#!/usr/bin/env python3
"""Verify target source provenance, ARM linkage and complete Intel HEX records."""
import hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=ROOT/'docs/audit/yeti60-target-build.json';build=json.loads(p.read_text())
    assert build['status']=='built' and build['board']=='yeti60'
    for name,h in build['source_sha256'].items():assert sha(ROOT/name)==h,'Stale firmware source: '+name
    details={}
    for variant,record in build['variants'].items():
        for name,h in record['outputs'].items():assert sha(ROOT/name)==h,'Changed firmware output: '+name
        folder=ROOT/'firmware/releases'/variant;elf=(folder/'yeti60.elf').read_bytes()
        assert elf[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<H',elf,18)[0]==40,'Not a 32-bit ARM ELF'
        for symbol in [b'yeti_scan\0',b'bt_enable\0',b'zmk_hog_send_keyboard_report\0',b'zmk_usb_get_status\0']:
            assert symbol in elf,'Missing target implementation: '+str(symbol)
        assert len((folder/'yeti60.bin').read_bytes())<0xf0000
        offset=0;seen=set();ended=False
        for line in (folder/'yeti60.hex').read_text().splitlines():
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
        details[variant]={'arm_elf':True,'hex_checksums':'passed','programmed_bytes':len(seen),'settings_partition_preserved':True}
    report={'status':'passed','variants':details,'build_manifest_sha256':sha(p),'physical_verification':False}
    (ROOT/'docs/audit/yeti60-target-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
