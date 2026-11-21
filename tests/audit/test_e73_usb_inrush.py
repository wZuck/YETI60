#!/usr/bin/env python3
"""Exercise attach region timing, interpolation and capture validation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from check_e73_usb_inrush import excess_regions, screen


def two_pulses(gap):
    """Two 30 µC pulses with short, linear threshold transitions."""
    start_second = .000202 + gap
    return [
        (0, .10), (.000001, .25), (.000200, .25), (.000201, .10),
        (.000202, .05), (start_second, .05), (start_second + .000001, .10),
        (start_second + .000002, .25), (start_second + .000201, .25),
        (start_second + .000202, .10), (start_second + .000203, .05), (.110, .05),
    ]


class InrushScreen(unittest.TestCase):
    def test_short_dip_keeps_pulses_in_one_region(self):
        result = excess_regions(two_pulses(.000080), 0)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0][2], 60)

    def test_long_dip_separates_pulses(self):
        result = excess_regions(two_pulses(.000120), 0)
        self.assertEqual(len(result), 2)
        for _, _, charge in result:
            self.assertAlmostEqual(charge, 30)

    def test_threshold_plateau_does_not_count_as_below(self):
        result = excess_regions([
            (0, .10), (.0002, .25), (.0004, .10), (.0008, .10),
            (.0010, .25), (.0012, .10), (.0013, 0), (.110, 0),
        ], 0)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0][2], 60)

    def test_capture_rising_from_below_integrates_positive_triangle(self):
        result = excess_regions([
            (0, 0), (.000002, .20), (.000004, 0), (.110, 0),
        ], 0)
        self.assertAlmostEqual(result[0][0], .000001)
        self.assertAlmostEqual(result[0][1], .000003)
        self.assertAlmostEqual(result[0][2], .1)

    def test_flat_capture_uses_sample_rate_and_uncertainty(self):
        trace = [(i / 1e6, .097) for i in range(100_001)]
        self.assertTrue(screen(trace, 2)["within_charge_limit"])
        with self.assertRaisesRegex(ValueError, "ended before"):
            screen(trace, 4)
        with self.assertRaisesRegex(ValueError, "exceeds 1"):
            screen(trace[::2])


if __name__ == "__main__":
    unittest.main()
