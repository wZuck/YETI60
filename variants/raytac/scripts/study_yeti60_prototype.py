#!/usr/bin/env python3
"""Reproducible pre-case prototype research, never a physical acceptance result."""
import csv
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union
from shapely import make_valid

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT/'docs/audit'
ADJACENT = {'F.Cu': 'In1.Cu', 'In1.Cu': 'F.Cu', 'In2.Cu': 'B.Cu', 'B.Cu': 'In2.Cu'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ground_shapes(records, normalizations=None):
    polys = [Polygon(p['outer'], p['holes']) for p in records if len(p['outer']) >= 3]
    normalized = []
    for p in polys:
        if not p.is_valid:
            fixed = make_valid(p)
            delta = abs(fixed.area-p.area)
            assert delta < .01, 'Native copper normalization exceeds 0.01 mm2; review geometry'
            if normalizations is not None:
                normalizations.append({'original_area_mm2': p.area, 'area_delta_mm2': delta})
            p = fixed
        if p.geom_type == 'Polygon':
            normalized.append(p)
        elif hasattr(p, 'geoms'):
            normalized.extend(q for q in p.geoms if q.geom_type in ['Polygon', 'MultiPolygon'])
    return unary_union(normalized)


def coverage(line, ground):
    total = line.length
    missing = line.difference(ground)
    return {'trace_mm': total, 'uncovered_centerline_mm': missing.length,
            'covered_fraction': 1-missing.length/total if total else 1}


def usb_study(native, paths):
    normalizations = []
    copper = {layer: ground_shapes(polys, normalizations) for layer, polys in native['ground_copper'].items()}
    result = {}
    for name, other in [('positive', 'negative'), ('negative', 'positive')]:
        edges = [p for p in paths[name]['ordered_path'] if p['kind'] == 'trace']
        opposing = {layer: [LineString([p['start'], p['end']])
                           for p in paths[other]['ordered_path'] if p['kind'] == 'trace' and p['layer'] == layer]
                    for layer in ADJACENT}
        groups = {}
        for layer in sorted({e['layer'] for e in edges}):
            lines = [LineString([e['start'], e['end']]) for e in edges if e['layer'] == layer]
            # Sum individual route edges for coverage: unary union can remove a
            # retraced segment, which must not silently change route length.
            measured = [coverage(line, copper[ADJACENT[layer]]) for line in lines]
            total = sum(v['trace_mm'] for v in measured)
            missing = sum(v['uncovered_centerline_mm'] for v in measured)
            partner = unary_union(opposing[layer])
            distant = sum(line.difference(partner.buffer(.75)).length for line in lines)
            groups[layer] = {'nearest_adjacent_layer': ADJACENT[layer], 'trace_mm': total,
                             'uncovered_centerline_mm': missing, 'covered_fraction': 1-missing/total,
                             'outside_same_layer_partner_0_75mm_mm': distant}
        vias = []
        seen = set()
        for edge in paths[name]['ordered_path']:
            if edge['kind'] != 'via' or edge['item'] in seen:
                continue
            seen.add(edge['item']); xy = list(edge['a'][2:])
            nearest = min(math.dist(xy, v['xy']) for v in native['ground_through_vias'])
            vias.append({'signal_via_uuid': edge['item'], 'xy_pcb_mm': xy,
                         'nearest_ground_through_via_center_distance_mm': nearest})
        total = sum(g['trace_mm'] for g in groups.values())
        missing = sum(g['uncovered_centerline_mm'] for g in groups.values())
        result[name] = {'layers': groups, 'trace_mm': total,
                        'uncovered_nearest_adjacent_GND_centerline_mm': missing,
                        'nearest_adjacent_GND_coverage_fraction': 1-missing/total,
                        'signal_vias': vias}
    return result, copper, normalizations


def thermal_power(vin, vbat, ichg, isys, vout=4.4, iq=.0015):
    assert vin >= vout >= vbat and ichg >= 0 and isys >= 0
    return (vin-vbat)*ichg + (vin-vout)*isys + vin*iq


def thermal_study(power):
    maximum = max(power['charging']['programmed_charge_mA_min_typ_max'])/1000
    rows = []
    for vin in [4.75, 5.0, 5.25]:
        for vb in [3.2, 3.7, 4.2]:
            for isys in [.02, .04]:
                # High-input-limit corner permits the full programmed charge
                # current. 1.5 mA is a published bias value at another stated
                # operating point, used as an explicit engineering allowance.
                pd = thermal_power(vin, vb, maximum, isys)
                rows.append({'VIN_V_ASSUMED': vin, 'VBAT_V_ASSUMED': vb,
                             'system_input_A_ASSUMED': isys, 'charge_A_programmed_max': maximum,
                             'power_W_estimated': pd,
                             'Tj_at_40C_theta44_5C_W_JEDEC_reference_C': 40+pd*44.5,
                             'Tj_at_40C_theta90C_W_SENSITIVITY_ONLY_C': 40+pd*90,
                             'theta_limit_for_125C_at_40C_C_W': 85/pd})
    return rows


def mechanical_study(fit):
    f = fit['selected_fasteners']
    # Additional tolerances are proposed incoming acceptance limits, not
    # manufacturer guarantees. Existing board/plate XY budgets remain intact.
    screw_min, screw_max = 4.8, 5.0
    washer_min, washer_max = .75, .85
    film_min, film_max = .08, .12
    tmin, tmax = fit['ordinary_board_thickness_budget']['finished_range_mm']
    reach_min = screw_min-washer_max-tmax-film_max
    reach_max = screw_max-washer_min-tmin-film_min
    bottom_clearance = (f['bottom_thread_depth']-.1)-reach_max
    assert reach_min > 1.6 and bottom_clearance > 0
    return {'installed_mounts': len(fit['mounting_hole_matches']),
            'unused_mounts': fit['unused_pcb_mount_refs'],
            'worst_radial_screw_clearance_mm': fit['minimum_fastener_radial_margin_worst_case_mm'],
            'nominal_plate_thread_turns': f['top_stud_length']/.4,
            'proposed_incoming_tolerances_mm': {'screw_underhead_length': [screw_min, screw_max],
                                               'washer_thickness': [washer_min, washer_max],
                                               'insulating_film': [film_min, film_max],
                                               'female_depth_minimum': f['bottom_thread_depth']-.1},
            'screw_engagement_interval_mm': [reach_min, reach_max],
            'female_thread_bottom_clearance_min_mm': bottom_clearance,
            'limitations': ['Incoming limits require supplier acceptance; blind-hole usable full thread differs from drill depth',
                           '2.5 nominal top-thread turns do not establish clamp strength, life or torque',
                           'Supplier NiZ/stabilizer geometry, full travel and local stiffness are unqualified']}


def divider_response(upper_ohm, lower_ohm, capacitance_F, wait_s):
    assert min(upper_ohm, lower_ohm, capacitance_F) > 0 and wait_s >= 0
    tau = (upper_ohm*lower_ohm/(upper_ohm+lower_ohm))*capacitance_F
    return tau, math.exp(-wait_s/tau)


def battery_filter(parts, pins):
    """Identify the shunt capacitor from actual nets, never reference order."""
    selected = []
    for ref, value in parts.items():
        nets = {net for (r, _), net in pins.items() if r == ref}
        if not ref.startswith('C') or nets != {'BAT_ADC', 'GND'}:
            continue
        cap = re.fullmatch(r'(\d+(?:\.\d+)?)([unp])(?:/10V)?', value)
        assert cap, 'Unsupported BAT_ADC capacitor value: '+ref+' '+value
        selected.append({'ref': ref, 'value': value, 'nets': sorted(nets),
                         'capacitance_F': float(cap[1])*{'u': 1e-6, 'n': 1e-9, 'p': 1e-12}[cap[2]]})
    assert selected, 'No BAT_ADC-to-GND capacitor found'
    return selected


def battery_study():
    core = (ROOT/'firmware/yeti60/core.c').read_text()
    body = core.split('int yeti_battery_mv(', 1)[1].split('int yeti_connections(', 1)[0]
    wait_us = int(re.search(r'wait\(s,\s*(\d+)\)', body)[1])
    netlist = ET.parse(ROOT/'hardware/ec60-nrf52840/netlist.xml').getroot()
    parts = {c.get('ref'): c.findtext('value') for c in netlist.findall('./components/comp')}
    pins = {(node.get('ref'), node.get('pin')): net.get('name')
            for net in netlist.findall('./nets/net') for node in net.findall('node')}
    assert parts['R51'] == parts['R52'] == '1M/1%'
    assert {pins['R51', '1'], pins['R51', '2']} == {'BAT_MEAS_TOP', 'BAT_ADC'}
    assert {pins['R52', '1'], pins['R52', '2']} == {'BAT_ADC', 'GND'}
    capacitors = battery_filter(parts, pins)
    capacitance = sum(c['capacitance_F'] for c in capacitors)
    tau, error = divider_response(1e6, 1e6, capacitance, wait_us/1e6)
    # Published SEMITEC 103AT nominal R/T table (kOhm), logarithmically
    # interpolated. These are approximate crossings, not tolerance bounds.
    table = [(-10, 42.47), (0, 27.28), (10, 17.96), (20, 12.09),
             (25, 10.00), (30, 8.313), (40, 5.827), (50, 4.160), (60, 3.020)]
    def temp(resistance_k):
        for (t0, r0), (t1, r1) in zip(table, table[1:]):
            if r0 >= resistance_k >= r1:
                return t0+(t1-t0)*math.log(resistance_k/r0)/math.log(r1/r0)
        raise AssertionError('NTC threshold outside table')
    return {'capacity_mAh': 1600, 'chemistry': '1S 4.2 V CC/CV lithium-ion polymer; not 4.35 V HV or LiFePO4',
            'BAT_ADC': {'shunt_capacitors_from_netlist': capacitors, 'R51_R52_ohm': [1e6, 1e6],
                        'C48_actual_nets': sorted({net for (ref, _), net in pins.items() if ref == 'C48'}),
                        'nominal_time_constant_s': tau, 'existing_wait_s': wait_us/1e6,
                        'step_settling_error_fraction': error,
                        'apparent_4200mV_after_fully_discharged_capacitor_mV': 4200*(1-error),
                        'wait_for_0_1_percent_settling_s': -tau*math.log(.001),
                        'nominal_0_1percent_settling_passed': error <= .001,
                        'C_and_R_tolerance_10pct_1pct_ASSUMED_error_fraction': math.exp(-wait_us/1e6/(tau*1.10*1.01)),
                        'target_battery_reporting_enabled': False,
                        'finding': 'Actual BAT_ADC filter C47 is 10nF; C48 is AFE rail decoupling and must not be substituted into the divider model. Nominal settling passes. Target ADC gain/offset/noise and low-voltage policy remain unqualified.'},
            'NTC': {'published_103AT_table_kOhm': table,
                    'nominal_hot_resistance_kOhm': .300/.075,
                    'nominal_cold_resistance_kOhm': 2.100/.075,
                    'nominal_hot_crossing_C_APPROX': temp(.300/.075),
                    'nominal_cold_crossing_C_APPROX': temp(2.100/.075),
                    'electrical_corner_hot_crossing_C_APPROX': [temp(.330/.072), temp(.270/.078)],
                    'electrical_corner_cold_crossing_C_APPROX': [temp(2.200/.072), temp(2.000/.078)],
                    'includes_NTC_tolerance_thermal_lag_or_self_heating': False,
                    'finding': 'BQ24074 plus a plain 103AT-compatible sensor cannot enforce the requested actual 15..43 C pack window; independent cell-coupled hardware interruption is mandatory.'},
            'discharge': {'cell_sheet_cutoff_V': 3.0,
                          'normal_target_software_low_voltage_cutoff_implemented': False,
                          'proposed_initial_bench_stop_V': 3.2,
                          'required_pack_response': 'Specify loaded-cell cutoff/recovery/delay/tolerance and off-state leakage. A generic PCM with a 2.4 V threshold does not establish the 3.0 V cell-sheet operating cutoff.'},
            'pack_procurement_approved': False,
            'independent_thermal_protector_reference_family': 'MinebeaMitsumi MM3855 is evidence that temperature-capable protection exists, not a selected/qualified suffix or a complete pack; cold cutoff needs separate proof.'}


def draw_usb(result, copper, paths):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Polygon as Patch
    plt.rcParams['svg.hashsalt'] = 'yeti60-prototype-research'
    for zh in [False, True]:
        plt.rcParams['font.family'] = 'Arial Unicode MS' if zh else 'DejaVu Sans'
        fig, axes = plt.subplots(4, 1, figsize=(13, 8), constrained_layout=True)
        for ax, layer in zip(axes, ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']):
            ground = copper[ADJACENT[layer]].intersection(box(104, 108, 368, 142))
            polygons = list(ground.geoms) if hasattr(ground, 'geoms') else [ground]
            for poly in polygons:
                if poly.geom_type != 'Polygon':
                    continue
                ax.add_patch(Patch(list(poly.exterior.coords), facecolor='#d4e5d9', edgecolor='none'))
                for hole in poly.interiors:
                    ax.add_patch(Patch(list(hole.coords), facecolor='white', edgecolor='none'))
            for name, color in [('positive', '#b54536'), ('negative', '#1d4c9b')]:
                for e in paths[name]['ordered_path']:
                    if e['kind'] == 'trace' and e['layer'] == layer:
                        ax.plot([e['start'][0], e['end'][0]], [e['start'][1], e['end'][1]], color=color, lw=1.5)
            ax.set_xlim(104, 368); ax.set_ylim(142, 108); ax.set_aspect('equal')
            ax.set_title((f'{layer} 信号；绿色为相邻 {ADJACENT[layer]} 接地铜' if zh else
                          f'{layer} signal; green = adjacent {ADJACENT[layer]} ground copper'), fontsize=10)
            ax.set_xlabel('PCB X (mm)'); ax.set_ylabel('PCB Y (mm)')
        axes[0].legend(handles=[Line2D([0], [0], color='#b54536', label='D+'),
                                Line2D([0], [0], color='#1d4c9b', label='D−')],
                       loc='upper right', ncol=2, fontsize=8)
        fig.suptitle('USB 相邻层接地铜检查；不是场仿真或眼图' if zh else
                     'USB adjacent-ground geometry screen; not a field solution or eye test', fontsize=14)
        name = 'usb-reference'+('.zh-CN' if zh else '')
        for ext in ['svg', 'png']:
            target = ROOT/f'docs/engineering/images/{name}.{ext}'
            fig.savefig(target, dpi=160, **({'metadata': {'Date': None}} if ext == 'svg' else {}))
            if ext == 'svg':
                target.write_text('\n'.join(line.rstrip() for line in target.read_text().splitlines())+'\n')
        plt.close(fig)


def main():
    native_path = ROOT/'.assembly-work/usb-reference-inputs.json'
    native = json.loads(native_path.read_text())
    for path, expected in native['source_sha256'].items():
        assert sha(ROOT/path) == expected, 'Stale native USB extraction'
    path_file = AUD/'USB-signal-paths.json'; paths = json.loads(path_file.read_text())['variants']['raytac']
    board = ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'
    assert paths['source_sha256']['hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'] == sha(board)
    usb, copper, normalizations = usb_study(native, paths)
    power_file = AUD/'yeti60-power-budget.json'; power = json.loads(power_file.read_text())
    fit_file = AUD/'yeti60-assembly.json'; fit = json.loads(fit_file.read_text())
    thermal = thermal_study(power)
    thermal_path = ROOT/'hardware/bom/charging-thermal-scenarios.csv'
    with thermal_path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(thermal[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(thermal)
    draw_usb(usb, copper, paths)
    outputs = [thermal_path, *sorted((ROOT/'docs/engineering/images').glob('usb-reference.*'))]
    report = {'status': 'research-completed-design-repair-required',
              'production_approved': False, 'physical_verification': False,
              'bare_board_order_ready': False,
              'blocking_design_findings': ['USB long-route pairing/reference remediation',
                                           'Supplier-qualified pack thermal/voltage/current limits and discharge cutoff'],
              'USB': usb, 'mechanical': mechanical_study(fit), 'battery': battery_study(), 'thermal_scenarios': thermal,
              'copper_polygon_normalizations': normalizations,
              'USB_screen_limits': ['2D centerline intersection with normalized native adjacent-layer ground polygons; holes preserved',
                                   'Nearest adjacent layer chosen by stack distance, not an assertion that it is the actual RF return plane',
                                   '0.75 mm partner proximity is a screening parameter, not a USB standard or impedance calculation',
                                   'Ground-via distance is a center distance; no return-loop inductance or topology solution',
                                   'C5, connectors, cable, module internals and fields are not included'],
              'thermal_limits': ['44.5 C/W is TI JEDEC reference-board RthetaJA, not measured YETI60 thermal resistance',
                                 '90 C/W, 40 C ambient, 4.75/5/5.25 V and 20/40 mA system load are sensitivity assumptions',
                                 'Current limiting, thermal foldback, CV taper and thermal coupling to the cell are not solved',
                                 'Junction temperature is not cell temperature or a safety certification'],
              'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), board, path_file, power_file, fit_file, ROOT/'mechanical/pcb-fabrication-spec.json', ROOT/'hardware/ec60-nrf52840/netlist.xml', ROOT/'firmware/yeti60/core.c', ROOT/'docs/engineering/prototype-sources.json']},
              'native_recipe_sha256': sha(ROOT/'scripts/export_yeti60_usb_reference.py'),
              'outputs': {str(p.relative_to(ROOT)): sha(p) for p in outputs}}
    (AUD/'prototype-research.json').write_text(json.dumps(report, indent=2)+'\n')
    print('USB nearest-adjacent ground coverage:', {k: round(v['nearest_adjacent_GND_coverage_fraction'], 4) for k, v in usb.items()})
    print('Highest conditional charger dissipation W:', max(t['power_W_estimated'] for t in thermal))
    print('Screw engagement mm:', report['mechanical']['screw_engagement_interval_mm'])


if __name__ == '__main__':
    main()
