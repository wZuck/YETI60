#!/usr/bin/env python3
"""Independent E73 ground/USB geometry screen, with a real pre-repair regression.

Run with requirements-audit.txt / CPython 3.14.7 after the native candidate
check. The CLI exports both boards using KiCad; no PCB is edited here.
This is not an impedance, current-distribution, eye or EMC solver.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union
from shapely import make_valid

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/e73-usb-repair'
BASELINE = 'aaa3292547c9831fd3fddfc1c02d843156aec34a'
PCB_NAME = 'EC60-nRF52840.kicad_pcb'
GROUND_HELPER = ROOT / 'variants/raytac/scripts/usb_short_ground.py'
REFERENCE_HELPER = ROOT / 'variants/raytac/scripts/study_yeti60_prototype.py'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


GROUND = module('e73_shared_ground_geometry', GROUND_HELPER)
REFERENCE = module('e73_shared_reference_geometry', REFERENCE_HELPER)


def hashes(record):
    for name, digest in record.items():
        assert sha(ROOT / name) == digest, ('Stale return input', name)


def analyze(native):
    # Connectivity and coverage must use the same valid planar geometry.
    # Native weakly simple zone rings may otherwise be interpreted differently
    # by buffer(0) and make_valid. Retain every positive-area polygon piece.
    native = copy.deepcopy(native)
    normalizations = []
    for layer, records in native['ground_copper'].items():
        valid = []
        for record in records:
            polygon = Polygon(record['outer'], record['holes'])
            if polygon.is_valid:
                valid.append(record)
                continue
            fixed = make_valid(polygon)
            delta = abs(fixed.area - polygon.area)
            assert delta < .01, 'Native copper normalization exceeds 0.01 mm2'
            normalizations.append({'layer': layer, 'bounds_pcb_mm': list(polygon.bounds),
                                   'original_area_mm2': polygon.area, 'area_delta_mm2': delta})
            valid.extend(polygon_records(fixed))
        native['ground_copper'][layer] = valid
    faults = []
    try:
        ground = GROUND.connected_ground(native)
    except AssertionError as error:
        ground = {'status': 'disconnected', 'reason': str(error)}
        faults.append('independent-ground-connectivity')
    reference, copper, additional_normalizations = REFERENCE.usb_study(native, native['USB_paths'])
    assert not additional_normalizations, 'Coverage renormalized the connected-ground geometry'
    for side in ['negative', 'positive']:
        row = reference[side]
        corridors = [LineString([e['start'], e['end']]).buffer(e['width_mm'] / 2, quad_segs=16)
                     for e in native['USB_paths'][side]['ordered_path'] if e['kind'] == 'trace']
        trace_area = unary_union(corridors)
        missing = trace_area.difference(copper['In2.Cu'])
        row['trace_footprint_mm2'] = trace_area.area
        row['uncovered_trace_footprint_mm2'] = missing.area
        row['nearest_adjacent_GND_trace_footprint_fraction'] = 1 - missing.area / trace_area.area
        # Check every actual primitive and land, including copper inside a pad
        # bypassed by the contacted-item graph's shortest centerline route.
        net = 'USB_DM' if side == 'negative' else 'USB_DP'
        whole = native['USB_all_copper'][net]
        shapes = [make_valid(Polygon(p['outer'], p['holes']))
                  for item in whole['tracks'] + whole['pads'] for p in item['polygons']]
        all_copper = unary_union(shapes)
        all_missing = all_copper.difference(copper['In2.Cu'])
        row['all_native_USB_copper_mm2'] = all_copper.area
        row['all_native_USB_copper_uncovered_mm2'] = all_missing.area
        row['all_native_USB_copper_reference_fraction'] = 1 - all_missing.area / all_copper.area
        row['native_track_primitives'] = len(whole['tracks'])
        row['native_lands'] = len(whole['pads'])
        if row['uncovered_nearest_adjacent_GND_centerline_mm'] > .000001 or missing.area > .000001 or all_missing.area > .000001:
            faults.append(side + '-reference-gap')
    return {'status': 'return-geometry-passed' if not faults else 'requires-return-repair',
            'faults': faults, 'independent_ground_connectivity': ground,
            'USB_reference': reference, 'polygon_normalizations': normalizations,
            'scope': 'Actual filled ground, conductors and plated bridges; full trace-footprint and centerline reference coverage',
            'coupling_screen_limit': 'The 0.75 mm partner-distance statistic is a project geometry probe, not a USB impedance/compliance requirement'}


def polygon_records(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Polygon':
        return [{'outer': list(geometry.exterior.coords),
                 'holes': [list(r.coords) for r in geometry.interiors]}]
    if hasattr(geometry, 'geoms'):
        return [row for g in geometry.geoms for row in polygon_records(g)]
    return []  # Zero-area linework is not conducting copper.


def injected_faults(native, baseline_result):
    assert baseline_result['status'] == 'requires-return-repair'
    assert all(baseline_result['USB_reference'][side]['uncovered_nearest_adjacent_GND_centerline_mm'] >= .70
               for side in ['negative', 'positive']), 'Pre-repair COL14 gap did not reproduce'
    cut = copy.deepcopy(native)
    longest = max((e for e in native['USB_paths']['positive']['ordered_path'] if e['kind'] == 'trace'), key=lambda e: e['length_mm'])
    midpoint = LineString([longest['start'], longest['end']]).interpolate(.5, normalized=True)
    stripe = box(midpoint.x - 2, midpoint.y - .3, midpoint.x + 2, midpoint.y + .3)
    cut['ground_copper']['In2.Cu'] = [row for p in cut['ground_copper']['In2.Cu']
                                     for row in polygon_records(make_valid(Polygon(p['outer'], p['holes'])).difference(stripe))]
    failed_reference = analyze(cut)
    assert failed_reference['status'] == 'requires-return-repair'
    assert 'positive-reference-gap' in failed_reference['faults'], 'A real missing ground stripe was missed'
    unplated = copy.deepcopy(native)
    unplated['ground_vertical_connectors'] = []
    failed_ground = analyze(unplated)
    assert 'independent-ground-connectivity' in failed_ground['faults'], 'Missing plated ground bridges were missed'
    return [{'case': 'pre-repair-COL14-reference-crossing', 'detected': True},
            {'case': 'cut-exported-In2-ground-under-USB', 'detected': True,
             'stripe_bounds_pcb_mm': list(stripe.bounds), 'faults': failed_reference['faults']},
            {'case': 'remove-all-plated-ground-bridges', 'detected': True}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-python', default='/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3')
    args = parser.parse_args()
    for name in ['return-check.json', 'return-faults.json']:
        (BASE / 'audit' / name).unlink(missing_ok=True)
    build = json.loads((BASE / 'audit/build.json').read_text())
    proof = json.loads((BASE / 'audit/native-check.json').read_text())
    hashes(build['source_sha256']); hashes(build['outputs']); hashes(proof['source_sha256'])
    assert proof['status'] == 'e73-usb-native-candidate-checks-passed'
    workspace = ROOT / '.assembly-work/e73-return-screen'
    workspace.mkdir(parents=True, exist_ok=True)
    baseline_board = workspace / PCB_NAME
    baseline_bytes = subprocess.check_output(['git', 'show', BASELINE + ':hardware/e73-usb-repair/' + PCB_NAME], cwd=ROOT)
    baseline_board.write_bytes(baseline_bytes)
    baseline_digest = sha(baseline_board)
    records = {}
    for name, path in [('baseline', baseline_board), ('current', BASE / PCB_NAME)]:
        target = workspace / (name + '-ground.json')
        subprocess.run([args.kicad_python, str(ROOT / 'scripts/export_e73_usb_ground.py'), '--pcb', str(path), '--output', str(target)], check=True, capture_output=True)
        records[name] = json.loads(target.read_text())
        hashes(records[name]['source_sha256'])
    baseline = analyze(records['baseline'])
    current = analyze(records['current'])
    sources = {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), GROUND_HELPER, REFERENCE_HELPER,
               ROOT / 'scripts/export_e73_usb_ground.py', BASE / 'audit/native-check.json', BASE / 'audit/build.json']}
    report = {**current, 'baseline': {'commit': BASELINE, 'PCB_sha256': baseline_digest, 'result': baseline},
              'manufacturing_released': False, 'physical_verification': False,
              'selected_by_assembly': False, 'source_sha256': sources,
              'native_export_sha256': {name: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest() for name, value in records.items()},
              'limits': ['Host-board geometry only; C5, cable and module-internal return paths are excluded',
                         'No dielectric/impedance, return-current, propagation delay, eye, ADC-noise or RF qualification',
                         'Polygon approximation, bounded validity normalization and nanometre joining are disclosed by the geometry helpers']}
    (BASE / 'audit/return-check.json').write_text(json.dumps(report, indent=2) + '\n')
    if current['status'] != 'return-geometry-passed':
        print(json.dumps(current, indent=2))
        raise SystemExit(2)
    cases = injected_faults(records['current'], baseline)
    tests = {'status': 'passed', 'cases': cases, 'physical_verification': False,
             'source_sha256': {**sources, 'hardware/e73-usb-repair/audit/return-check.json': sha(BASE / 'audit/return-check.json')}}
    (BASE / 'audit/return-faults.json').write_text(json.dumps(tests, indent=2) + '\n')
    print(current['status'], 'ground components:', current['independent_ground_connectivity'].get('connected_components'))
    for side in ['negative', 'positive']:
        print(side, current['USB_reference'][side])
    print('Reference fault cases:', len(cases))
    raise SystemExit(0 if current['status'] == 'return-geometry-passed' else 2)


if __name__ == '__main__':
    main()
