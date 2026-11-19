#!/usr/bin/env python3
"""Screen CORNER-05 unplugging and lift motion against current installed CAD."""

import hashlib
from itertools import product
import json
import math
from pathlib import Path
from unittest.mock import patch

import check_e73_corner_harness as harness_check
from cad_geometry import bounds, intersection_volume, load
from check_e73_corner_harness import bodies, datums, pcb_solid
from check_yeti60_assembly import box, distance, move
from check_yeti60_interconnects import near
from e73_corner_harness_paths import envelope_wire, sweep_wire
from e73_service_route import POWER_TRIAL, USB_TRIAL, trial_paths

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'hardware/e73-hhkb-corner'
AUDIT = BASE/'audit'
WORK = ROOT/'.assembly-work/e73-corner'
PORTS = {'J4': (4, -1, 0), 'J2': (3, 0, 1), 'C5': (4, 0, -1)}
PROXY_STROKE_MM = 4.0
LIFT_MM = 25.0
MIN_GAP_MM = .15


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def verify(report):
    for section in ('source_sha256', 'outputs'):
        for name, digest in report.get(section, {}).items():
            assert sha(ROOT/name) == digest, ('Stale service-motion input', name)


def plug_bounds(exit_point, count, vx, vy):
    """Same conservative housing as the current harness study."""
    x, y, z = exit_point
    cx, cy = x-2.5*vx, y-2.5*vy
    hx, hy = (2.5, (count+1)/2) if vx else ((count+1)/2, 2.5)
    return [cx-hx, cy-hy, z-1.5, cx+hx, cy+hy, z+1.5]


def translated_union_bounds(bb, vector):
    """Exact swept envelope for an axis-aligned box on one axis."""
    assert sum(bool(step) for step in vector)==1
    return [bb[i] + min(0, vector[i]) for i in range(3)] + [
        bb[i+3] + max(0, vector[i]) for i in range(3)]


def nearest(shape, obstacles, limit):
    bb = bounds(shape)
    records = []
    for name, part in obstacles.items():
        if not near(bb, bounds(part), limit):
            continue
        gap = distance(shape, part)
        if gap <= limit:
            records.append({'obstacle':name, 'gap_mm':gap,
                            'intersection_mm3':intersection_volume(shape, part) if gap<=1e-6 else 0})
    return sorted(records, key=lambda row: (row['gap_mm'], row['obstacle']))


def wire_lift_witnesses(routes, od):
    pairs = [('1','usb','3'), ('2','battery','3')]
    findings = []
    for power_pin, fixed_family, fixed_pin in pairs:
        moving = sweep_wire(routes['power'][power_pin],od)
        fixed = sweep_wire(routes[fixed_family][fixed_pin],od)
        assert intersection_volume(moving,fixed)<1e-6
        for offset in [.25,.50,.75,1,1.25,1.5,1.75,2,2.25,2.5,3]:
            shifted = move(moving,z=offset)
            if distance(shifted,fixed)>1e-6:
                continue
            overlap = intersection_volume(shifted,fixed)
            if overlap>1e-6:
                findings.append({'moving_wire':'power.'+power_pin,
                                 'fixed_wire':fixed_family+'.'+fixed_pin,
                                 'lift_mm':offset,'intersection_mm3':overlap})
                break
    return findings


def certify_lift_pair(moving, fixed):
    """Bound the whole vertical interval using 1-Lipschitz solid distance."""
    a, b = bounds(moving), bounds(fixed)
    lateral_gap = math.hypot(*(max(0, a[i]-b[i+3], b[i]-a[i+3]) for i in range(2)))
    if lateral_gap >= MIN_GAP_MM:
        return {'certified_gap_mm': lateral_gap, 'evaluations': 0}
    above = max(0, b[5] + MIN_GAP_MM - a[2])
    if above == 0:
        return {'certified_gap_mm': a[2]-b[5], 'evaluations': 0}

    # After this height the moving minimum Z clears the fixed maximum Z.
    high = min(LIFT_MM, above)
    unresolved = [(0., high)]
    certified = [MIN_GAP_MM] if high < LIFT_MM else []
    evaluations = 0
    while unresolved:
        lo, hi = unresolved.pop()
        midpoint = (lo+hi)/2
        measured = distance(move(moving, z=midpoint), fixed)
        lower = measured - (hi-lo)/2 - .0001  # Numerical buffer in millimetres.
        evaluations += 1
        if lower >= MIN_GAP_MM:
            certified.append(lower)
            continue
        assert measured >= MIN_GAP_MM and hi-lo > .0001, (
            'Candidate wire lift clearance not certified', midpoint, measured)
        unresolved.extend([(lo, midpoint), (midpoint, hi)])
    return {'certified_gap_mm': min(certified), 'evaluations': evaluations}


