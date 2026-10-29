#!/usr/bin/env python3
"""Check shortage arithmetic and reject ambiguous stock reuse."""
import copy
import csv
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('inventory', ROOT / 'scripts/plan_yeti60_inventory.py')
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


class InventoryAllocation(unittest.TestCase):
    def setUp(self):
        self.stock = json.loads(planner.INPUT.read_text())
        with planner.BOM.open() as source:
            self.bom = list(csv.DictReader(source))

    def test_shared_capacitor_pool_shortage_is_not_covered_by_in_transit(self):
        self.stock['mainboard'][0]['received_units'] = 1
        self.stock['mainboard'][0]['in_transit_units'] = 10000
        result = planner.allocate(self.stock, self.bom)
        self.assertEqual(sum(r['from_stock'] for r in result), 7)
        self.assertEqual(sum(r['buy'] for r in result), 69)
        self.assertEqual(next(r for r in result if r['references'] == 'C31')['buy'], 1)

    def test_wrong_footprint_is_rejected(self):
        self.stock['mainboard'][0]['package'] = 'C_0805_2012Metric'
        with self.assertRaisesRegex(AssertionError, 'Package mismatch'):
            planner.allocate(self.stock, self.bom)

    def test_shared_pool_is_labelled_without_inflating_allocated_quantity(self):
        rows = planner.allocate(self.stock, self.bom)
        caps = [r for r in rows if r['references'] in ['C9, C11, C12', 'C31']]
        self.assertEqual(sum(r['from_stock'] for r in caps), 4)
        self.assertTrue(all(r['received_pool_units'] == 100 for r in caps))
        self.assertTrue(all('shared by source row' in planner.stock_note(r) for r in caps))
        self.assertTrue(all('共享' in planner.stock_note(r, True) for r in caps))

    def test_unmatched_parts_are_marked_for_purchase(self):
        rows = planner.allocate(self.stock, self.bom)
        module = next(r for r in rows if r['references'] == 'U1')
        self.assertEqual((module['from_stock'], module['buy']), (0, 1))
        self.assertIn('purchase required', planner.stock_note(module))

    def test_wrong_value_is_rejected(self):
        self.stock['mainboard'][0]['design_values'] = ['15p']
        with self.assertRaisesRegex(AssertionError, 'Value mismatch'):
            planner.allocate(self.stock, self.bom)

    def test_same_pool_cannot_be_imported_twice(self):
        self.stock['mainboard'].append(copy.deepcopy(self.stock['mainboard'][0]))
        with self.assertRaisesRegex(AssertionError, 'Stock pool counted twice'):
            planner.allocate(self.stock, self.bom)

    def test_same_reference_cannot_take_two_allocations(self):
        duplicate = copy.deepcopy(self.stock['mainboard'][0])
        duplicate['source_row'] = 999
        self.stock['mainboard'].append(duplicate)
        with self.assertRaisesRegex(AssertionError, 'Reference allocated twice'):
            planner.allocate(self.stock, self.bom)


if __name__ == '__main__':
    unittest.main(verbosity=2)
