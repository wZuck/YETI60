#!/usr/bin/env python3
"""Screen a measured upstream USB 2.0 attach-current CSV."""

import argparse
import csv
import json
import math
from pathlib import Path


THRESHOLD_A = .100
SPLIT_BELOW_S = .000100
MIN_CAPTURE_S = .100
MAX_SAMPLE_INTERVAL_S = .000001
CHARGE_LIMIT_UC = 50.0
TIME_ROUNDING_S = 1e-12


def subintervals(start, end, left, right):
    """Split a linear sampled span at its 100 mA crossing."""
    if left * right < 0:
        crossing = start + (end - start) * left / (left - right)
        yield start, crossing, left, 0
        yield crossing, end, 0, right
    else:
        yield start, end, left, right


def excess_regions(samples, uncertainty_a):
    regions = []
    first_rise = None
    region_start = None
    below_since = None
    last_positive_end = None
    charge_uc = 0.0
    for (start, a), (end, b) in zip(samples, samples[1:]):
        if end <= 0:
            continue
        # Capture time zero is the observed VBUS/GND contact.
        if start < 0:
            a += (b - a) * (-start) / (end - start)
            start = 0.0
        left, right = a + uncertainty_a - THRESHOLD_A, b + uncertainty_a - THRESHOLD_A
        for t0, t1, y0, y1 in subintervals(start, end, left, right):
            if max(y0, y1) > 0:
                if region_start is None:
                    region_start = t0
                    charge_uc = 0.0
                if first_rise is None:
                    first_rise = t0
                charge_uc += (t1 - t0) * (y0 + y1) / 2 * 1_000_000
                last_positive_end = t1
                below_since = None
            elif region_start is not None:
                if min(y0, y1) == 0:
                    below_since = None
                    continue
                if below_since is None or y0 == 0:
                    below_since = t0
                if t1 - below_since + TIME_ROUNDING_S >= SPLIT_BELOW_S:
                    regions.append((region_start, last_positive_end, charge_uc))
                    region_start = None
                    below_since = None
    if region_start is not None:
        raise ValueError("Capture ended before a region returned below 100 mA for 100 µs")
    if first_rise is not None and samples[-1][0] - first_rise + TIME_ROUNDING_S < MIN_CAPTURE_S:
        raise ValueError("Capture needs at least 100 ms after the first inrush region starts")
    return regions


def screen(samples, uncertainty_ma=0.0):
    if not math.isfinite(uncertainty_ma) or uncertainty_ma < 0:
        raise ValueError("Current uncertainty must be finite and non-negative")
    if any(not math.isfinite(v) for sample in samples for v in sample):
        raise ValueError("Time and current samples must be finite")
    if len(samples) < 2 or samples[0][0] > 0 or samples[-1][0] + TIME_ROUNDING_S < MIN_CAPTURE_S:
        raise ValueError("Capture must cover contact at 0 s through at least 100 ms after contact")
    intervals = [b[0] - a[0] for a, b in zip(samples, samples[1:])]
    if min(intervals) <= 0:
        raise ValueError("Time samples must be strictly increasing")
    longest_interval = max(intervals)
    if longest_interval > MAX_SAMPLE_INTERVAL_S + TIME_ROUNDING_S:
        raise ValueError("Sample interval exceeds 1 µs. Use at least 1 MS/s with no decimation")
    regions = excess_regions(samples, uncertainty_ma / 1000)
    peak_uc = max((charge for _, _, charge in regions), default=0.0)
    return {
        "scope": "USB 2.0 attach bench screen of supplied trace",
        "charge_limit_uC": CHARGE_LIMIT_UC,
        "maximum_region_charge_uC": round(peak_uc, 6),
        "within_charge_limit": peak_uc <= CHARGE_LIMIT_UC + 1e-9,
        "sample_count": len(samples),
        "maximum_sample_interval_us": round(longest_interval * 1e6, 6),
        "current_uncertainty_added_mA": uncertainty_ma,
        "regions": [
            {"first_crossing_s": round(start, 9), "last_above_threshold_s": round(end, 9),
             "excess_charge_uC": round(charge_uc, 6)}
            for start, end, charge_uc in regions
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="CSV with time_s and current_a columns")
    parser.add_argument("--current-uncertainty-ma", type=float, default=0.0,
                        help="Add the stated absolute probe uncertainty in mA to every sample")
    args = parser.parse_args()
    try:
        with args.capture.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not {"time_s", "current_a"} <= set(reader.fieldnames or ()):
                raise ValueError("CSV needs time_s and current_a columns")
            samples = [(float(row["time_s"]), float(row["current_a"])) for row in reader]
        result = screen(samples, args.current_uncertainty_ma)
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))
    return 0 if result["within_charge_limit"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
