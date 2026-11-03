"""Reject stale purchases and reverting the enlarged power capacitor lands."""
import copy
import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import usb_short_passive_contract as contract
from kicad_sexpr import child, children, dumps, loads


class PassiveFailures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        for name in ['EC60-nRF52840.kicad_pcb', 'netlist.xml', 'power-passives.json',
                     'frozen-footprints.json', 'mainboard-purchase.csv', 'mainboard-purchase.zh-CN.csv']:
            shutil.copyfile(contract.BASE / name, self.base / name)
        for p in contract.BASE.glob('*.kicad_sch'):
            shutil.copyfile(p, self.base / p.name)
        shutil.copytree(contract.BASE / 'YAECKB.pretty', self.base / 'YAECKB.pretty')

    def rejected(self):
        with patch.object(contract, 'BASE', self.base):
            with self.assertRaises(AssertionError):
                contract.verify_passives()

    def board_fault(self, mutate):
        p = self.base / 'EC60-nRF52840.kicad_pcb'; b = loads(p.read_text())
        f = next(f for f in children(b, 'footprint') if contract.properties(f)['Reference'] == 'C40')
        mutate(f); p.write_text(dumps(b) + '\n'); self.rejected()

    def test_old_0603_lands_rejected(self):
        self.board_fault(lambda f: child(children(f, 'pad')[0], 'size').__setitem__(slice(1, None), [.9, .95]))

    def test_moved_capacitor_rejected(self):
        self.board_fault(lambda f: child(f, 'at').__setitem__(1, 123.9))

    def test_old_value_rejected(self):
        self.board_fault(lambda f: next(p for p in children(f, 'property') if p[1] == 'Value').__setitem__(2, '1u/10V'))

    def csv_fault(self, suffix, field, value):
        p = self.base / ('mainboard-purchase' + suffix + '.csv')
        with p.open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        keys = list(rows[0])
        next(r for r in rows if r[keys[0]] == 'J1')[keys[field]] = value
        with p.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
        self.rejected()

    def test_stale_english_connector_name_rejected(self):
        self.csv_fault('', 4, 'REAR_USB_DAUGHTERBOARD')

    def test_stale_chinese_connector_name_rejected(self):
        self.csv_fault('.zh-CN', 4, 'REAR_USB_DAUGHTERBOARD')

    def test_wrong_package_rejected(self):
        p = self.base / 'mainboard-purchase.csv'; s = p.read_text(); p.write_text(s.replace('C_0805_2012Metric', 'C_0603_1608Metric', 1)); self.rejected()

    def test_lower_effective_capacitance_rejected(self):
        p = self.base / 'power-passives.json'; s = json.loads(p.read_text()); s['capacitors']['C41']['effective_target_uF'] = 2.2
        p.write_text(json.dumps(s)); self.rejected()

    def test_all_geometry_consumers_receive_revised_bounds(self):
        spec = json.loads((self.base / 'power-passives.json').read_text())
        assembly = {'nominal_stack': {'pcb_bottom_z': -2}, 'component_envelopes': [dict(ref=r) for r in sorted(contract.REVISED)]}
        native = {'revised_passives': [dict(ref=r, bbox_pcb_mm=[c['position'][0]-1.7, c['position'][1]-1.7, c['position'][0]+1.7, c['position'][1]+1.7], **c) for r, c in spec['capacitors'].items()]}
        original = copy.deepcopy(assembly); result = contract.apply_passive_envelopes(assembly, native)
        self.assertEqual(assembly, original)
        c32 = next(p for p in result['component_envelopes'] if p['ref'] == 'C32')
        self.assertEqual(c32['position_pcb_mm'], [346.4, 118])
        self.assertAlmostEqual(c32['render_body_bounds_case_mm'][3]-c32['render_body_bounds_case_mm'][0], 1.45)
        self.assertAlmostEqual(c32['render_body_bounds_case_mm'][4]-c32['render_body_bounds_case_mm'][1], 2.2)
        self.assertEqual(c32['bounds_case_mm'][2], -5)


if __name__ == '__main__':
    unittest.main()
