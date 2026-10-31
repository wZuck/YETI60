#!/usr/bin/env python3
"""Reject the old alternative-layout choices at right Shift and Fn."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('geometry', ROOT/'scripts/check_yeti60_key_geometry.py')
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


class PlateKeyMapping(unittest.TestCase):
    def setUp(self):
        native = json.loads((ROOT/'.assembly-work/build-map.json').read_text())
        plate = json.loads((ROOT/'docs/audit/yeti60-assembly.json').read_text())['active_key_positions']
        self.matches = geometry.identify(native, plate)
        self.dts = geometry.DTS.read_text()
        self.scanner = geometry.SCANNER.read_text()
        geometry.verify(self.matches, self.dts, self.scanner)

    def test_reject_old_right_shift_column(self):
        self.assertIn('RC(3,13)', self.dts)
        with self.assertRaisesRegex(AssertionError, 'Firmware transform'):
            geometry.verify(self.matches, self.dts.replace('RC(3,13)', 'RC(3,12)'), self.scanner)

    def test_reject_old_fn_row(self):
        self.assertIn('RC(3,14)', self.dts)
        with self.assertRaisesRegex(AssertionError, 'Firmware transform'):
            geometry.verify(self.matches, self.dts.replace('RC(3,14)', 'RC(4,14)'), self.scanner)

    def test_reject_old_calibration_masks(self):
        with self.assertRaisesRegex(AssertionError, 'Calibration active mask'):
            geometry.verify(self.matches, self.dts,
                            self.scanner.replace('0x6ffd', '0x1ffd').replace('0x0646', '0x4646'))


if __name__=='__main__':
    unittest.main(verbosity=2)
