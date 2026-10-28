#!/usr/bin/env python3
"""Fault injection: current integration must reject contradictory/stale evidence."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('integration', ROOT / 'scripts/check_project_integration.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


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

    def test_reversed_usb_data_contract(self):
        self.rejects('hardware/ec60-nrf52840/components.json',
                     lambda data: data['J1']['pins'].update({'2': 'D+', '3': 'D-'}))

    def test_stale_simulation_trace(self):
        self.rejects('docs/audit/yeti60-firmware-simulation.json',
                     lambda data: data.update(trace_sha256='0' * 64))

    def test_component_case_collision(self):
        self.rejects('docs/audit/yeti60-assembly.json',
                     lambda data: data.update(colliding_envelopes=['injected collision']))

    def test_partial_render_keeps_stale_view(self):
        self.rejects('renders/yeti60-assembly/render-manifest.json',
                     lambda data: data['outputs']['rear.png'].update(recipe_sha256='0' * 64))

    def test_changed_image_bytes(self):
        original = audit.sha
        path = ROOT / 'renders/yeti60-assembly/assembled.png'
        with patch.object(audit, 'sha', side_effect=lambda candidate: '0' * 64 if candidate == path else original(candidate)):
            with self.assertRaisesRegex(AssertionError, 'Changed render asset'):
                audit.verify()


if __name__ == '__main__':
    unittest.main(verbosity=2)
