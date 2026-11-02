#!/usr/bin/env python3
"""Check physical-model invariants and geometry holes, not just report presence."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import unittest
from shapely.geometry import LineString, Polygon

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('prototype', ROOT/'scripts/study_yeti60_prototype.py')
study = importlib.util.module_from_spec(spec); spec.loader.exec_module(study)


class ResearchModelChecks(unittest.TestCase):
    def test_a_ground_void_is_not_filled_by_the_screen(self):
        records = [{'outer': [(0, 0), (10, 0), (10, 10), (0, 10)],
                    'holes': [[(4, 4), (6, 4), (6, 6), (4, 6)]]}]
        result = study.coverage(LineString([(0, 5), (10, 5)]), study.ground_shapes(records))
        self.assertAlmostEqual(result['uncovered_centerline_mm'], 2)
        self.assertAlmostEqual(result['covered_fraction'], .8)

    def test_absent_reference_cannot_pass_coverage(self):
        result = study.coverage(LineString([(0, 0), (10, 0)]), Polygon())
        self.assertEqual(result['covered_fraction'], 0)

    def test_thermal_charge_loss_is_conserved(self):
        # At zero system/bias current all dissipated input power is the
        # voltage drop times charge current, not the full battery power.
        self.assertAlmostEqual(study.thermal_power(5, 3.2, .4, 0, iq=0), .72)
        self.assertAlmostEqual(study.thermal_power(5, 3.2, 0, .04, iq=0), .024)

    def test_settling_model_distinguishes_10nF_from_1uF(self):
        # Explicit circuit examples; the actual filter is selected by nets.
        tau, error = study.divider_response(1e6, 1e6, 1e-6, .05)
        self.assertAlmostEqual(tau, .5)
        self.assertGreater(error, .90)
        self.assertLess(4200*(1-error), 401)
        _, corrected = study.divider_response(1e6, 1e6, 10e-9, .05)
        self.assertLess(corrected, .0001)

    def test_filter_selection_uses_nets_not_reference_numbers(self):
        parts = {'C47': '10n', 'C48': '1u/10V'}
        pins = {('C47', '1'): 'BAT_ADC', ('C47', '2'): 'GND',
                ('C48', '1'): 'AFE_3V3', ('C48', '2'): 'GND'}
        caps = study.battery_filter(parts, pins)
        self.assertEqual([c['ref'] for c in caps], ['C47'])
        self.assertAlmostEqual(sum(c['capacitance_F'] for c in caps), 10e-9)
        # Renumbering both capacitors must not change the electrical result.
        renamed_parts = {'C48': '10n', 'C47': '1u/10V'}
        renamed_pins = {(('C48' if r == 'C47' else 'C47'), p): n for (r, p), n in pins.items()}
        caps = study.battery_filter(renamed_parts, renamed_pins)
        self.assertEqual([c['ref'] for c in caps], ['C48'])
        self.assertAlmostEqual(sum(c['capacitance_F'] for c in caps), 10e-9)

    def test_plain_NTC_window_does_not_qualify_requested_pack(self):
        ntc = study.battery_study()['NTC']
        self.assertLess(ntc['nominal_cold_crossing_C_APPROX'], 15)
        self.assertGreater(ntc['nominal_hot_crossing_C_APPROX'], 43)
        self.assertFalse(ntc['includes_NTC_tolerance_thermal_lag_or_self_heating'])

    def test_thread_bottoming_is_rejected(self):
        fit = json.loads((ROOT/'docs/audit/yeti60-assembly.json').read_text())
        good = study.mechanical_study(fit)
        self.assertAlmostEqual(good['female_thread_bottom_clearance_min_mm'], .37)
        bad = copy.deepcopy(fit); bad['selected_fasteners']['bottom_thread_depth'] = 2.5
        with self.assertRaises(AssertionError):
            study.mechanical_study(bad)


if __name__ == '__main__':
    unittest.main(verbosity=2)
