#!/usr/bin/env python3
"""Reject cross-version, corrupt and overclaimed firmware acceptance evidence."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from check_yeti60_firmware_suite import REPORTS,verify_reports,sha
class Evidence(unittest.TestCase):
    def setUp(self):
        read=lambda n:json.loads((ROOT/'docs/audit'/(n+'.json')).read_text())
        self.reports={n:read(n) for n in REPORTS};self.build=read('yeti60-target-build');self.target=read('yeti60-target-check')
        self.digest=sha(ROOT/'docs/audit/yeti60-target-build.json')
    def check(self):return verify_reports(self.reports,self.build,self.digest,self.target)
    def test_current_evidence(self):self.assertEqual(self.check()['status'],'passed')
    def test_different_module_configuration(self):
        self.build['variants']['normal']['E73_configuration']['REG1']='DCDC'
        with self.assertRaises(AssertionError):self.check()
    def test_missing_NFC_UICR(self):
        self.target['variants']['calibrator']['NFC_GPIO_UICR']=False
        with self.assertRaises(AssertionError):self.check()
    def test_cross_build_storage(self):
        self.reports['nvs-powercut']['target_build_manifest_sha256']='0'*64
        with self.assertRaises(AssertionError):self.check()
    def test_incomplete_powercut_model(self):
        self.reports['nvs-powercut']['total_cut_trials']-=1
        with self.assertRaises(AssertionError):self.check()
    def test_small_event_queue(self):
        self.reports['scan-control']['event_queue_capacity']=16
        with self.assertRaises(AssertionError):self.check()
    def test_legacy_record_format(self):
        self.reports['calibration']['storage_integrity']['record_bytes']=304
        with self.assertRaises(AssertionError):self.check()
    def test_recovery_erases_calibration(self):
        self.target['recovery_binding']['calibration_settings_erase_binding']=True
        with self.assertRaises(AssertionError):self.check()
    def test_wrong_GPIO_mutation_accepted(self):
        self.reports['gpio-mode-policy']['rejected_mutants'][0]['exit_code']=0
        with self.assertRaises(AssertionError):self.check()
    def test_analog_model_claims_physical_margin(self):
        self.reports['analog-waveform']['AFE_saturation_qualified']=True
        with self.assertRaises(AssertionError):self.check()
    def test_physical_result_is_not_inherited(self):
        self.reports['key-pipeline']['physical_verification']=True
        with self.assertRaises(AssertionError):self.check()
    def test_USB_deconfiguration_permission(self):
        self.reports['usb-event-policy']['configuration_zero_rejected']=False
        with self.assertRaises(AssertionError):self.check()
if __name__=='__main__':unittest.main()
