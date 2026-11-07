"""Freeze the relocated power stage, ordinary vias and bounded local paths."""
import copy
import json
import subprocess
from pathlib import Path
from kicad_sexpr import child, children, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'
BASELINE = '9eaa30719849629d6ddb1a5950dfe071d389191a'
MOVED = {'U6', 'L1', 'C40', 'C41', 'C42', 'C43', 'C44', 'C45', 'C46', 'R45', 'R46', 'R47'}


def props(f):
    return {str(p[1]): str(p[2]) for p in children(f, 'property')}


def pose(f):
    values = list(map(float, child(f, 'at')[1:]))
    return values + [0] * (3-len(values))


def via_map(tree):
    return {str(child(v, 'uuid')[1]): {
        'net': str(child(v, 'net')[1]), 'position': list(map(float, child(v, 'at')[1:])),
        'land_mm': float(child(v, 'size')[1]), 'drill_mm': float(child(v, 'drill')[1]),
        'layers': list(child(v, 'layers')[1:]), 'tenting': child(v, 'tenting'),
        'type': str(v[1]) if not isinstance(v[1], list) else 'through',
    } for v in children(tree, 'via')}


def local_pads(f):
    """Compare all land/paste/net details, normalizing only global rotation."""
    result = []
    for pad in children(f, 'pad'):
        p = copy.deepcopy(pad)
        p[:] = [v for v in p if not (isinstance(v, list) and v[0] == 'uuid')]
        at = child(p, 'at'); angle = float(at[3]) if len(at) > 3 else 0
        at[:] = ['at', float(at[1]), float(at[2]), round((angle-pose(f)[2]) % 360, 6)]
        result.append(p)
    return result


def verify_layout():
    spec = json.loads((BASE / 'power-layout.json').read_text())
    assert spec['baseline_commit'] == BASELINE and set(spec['component_positions']) == MOVED
    old = loads(subprocess.check_output(['git', 'show', BASELINE + ':variants/raytac/hardware/usb-short-route/EC60-nRF52840.kicad_pcb'], cwd=ROOT).decode())
    board = loads((BASE / 'EC60-nRF52840.kicad_pcb').read_text())
    oldparts = {props(f)['Reference']: f for f in children(old, 'footprint')}
    parts = {props(f)['Reference']: f for f in children(board, 'footprint')}
    from repair_usb_short_charger_package import lands
    for ref, position in spec['component_positions'].items():
        f, previous = parts[ref], copy.deepcopy(oldparts[ref])
        if ref=='U6': lands(previous, ref)
        assert pose(f) == position, ('Unexpected power component position', ref)
        assert f[1] == previous[1] and props(f)['Value'] == props(previous)['Value']
        assert child(f, 'layer') == child(previous, 'layer') == ['layer', 'B.Cu']
        assert local_pads(f) == local_pads(previous), ('Changed power land/paste geometry', ref)
    expected_charger=copy.deepcopy(oldparts['U5']);lands(expected_charger,'U5')
    assert local_pads(parts['U5'])==local_pads(expected_charger),'Changed RGT land/stencil contract'
    before, after = via_map(old), via_map(board)
    actual = dict(added={k:v for k,v in after.items() if k not in before},
                  removed={k:v for k,v in before.items() if k not in after},
                  moved={k:dict(before=before[k], after=v) for k,v in after.items() if k in before and v != before[k]})
    assert actual == spec['via_changes'], 'Unexpected via additions, removals or moves'
    for v in actual['added'].values():
        assert v['type'] == 'through' and v['layers'] == ['F.Cu', 'B.Cu']
        assert v['land_mm'] == .5 and v['drill_mm'] == .3
    thermal = after[spec['U6_thermal_via_uuid']]
    assert thermal['net'] == 'GND' and thermal['position'] == pose(parts['U6'])[:2]
    assert thermal['tenting'] == ['tenting', ['front', 'yes'], ['back', 'yes']]
    areas = [z for z in children(board, 'zone') if child(z, 'name') == ['name', 'L1_INTERLAND_NO_COPPER']]
    assert len(areas) == 1, 'Missing or duplicate inductor copper keepout'
    area = areas[0]
    assert child(area, 'layer') == ['layer', 'B.Cu']
    assert child(area, 'keepout') == ['keepout', ['tracks', 'not_allowed'], ['vias', 'not_allowed'], ['pads', 'allowed'], ['copperpour', 'not_allowed'], ['footprints', 'allowed']]
    points = child(child(area, 'polygon'), 'pts')
    assert [list(map(float, p[1:])) for p in points[1:]] == spec['L1_central_gap_keepout_polygon_mm']
    return spec


def verify_paths(paths, spec):
    actual = {(p['from'], p['to']): p for p in paths}
    assert len(actual) == len(paths) == len(spec['local_path_limits'])
    for limit in spec['local_path_limits']:
        p = actual[limit['from'], limit['to']]
        assert p['conservative_track_length_mm'] <= limit['max_length_mm'], ('Long local power path', p)
        assert p['min_trace_width_mm'] >= limit['min_width_mm'], ('Narrow local power path', p)
        assert p['track_layers'] == ['B.Cu'] and p['surface_only'], ('Power path leaves component layer', p)
    return True