def audit_trial(spec, native, assembly, exits, bottom, case, variants):
    spec = dict(spec, usb=dict(spec['usb'], twist_rear_turns=USB_TRIAL['twist_rear_turns'],
                               twist_down_turns=USB_TRIAL['twist_down_turns']))
    wire = spec['wire']
    diameter = wire['insulation_od_max'] + 2*wire['case_and_route_position_allowance']
    trials = []
    for variant in variants:
        delta = variant['pcb_bottom_shift_mm']
        # Use the same installed checks, replacing only the route factory for
        # this call. The selected design and all of its inputs stay intact.
        with patch.object(harness_check, 'paths', trial_paths):
            trial = harness_check.evaluate(spec, native, assembly, exits, bottom, case, delta)
        residuals = []
        for row in trial['wires']:
            assert row['minimum_bend_radius_mm'] >= 4-1e-6, row
            for obstacle, gap in row['clearances_mm'].items():
                state_allowance = math.sqrt(3)*.15+.002 if obstacle in ('bottom', 'top') else 0
                residuals.append(gap - state_allowance)
        residuals.extend(cross['gap_mm'] for cross in trial['crossings'])
        assert min(residuals) >= MIN_GAP_MM-1e-6, (delta, min(residuals))

        shapes = {}
        for family, leads in trial['routes'].items():
            for pin, route in leads.items():
                original = variant['routes'][family][pin]
                assert math.dist(original[0]['start'], route[0]['start']) < 1e-6
                assert math.dist(original[-1]['end'], route[-1]['end']) < 1e-6
                shapes[family, pin] = envelope_wire(route, diameter)
        moving = [key for key in shapes if key[0] == 'power']
        fixed = [key for key in shapes if key[0] != 'power']
        proof = [dict(certify_lift_pair(shapes[a], shapes[b]),
                      power_conductor='.'.join(a), fixed_conductor='.'.join(b))
                 for a, b in product(moving, fixed)]
        trials.append({
            'PCB_thickness_mm': assembly['stack']['pcb_thickness']-delta,
            'minimum_static_residual_gap_mm': min(residuals),
            'USB_geometric_pair_skew_mm': trial['USB_geometric_pair_skew_mm'],
            'free_lengths_mm': {row['family']+'.'+row['pin']: row['free_length_mm']
                                for row in trial['wires']},
            'crossings': trial['crossings'],
            'wire_lift_pairs': proof,
        })
    return {'USB': USB_TRIAL, 'power': POWER_TRIAL, 'lift_mm': LIFT_MM,
            'minimum_gap_mm': MIN_GAP_MM, 'variants': trials,
            'fixed_wire_route_envelope_diameter_mm': diameter,
            'moving_wire_route_envelope_diameter_mm': diameter,
            'selected_for_assembly': False}


