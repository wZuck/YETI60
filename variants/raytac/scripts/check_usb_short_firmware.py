#!/usr/bin/env python3
"""Verify published candidate HEX/BIN, source mapping and build/test evidence."""
import hashlib,json
from yeti60_calibration_contract import version
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/usb-short-route';PUB=BASE/'firmware'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    m=json.loads((PUB/'manifest.json').read_text());assert m['status']=='candidate-normal-and-calibrator-built-and-host-checked' and not m['physical_verification'] and not m['canonical_releases_modified']
    for group in ['source_sha256','published_outputs','evidence']:
        for rel,h in m[group].items():assert sha(ROOT/rel)==h,('Candidate firmware provenance mismatch',rel)
    assert sha(BASE/'audit/native-check.json')==m['native_acceptance_sha256'];assert sha(BASE/'audit/geometry-check.json')==m['local_geometry_acceptance_sha256']
    build=json.loads((PUB/'build.json').read_text());target=json.loads((PUB/'target-check.json').read_text());assert sha(PUB/'build.json')==target['build_manifest_sha256']
    assert set(build['variants'])=={'normal','calibrator'} and all(v['USB_configuration_mA']==500 for v in target['variants'].values())
    for details in target['variants'].values():
        assert details['diagnostic_clock_hz']==32768
        assert details['kscan_event_queue_size']==128 and details['builtin_atomics']
        linkage=details['USB_callback_linkage']
        assert linkage['ZMK_init_calls_wrapper'] and linkage['wrapper_calls_original_stack'] and linkage['charger_event_callback_linked']
    for record in build['variants'].values():
        assert record['calibration_version']==version(ROOT,record['calibration_scan_configuration'],BASE/'EC60-nRF52840.kicad_pcb')
        recovery=record['recovery_binding']
        assert recovery['window_ms']==400 and recovery['single_tap']==recovery['hold']=='none'
        assert recovery['clears']=='selected BLE profile only' and not recovery['calibration_settings_erase_binding']
    assert len({r['calibration_version'] for r in build['variants'].values()})==1
    for name in ['build.json','simulation.json','calibration.json','gpio-mode-policy.json','scan-control.json']:
        d=json.loads((PUB/name).read_text());assert d['status']==('built' if name=='build.json' else 'passed')
        for rel,h in d.get('source_sha256',{}).items():
            p=BASE/Path(rel).name if rel in ['hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb','hardware/ec60-nrf52840/netlist.xml'] else ROOT/rel
            assert sha(p)==h,('Stale source in build/test report',name,rel)
        if name=='gpio-mode-policy.json':
            assert not d['physical_verification'] and d['nominal_scan_samples']==150
            assert len(d['positive_cases'])==5 and len(d['rejected_mutants'])==4
        if name=='scan-control.json':
            assert not d['physical_verification'] and d['event_queue_capacity']==128
            assert d['undrained_burst_events_checked']==120 and d['active_keys_checked']==60
            assert len(d['positive_cases'])==14 and len(d['rejected_mutants'])==13
            assert d['calibration_record_bytes']==308 and d['legacy_record_bytes_rejected']==304
            assert all(case['exit_code']!=0 for case in d['rejected_mutants'])
        if name=='calibration.json':
            storage=d['storage_integrity']
            assert storage['record_bytes']==308 and storage['independent_zlib_records']==512
            assert storage['single_bit_flips_rejected']==2464 and storage['byte_inversions_rejected']==308
            assert storage['sliding_32_bit_bursts_rejected']==2433 and len(storage['rejected_mutants'])==3
            assert not storage['physical_power_cut_tested'] and all(c['exit_code']!=0 for c in storage['rejected_mutants'])
    for variant in ['normal','calibrator']:
        folder=PUB/'releases'/variant;encoded={};offset=0;ended=False
        for line in (folder/'yeti60-raytac.hex').read_text().splitlines():
            assert not ended and line.startswith(':');data=bytes.fromhex(line[1:]);assert len(data)==data[0]+5 and sum(data)%256==0
            size,at,kind=data[0],int.from_bytes(data[1:3],'big'),data[3]
            if kind==0:
                for i,v in enumerate(data[4:4+size]):
                    address=offset+at+i;assert address not in encoded;assert address<0xf0000 or 0x10001000<=address<0x10002000;encoded[address]=v
            elif kind==4:offset=int.from_bytes(data[4:6],'big')<<16
            elif kind==2:offset=int.from_bytes(data[4:6],'big')<<4
            elif kind==1:ended=True
            else:assert kind in [3,5]
        assert ended and encoded
        binary=(folder/'yeti60-raytac.bin').read_bytes();assert all(encoded.get(i,255)==v for i,v in enumerate(binary))
        assert sha(folder/'yeti60-raytac.hex')==build['variants'][variant]['outputs']['firmware/releases/'+variant+'/yeti60-raytac.hex']
        assert sha(folder/'yeti60-raytac.bin')==build['variants'][variant]['outputs']['firmware/releases/'+variant+'/yeti60-raytac.bin']
    print('Candidate sources, native/CAD fingerprints, both HEX/BIN images and host/target/calibration evidence agree')
if __name__=='__main__':main()
