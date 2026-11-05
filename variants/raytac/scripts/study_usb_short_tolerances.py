#!/usr/bin/env python3
"""Measure limiting shell interfaces and expose incomplete tolerance budgets.

This is a diagnostic, not manufacturing acceptance. Passing execution means
that current geometry and arithmetic were checked, including known deficits.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'
PROFILE_CHORD_MM = .002


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def perimeter(plate, stack):
    """Outer side surface only: internal key/fastener openings are out of scope."""
    import ezdxf
    from ezdxf.path import make_path
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Vec
    from check_yeti60_assembly import wire
    profiles = []
    for entity in ezdxf.readfile(plate).modelspace().query('LWPOLYLINE'):
        pts = [(-p.x, -p.y, stack['plate_bottom_z'])
               for p in make_path(entity).flattening(PROFILE_CHORD_MM)]
        extent = [(max(p[i] for p in pts) - min(p[i] for p in pts)) for i in (0, 1)]
        profiles.append((math.prod(extent), pts))
    assert profiles
    outline = wire(max(profiles, key=lambda p: p[0])[1], True)
    return BRepPrimAPI_MakePrism(outline, gp_Vec(0, 0, stack['plate_thickness_mm'])).Shape()


def clearance(fixed, moving):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    q = BRepExtrema_DistShapeShape(fixed, moving)
    q.Perform()
    assert q.IsDone() and q.NbSolution()
    pairs = []
    for i in range(1, min(8, q.NbSolution()) + 1):
        a, b = q.PointOnShape1(i), q.PointOnShape2(i)
        pairs.append(dict(case=[a.X(), a.Y(), a.Z()], moving=[b.X(), b.Y(), b.Z()]))
    return dict(nominal_gap_mm=q.Value(), nearest_point_pairs_case_mm=pairs)


def budget(interfaces, spec, fabrication):
    """Directional budgets at the measured XY ear walls and Z-facing floor.

    Unspecified terms remain unknown; they are never silently counted as zero
    in an acceptance claim. The subtotal deliberately shows an optimistic
    residual before those terms, which is already below the project target.
    """
    case = spec['case']['linear_tolerance']
    # Use measured finished-board CAD thickness, not rounded 1.6 mm.
    board_growth = max(fabrication['ordinary_thickness_acceptance_range_mm']) - fabrication['CAD_finished_envelope_mm']
    assert board_growth > 0
    target = .15  # Project air-gap target, not a supplier tolerance guarantee.
    result = []
    for label in ('plate-top', 'plate-bottom'):
        parts = dict(case_local_wall_inward=case, plate_CAD_chord_error=PROFILE_CHORD_MM)
        unknown = ['Plate outer-cut dimension and position tolerances',
                   'Installed plate XY translation, rotation and gasket compliance']
        result.append(dict(interface=label, nominal_gap_mm=interfaces[label]['nominal_gap_mm'],
                           known_directional_allowances_mm=parts,
                           known_allowance_sum_mm=sum(parts.values()),
                           optimistic_remaining_gap_mm=interfaces[label]['nominal_gap_mm']-sum(parts.values()),
                           project_minimum_air_gap_mm=target, unquantified_terms=unknown))
    parts = dict(finished_PCB_downward_growth=board_growth,
                 shoulder_length=spec['pcb_fastener']['shoulder_length_tolerance'],
                 insulating_film=spec['pcb_fastener']['top_insulator_thickness_tolerance'],
                 case_floor_inward=case)
    result.append(dict(interface='SW100-bottom', nominal_gap_mm=interfaces['SW100-bottom']['nominal_gap_mm'],
                       known_directional_allowances_mm=parts, known_allowance_sum_mm=sum(parts.values()),
                       optimistic_remaining_gap_mm=interfaces['SW100-bottom']['nominal_gap_mm']-sum(parts.values()),
                       project_minimum_air_gap_mm=target,
                       unquantified_terms=['Installed plate Z position and gasket compression variation',
                                           'Switch maximum installed height, solder standoff and PCB warpage']))
    for row in result:
        row['additional_clearance_needed_before_unknown_terms_mm'] = max(0., target-row['optimistic_remaining_gap_mm'])
        row['conditional_screen'] = 'insufficient' if row['optimistic_remaining_gap_mm'] < target else 'unknown-terms-open'
        row['combined_tolerance_qualified'] = False
    return result


def validate(report):
    assert report['status'] == 'diagnostic-complete-tolerance-qualification-open'
    assert not report['manufacturing_released'] and not report['physical_verification']
    assert not report['combined_tolerance_qualified']
    assert {r['interface'] for r in report['directional_budgets']} == {'plate-top', 'plate-bottom', 'SW100-bottom'}
    for row in report['directional_budgets']:
        assert not row['combined_tolerance_qualified'] and row['unquantified_terms']
        total = sum(row['known_directional_allowances_mm'].values())
        assert math.isclose(total, row['known_allowance_sum_mm'], abs_tol=1e-9)
        assert math.isclose(row['optimistic_remaining_gap_mm'], row['nominal_gap_mm']-total, abs_tol=1e-9)
        required = max(0., row['project_minimum_air_gap_mm']-row['optimistic_remaining_gap_mm'])
        assert math.isclose(required, row['additional_clearance_needed_before_unknown_terms_mm'], abs_tol=1e-9)
        expected = 'insufficient' if row['optimistic_remaining_gap_mm'] < row['project_minimum_air_gap_mm'] else 'unknown-terms-open'
        assert row['conditional_screen'] == expected


def verify_evidence(report, spec, fabrication):
    validate(report)
    assert report['directional_budgets'] == budget(report['measured_interfaces'], spec, fabrication), 'Stale or incomplete directional tolerance budget'


def main():
    from cad_geometry import load, bounds
    from check_usb_short_closed_assembly import hashes
    assembly = read(BASE/'audit/assembly.json')
    motion = read(BASE/'audit/vertical-motion.json')
    closed = read(BASE/'audit/closed-assembly.json')
    for report in (assembly, motion, closed):
        hashes(report['source_sha256'])
    hashes(closed['case']['outputs'])
    spec = read(ROOT/'mechanical/assembly-spec.raytac.json')
    fabrication = read(ROOT/'mechanical/pcb-fabrication-spec.json')
    assert assembly['plate_profile_chord_error_mm'] == PROFILE_CHORD_MM
    plate_path = ROOT/'mechanical/felk60_plate_hhkb.plate-mount.dxf'
    side = perimeter(plate_path, assembly['nominal_stack'])
    interfaces = {}
    for name, path in [('plate-top', ROOT/'mechanical/generated/yeti60-top.step'),
                       ('plate-bottom', BASE/'mechanical/yeti60-bottom-short-usb.step')]:
        interfaces[name] = clearance(load(path), side)
        print(name, interfaces[name]['nominal_gap_mm'], flush=True)
    for label in ('plate-top', 'plate-bottom'):
        # Confirm these are XY-facing perimeter walls, not vertical gasket gaps.
        for pair in interfaces[label]['nearest_point_pairs_case_mm']:
            d = [b-a for a, b in zip(pair['case'], pair['moving'])]
            assert abs(d[2]) < .00001 and min(abs(d[0]), abs(d[1])) < .00001
            assert max(abs(d[0]), abs(d[1])) > .1
    for name, label in [('plate-exact-planar-footprint', 'plate-bottom'), ('SW100', 'SW100-bottom')]:
        measured = next(r for r in motion['limiting_nominal_features'] if r['part'] == name)
        if label in interfaces:
            assert abs(measured['nominal_gap_mm']-interfaces[label]['nominal_gap_mm']) < .003
        else:
            interfaces[label] = dict(nominal_gap_mm=measured['nominal_gap_mm'],
                                     nearest_point_pairs_case_mm=measured['nearest_point_pairs_case_mm'])
    switch = next(r for r in assembly['component_envelopes'] if r['ref'] == 'SW100')
    for pair in interfaces['SW100-bottom']['nearest_point_pairs_case_mm']:
        d = [b-a for a, b in zip(pair['case'], pair['moving'])]
        assert abs(d[0])+abs(d[1]) < .00001 and d[2] > .1
    assert math.isclose(switch['height_envelope_mm'], 3.5)
    sources = [Path(__file__), ROOT/'scripts/cad_geometry.py', ROOT/'scripts/check_yeti60_assembly.py',
               ROOT/'scripts/check_usb_short_closed_assembly.py', BASE/'audit/assembly.json',
               BASE/'audit/vertical-motion.json', BASE/'audit/closed-assembly.json', plate_path,
               ROOT/'mechanical/assembly-spec.raytac.json', ROOT/'mechanical/pcb-fabrication-spec.json',
               ROOT/'mechanical/generated/yeti60-top.step', BASE/'mechanical/yeti60-bottom-short-usb.step']
    result = dict(status='diagnostic-complete-tolerance-qualification-open',
                  manufacturing_released=False, physical_verification=False, combined_tolerance_qualified=False,
                  project_gap_target_basis='0.15 mm local design reserve; not an IPC/JLC/vendor certification',
                  measured_interfaces=interfaces, measured_plate_perimeter_bounds_mm=bounds(side),
                  directional_budgets=budget(interfaces, spec, fabrication),
                  switch_height_basis=switch['height_basis'],
                  scope='Three limiting interfaces only; installed outer plate perimeter and SW100 floor. No full key mechanism, fastener, flexing harness or service-access qualification.',
                  interpretation='Known directional allowances are a subtotal, not a completed worst-case tolerance stack. A deficit is loss of specified reserve; it is not proof of physical collision. Both shells need the plate-ear repair.',
                  source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources})
    verify_evidence(result, spec, fabrication)
    (BASE/'audit/tolerance-diagnostic.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Measured three limiting interfaces; combined tolerance remains OPEN.', flush=True)


if __name__ == '__main__':
    main()