def main():
    derived_export = WORK/'copper.json'
    sources = [AUDIT/'harness-study.json', AUDIT/'retention-study.json', AUDIT/'harness-native.json',
               AUDIT/'local-models.json', AUDIT/'retention-prints.json',
               ROOT/'hardware/e73-corner-harness-spec.json', ROOT/'mechanical/assembly-spec.json',
               ROOT/'docs/audit/yeti60-daughterboard.json', ROOT/'scripts/check_e73_corner_harness.py',
               ROOT/'scripts/e73_corner_harness_paths.py', ROOT/'scripts/interconnect_geometry.py',
               ROOT/'scripts/check_yeti60_assembly.py',ROOT/'scripts/cad_geometry.py',
               ROOT/'scripts/check_yeti60_interconnects.py', ROOT/'scripts/e73_service_route.py',
               Path(__file__)]
    harness, retention, native, models, printing, spec, assembly = map(read,sources[:7])
    geometry = read(derived_export)
    geometry_sha256 = sha(derived_export)
    for report in (harness,retention,native,models,printing,geometry):
        verify(report)
    assert not harness['failures'] and not retention['failures']
    assert len(harness['variants']) == len(retention['variants']) == 3
    board = BASE/'EC60-nRF52840.kicad_pcb'
    assert native['source_PCB_sha256']==sha(board)
    assert geometry['source_sha256'][str(board.relative_to(ROOT))]==sha(board)
    bottom_path = ROOT/assembly['geometry']['bottom']
    case = load(bottom_path)
    bottom, exits = datums(native,assembly,spec)
    assert exits == harness['connector_exits_case_mm']
    battery = assembly['battery']
    x,y,X,Y = battery['bounds_xy']
    z = battery['top_z']
    pack = box([x,y,z-battery['full_envelope_including_growth'][2],X,Y,z])
    sources.extend([board,bottom_path])
    fixed_guides = {}
    pcb_guides = {}
    all_retainer_parts = retention['variants'][0]['parts']
    for part in all_retainer_parts:
        name = part['name']
        path = BASE/'mechanical/retention/assembly-reference'/(name+'.step')
        assert sha(path)==printing['outputs'][str(path.relative_to(ROOT))]
        group = pcb_guides if part['mount'].startswith('PCB') else fixed_guides
        group[name] = load(path)
        sources.append(path)
    assert len(fixed_guides)+len(pcb_guides)==33
    before = {str(path.relative_to(ROOT)):sha(path) for path in sources}

    records = []
    for variant in harness['variants']:
        delta = variant['pcb_bottom_shift_mm']
        thickness = assembly['stack']['pcb_thickness']-delta
        board_solid = pcb_solid(bottom+delta,thickness)
        pcb_parts = bodies(native,assembly,spec,bottom,delta)
        obstacles = dict(pcb_parts, bottom=case, pack=pack, PCB=board_solid, **fixed_guides)
        obstacles.update({ref: move(part,z=delta) for ref,part in pcb_guides.items()})
        plugs = {}
        for port,(count,vx,vy) in PORTS.items():
            x,y,z = exits[port]
            if port!='C5':
                z += delta
            plugs[port] = plug_bounds([x,y,z],count,vx,vy)
        for port,(count,vx,vy) in PORTS.items():
            bb = plugs[port]
            sweep = translated_union_bounds(bb, (PROXY_STROKE_MM*vx,PROXY_STROKE_MM*vy,0))
            fixed = {ref:part for ref,part in obstacles.items() if ref not in (port,'PCB')}
            fixed.update({'plug-'+ref:box(bounds_) for ref,bounds_ in plugs.items() if ref!=port})
            checks = nearest(box(sweep),fixed,1.5)
            # Place a small straight tool at the wire end of the housing. This
            # deliberately tests this access approach, not all possible tools.
            x,y = exits[port][:2]
            tool = box([x-1,y-1,bb[2],x+1,y+1,10])
            pcb_hit = intersection_volume(tool,board_solid)
            assert pcb_hit>1, (port,pcb_hit)
            records.append({'ref':port,'PCB_thickness_mm':thickness,'plug_bounds_case_mm':bb,
                            'trial_stroke_mm':PROXY_STROKE_MM,'swept_bounds_case_mm':sweep,
                            'nearest_nominal_rigid_obstacles':checks,
                            'nominal_rigid_sweep_has_intersection':any(row['intersection_mm3']>1e-6 for row in checks),
                            'straight_top_tool_cross_section_mm':[2,2],
                            'straight_top_tool_intersection_with_PCB_mm3':pcb_hit})

    nominal = harness['variants'][0]['routes']
    od = spec['wire']['insulation_od_max']
    witnesses = wire_lift_witnesses(nominal,od)
    assert witnesses, 'Expected rigid deck-lift obstruction not reproduced'
    pcb_z_sweep = pcb_solid(bottom,assembly['stack']['pcb_thickness']+LIFT_MM)
    assert intersection_volume(pcb_z_sweep,case) < 1e-6
    front_power_guides = []
    for name,part in pcb_guides.items():
        swept = box(translated_union_bounds(bounds(part), (0,0,LIFT_MM)))
        front_power_guides.extend(dict(row, moving_part=name) for row in nearest(swept,{'bottom':case},.55))
    assert not any(row['intersection_mm3']>1e-6 for row in front_power_guides)

    assert len(records) == 9 and not any(
        row['nominal_rigid_sweep_has_intersection'] for row in records)
    candidate = audit_trial(spec, native, assembly, exits, bottom, case, harness['variants'])
    for path, digest in before.items():
        assert sha(ROOT/path) == digest, ('Service input changed during trial', path)
    assert sha(derived_export) == geometry_sha256
    report = {
        'status':'service-obstructions-reproduced',
        'physical_verification':False,
        'manufacturing_released':False,
        'complete_service_path_qualified':False,
        'source_sha256':before,
        'derived_copper_export_sha256':geometry_sha256,
        'plug_axis_sweeps':records,
        'selected_vertical_lift':{
            'lift_mm':LIFT_MM,'bare_PCB_case_gap_mm':distance(pcb_z_sweep,case),
            'PCB_mounted_guide_case_near_contacts':front_power_guides,
            'blocked_power_conductor_witnesses':witnesses,
        },
        'alternate_crossing_trial':candidate,
        'scope':[
            'Four millimetres is a trial stroke for nominal rigid housings, excluding each plug’s owning header and PCB mating plane. It does not qualify travel, release force, tool tolerance, or lead flex.',
            'The rigid lift translates the power bridge relative to the seated USB and battery routes. Interference with the assumed full insulation diameter is a counterexample to this motion, not a proof that all removal motions fail.',
            'No new case opening or harness retainer placement is released by this report.',
            'The alternate crossing proves only installed wire clearances and relative wire translation. It does not prove deck or mount motion, parked plugs, release and re-mating, retention, strain, or electrical performance.',
        ],
    }
    (AUDIT/'service-motion.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'], 'tool sweeps:',len(records), 'wire witnesses:',witnesses)


if __name__ == '__main__':
    main()
