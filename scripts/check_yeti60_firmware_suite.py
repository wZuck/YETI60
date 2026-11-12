#!/usr/bin/env python3
"""Verify current E73 firmware evidence; host models do not qualify hardware."""
import hashlib,json
from pathlib import Path
from yeti60_hid_contract import verify_summary as verify_hid
from yeti60_scan_control_contract import verify as verify_scan
from yeti60_key_pipeline_contract import verify as verify_pipeline
from yeti60_nvs_contract import verify as verify_nvs
ROOT=Path(__file__).resolve().parents[1]
AUD=ROOT/'docs/audit'
REPORTS=['gpio-mode-policy','scan-control','key-pipeline','nvs-powercut','firmware-recovery','analog-waveform','calibration','usb-event-policy']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify_reports(reports,build,build_sha,target):
    assert build['status']=='built' and target['status']=='passed'
    assert target['build_manifest_sha256']==build_sha
    assert set(build['variants'])==set(target['variants'])=={'normal','calibrator'}
    assert len({v['calibration_version'] for v in build['variants'].values()})==1
    for name,variant in build['variants'].items():
        assert variant['E73_configuration']=={'LF_clock':'internal-RC','REG1':'LDO','REG0_DCDC':False,'NFC_pins':'GPIO','HEX_NFCPINS_UICR':0xfffffffe}
        assert target['variants'][name]['NFC_GPIO_UICR'] and target['variants'][name]['REG1_mode']=='LDO'
        assert target['variants'][name]['USB_configuration_mA']==500
        verify_hid(target['variants'][name]['HID_linked_layout'])
    for name in REPORTS:
        assert reports[name]['physical_verification'] is False,(name,'Cannot inherit physical acceptance')
        assert reports[name]['status']==('model-regression-passed-physical-open' if name=='analog-waveform' else 'passed'),name
    gpio=reports['gpio-mode-policy']
    assert gpio['upstream_revision']==build['dependencies']['zephyr']
    assert gpio['GPIO_constants_checked_against_pinned_headers'] and gpio['nominal_scan_samples']==150
    assert len(gpio['positive_cases'])==5 and len(gpio['rejected_mutants'])==4
    assert all(c['exit_code']!=0 for c in gpio['rejected_mutants'])
    verify_scan(reports['scan-control'],build,build_sha)
    verify_pipeline(reports['key-pipeline'],build,build_sha)
    verify_nvs(reports['nvs-powercut'],build,build_sha)
    recovery=reports['firmware-recovery']
    assert recovery['upstream_revision']==build['dependencies']['zmk'] and {x['case'] for x in recovery['CMake_mutation_cases']}=={'same','scanner','GPIO-mode','scan-control','waveform','calibration','header','stack','plate','keymap-only','effective-idle','effective-gating'}
    assert target['recovery_binding']['clears']=='selected BLE profile only'
    assert not target['recovery_binding']['calibration_settings_erase_binding']
    storage=reports['calibration']['storage_integrity']
    assert storage['record_bytes']==308 and storage['independent_zlib_records']==512
    assert storage['single_bit_flips_rejected']==2464 and storage['byte_inversions_rejected']==308
    assert storage['sliding_32_bit_bursts_rejected']==2433 and not storage['physical_power_cut_tested']
    assert len(storage['rejected_mutants'])==3 and all(c['exit_code']!=0 for c in storage['rejected_mutants'])
    analog=reports['analog-waveform']
    assert {c['case'] for c in analog['order_mutants_rejected']}=={'rise-before-release','fall-before-clamp'}
    assert all(c['exit_code']!=0 for c in analog['order_mutants_rejected']) and len(analog['sensitivities'])==36
    assert analog['illustrative_correct_delta_ADC_codes']>32 and analog['illustrative_wrong_rise_delta_ADC_codes']==0
    assert not any(analog[x] for x in ['ADC_API_latency_qualified','key_capacitance_measured','opamp_dynamic_model','AFE_saturation_qualified'])
    assert analog['diagnostic_counter']['clock_hz']==32768 and analog['diagnostic_counter']['one_tick_quantization_guard']
    usb=reports['usb-event-policy']
    assert usb['upstream_revision']==build['dependencies']['zmk'] and len(usb['cases'])==11
    assert usb['synchronous_disable_before_upstream_notification'] and usb['configuration_zero_rejected']
    assert usb['GPIO_fault_latched'] and usb['unintended_external_ILIM_mode_rejected']
    return dict(status='passed',physical_verification=False,normal_and_calibrator=True,E73_GPIO_ADC_RC_LDO_NFC_preserved=True,
                active_keys=60,event_queue=128,CRC_record_bytes=308,NVS_cut_trials=14795,
                analog_model='passive RC sensitivity only; measured NiZ/opamp/timing margins remain open')
def verify():
    paths=[AUD/(name+'.json') for name in REPORTS]+[AUD/'yeti60-target-build.json',AUD/'yeti60-target-check.json']
    data={p.stem:json.loads(p.read_text()) for p in paths}
    for name,report in data.items():
        for key in ['source_sha256','outputs','verification_recipe_sha256']:
            for path,digest in report.get(key,{}).items():assert sha(ROOT/path)==digest,('Stale firmware evidence',name,path)
    for variant in data['yeti60-target-build']['variants'].values():
        for path,digest in variant['outputs'].items():assert sha(ROOT/path)==digest,('Stale firmware binary',path)
    report=verify_reports(data,data['yeti60-target-build'],sha(AUD/'yeti60-target-build.json'),data['yeti60-target-check'])
    report['evidence_sha256']={str(p.relative_to(ROOT)):sha(p) for p in paths}
    report['source_sha256']={'scripts/check_yeti60_firmware_suite.py':sha(Path(__file__))}
    return report
def main():
    report=verify()
    (AUD/'firmware-suite.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
