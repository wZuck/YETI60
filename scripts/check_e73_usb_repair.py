#!/usr/bin/env python3
"""Independently check the E73 USB repair. Run with KiCad Python.

This checks the native candidate, not the canonical PCB or full keyboard release.
Rules are enabled in a disposable project; the original project is not edited.
"""
import concurrent.futures
from collections import Counter
import copy
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

import pcbnew as pcb
from check_schematic_current import signature
from check_yeti60_signal_paths import build_graph
from kicad_sexpr import child, children, loads
from e73_battery_service import verify as verify_battery, spec as battery_spec

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/e73-usb-repair'
SOURCE = ROOT / 'hardware/ec60-nrf52840'
NAME = 'EC60-nRF52840'
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
REMOVED = {'D1', 'R30', 'R31'}
LAYERS = [pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def uid(item):
    return item.m_Uuid.AsString()


def netlist_contract(original, candidate):
    components, nets = signature(original)
    expected_components = copy.deepcopy(components)
    expected_nets = copy.deepcopy(nets)
    for ref in REMOVED:
        del expected_components[ref]
    expected_components['J1'] = ('USB_POWER_IN', components['J1'][1])
    expected_components['J2'] = (components['J2'][0],battery_spec()['footprint_id'])
    expected_components.update({
        'J4': ('USB_C5_INPUT', 'YAECKB:JST-SR-4__J4'),
        'J5': ('USB_POWER_OUT', 'YAECKB:JST_SH_SM02B_SRSS_TB__J5'),
    })
    for net, nodes in list(expected_nets.items()):
        nodes = [n for n in nodes if n[0] not in REMOVED and n not in [('J1', '2'), ('J1', '3')]]
        if nodes:
            expected_nets[net] = nodes
        else:
            del expected_nets[net]
    for net, nodes in {'USB_DM': [('J4', '2')], 'USB_DP': [('J4', '3')],
                       'USB_FEED': [('J4', '1'), ('J5', '1')],
                       'GND': [('J4', '4'), ('J5', '2')],
                       'unconnected-(J1-Pin_2-Pad2)': [('J1', '2')],
                       'unconnected-(J1-Pin_3-Pad3)': [('J1', '3')]}.items():
        expected_nets.setdefault(net, []).extend(nodes)
    expected_nets = {k: sorted(v) for k, v in expected_nets.items()}
    assert signature(candidate) == (expected_components, expected_nets), 'Unexpected component/net changes or missing hierarchy'
    return {'components': len(expected_components), 'nets': len(expected_nets),
            'all_non_USB_nodes_preserved': True}


def pad_geometry(pad):
    position = pad.GetPosition()
    size = pad.GetSize()
    drill = pad.GetDrillSize()
    return (pad.GetNumber(), (position.x, position.y), (size.x, size.y),
            round(pad.GetOrientationDegrees(), 6), pad.GetShape(),
            (drill.x, drill.y), tuple(pad.IsOnLayer(l) for l in LAYERS))


def preserved_geometry(board, source):
    original = {f.GetReference(): f for f in source.GetFootprints()}
    actual = {f.GetReference(): f for f in board.GetFootprints()}
    assert set(actual) == (set(original) - REMOVED) | {'J4', 'J5'}
    for ref, before in original.items():
        if ref in REMOVED or ref in ['C32','J2']:
            continue
        after = actual[ref]
        assert before.GetPosition() == after.GetPosition(), ('Moved retained footprint', ref)
        assert before.GetLayer() == after.GetLayer(), ('Flipped retained footprint', ref)
        assert {uid(p): pad_geometry(p) for p in before.Pads()} == {uid(p): pad_geometry(p) for p in after.Pads()}, ('Changed lands', ref)
        for pad in before.Pads():
            target = next(p for p in after.Pads() if uid(p) == uid(pad))
            expected = 'unconnected-(J1-Pin_' + pad.GetNumber() + '-Pad' + pad.GetNumber() + ')' if ref == 'J1' and pad.GetNumber() in ['2', '3'] else pad.GetNetname()
            assert target.GetNetname() == expected, ('Unexpected retained pad net', ref, pad.GetNumber())
    assert len(list(actual['U1'].Pads())) == 43
    for before in original['C32'].Pads():
        after=next(p for p in actual['C32'].Pads() if p.GetNumber()==before.GetNumber())
        assert before.GetSize()==after.GetSize() and before.GetShape()==after.GetShape() and before.GetNetname()==after.GetNetname(),'Changed C32 lands/value nets'
    spec = json.loads((ROOT / 'hardware/e73-usb-repair-spec.json').read_text())
    for ref,position in spec['headers_pcb_mm'].items():
        assert actual[ref].GetPosition()==pcb.VECTOR2I(*[pcb.FromMM(v)for v in position]),('Header position differs from contract',ref)
        assert abs(actual[ref].GetOrientationDegrees()-spec['header_orientation_deg'][ref])<1e-6,('Header orientation',ref)
    assert actual['C32'].GetPosition()==pcb.VECTOR2I(*[pcb.FromMM(v)for v in spec['C32_pcb_mm'][:2]])
    assert abs(actual['C32'].GetOrientationDegrees()-spec['C32_pcb_mm'][2])<1e-6
    source_tree = loads((SOURCE / (NAME + '.kicad_pcb')).read_text())
    source_items = {child(n, 'uuid')[1]: n for n in source_tree[1:] if isinstance(n, list) and n[0] in ['segment', 'arc', 'via']}
    actual_tree = loads((BASE / (NAME + '.kicad_pcb')).read_text())
    actual_items = {child(n, 'uuid')[1]: n for n in actual_tree[1:] if isinstance(n, list) and n[0] in ['segment', 'arc', 'via']}
    retained = 0
    original_native = {uid(t): t for t in source.GetTracks()}
    actual_native = {uid(t): t for t in board.GetTracks()}

    def primitive(t):
        signature = (t.GetClass(), t.GetNetname(), t.GetStart().x, t.GetStart().y,
                     t.GetEnd().x, t.GetEnd().y, t.GetLayer(), t.GetWidth(pcb.F_Cu) if isinstance(t, pcb.PCB_VIA) else t.GetWidth())
        if isinstance(t, pcb.PCB_VIA):
            signature += (t.GetViaType(), t.GetDrillValue(), t.TopLayer(), t.BottomLayer())
        return signature

    graphical_kinds = {'fp_line', 'fp_arc', 'fp_circle', 'fp_poly', 'fp_rect', 'fp_curve'}
    tree_footprints = []
    for tree in [source_tree, actual_tree]:
        tree_footprints.append({next(p[2] for p in children(f, 'property') if p[1] == 'Reference'):
                                [n for n in f if isinstance(n, list) and n[0] in graphical_kinds]
                                for f in children(tree, 'footprint')})
    for ref in original:
        if ref not in REMOVED and ref not in ['C32','J2']:
            assert tree_footprints[0][ref] == tree_footprints[1][ref], ('Changed footprint graphics/outline', ref)
    for kind in ['gr_line', 'gr_arc', 'gr_circle', 'gr_poly', 'gr_rect']:
        assert children(source_tree, kind) == children(actual_tree, kind), ('Changed board drawing', kind)
    removed_ground = set(spec['removed_C32_GND_fanout_UUIDs'])
    control_removed=set(spec['removed_ROW_DRV4_loop_item_UUIDs'])
    assert all(source_items[k] and child(source_items[k],'net')[1]=='ROW_DRV4'for k in control_removed),'Unexpected control repair net'
    reset_removed=set(spec['removed_RESET_B_item_UUIDs'])
    assert all(child(source_items[k],'net')[1]=='RESET_N'for k in reset_removed)
    control_removed|=reset_removed
    analog_removed=set(spec['removed_COL14_reference_item_UUIDs'])
    assert all(child(source_items[k],'net')[1]=='COL14'for k in analog_removed),'Unexpected analog reroute net'
    control_removed|=analog_removed
    battery=battery_spec()
    for identifier,record in battery['removed_source_items'].items():
        assert child(source_items[identifier],'net')[1]==record['net'],'Unexpected battery reroute net'
    control_removed|=set(battery['removed_source_items'])
    assert removed_ground <= set(source_items)
    for key, item in source_items.items():
        net = child(item, 'net')[1]
        retired = key in removed_ground|control_removed or net in ['D-', 'D+', 'USB_DM', 'USB_DP']
        retired |= item[0] == 'segment' and net == 'USB_5V' and child(item, 'layer')[1] == 'B.Cu' and min(float(child(item, 'start')[1]), float(child(item, 'end')[1])) >= 342.5
        if key==battery['changed_arc']['UUID']:
            expected=copy.deepcopy(item);child(expected,'layer')[1]=battery['changed_arc']['target_layer']
            assert actual_items[key]==expected,'Unexpected battery arc change beyond its documented layer transfer'
            continue
        if retired:
            assert key not in actual_items, ('Retired copper still present', key)
        else:
            # Compare every primitive, including net, layer and actual coordinates.
            assert key in actual_items and item == actual_items[key], ('Retained copper changed', key)
            assert key in actual_native and primitive(original_native[key]) == primitive(actual_native[key]), ('Live retained copper changed', key)
            retained += 1
    inherited_pad_via_overlaps = []
    for via in board.GetTracks():
        if not isinstance(via, pcb.PCB_VIA):
            continue
        assert via.GetViaType() == pcb.VIATYPE_THROUGH, 'Special-process via'
        assert via.GetWidth(pcb.F_Cu) >= pcb.FromMM(.5) and via.GetDrillValue() >= pcb.FromMM(.3), 'Non-ordinary via dimensions'
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetAttribute() == pcb.PAD_ATTRIB_SMD and pad.IsOnLayer(pcb.B_Cu):
                    if not pcb.SHAPE.Collide(via.GetEffectiveShape(pcb.B_Cu), pad.GetEffectiveShape(pcb.B_Cu), 0):
                        continue
                    # Retained non-module overlaps are disclosed, not qualified.
                    # New vias and all module/relocated capacitor overlaps fail.
                    # Existing solder-wicking/DFM issues stay on design hold.
                    assert fp.GetReference() not in ['U1','C32'] and uid(via) in original_native and primitive(via) == primitive(original_native[uid(via)]), ('New or module via overlaps SMD land', fp.GetReference(), pad.GetNumber())
                    inherited_pad_via_overlaps.append({'reference':fp.GetReference(),'pad':pad.GetNumber(),'via_UUID':uid(via)})
    battery_check=verify_battery(board,source)
    return {'E73_lands_preserved': 43, 'retained_copper_items_unchanged': retained,'battery_service':battery_check,
            'outline_and_mount_geometry_preserved': True, 'ordinary_through_vias_only': True,
            'new_or_module_via_in_pad': False,
            'inherited_pad_via_overlaps': inherited_pad_via_overlaps,
            'inherited_via_limit': 'Unchanged open/tented through vias overlapping retained lands (including thermal lands); pad solder wicking/DFM qualification remains open'}


def connectivity(board, netlist):
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    items = {uid(v): v for v in list(board.GetTracks()) + [p for f in board.GetFootprints() for p in f.Pads()] + list(board.Zones())}
    pads = {(f.GetReference(), p.GetNumber()): p for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()}
    cache = {}
    for pad in pads.values():
        if uid(pad) in cache:
            continue
        todo = [pad]
        seen = set()
        while todo:
            item = todo.pop()
            if uid(item) in seen:
                continue
            seen.add(uid(item))
            todo.extend(items[uid(other)] for other in conn.GetConnectedItems(item) if other.GetNetCode() == pad.GetNetCode() and uid(other) in items)
        for key in seen:
            cache[key] = uid(pad)
    checks = []
    for net in ET.parse(netlist).findall('./nets/net'):
        nodes = [(n.get('ref'), n.get('pin')) for n in net.findall('node')]
        for node in nodes:
            assert node in pads and pads[node].GetNetname() == net.get('name'), ('Missing or incorrect physical pad', net.get('name'), node)
        for node in nodes[1:]:
            a, b = nodes[0], node
            assert cache[uid(pads[a])] == cache[uid(pads[b])], ('Physical open', net.get('name'), a, b)
            checks.append({'net': net.get('name'), 'from': '.'.join(a), 'to': '.'.join(b)})
    return {'signal_power_pairs': sum(c['net'] != 'GND' for c in checks),
            'ground_pairs': sum(c['net'] == 'GND' for c in checks), 'all_pairs': checks,
            'limitation': 'Zone-item connectivity; independent filled-island/return checks remain required'}


def usb_paths(board):
    graph, ports, pads = build_graph(board, {'USB_DM', 'USB_DP'})
    result = {}
    for side, pin, endpoint in [('negative', '2', '29'), ('positive', '3', '31')]:
        length, _, edge_ids = graph.path(ports['J4', pin], {ports['U1', endpoint]})
        edges = [graph.edges[i] for i in edge_ids]
        assert 0 < length < 12
        assert not any(e['kind'] == 'via' for e in edges)
        assert {e['layer'] for e in edges if e['kind'] == 'trace'} == {'B.Cu'}
        result[side] = {'from': 'J4.' + pin, 'to': 'U1.' + endpoint,
                        'geometric_centerline_path_mm': length, 'via_count': 0, 'ordered_path': edges}
    result['geometric_path_difference_mm'] = abs(result['negative']['geometric_centerline_path_mm'] - result['positive']['geometric_centerline_path_mm'])
    assert result['geometric_path_difference_mm'] < .05
    return result


def c5_protection():
    path = ROOT / 'variants/raytac/scripts/check_yeti60_c5_protection.py'
    spec = importlib.util.spec_from_file_location('e73_c5_native_check', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    board = pcb.LoadBoard(str(ROOT / 'hardware/usb-daughterboard/upstream/UDB.kicad_pcb'))
    return {'status': 'actual-protected-I/O-and-ground-paths-passed', 'paths': module.verify(board),
            'daughterboard_modified': False, 'physical_verification': False}


def native_rules():
    config = json.loads((BASE / (NAME + '.kicad_pro')).read_text())
    for key, level in config['board']['design_settings']['rule_severities'].items():
        if level == 'ignore':
            config['board']['design_settings']['rule_severities'][key] = 'error' if key == 'footprint_type_mismatch' else 'warning'
    with tempfile.TemporaryDirectory(prefix='e73-usb-native-') as folder:
        scratch = Path(folder)
        for p in BASE.glob('*.kicad_sch'):
            shutil.copyfile(p, scratch / p.name)
        for name in [NAME + '.kicad_pcb', 'sym-lib-table', 'fp-lib-table', 'YAECKB.kicad_sym']:
            shutil.copyfile(BASE / name, scratch / name)
        (scratch / 'YAECKB.pretty').symlink_to((BASE / 'YAECKB.pretty').resolve(), target_is_directory=True)
        (scratch / (NAME + '.kicad_pro')).write_text(json.dumps(config))
        commands = [
            [CLI, 'pcb', 'drc', '--all-track-errors', '--schematic-parity', '--severity-all', '--refill-zones', '--format', 'json', '-o', str(BASE / 'audit/DRC-strict.json'), str(scratch / (NAME + '.kicad_pcb'))],
            [CLI, 'sch', 'erc', '--format', 'json', '--severity-all', '-o', str(BASE / 'audit/ERC.json'), str(scratch / (NAME + '.kicad_sch'))],
            [CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', str(scratch / 'fresh.xml'), str(scratch / (NAME + '.kicad_sch'))],
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda c: subprocess.run(c, capture_output=True, text=True), commands))
        assert all(r.returncode == 0 for r in results), [r.stderr[-1500:] for r in results if r.returncode]
        assert signature(scratch / 'fresh.xml') == signature(BASE / 'netlist.xml'), 'Stale candidate netlist'
    drc = json.loads((BASE / 'audit/DRC-strict.json').read_text())
    erc = json.loads((BASE / 'audit/ERC.json').read_text())
    errors = [v for v in drc['violations'] + drc.get('schematic_parity', []) + drc['unconnected_items'] if v['severity'] == 'error']
    errors += [v for sheet in erc['sheets'] for v in sheet['violations'] if v['severity'] == 'error']
    assert not errors, ('Native DRC/ERC/parity/opens', errors[:15])
    counts = Counter(v['type'] for v in drc['violations'])
    assert not any(n >= 199 for n in counts.values()), 'Native result category may be truncated'
    assert not any(counts[k]for k in ['track_dangling','via_dangling','track_not_centered_on_via']),'Unresolved dangling/off-center copper'
    native_board = pcb.LoadBoard(str(BASE / (NAME + '.kicad_pcb')))
    fp_refs = {uid(f): f.GetReference() for f in native_board.GetFootprints()}
    permitted = set(json.loads((SOURCE / 'metadata-audit.json').read_text())['non_purchased_geometry_references']) | {'REF**'}
    for violation in drc['violations']:
        if violation['type'] == 'missing_courtyard':
            assert all(fp_refs.get(i['uuid']) in permitted for i in violation['items'])
    return {'errors': 0, 'opens': 0, 'parity_errors': 0, 'warnings_by_type': dict(counts),
            'ERC_warnings_by_type': dict(Counter(v['type'] for sheet in erc['sheets'] for v in sheet['violations']))}


def main():
    destination = BASE / 'audit/native-check.json'
    destination.unlink(missing_ok=True)
    build = json.loads((BASE / 'audit/build.json').read_text())
    for name, expected in {**build['source_sha256'], **build['outputs']}.items():
        assert sha(ROOT / name) == expected, ('Stale candidate build', name)
    assert sha(BASE / (NAME + '.kicad_pro')) == sha(SOURCE / (NAME + '.kicad_pro')), 'Changed project rules'
    for name in ['analog.kicad_sch', 'matrix.kicad_sch', 'mounting.kicad_sch']:
        assert sha(BASE / name) == sha(SOURCE / name), ('Changed or missing hierarchy', name)
    expected_power=loads((SOURCE/'power.kicad_sch').read_text())
    j2=next(s for s in children(expected_power,'symbol') if any(p[1:3]==['Reference','J2'] for p in children(s,'property')))
    next(p for p in children(j2,'property') if p[1]=='Footprint')[2]=battery_spec()['footprint_id']
    assert loads((BASE/'power.kicad_sch').read_text())==expected_power,'Unexpected power-sheet change beyond J2 footprint identity'
    rules = native_rules()
    board = pcb.LoadBoard(str(BASE / (NAME + '.kicad_pcb')))
    source = pcb.LoadBoard(str(SOURCE / (NAME + '.kicad_pcb')))
    report = {'status': 'e73-usb-native-candidate-checks-passed',
              'selected_by_assembly': False, 'manufacturing_released': False, 'physical_verification': False,
              'native_rules': rules,
              'netlist': netlist_contract(SOURCE / 'netlist.xml', BASE / 'netlist.xml'),
              'preserved_geometry': preserved_geometry(board, source),
              'connectivity': connectivity(board, BASE / 'netlist.xml'),
              'USB_paths': usb_paths(board), 'C5_protection': c5_protection(),
              'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT/'scripts/e73_battery_service.py',ROOT/'hardware/e73-battery-service-spec.json',ROOT/battery_spec()['source_library'], ROOT / 'scripts/check_schematic_current.py', ROOT / 'scripts/check_yeti60_signal_paths.py', ROOT / 'scripts/kicad_sexpr.py', ROOT / 'mechanical/pcb-fabrication-spec.json', BASE / 'audit/build.json', ROOT / 'variants/raytac/scripts/check_yeti60_c5_protection.py', ROOT / 'hardware/usb-daughterboard/upstream/UDB.kicad_pcb', SOURCE / 'netlist.xml', SOURCE / 'metadata-audit.json']},
              'open_checks': ['Independent filled-ground islands and USB return reference',
                              'Connector/capacitor/plug case and tolerance envelopes',
                              'Complete nine-wire routes, connector withdrawal and service movements',
                              'Left power layout, inherited SMD-pad via overlaps and battery body/connected service qualification',
                              'Native component-model closure, candidate-specific firmware/calibration fingerprint and CAM',
                              'Supplier-qualified battery, physical USB/BLE/charging/thermal/RF/fit']}
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['connectivity', 'source_sha256', 'USB_paths']}, indent=2))
    print('Native connected pairs:', report['connectivity']['signal_power_pairs'], report['connectivity']['ground_pairs'])
    print('USB paths (mm):', {s: report['USB_paths'][s]['geometric_centerline_path_mm'] for s in ['negative', 'positive']})


if __name__ == '__main__':
    main()
