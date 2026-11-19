#!/usr/bin/env python3
"""Draw the E73 service trial and verify the plate's vertical removal envelope."""

import json
from pathlib import Path

import ezdxf
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

from check_e73_corner_harness import bodies, cut, datums, pcb_solid
from check_e73_corner_service import (
    AUDIT, LIFT_MM, PORTS, ROOT, load, nearest, plug_bounds, read, sha,
    translated_union_bounds, verify,
)
from check_yeti60_assembly import box, move
from e73_corner_harness_paths import point_at
from e73_corner_retention import build
from e73_fit_geometry import plate_envelope, screen
from e73_service_leads import (
    BATTERY_GUIDE_STATIONS, PARK_DROP, PARK_TRAVEL, flex_routes, position_exits, trial_spec,
)


def draw(seated, parked, zh):
    plt.rcParams['font.family'] = ['Arial Unicode MS', 'DejaVu Sans']
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.8), layout='constrained')
    labels = ('接合', '脱开并停放') if zh else ('Seated', 'Unplugged and parked')
    for ax, family, pin, limits in (
        (axes[0], 'battery', '2', (148, 200, -131, -103)),
        (axes[1], 'usb', '1', (187, 223, -175, -137)),
    ):
        for routes, label, color, style in zip((seated, parked), labels, ('#264b78', '#a34f23'), ('-', '--')):
            samples = [point_at(piece, i/48) for piece in routes[family][pin] for i in range(49)]
            ax.plot([x for x, _, _ in samples], [y for _, y, _ in samples], style,
                    label=label, color=color, linewidth=1.9)
        ax.set(xlim=limits[:2], ylim=limits[2:], aspect='equal',
               xlabel='X (mm)', ylabel='Y (mm)')
        ax.grid(alpha=.2)
        ax.legend(loc='lower right', fontsize=9)
    for station in BATTERY_GUIDE_STATIONS:
        axes[0].axvline(station, color='#555555', linestyle=':', linewidth=1)
    axes[0].set_title('J2 电池线与移动后的理线位置' if zh else 'J2 battery lead and relocated guides')
    axes[1].set_title('USB 前侧回环' if zh else 'USB front loop')
    fig.suptitle('E73 壳内线束随动试验 · 俯视' if zh else 'E73 service lead trial · top view')
    target = AUDIT/('service-lead-paths.zh-CN.png' if zh else 'service-lead-paths.png')
    fig.savefig(target, dpi=160)
    plt.close(fig)
    return target


def access_path(native, assembly, spec, exits, seated, case, bottom, thicknesses, windows):
    """Check the full two-step rigid motion through the existing trial windows."""
    rigid, films = build(spec, case, seated, exits, bottom)
    results = []
    for thickness in thicknesses:
        delta = assembly['stack']['pcb_thickness']-thickness
        obstacles = bodies(native, assembly, spec, bottom, delta)
        obstacles['PCB'] = pcb_solid(bottom+delta, thickness)
        for region in rigid+films:
            shape = region['shape']
            obstacles[region['name']] = move(shape, z=delta) if region['mount'].startswith('PCB') else shape
        for ref, travel in PARK_TRAVEL.items():
            count, vx, vy = PORTS[ref]
            along = (travel*vx, travel*vy, 0)
            down = (0, 0, -PARK_DROP)
            x, y, z = exits[ref]
            edge = plug_bounds([x, y, z+delta], count, vx, vy)
            housing = box(edge)
            opening = cut(case, box(windows[ref]))
            fixed = dict(obstacles, bottom=opening)
            axial = box(translated_union_bounds(edge, along))
            # The housing and its own header are mated at the start.
            mates = {name:part for name, part in fixed.items() if name != ref}
            axial_checks = nearest(axial, mates, .3)
            assert not any(row['intersection_mm3'] > 1e-6 for row in axial_checks), axial_checks
            dropped = box(translated_union_bounds(
                [value+along[i % 3] for i, value in enumerate(edge)], down))
            vertical_checks = nearest(dropped, fixed, .3)
            assert not any(row['intersection_mm3'] > 1e-6 for row in vertical_checks), vertical_checks
            assert not nearest(housing, {'bottom':case}, 0), ('Mated plug touches the case', ref)
            results.append({'ref': ref, 'PCB_thickness_mm': thickness,
                            'trial_window_case_bounds_mm': windows[ref],
                            'axial_mm': travel, 'downward_mm': PARK_DROP,
                            'axial_near_objects': axial_checks, 'downward_near_objects': vertical_checks})
    return results


def main():
    report = AUDIT/'service-leads.json'
    evidence = read(report)
    verify(evidence)
    assert evidence['status'] == 'service-lead-candidate-poses-passed'
    assembly = read(ROOT/'mechanical/assembly-spec.json')
    geom = assembly['geometry']
    dxf, bottom, fit = (ROOT/geom[name] for name in ('plate', 'bottom', 'fit_spec'))
    stack = dict(assembly['stack'], plate_thickness_mm=assembly['stack']['plate_thickness'])
    tolerance = read(fit)
    envelope = plate_envelope(ezdxf.readfile(dxf), tolerance, stack, travel=LIFT_MM)
    case = load(bottom)
    plate = screen(case, envelope, tolerance, 'M04 bottom to swept plate envelope')
    spec = trial_spec(read(ROOT/'hardware/e73-corner-harness-spec.json'))
    native = read(AUDIT/'harness-native.json')
    board_z, exits = datums(native, assembly, spec)
    seated, _, _ = flex_routes(spec, exits, exits, 0)
    parked, _, _ = flex_routes(spec, exits, position_exits(exits, 1, 1, 1, 1), 0)
    retention = read(ROOT/'hardware/e73-corner-retention-spec.json')
    spec['guides'] = dict(retention['guides'], battery_x=BATTERY_GUIDE_STATIONS)
    study = read(AUDIT/'service-motion.json')
    windows = {row['ref']:row['window_case_bounds_mm']
               for row in study['alternative_access_trial']['underside_jaw_checks']
               if row['PCB_bottom_shift_mm'] == 0}
    thicknesses = [variant['PCB_thickness_mm'] for variant in evidence['variants']]
    access = access_path(native, assembly, spec, exits, seated, case, board_z, thicknesses, windows)
    outputs = [draw(seated, parked, zh) for zh in (False, True)]
    sources = [report, Path(__file__), dxf, bottom, fit, ROOT/'scripts/e73_fit_geometry.py']
    record = {
        'status': 'service-reference-drawings-and-plate-clearance-checked',
        'selected_for_assembly': False,
        'physical_verification': False,
        'manufacturing_released': False,
        'plate_lift_mm': LIFT_MM,
        'plate_clearance': plate,
        'rigid_housing_travel': access,
        'source_sha256': dict(evidence['source_sha256'], **{
            str(path.relative_to(ROOT)):sha(path) for path in sources}),
        'outputs': {str(path.relative_to(ROOT)):sha(path) for path in outputs},
    }
    (AUDIT/'service-reference.json').write_text(json.dumps(record, indent=2)+'\n')
    print(record['status'], plate)


if __name__ == '__main__':
    main()
