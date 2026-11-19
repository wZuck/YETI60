#!/usr/bin/env python3
"""Build an M05 dry-fit harness package against its actual closed case."""

from concurrent.futures import ProcessPoolExecutor
import csv
import json
from pathlib import Path
from unittest.mock import patch

from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound

import check_e73_service_leads as service
from cad_geometry import bounds, intersection_volume, load
from check_e73_corner_service import AUDIT, BASE, ROOT, read, sha, verify
from check_yeti60_assembly import distance, move
from check_yeti60_interconnects import write_step
from e73_corner_harness_paths import paired_data
from e73_corner_retention import build
from e73_fit_geometry import volume
from e73_service_leads import BATTERY_GUIDE_STATIONS, flex_routes, trial_spec
from export_e73_retention_prints import mesh


OUT = BASE/'mechanical/service-case-m05'
PHASES = {'twist_rear_turns': 3.06, 'twist_down_turns': .613, 'twist_return_turns': .327}
MOVED = {'BAT-R1', 'BAT-R2', 'BAT-R1-film', 'BAT-R2-film'}
PORT_FAMILIES = {'J4': 'usb', 'J5': 'power', 'J2': 'battery'}


def matched_spec(source):
    spec = trial_spec(source)
    spec['usb'].update(PHASES)
    return spec


def closed_case():
    loaded = [load(OUT/(name+'-REVIEW.step')) for name in ('bottom-m05', 'cover-J2', 'cover-J4')]
    maker = BRep_Builder()
    assembly = TopoDS_Compound()
    maker.MakeCompound(assembly)
    for part in loaded:
        maker.Add(assembly, part)
    return assembly


def run_m05(delta):
    assembly = read(ROOT/'mechanical/assembly-spec.json')
    bottom_path = ROOT/assembly['geometry']['bottom']
    shell = closed_case()
    assert max(abs(a-b) for a,b in zip(bounds(shell),bounds(load(bottom_path)))) < .0001
    def use_m05(path):
        assert path == bottom_path
        return shell
    # Keep the proven pose sequence and limits. Change only the case solids
    # and winding phase for this prototype-specific run.
    with patch.object(service, 'trial_spec', matched_spec), patch.object(service, 'load', use_m05):
        result = service.run_thickness(delta)
    assert max(s['USB_pair_skew_mm'] for s in result['states']) < .005
    return result


def export_guides(assembly, records):
    spec = matched_spec(read(ROOT/'hardware/e73-corner-harness-spec.json'))
    retainer_spec = read(ROOT/'hardware/e73-corner-retention-spec.json')
    spec['guides'] = dict(retainer_spec['guides'], battery_x=BATTERY_GUIDE_STATIONS)
    native = read(AUDIT/'harness-native.json')
    base_z, exits = service.harness.datums(native, assembly, spec)
    routes, centre, _ = flex_routes(spec, exits, exits, 0)
    routes['usb'].update(paired_data(centre, spec)[0])
    case = load(OUT/'bottom-m05-REVIEW.step')
    parts, films = build(spec, case, routes, exits, base_z)
    old = BASE/'mechanical/retention'
    outputs = []
    shifted = {}
    reused = []
    for item in parts+films:
        name = item['name']
        shape = item['shape']
        if name not in MOVED:
            existing = load(old/'assembly-reference'/(name+'.step'))
            overlap = intersection_volume(shape, existing)
            assert max(abs(volume(part)-overlap) for part in (shape, existing)) < .0001, name
            reused.append(name)
            continue
        datum = item['datum_case_mm']
        source = OUT/'harness'/(name+'-M05.step')
        write_step(shape, source)
        outputs.append(source)
        if name.endswith('-film'):
            shifted[name] = {'case_datum_mm': datum, 'source': str(source.relative_to(ROOT)),
                             'role': 'cut-film-reference'}
            continue
        gap = distance(shape, case)
        assert abs(gap-spec['guides']['bond_gap']) < .001
        push_in = .001
        area = intersection_volume(move(shape, z=-(gap+push_in)), case)/push_in
        assert area > 1, (name, area)
        target = source.with_suffix('.stl')
        local = move(shape, *[-v for v in bounds(shape)[:3]])
        metrics = mesh(local, target)
        outputs.append(target)
        shifted[name] = dict(metrics, case_datum_mm=datum, bonding_gap_mm=gap,
                             nominal_contact_area_estimate_mm2=area,
                             source=str(source.relative_to(ROOT)), print_STL=str(target.relative_to(ROOT)))
    assert set(shifted) == MOVED and len(reused) == 29
    assert sum(item in reused for item in [q['name'] for q in parts]) == 14
    assert len({row['PCB_thickness_mm'] for row in records}) == 3
    return outputs, shifted, reused


