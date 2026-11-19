#!/usr/bin/env python3
"""Check M05's open-case straight lift after J2 and J4 have been parked."""

from concurrent.futures import ProcessPoolExecutor
from itertools import product
import json
from pathlib import Path

from build_e73_m05_harness import OUT, matched_spec
from cad_geometry import bounds, load
from check_e73_corner_harness import bodies, datums, pcb_solid
from check_e73_corner_service import (
    AUDIT, LIFT_MM, MIN_GAP_MM, PORTS, ROOT, certify_lift_pair, nearest,
    plug_bounds, read, sha, translated_union_bounds, verify,
)
from check_yeti60_assembly import box, move
from e73_corner_harness_paths import envelope_wire, paired_data
from e73_corner_retention import build
from e73_service_leads import BATTERY_GUIDE_STATIONS, flex_routes, position_exits


def check_thickness(delta):
    spec = matched_spec(read(ROOT/'hardware/e73-corner-harness-spec.json'))
    spec['guides'] = dict(read(ROOT/'hardware/e73-corner-retention-spec.json')['guides'],
                          battery_x=BATTERY_GUIDE_STATIONS)
    assembly = read(ROOT/'mechanical/assembly-spec.json')
    native = read(AUDIT/'harness-native.json')
    bottom, exits = datums(native, assembly, spec)
    thickness = assembly['stack']['pcb_thickness']-delta
    case = load(OUT/'bottom-m05-REVIEW.step')
    seated, _, _ = flex_routes(spec, exits, exits, 0)
    guides, films = build(spec, case, seated, exits, bottom)
    parked = position_exits(exits, 1, 1, 1, 1)
    routed, centre, _ = flex_routes(spec, exits, parked, delta)
    routed['usb'].update(paired_data(centre, spec)[0])
    w = spec['wire']
    diameter = w['insulation_od_max']+2*w['case_and_route_position_allowance']
    wires = {family+'.'+pin:envelope_wire(lead, diameter)
             for family, leads in routed.items() for pin, lead in leads.items()}
    moving_leads = {name:shape for name,shape in wires.items() if name.startswith('power.')}
    fixed_leads = {name:shape for name,shape in wires.items() if name not in moving_leads}
    parts = bodies(native, assembly, spec, bottom, delta)
    stationary = {name:shape for name,shape in parts.items() if name.startswith('C5')}
    stationary['M05 bottom'] = case
    pack = assembly['battery']
    x,y,X,Y = pack['bounds_xy']
    z = pack['top_z']
    stationary['pack'] = box([x,y,z-pack['full_envelope_including_growth'][2],X,Y,z])
    for ref in PORTS:
        x,y,z = parked[ref]
        stationary[ref+'-plug'] = box(plug_bounds((x,y,z+(0 if ref=='C5' else delta)), *PORTS[ref]))

    travel = (0,0,LIFT_MM)
    moving_rigid = {name:shape for name,shape in parts.items() if not name.startswith('C5')}
    for part in guides+films:
        if part['mount'].startswith('PCB'):
            moving_rigid[part['name']] = move(part['shape'], z=delta)
        else:
            stationary[part['name']] = part['shape']
    for ref, count, vx, vy in [('J1',4,1,0), ('J5',2,0,-1)]:
        x,y,z = exits[ref]
        moving_rigid[ref+'-plug'] = box(plug_bounds((x,y,z+delta), count, vx, vy))
    swept = {name:box(translated_union_bounds(bounds(shape), travel))
             for name,shape in moving_rigid.items()}
    swept['PCB'] = pcb_solid(bottom+delta, thickness+LIFT_MM)
    collisions = {name:nearest(shape,fixed_leads,MIN_GAP_MM)
                  for name,shape in swept.items()}
    assert not any(collisions.values()), (thickness, collisions)
    stationary.update(fixed_leads)
    proofs = []
    for a,b in product(moving_leads, stationary):
        proof = certify_lift_pair(moving_leads[a], stationary[b])
        assert proof['certified_gap_mm'] >= MIN_GAP_MM
        proofs.append(dict(proof, moving_conductor=a, stationary_obstacle=b))
    return {'PCB_thickness_mm': thickness, 'wire_envelope_diameter_mm': diameter,
            'moving_rigid_items_checked_against_stationary_wires': len(swept),
            'stationary_conductors_checked_against_moving_rigid_items': len(fixed_leads),
            'rigid_against_wire_min_clearance_greater_than_mm': MIN_GAP_MM,
            'moving_power_wire_checks': proofs}


def main():
    harness_path = AUDIT/'m05-harness.json'
    harness = read(harness_path)
    verify(harness)
    thicknesses = [v['PCB_thickness_mm'] for v in harness['trial_variants']]
    nominal = read(ROOT/'mechanical/assembly-spec.json')['stack']['pcb_thickness']
    recipe = [harness_path, Path(__file__)]
    inputs = dict(harness['source_sha256'], **{str(p.relative_to(ROOT)):sha(p) for p in recipe})
    with ProcessPoolExecutor(max_workers=len(thicknesses)) as pool:
        variants = list(pool.map(check_thickness, (nominal-t for t in thicknesses)))
    assert all(sha(ROOT/path)==digest for path,digest in inputs.items())
    (AUDIT/'m05-lift.json').write_text(json.dumps({
        'status': 'M05-parked-harness-vertical-clearance-checked',
        'source_sha256': inputs,
        'physical_verification': False,
        'manufacturing_released': False,
        'travel_mm': LIFT_MM,
        'variants': variants,
        'scope': [
            'Upper shell and bottom covers removed, both mainboard cable housings already parked, and fixed wire paths held in their modeled positions.',
            'The deck includes the PCB, fitted components and fastener envelopes, PCB guides and the power bridge. The separate steel plate to bottom proof is in service-reference.json.',
            'The rigid-item checks cover continuous swept envelopes against expanded stationary leads. The moving-wire distance proof covers the entire lift interval against stationary parts and leads.',
            'The release tool, flex between plug poses, actual fastener and guide tolerances, and physical operation remain open.',
        ],
    }, indent=2)+'\n')
    print('M05-parked-harness-vertical-clearance-checked', flush=True)


if __name__ == '__main__':
    main()
