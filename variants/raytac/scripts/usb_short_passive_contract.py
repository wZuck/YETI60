"""Bind generic passive requirements to actual symbols, lands and purchase rows."""
import copy
import csv
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from kicad_sexpr import child, children, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'
REVISED = {'C32', 'C40', 'C41', 'C42', 'C43', 'C45', 'C46'}


def properties(node):
    return {str(p[1]): str(p[2]) for p in children(node, 'property')}


def verify_passives():
    spec = json.loads((BASE / 'power-passives.json').read_text())
    assert set(spec['capacitors']) == REVISED
    board = loads((BASE / 'EC60-nRF52840.kicad_pcb').read_text())
    footprints = {properties(f)['Reference']: f for f in children(board, 'footprint')}
    sheets = [loads(p.read_text()) for p in BASE.glob('*.kicad_sch')]
    symbols = {properties(s).get('Reference'): s for t in sheets for s in children(t, 'symbol')}
    netlist = ET.parse(BASE / 'netlist.xml')
    native = {p.get('ref'): (p.findtext('value'), p.findtext('footprint')) for p in netlist.findall('./components/comp')}
    manifest = json.loads((BASE / 'frozen-footprints.json').read_text())
    for ref, c in spec['capacitors'].items():
        assert c['value'] == ('4.7u/16V' if ref == 'C32' else '2.2u/25V' if ref == 'C40' else '22u/10V')
        assert c['body_max_LWH_mm'] == [2.2, 1.45, 1.45]
        assert c['pad_size_mm'] == [.9, 1.2] and c['pad_centres_local_mm'] == [[-.95, 0], [.95, 0]]
        assert c['effective_target_uF'] >= (2.2 if ref == 'C32' else 1 if ref == 'C40' else 5 if ref in ['C45', 'C46'] else 4.7)
        f = footprints[ref]
        assert f[1] == c['footprint'] and child(f, 'layer')[1] == 'B.Cu'
        assert properties(f)['Value'] == c['value']
        position = list(map(float, child(f, 'at')[1:])); position += [0] * (3-len(position))
        assert position == c['position'], ('Moved power capacitor', ref)
        assert native[ref] == (c['value'], c['footprint'])
        assert properties(symbols[ref])['Value'] == c['value'] and properties(symbols[ref])['Footprint'] == c['footprint']
        assert manifest[ref]['id'] == c['footprint']
        assert manifest[ref]['baseline'] == 'Project 0805 lands, 0.9 x 1.2 mm, 1.9 mm pitch; see power-passives.json'
        lib = loads((BASE / 'YAECKB.pretty' / (c['footprint'].split(':')[1] + '.kicad_mod')).read_text())
        for source in [f, lib]:
            pads = sorted(children(source, 'pad'), key=lambda p: p[1])
            assert len(pads) == 2
            for p, centre in zip(pads, c['pad_centres_local_mm']):
                assert list(map(float, child(p, 'at')[1:3])) == centre
                assert list(map(float, child(p, 'size')[1:])) == c['pad_size_mm'], ('Wrong power capacitor lands', ref)
            courtyard = next(n for n in children(source, 'fp_rect') if child(n, 'layer')[1].endswith('CrtYd'))
            assert list(map(float, child(courtyard, 'start')[1:])) == [-1.65, 1]
            assert list(map(float, child(courtyard, 'end')[1:])) == [1.65, -1]
    # Every listed component must carry the native design value. A changed
    # connector label must not silently retain the previous purchase name.
    for suffix in ['', '.zh-CN']:
        with (BASE / ('mainboard-purchase' + suffix + '.csv')).open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        keys = list(rows[0]); seen = set()
        for row in rows:
            refs = [r.strip() for r in row[keys[0]].split(',')]
            assert int(row[keys[1]]) == len(refs)
            assert int(row[keys[2]]) + int(row[keys[3]]) == len(refs)
            for ref in refs:
                assert ref not in seen; seen.add(ref)
                assert row[keys[4]] == native[ref][0], ('Stale purchase value', suffix, ref, row[keys[4]], native[ref][0])
                if ref[0] in ['R', 'C']:
                    package = native[ref][1].split(':')[1].split('__')[0]
                    assert row[keys[5]] == package, ('Wrong purchase package', suffix, ref)
                if ref in REVISED:
                    assert 'PASSIVES' in row[keys[7]], ('Missing generic specification', suffix, ref)
        assert len(seen) == 75
    return spec


def apply_passive_envelopes(assembly, native):
    """All candidate geometry consumers must see the same revised component map."""
    result = copy.deepcopy(assembly)
    byref = {p['ref']: p for p in result['component_envelopes']}
    assert {p['ref'] for p in native['revised_passives']} == REVISED
    z = result['nominal_stack']['pcb_bottom_z']
    for p in native['revised_passives']:
        entry = byref[p['ref']]
        x0, y0, x1, y1 = p['bbox_pcb_mm']
        x, y, angle = p['position']
        length, width, height = p['body_max_LWH_mm']
        a = math.radians(angle)
        hx = (abs(math.cos(a)) * length + abs(math.sin(a)) * width) / 2
        hy = (abs(math.sin(a)) * length + abs(math.cos(a)) * width) / 2
        # Native courtyard covers XY body and soldering allowance; preserve
        # the larger legacy 3 mm height, independently of the render body.
        entry.update(value=p['value'], position_pcb_mm=[x, y], angle_deg=angle,
                     bounds_case_mm=[x0, -y1, z-3, x1, -y0, z], height_envelope_mm=3,
                     height_basis='Revised native 0805 courtyard and conservative 3 mm assembly height',
                     render_body_bounds_case_mm=[x-hx, -y-hy, z-height, x+hx, -y+hy, z],
                     clearance_basis='Generic 0805 maximum body 2.2 x 1.45 x 1.45 mm plus native courtyard')
    return result