def export_lengths(lengths):
    paths = []
    shared = (lengths['usb.2']+lengths['usb.3'])/2
    for zh in (False, True):
        suffix = '.zh-CN.csv' if zh else '.csv'
        source = BASE/'mechanical'/('harness-conductors'+suffix)
        target = OUT/'harness'/('wire-lengths-m05'+suffix)
        paths.append(target)
        with source.open(newline='') as template, target.open('w', newline='') as handle:
            reader = csv.reader(template)
            writer = csv.writer(handle, lineterminator='\n')
            header = next(reader)
            writer.writerow(header)
            rows = list(reader)
            assert len(rows) == len(lengths) == 9
            for row in rows:
                port, pin = row[1:3]
                key = PORT_FAMILIES[port]+'.'+pin
                value = shared if key in ('usb.2', 'usb.3') else lengths[key]
                row[6] = f'{value:.3f}'
                row[-1] = 'M05 台架试装目标' if zh else 'M05 dry-fit target'
                writer.writerow(row)
    return paths


def power_loss(lengths, previous):
    wire_length = sum(lengths[pin] for pin in ('usb.1', 'usb.4', 'power.1', 'power.2'))
    wire_r20 = previous['wire_loop_20C_ohm'] * wire_length / previous['four_wire_free_lengths_sum_mm']
    traces = previous['positive_PCB_centerline_20C_ohm']
    temp_c = previous['copper_temperature_C_assumed']
    modeled_hot_resistance = (traces+wire_r20) * (1+.00393*(temp_c-20))
    extra = modeled_hot_resistance-previous['modeled_series_at_temperature_ohm']
    return {'AWG28_wire_length_mm': wire_length, 'wire_resistance_at_20C_ohm': wire_r20,
            'copper_temperature_C': temp_c, 'model_R_at_temperature_ohm': modeled_hot_resistance,
            'extra_drop_at_500mA_V': .5*extra,
            'included_drop_at_500mA_V': .5*modeled_hot_resistance,
            'excluded': previous['excluded']}


def main():
    inputs = [AUDIT/'service-case-m05.json', AUDIT/'service-leads.json', AUDIT/'retention-prints.json',
              AUDIT/'power-process.json',
              BASE/'mechanical/harness-conductors.csv', BASE/'mechanical/harness-conductors.zh-CN.csv',
              ROOT/'scripts/export_e73_retention_prints.py', Path(__file__)]
    hashes = {}
    for path in inputs[:4]:
        report = read(path)
        verify(report)
        hashes.update(report['source_sha256'])
        hashes.update(report['outputs'] if 'outputs' in report else {})
    hashes.update({str(path.relative_to(ROOT)):sha(path) for path in inputs})
    original = read(AUDIT/'harness-study.json')
    deltas = [row['pcb_bottom_shift_mm'] for row in original['variants']]
    with ProcessPoolExecutor(max_workers=len(deltas)) as pool:
        rows = list(pool.map(run_m05, deltas))
    (OUT/'harness').mkdir(exist_ok=True)
    assembly = read(ROOT/'mechanical/assembly-spec.json')
    models, shifted, reused = export_guides(assembly, rows)
    tables = export_lengths(rows[0]['seated_free_lengths_mm'])
    loss = power_loss(rows[0]['seated_free_lengths_mm'], read(AUDIT/'power-process.json')['charge_headroom'])
    assert all(sha(ROOT/path) == digest for path, digest in hashes.items())
    result = {
        'status': 'M05-prototype-paired-harness-ready-for-dry-fit',
        'manufacturing_released': False,
        'physical_verification': False,
        'case': 'M05',
        'nominal_winding_turns': PHASES,
        'shifted_battery_parts': shifted,
        'reused_M04_parts': reused,
        'trial_variants': rows,
        'charging_path_sensitivity': loss,
        'source_sha256': hashes,
        'outputs': {str(p.relative_to(ROOT)):sha(p) for p in models+tables},
        'limits': [
            'Free lengths exclude stripped ends and crimp allowances. Wire placement and repeatable feed through the guide slots require a physical sample.',
            'A modeled ADC/USB routing clearance and matched geometric length do not establish USB signal integrity, pack qualification or BLE performance.',
            'The closed-case model uses the M05 shell and covers. The actual tool, cover fastening, assembly/removal and stiffness must still be demonstrated.',
        ],
    }
    (AUDIT/'m05-harness.json').write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
