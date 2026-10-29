#!/usr/bin/env python3
"""An otherwise plausible fabrication archive must identify the chosen MCU."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('variants',ROOT/'scripts/run_all_variants.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class VariantPackages(unittest.TestCase):
    def check(self, actual, expected):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'review.zip'
            with zipfile.ZipFile(path,'w') as archive:
                archive.writestr('manifest.json',json.dumps({'controller_module':actual,
                    'copper_layers':['F.Cu','In1.Cu','In2.Cu','B.Cu'],'blind_drill_hits':0,'placement_parts':76}))
            return module.verify_archive(path,expected)

    def test_reject_raytac_package_for_e73(self):
        with self.assertRaisesRegex(AssertionError,'different module'):
            self.check('MDBT50Q-1MV2','E73-2G4M08S1C')

    def test_reject_e73_package_for_raytac(self):
        with self.assertRaisesRegex(AssertionError,'different module'):
            self.check('E73-2G4M08S1C','MDBT50Q-1MV2')

    def test_accept_matching_module(self):
        for name in ['E73-2G4M08S1C','MDBT50Q-1MV2']:
            self.assertEqual(self.check(name,name)['module'],name)


if __name__=='__main__':
    unittest.main(verbosity=2)
