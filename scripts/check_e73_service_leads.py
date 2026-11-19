#!/usr/bin/env python3
"""Check staged E73 plug movement with constant-length cable routing trials."""

from concurrent.futures import ProcessPoolExecutor
from itertools import product
import json
import math
from pathlib import Path
from unittest.mock import patch

import check_e73_corner_harness as harness
from cad_geometry import bounds, intersection_volume, load
from check_e73_corner_service import (
    AUDIT, BASE, LIFT_MM, MIN_GAP_MM, PORTS, ROOT, WORK, nearest, plug_bounds,
    read, sha, translated_union_bounds, verify,
)
from check_yeti60_assembly import box, distance, move
from check_yeti60_interconnects import near
from e73_corner_harness_paths import envelope_wire
from e73_corner_retention import build
from e73_retention_channels import capture
from e73_service_leads import (
    BATTERY_BOW_RADIUS, BATTERY_BOW_START, BATTERY_GUIDE_STATIONS, PARK_DROP,
    PARK_TRAVEL, flex_routes, position_exits, trial_spec,
)


# Plug motion is axial first, then downward. The battery is disconnected first.
STATES = {
    'seated': (0, 0, 0, 0),
    'J2-halfway': (.5, 0, 0, 0),
    'J2-axial-end': (1, 0, 0, 0),
    'J2-parked': (1, 1, 0, 0),
    'J4-halfway': (1, 1, .5, 0),
    'J4-axial-end': (1, 1, 1, 0),
    'both-parked': (1, 1, 1, 1),
}


def check_guide_channels(installed, routes, spec, guides, delta):
    wire = spec['wire']
    od = wire['insulation_od_max']
    relative_od = od+2*spec['guides']['local_wire_position_allowance']
    installed_od = od+2*wire['case_and_route_position_allowance']
    paths = {(family, pin):path for family, leads in routes.items() for pin, path in leads.items()}
    relative = {key: envelope_wire(path, relative_od) for key, path in paths.items()}
    physical = {key: envelope_wire(path, od) for key, path in paths.items()}
    wide = {key: envelope_wire(path, installed_od) for key, path in paths.items()}
    count = 0
    gaps = []
    for part in guides:
        solid = move(part['shape'], z=delta) if part['mount'].startswith('PCB') else part['shape']
        if part.get('category') != 'retention-film':
            sockets = capture(part, relative, installed, spec, delta)
            assert all(row['captured'] for row in sockets), (part['name'], sockets)
            count += len(sockets)
        bb = bounds(solid)
        for key in paths:
            if key[0] == part['family']:
                wire_shape = physical[key]
                if near(bb, bounds(wire_shape), 0) and distance(solid, wire_shape) < 1e-6:
                    assert intersection_volume(solid, wire_shape) < 1e-6, (part['name'], key)
            else:
                wire_shape = wide[key]
                if near(bb, bounds(wire_shape), .26):
                    gaps.append((distance(solid, wire_shape)-.10, part['name'], key))
    worst = min(gaps, default=(.16, None, None))
    assert worst[0] >= MIN_GAP_MM-1e-6, worst
    return {'channels_checked': count, 'foreign_route_gap_mm_at_least': min(.16, worst[0])}


def parked_housing_clearance(native, assembly, spec, exits, parked, bottom, delta, case, guides):
    parts = harness.bodies(native, assembly, spec, bottom, delta)
    drift = (0, 0, LIFT_MM)
    deck_sweep = {
        name: box(translated_union_bounds(bounds(shape), drift))
        for name, shape in parts.items() if not name.startswith('C5')}
    thickness = assembly['stack']['pcb_thickness']-delta
    deck_sweep['PCB'] = harness.pcb_solid(bottom+delta, thickness+LIFT_MM)
    fixed = {name: shape for name, shape in parts.items() if name.startswith('C5')}
    fixed['bottom'] = case
    for part in guides:
        shape = part['shape']
        if part['mount'].startswith('PCB'):
            deck_sweep[part['name']] = box(translated_union_bounds(bounds(move(shape, z=delta)), drift))
        else:
            fixed[part['name']] = shape
    for name, count, vx, vy in [('J1', 4, 1, 0), ('J5', 2, 0, -1)]:
        x,y,z = exits[name]
        bb = plug_bounds((x, y, z+delta), count, vx, vy)
        deck_sweep[name+'-plug'] = box(translated_union_bounds(bb, drift))
    results = []
    for ref in PARK_TRAVEL:
        x,y,z = parked[ref]
        housing = box(plug_bounds((x, y, z+delta), *PORTS[ref]))
        stops = nearest(housing, dict(fixed, **deck_sweep), .50)
        assert not stops, (ref, stops)
        results.append({'ref': ref, 'wire_exit_case_mm': [x, y, z+delta],
                        'housing_clearance_to_rigid_objects_mm_greater_than': .50})
    return results


