#!/usr/bin/env python3
"""Fault injection: current integration must reject contradictory/stale evidence."""
import copy
import importlib.util
import json
import tempfile
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('integration', ROOT / 'scripts/check_project_integration.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
materials_spec = importlib.util.spec_from_file_location('materials', ROOT / 'scripts/check_yeti60_materials.py')
materials = importlib.util.module_from_spec(materials_spec)
materials_spec.loader.exec_module(materials)


class SharedLinkFailures(unittest.TestCase):
    def test_missing_shared_source_rejected(self):
        with tempfile.TemporaryDirectory(prefix='yeti60-link-') as folder:
            link = Path(folder)/'zmk'
            link.symlink_to(Path(folder)/'missing-upstream', target_is_directory=True)
            with self.assertRaisesRegex(AssertionError, 'Broken tracked shared link'):
                audit.verify_shared_links([link])


class MechanicalProseFailures(unittest.TestCase):
    def setUp(self):
        self.texts = {name: (ROOT/name).read_text() for name in materials.MECHANICAL_PROSE}
        self.mechanism = json.loads((ROOT/'mechanical/yeti60-key-mechanism.json').read_text())
        materials.verify_mechanical_prose(self.texts, self.mechanism)

    def test_old_mount_count_in_either_inventory_language(self):
        for name, old, wrong in [
            ('docs/engineering/inventory-allocation.md', 'Need 28 M1.6', 'Need 29 M1.6'),
            ('docs/engineering/inventory-allocation.zh-CN.md', '需要 28 只', '需要 29 只'),
        ]:
            with self.subTest(name=name):
                texts = dict(self.texts)
                texts[name] = texts[name].replace(old, wrong)
                with self.assertRaisesRegex(AssertionError, 'Stale mechanism prose'):
                    materials.verify_mechanical_prose(texts, self.mechanism)

    def test_old_plate_thickness_in_either_render_language(self):
        for name in ['renders/yeti60-assembly/README.md', 'renders/yeti60-assembly/README.zh-CN.md']:
            with self.subTest(name=name):
                texts = dict(self.texts)
                texts[name] = texts[name].replace('1.6', '1.2')
                with self.assertRaisesRegex(AssertionError, 'Stale mechanism prose'):
                    materials.verify_mechanical_prose(texts, self.mechanism)

    def test_old_count_in_acceptance(self):
        texts = dict(self.texts)
        texts['docs/testing/README.md'] = texts['docs/testing/README.md'].replace('28 installed mounts', '29 installed mounts')
        with self.assertRaisesRegex(AssertionError, 'Stale mechanism prose'):
            materials.verify_mechanical_prose(texts, self.mechanism)


class EvidenceFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Otherwise a pre-existing failure could make every negative test pass.
        assert audit.verify()['status'] == 'passed'

    def rejects(self, relative_path, mutate):
        original = audit.read
        path = ROOT / relative_path

        def injected(candidate):
            data = original(candidate)
            if candidate == path:
                data = copy.deepcopy(data)
                mutate(data)
            return data

        with patch.object(audit, 'read', side_effect=injected):
            with self.assertRaises(AssertionError):
                audit.verify()

    def test_short_scan_event_queue_rejected(self):
        self.rejects('docs/audit/scan-control.json',
                     lambda data: data.update(event_queue_capacity=4))

    def test_key_pipeline_cannot_claim_physical_acceptance(self):
        self.rejects('docs/audit/key-pipeline.json',
                     lambda data: data.update(physical_verification=True))

    def test_key_pipeline_missing_Fn_coverage_rejected(self):
        self.rejects('docs/audit/key-pipeline.json',
                     lambda data: data['positive_cases'][1].update(checked=0))

    def test_key_pipeline_wrong_candidate_rollover_rejected(self):
        self.rejects('hardware/usb-short-route/firmware/key-pipeline.json',
                     lambda data: data['resolved_HID_configuration'].update(CONFIG_ZMK_HID_KEYBOARD_REPORT_SIZE='60'))

    def test_missing_candidate_connection_check_rejected(self):
        self.rejects('hardware/usb-short-route/audit/native-check.json',
                     lambda data: data['physical_pin_pairs'].pop())

    def test_failed_candidate_connection_check_rejected(self):
        self.rejects('hardware/usb-short-route/audit/native-check.json',
                     lambda data: data['physical_pin_pairs'][0].update(connected=False))

    def test_missing_unused_fullscale_coverage_rejected(self):
        self.rejects('docs/audit/scan-control.json',
                     lambda data: data['inactive_idle'].update(unused_fullscale_positions=0))

    def test_incorrect_idle_gate_count_rejected(self):
        self.rejects('docs/audit/scan-control.json',
                     lambda data: data['inactive_idle'].update(idle_sleeps=0))

    def test_missed_idle_short_tap_rejected(self):
        self.rejects('docs/audit/scan-control.json',
                     lambda data: data['idle_short_tap'].update(presses=0))

    def test_missing_single_frame_noise_trial_rejected(self):
        self.rejects('docs/audit/scan-control.json',
                     lambda data: data['idle_short_tap'].update(single_frame_spikes=0))

    def test_duplicate_compiled_matrix_position_rejected(self):
        self.rejects('docs/audit/scan-control.json',
                     lambda data: data['compiled_matrix_positions'].__setitem__(0,data['compiled_matrix_positions'][1]))

    def test_unchecked_calibration_storage_rejected(self):
        self.rejects('docs/audit/calibration.json',
                     lambda data: data['storage_integrity'].update(independent_zlib_records=0))

    def test_missing_NVS_recovery_trials_rejected(self):
        self.rejects('docs/audit/nvs-powercut.json',
                     lambda data: data.update(total_cut_trials=0))

    def test_NVS_model_cannot_claim_physical_acceptance(self):
        self.rejects('docs/audit/nvs-powercut.json',
                     lambda data: data.update(physical_verification=True))

    def test_host_storage_checks_cannot_claim_physical_power_cut(self):
        self.rejects('docs/audit/calibration.json',
                     lambda data: data['storage_integrity'].update(physical_power_cut_tested=True))

    def test_missing_scan_fault_mutants_rejected(self):
        self.rejects('docs/audit/scan-control.json',
                     lambda data: data.update(rejected_mutants=[]))

    def test_host_scanner_test_cannot_claim_physical_acceptance(self):
        self.rejects('docs/audit/scan-control.json',
                     lambda data: data.update(physical_verification=True))

    def test_candidate_reference_gap_rejected(self):
        self.rejects('hardware/usb-short-route/audit/geometry-check.json',
                     lambda data: data['USB_reference_screen']['positive'].update(nearest_adjacent_GND_coverage_fraction=.8))

    def test_candidate_stale_firmware_binding_rejected(self):
        self.rejects('hardware/usb-short-route/firmware/manifest.json',
                     lambda data: data.update(native_acceptance_sha256='0'*64))

    def test_reversed_usb_data_contract(self):
        self.rejects('hardware/ec60-nrf52840/components.json',
                     lambda data: data['J1']['pins'].update({'2': 'D+', '3': 'D-'}))

    def test_stale_simulation_trace(self):
        self.rejects('docs/audit/yeti60-firmware-simulation.json',
                     lambda data: data.update(trace_sha256='0' * 64))

    def test_component_case_collision(self):
        self.rejects('docs/audit/yeti60-assembly.json',
                     lambda data: data.update(colliding_envelopes=['injected collision']))

    def test_inventory_cannot_credit_in_transit_parts(self):
        self.rejects('docs/audit/yeti60-inventory.json',
                     lambda data: data.update(in_transit_credited=1))

    def test_partial_render_keeps_stale_view(self):
        self.rejects('renders/yeti60-assembly/render-manifest.json',
                     lambda data: data['outputs']['rear.png'].update(recipe_sha256='0' * 64))

    def test_spacebar_conflicting_support(self):
        self.rejects('docs/audit/yeti60-assembly.json',
                     lambda data: data['mounting_hole_matches'][0].update(pcb_ref='H26'))

    def test_old_upper_gasket_stock(self):
        self.rejects('docs/audit/yeti60-assembly.json',
                     lambda data: data['gasket_stock_mm'].update(top=2.0))

    def test_missing_stabilizer_stems(self):
        self.rejects('renders/yeti60-assembly/render-manifest.json',
                     lambda data: data['exploded_visible_objects_by_group'].update(stabilizers=9))

    def test_research_cannot_release_an_unqualified_board(self):
        self.rejects('docs/audit/prototype-research.json',
                     lambda data: data.update(bare_board_order_ready=True))

    def test_incomplete_candidate_CAM_records_rejected(self):
        self.rejects('hardware/usb-short-route/audit/fabrication-check.json',
                     lambda data: data['IPC'].update(all_test_records_checked=1))

    def test_CAM_parity_cannot_claim_physical_release(self):
        self.rejects('hardware/usb-short-route/audit/fabrication-check.json',
                     lambda data: data.update(manufacturing_released=True))

    def test_nominal_assembly_cannot_claim_tolerance_release(self):
        self.rejects('hardware/usb-short-route/audit/tolerance-diagnostic.json',
                     lambda data: data.update(combined_tolerance_qualified=True))

    def test_top_shell_tolerance_budget_cannot_be_omitted(self):
        self.rejects('hardware/usb-short-route/audit/tolerance-diagnostic.json',
                     lambda data: data['directional_budgets'].pop(0))

    def test_changed_image_bytes(self):
        original = audit.sha
        path = ROOT / 'renders/yeti60-assembly/assembled.png'
        with patch.object(audit, 'sha', side_effect=lambda candidate: '0' * 64 if candidate == path else original(candidate)):
            with self.assertRaisesRegex(AssertionError, 'Changed render asset'):
                audit.verify()


if __name__ == '__main__':
    unittest.main(verbosity=2)
