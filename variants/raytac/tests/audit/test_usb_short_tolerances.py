"""Reject optimistic or mislabelled tolerance evidence, using current geometry."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from study_usb_short_tolerances import BASE, ROOT, budget, read, validate, verify_evidence


class ToleranceEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(BASE/'audit/tolerance-diagnostic.json')
        cls.spec = read(ROOT/'mechanical/assembly-spec.raytac.json')
        cls.fabrication = read(ROOT/'mechanical/pcb-fabrication-spec.json')
        verify_evidence(cls.report, cls.spec, cls.fabrication)

    def test_both_shells_have_same_locator_limit(self):
        interfaces = self.report['measured_interfaces']
        for name in ('plate-top', 'plate-bottom'):
            self.assertAlmostEqual(interfaces[name]['nominal_gap_mm'], .25, places=5)

    def test_actual_finished_thickness_used(self):
        rows = budget(self.report['measured_interfaces'], self.spec, self.fabrication)
        switch = next(r for r in rows if r['interface'] == 'SW100-bottom')
        self.assertAlmostEqual(switch['known_directional_allowances_mm']['finished_PCB_downward_growth'], .1538)
        self.assertAlmostEqual(switch['optimistic_remaining_gap_mm'], .0562)

    def test_profile_approximation_consumes_locator_reserve(self):
        rows = budget(self.report['measured_interfaces'], self.spec, self.fabrication)
        for row in rows[:2]:
            self.assertEqual(row['known_directional_allowances_mm']['plate_CAD_chord_error'], .002)
            self.assertAlmostEqual(row['optimistic_remaining_gap_mm'], .098, places=5)

    def test_ordinary_thicker_board_consumes_more_reserve(self):
        normal = budget(self.report['measured_interfaces'], self.spec, self.fabrication)[2]
        larger = copy.deepcopy(self.fabrication)
        larger['ordinary_thickness_acceptance_range_mm'][1] += .1
        changed = budget(self.report['measured_interfaces'], self.spec, larger)[2]
        self.assertAlmostEqual(changed['optimistic_remaining_gap_mm'], normal['optimistic_remaining_gap_mm']-.1)

    def test_tighter_case_tolerance_does_not_close_unknown_terms(self):
        smaller = copy.deepcopy(self.spec)
        smaller['case']['linear_tolerance'] = .01
        for row in budget(self.report['measured_interfaces'], smaller, self.fabrication):
            self.assertFalse(row['combined_tolerance_qualified'])
            self.assertTrue(row['unquantified_terms'])

    def test_nominal_pass_cannot_be_relabelled_tolerance_pass(self):
        report = copy.deepcopy(self.report)
        report['directional_budgets'][0]['conditional_screen'] = 'passed'
        with self.assertRaises(AssertionError):
            validate(report)

    def test_incomplete_allowance_subtotal_rejected(self):
        report = copy.deepcopy(self.report)
        report['directional_budgets'][2]['known_directional_allowances_mm'].pop('finished_PCB_downward_growth')
        with self.assertRaises(AssertionError):
            validate(report)

    def test_missing_top_shell_rejected(self):
        report = copy.deepcopy(self.report)
        report['directional_budgets'].pop(0)
        with self.assertRaises(AssertionError):
            validate(report)

    def test_consistently_rewritten_allowance_omission_rejected(self):
        report = copy.deepcopy(self.report)
        row = report['directional_budgets'][2]
        removed = row['known_directional_allowances_mm'].pop('finished_PCB_downward_growth')
        row['known_allowance_sum_mm'] -= removed
        row['optimistic_remaining_gap_mm'] += removed
        row['additional_clearance_needed_before_unknown_terms_mm'] = 0.
        row['conditional_screen'] = 'unknown-terms-open'
        validate(report)  # Internally consistent arithmetic is not sufficient.
        with self.assertRaisesRegex(AssertionError, 'incomplete directional tolerance'):
            verify_evidence(report, self.spec, self.fabrication)

    def test_incomplete_diagnostic_cannot_release_manufacturing(self):
        for flag in ('manufacturing_released', 'physical_verification', 'combined_tolerance_qualified'):
            with self.subTest(flag=flag):
                report = copy.deepcopy(self.report)
                report[flag] = True
                with self.assertRaises(AssertionError):
                    validate(report)


if __name__ == '__main__':
    unittest.main()