def run_thickness(delta):
    spec = trial_spec(read(ROOT/'hardware/e73-corner-harness-spec.json'))
    retention = read(ROOT/'hardware/e73-corner-retention-spec.json')
    spec['guides'] = dict(retention['guides'], battery_x=BATTERY_GUIDE_STATIONS)
    assembly = read(ROOT/'mechanical/assembly-spec.json')
    native = read(AUDIT/'harness-native.json')
    case = load(ROOT/assembly['geometry']['bottom'])
    bottom, exits = harness.datums(native, assembly, spec)
    installed, _, _ = flex_routes(spec, exits, exits, 0)
    retainers, films = build(spec, case, installed, exits, bottom)
    guides = retainers+films
    lengths = {}
    rows = []
    for name, state in STATES.items():
        print(delta, name, flush=True)
        shifted = position_exits(exits, *state)
        routes, centre, deflection = flex_routes(spec, exits, shifted, delta)
        with patch.object(harness, 'paths', return_value=(routes, centre)):
            evaluation = harness.evaluate(spec, native, assembly, shifted, bottom, case, delta)
        residuals = []
        measured = {}
        for wire in evaluation['wires']:
            assert wire['minimum_bend_radius_mm'] >= spec['wire']['minimum_static_bend_radius']-1e-6, wire
            key = wire['family']+'.'+wire['pin']
            measured[key] = wire['free_length_mm']
            for obstacle, clearance in wire['clearances_mm'].items():
                allowance = math.sqrt(3)*.15+.002 if obstacle in ('top', 'bottom') else 0
                residuals.append((clearance-allowance, key, obstacle))
        residuals.extend((cross['gap_mm'], str(cross['wires']), 'crossing')
                         for cross in evaluation['crossings'])
        worst = min(residuals)
        assert worst[0] >= MIN_GAP_MM-1e-6, (name, delta, worst)
        if name == 'seated':
            lengths = measured
        errors = {key: measured[key]-lengths[key] for key in measured}
        assert max(map(abs, errors.values())) < .06, (name, errors)
        guide_checks = check_guide_channels(installed, evaluation['routes'], spec, guides, delta)
        rows.append(dict(deflection, state=name, residual_gap_mm=worst[0],
                         tightest_route_and_obstacle=list(worst[1:]),
                         minimum_bend_mm=min(wire['minimum_bend_radius_mm'] for wire in evaluation['wires']),
                         free_length_difference_mm=errors, guide_checks=guide_checks,
                         USB_pair_skew_mm=evaluation['USB_geometric_pair_skew_mm']))
    return {'PCB_thickness_mm': assembly['stack']['pcb_thickness']-delta,
            'seated_free_lengths_mm': lengths, 'states': rows,
            'parked_housings': parked_housing_clearance(
                native, assembly, spec, exits, shifted, bottom, delta, case, guides)}


def main():
    service = read(AUDIT/'service-motion.json')
    verify(service)
    board_geometry = read(WORK/'copper.json')
    verify(board_geometry)
    assert service['derived_copper_export_sha256'] == sha(WORK/'copper.json')
    harness_report = read(AUDIT/'harness-study.json')
    declared_inputs = [AUDIT/'service-motion.json', Path(__file__),
                       ROOT/'scripts/e73_service_leads.py',
                       ROOT/'scripts/e73_corner_retention.py', ROOT/'scripts/e73_retention_channels.py',
                       ROOT/'hardware/e73-corner-retention-spec.json']
    inputs = dict(service['source_sha256'], **{str(path.relative_to(ROOT)):sha(path) for path in declared_inputs})
    deltas = [variant['pcb_bottom_shift_mm'] for variant in harness_report['variants']]
    with ProcessPoolExecutor(max_workers=len(deltas)) as pool:
        variants = list(pool.map(run_thickness, deltas))
    assert all(sha(ROOT/path) == digest for path, digest in inputs.items()), 'Inputs changed during trial'
    report = {
        'status': 'service-lead-candidate-poses-passed',
        'selected_for_assembly': False,
        'physical_verification': False,
        'manufacturing_released': False,
        'source_sha256': inputs,
        'battery_axial_travel_mm': PARK_TRAVEL['J2'],
        'USB_axial_travel_mm': PARK_TRAVEL['J4'],
        'housing_downward_travel_mm': PARK_DROP,
        'battery_bow_start_case_x_mm': BATTERY_BOW_START,
        'battery_bow_center_radius_mm': BATTERY_BOW_RADIUS,
        'proposed_battery_guide_case_x_mm': BATTERY_GUIDE_STATIONS,
        'variants': variants,
        'limits': [
            'Discrete poses with exact curve sweeps in each pose. Clearance between poses, actual elastic paths, tool and insulation friction, fatigue, retention force and axial contact strain are open.',
            'Moving wires can feed axially in the proposed guide channels. Physical slack take-up, the cover, the tool and the wiring process must be demonstrated.',
            'Parked housing checks cover the rigid-only deck sweep. They exclude the steel plate and nearby flexible wires.',
        ],
    }
    (AUDIT/'service-leads.json').write_text(json.dumps(report, indent=2)+'\n')
    print(report['status'])


if __name__ == '__main__':
    main()
