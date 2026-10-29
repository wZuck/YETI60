#!/usr/bin/env python3
"""Reject module/pin substitutions that could pass generic nRF connectivity."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('e73',ROOT/'scripts/check_e73_variant.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class E73Contract(unittest.TestCase):
    def setUp(self):
        self.profile=json.loads((ROOT/'hardware/module-options/e73.json').read_text())
        self.part=json.loads((module.HW/'components.json').read_text())['U1']
        self.pinmap=json.loads((module.HW/'pinmap.json').read_text())

    def test_reject_old_raytac_adc_even_if_both_contracts_agree(self):
        for contract in [self.part['pins'],self.pinmap['module_pin_nets']]:
            contract['20']=contract.pop('4')
        with self.assertRaisesRegex(AssertionError,'pin assignment'):
            module.verify_pin_contract(self.profile,self.part,self.pinmap)

    def test_reject_missing_vddh_connection(self):
        del self.part['pins']['23']
        with self.assertRaisesRegex(AssertionError,'pin assignment'):
            module.verify_pin_contract(self.profile,self.part,self.pinmap)

    def test_reject_different_ebyte_variant(self):
        self.part['value']='E73-2G4M04S'
        with self.assertRaisesRegex(AssertionError,'Wrong module'):
            module.verify_pin_contract(self.profile,self.part,self.pinmap)

    def test_reject_omitted_hidden_gpio_land(self):
        del self.pinmap['module_pin_nets']['12']
        with self.assertRaisesRegex(AssertionError,'pin assignment'):
            module.verify_pin_contract(self.profile,self.part,self.pinmap)


if __name__=='__main__':
    unittest.main(verbosity=2)
