#!/usr/bin/env python3
"""Build the E73 HHKB corner placement from the separate USB/power candidate.

Run with KiCad Python. This is a routing work product, never an order package.
The generated report deliberately records open connections and failed gates.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pcbnew as pcb
from kicad_sexpr import Atom, child, children, dumps, loads, symbol_pins

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'hardware/e73-corner-spec.json'
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
NAME = 'EC60-nRF52840'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    s = json.loads(SPEC.read_text())
    source, out = ROOT / s['source_directory'], ROOT / s['output_directory']
    assert sha(source / (NAME + '.kicad_pcb')) == s['source_board_sha256'], 'Review changed relocation source before rebuilding'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'audit').mkdir(exist_ok=True)
    for old in (out / 'audit').glob('*.json'):
        old.unlink()
    inputs = [SPEC, Path(__file__), ROOT / 'scripts/kicad_sexpr.py', ROOT / 'scripts/check_schematic_current.py', ROOT / 'scripts/screen_yeti60_interference.py']
    for p in sorted(source.iterdir()):
        if p.is_file() and (p.suffix in ['.kicad_pcb', '.kicad_pro', '.kicad_sch', '.kicad_sym', '.xml', '.csv', '.json'] or p.name in ['sym-lib-table', 'fp-lib-table']):
            shutil.copyfile(p, out / p.name)
            inputs.append(p)
    for directory in ['YAECKB.pretty', 'models']:
        if (source / directory).exists():
            shutil.copytree(source / directory, out / directory, dirs_exist_ok=True)
            inputs.extend(p for p in sorted((source / directory).rglob('*')) if p.is_file())
    from kicad_sexpr import form
    tree = loads((source / (NAME + '.kicad_pcb')).read_text())
    reference = lambda f: next(p[2] for p in children(f, 'property') if p[1] == 'Reference')
    original = next(f for f in children(tree, 'footprint') if reference(f) == 'U1')
    ox, oy = [float(v) for v in child(original, 'at')[1:3]]
    tx, ty = s['module_origin_PCB_mm']
    assert s['rigid_rotation_deg'] == 0
    signal_nets = {str(child(p, 'net')[1]) for p in children(original, 'pad') if child(p, 'net')} - {'', 'GND', '+3.3V', 'USB_5V', 'USB_DM', 'USB_DP'}
    signal_nets = {n for n in signal_nets if not n.startswith('unconnected-')}
    removed = []
    # Remove AST nodes before native loading. Repeated SWIG Remove calls can
    # invalidate the native containers and must not be used for bulk changes.
    for t in list(tree[1:]):
        if not isinstance(t, list):
            continue
        if t[0] == 'footprint' and reference(t) in s['removed_electrodes']:
            tree.remove(t)
            continue
        if t[0] == 'zone' and child(t, 'name') and child(t, 'name')[1] == 'RF_ANTENNA_NO_COPPER':
            tree.remove(t)
            continue
        if t[0] not in ['segment', 'arc', 'via']:
            continue
        net = str(child(t, 'net')[1])
        if str(child(t, 'uuid')[1]) in s['reference_corridor_repair']['removed_In2_UUIDs']:
            assert net == 'COL14' and child(t, 'layer')[1] == 'In2.Cu'
            removed.append({'uuid': str(child(t, 'uuid')[1]), 'net': net})
            tree.remove(t)
            continue
        if net in ['USB_DM', 'USB_DP']:
            removed.append({'uuid': str(child(t, 'uuid')[1]), 'net': net})
            tree.remove(t)
            continue
        points = [list(map(float, child(t, k)[1:3])) for k in (['at'] if t[0] == 'via' else ['start', 'end'])]
        local = (net in ['GND', '+3.3V', 'USB_5V']
                 and min(q[0] for q in points) > 342 and max(q[1] for q in points) < 137
                 and (net != 'GND' or min(q[1] for q in points) >= 116))
        retired_stub = min(q[0] for q in points) > 329 and min(q[1] for q in points) > 180
        corner_contact = (max(q[0] for q in points) >= 329 and min(q[0] for q in points) <= 356.812704
                          and max(q[1] for q in points) >= 179.5 and min(q[1] for q in points) <= 198.50966)
        # Retain the left-side analog feedback, pull-ups and charger-local
        # branches. Only the module feed trunks of these nets are retired.
        # Re-routing the entire ADC net would needlessly disturb U3 feedback.
        signal_trunk = net in signal_nets and (max(q[0] for q in points) > 356
            or (max(q[0] for q in points) > 344 and min(q[1] for q in points) < 132 and max(q[1] for q in points) > 114))
        if (net == 'APLEX_EN_PIN_1' and max(q[0] for q in points) > 340) or signal_trunk or local or retired_stub or corner_contact:
            removed.append({'uuid': str(child(t, 'uuid')[1]), 'net': net})
            tree.remove(t)
    # Restore the old right edge in its existing outline footprint coordinates.
    outline = next(f for f in children(tree, 'footprint') if any(child(g, 'layer')[1] == 'Edge.Cuts' for g in children(f, 'fp_line')))
    ex, ey = [float(v) for v in child(outline, 'at')[1:3]]
    old_wing = []
    for g in children(outline, 'fp_line') + children(outline, 'fp_arc'):
        if child(g, 'layer')[1] != 'Edge.Cuts':
            continue
        ends = [[float(v[1]) + ex, float(v[2]) + ey] for v in [child(g, 'start'), child(g, 'end')]]
        if min(v[0] for v in ends) >= 356.8127 and min(v[1] for v in ends) >= 113.9999 and max(v[1] for v in ends) <= 132.5001:
            old_wing.append(g)
    assert len(old_wing) == 7, ('Unexpected old wing geometry', len(old_wing))
    for g in old_wing:
        outline.remove(g)
    import uuid
    outline.append(form('fp_line', form('start', 356.812704-ex, 114-ey), form('end', 356.812704-ex, 132.5-ey),
                        form('stroke', form('width', .3), form('type', Atom('solid'))), form('layer', 'Edge.Cuts'),
                        form('uuid', str(uuid.uuid5(uuid.NAMESPACE_URL, 'yeti60-e73-corner-restored-edge')))))
    pcb_path = out / (NAME + '.kicad_pcb')
    pcb_path.write_text(dumps(tree) + '\n')
    board = pcb.LoadBoard(str(pcb_path))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    origin = pcb.VECTOR2I(pcb.FromMM(ox), pcb.FromMM(oy))
    angle = pcb.EDA_ANGLE(s['rigid_rotation_deg'], pcb.DEGREES_T)
    delta = pcb.VECTOR2I(pcb.FromMM(tx-ox), pcb.FromMM(ty-oy))
    for ref in s['rigid_cluster']:
        fps[ref].Flip(origin, pcb.FLIP_DIRECTION_TOP_BOTTOM)
        fps[ref].Rotate(origin, angle)
        fps[ref].Move(delta)
    for ref, pose in s['other_placements_PCB_mm'].items():
        wanted_side = pcb.F_Cu if ref in s['front_parts'] else pcb.B_Cu
        if fps[ref].GetLayer() != wanted_side:
            fps[ref].Flip(fps[ref].GetPosition(), pcb.FLIP_DIRECTION_TOP_BOTTOM)
        fps[ref].SetOrientationDegrees(pose[2])
        fps[ref].SetPosition(pcb.VECTOR2I(*[pcb.FromMM(v) for v in pose[:2]]))
    zone = pcb.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetZoneName('E73_CORNER_ANTENNA_PROVISIONAL')
    zone.SetLayerSet(pcb.LSET.AllCuMask(4))
    zone.SetDoNotAllowZoneFills(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowPads(True)
    zone.SetDoNotAllowFootprints(False)
    x, y, X, Y = s['provisional_antenna_keepout_PCB_mm']
    zone.Outline().NewOutline()
    for u, v in [(x, y), (X, y), (X, Y), (x, Y)]:
        zone.Outline().Append(pcb.FromMM(u), pcb.FromMM(v))
    board.Add(zone)
    # Reserve the actual adjacent reference beneath each planned USB trace.
    # Only tracks/vias are forbidden: connected ground fill remains allowed.
    # Explicit connector/via launch exceptions are checked independently.
    from screen_yeti60_interference import rect
    launch = rect([347.5,109.5,351,112.5])
    for position in s['data_launch_vias_PCB_mm'].values():
        disk = pcb.PCB_VIA(board)
        disk.SetPosition(pcb.VECTOR2I(*(pcb.FromMM(v) for v in position)))
        disk.SetWidth(pcb.FromMM(1.8))
        poly = pcb.SHAPE_POLY_SET()
        disk.TransformShapeToPolygon(poly, pcb.In2_Cu, 0, pcb.FromMM(.001), pcb.ERROR_OUTSIDE)
        launch.BooleanAdd(poly)
    for net, points in s['data_paths_B_Cu_mm'].items():
        for index,(a,z) in enumerate(zip(points,points[1:])):
            trace = pcb.PCB_TRACK(board)
            trace.SetStart(pcb.VECTOR2I(*(pcb.FromMM(v) for v in a)))
            trace.SetEnd(pcb.VECTOR2I(*(pcb.FromMM(v) for v in z)))
            trace.SetWidth(pcb.FromMM(.3))
            poly = pcb.SHAPE_POLY_SET()
            trace.TransformShapeToPolygon(poly, pcb.In2_Cu, pcb.FromMM(.1), pcb.FromMM(.001), pcb.ERROR_OUTSIDE)
            poly.BooleanSubtract(launch)
            for component in range(poly.OutlineCount()):
                assert poly.HoleCount(component)==0, 'USB reference reservation needs explicit hole support'
                guard = pcb.ZONE(board)
                guard.SetIsRuleArea(True)
                guard.SetLayer(pcb.In2_Cu)
                guard.SetDoNotAllowTracks(True)
                guard.SetDoNotAllowVias(True)
                guard.SetDoNotAllowPads(False)
                guard.SetDoNotAllowZoneFills(False)
                guard.SetDoNotAllowFootprints(False)
                guard.SetZoneName('E73_USB_REFERENCE_'+net+'_'+str(index)+'_'+str(component))
                guard.Outline().NewOutline()
                chain = poly.Outline(component)
                for i in range(chain.PointCount()):
                    pt = chain.CPoint(i)
                    guard.Outline().Append(pt.x,pt.y)
                board.Add(guard)
    pcb.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    pcb.SaveBoard(str(out / (NAME + '.kicad_pcb')), board)
    saved = loads(pcb_path.read_text())
    def append_segment(net, start, end, width, layer, tag):
        assert start != end
        saved.append(form('segment', form('start', *start), form('end', *end), form('width', width),
                          form('layer', layer), form('net', net),
                          form('uuid', str(uuid.uuid5(uuid.NAMESPACE_URL, 'yeti60-e73-corner/'+tag)))))
    def append_via(net, position, tag):
        saved.append(form('via', form('at', *position), form('size', .5), form('drill', .3),
                          form('layers', 'F.Cu', 'B.Cu'),
                          form('tenting', form('front', Atom('yes')), form('back', Atom('yes'))),
                          form('net', net), form('uuid', str(uuid.uuid5(uuid.NAMESPACE_URL, 'yeti60-e73-corner/'+tag)))))
    for ref, pins in s['front_escape_vias'].items():
        for number, position in pins.items():
            pad = next(p for p in fps[ref].Pads() if p.GetNumber() == number)
            assert pad.IsOnLayer(pcb.F_Cu) and pad.GetNetname() and not pad.GetNetname().startswith('unconnected-')
            start = list(pcb.ToMM(pad.GetPosition()))
            tag = 'escape/'+ref+'/'+number
            width = .3 if pad.GetNetname() in ['GND', '+3.3V', 'USB_5V', 'USB_FEED'] else .127
            bends = s.get('front_escape_bends', {}).get(ref, {}).get(number, [])
            points = [start, *bends, position]
            for i, (a, z) in enumerate(zip(points, points[1:])):
                append_segment(pad.GetNetname(), a, z, width, 'F.Cu', tag+'/track/'+str(i))
            append_via(pad.GetNetname(), position, tag+'/via')
    for net, position in s['data_launch_vias_PCB_mm'].items():
        number = '29' if net == 'USB_DM' else '31'
        pad = next(p for p in fps['U1'].Pads() if p.GetNumber() == number)
        assert pad.GetNetname() == net
        append_segment(net, list(pcb.ToMM(pad.GetPosition())), position, .3, 'F.Cu', 'dataF/'+net+'/track')
        append_via(net, position, 'data/'+net+'/via')
    repair = s['reference_corridor_repair']
    for i, (a, z) in enumerate(zip(repair['points_PCB_mm'], repair['points_PCB_mm'][1:])):
        append_segment(repair['net'], a, z, repair['width_mm'], repair['layer'], 'reference-repair/'+str(i))
    for net, points in s['data_paths_B_Cu_mm'].items():
        for i, (a, z) in enumerate(zip(points, points[1:])):
            append_segment(net, a, z, .3, 'B.Cu', 'dataB/'+net+'/'+str(i))
    for i, position in enumerate(s['ground_stitch_vias_PCB_mm']):
        append_via('GND', position, 'USB-GND/'+str(i))
    antenna_zone = next(z for z in children(saved, 'zone') if child(z, 'name') and child(z, 'name')[1] == 'E73_CORNER_ANTENNA_PROVISIONAL')
    child(antenna_zone, 'uuid')[1] = str(uuid.uuid5(uuid.NAMESPACE_URL, 'yeti60-e73-corner/antenna-keepout'))
    for z in children(saved,'zone'):
        name = child(z,'name')
        if name and name[1].startswith('E73_USB_REFERENCE_'):
            child(z,'uuid')[1] = str(uuid.uuid5(uuid.NAMESPACE_URL,'yeti60-e73-corner/'+name[1]))
    pcb_path.write_text(dumps(saved) + '\n')
    normalized = pcb.LoadBoard(str(pcb_path))
    assert normalized is not None
    pcb.ZONE_FILLER(normalized).Fill(normalized.Zones())
    normalized.BuildConnectivity()
    pcb.SaveBoard(str(pcb_path), normalized)
    patch_name = s.get('routing_patch')
    if patch_name:
        patch_path = ROOT/patch_name
        patch = json.loads(patch_path.read_text())
        assert sha(pcb_path)==patch['base_board_sha256'], 'Route patch targets a different placed PCB'
        route_tree = loads(pcb_path.read_text())
        copper_nodes = {str(child(q,'uuid')[1]):q for kind in ['segment','arc','via'] for q in children(route_tree,kind)}
        for item in patch.get('items_to_remove',[]):
            q = copper_nodes[item['uuid']]
            assert hashlib.sha256(dumps(q).encode()).hexdigest()==item['sha256']
            assert child(q,'net')[1]==item['net']=='GND', 'Only the reviewed orphan ground tail may be removed'
            route_tree.remove(q)
            removed.append(dict(uuid=item['uuid'],net=item['net']))
        allowed = {p.GetNetname() for p in fps['U1'].Pads()}|{'COL13','COL14','ROW4'}
        for text in patch['items']:
            q = loads(text)
            assert q[0] in ['segment','arc','via'] and child(q,'net')[1] in allowed
            identifier = str(child(q,'uuid')[1])
            assert identifier not in copper_nodes, 'Route patch duplicates existing copper'
            if q[0]!='via':assert child(q,'layer')[1] in ['B.Cu','In2.Cu']
            route_tree.append(q)
            copper_nodes[identifier]=q
        pcb_path.write_text(dumps(route_tree)+'\n')
        routed = pcb.LoadBoard(str(pcb_path))
        pcb.ZONE_FILLER(routed).Fill(routed.Zones())
        routed.BuildConnectivity()
        pcb.SaveBoard(str(pcb_path),routed)
        inputs.append(patch_path)
    plugin = pcb.PCB_IO_MGR.FindPlugin(pcb.PCB_IO_MGR.KICAD_SEXP)
    plugin.FootprintSave(str(out / 'YAECKB.pretty'), fps['REF**'])
    # Remove the two unused sensing symbols and only their generated dedicated
    # label connections. All 60 effective sensors and their pin roles survive.
    path = out / 'matrix.kicad_sch'
    tree = loads(path.read_text())
    for sym in list(children(tree, 'symbol')):
        if reference(sym) in s['removed_electrodes']:
            # The matrix uses shared buses, not the generated dedicated
            # global-label wiring used on the controller sheet. Preserve the
            # SG bus that passes directly through pin 3; remove only the two
            # dedicated sensing branches to pins 1 and 2.
            library = next(q for q in children(child(tree, 'lib_symbols'), 'symbol') if q[1] == child(sym, 'lib_id')[1])
            sx, sy, rotation = map(float, child(sym, 'at')[1:])
            assert rotation == 0
            pins = symbol_pins(library)
            for number in ['1', '2']:
                dx, dy = pins[number]['at'][:2]
                point = (round(sx+dx, 6), round(sy-dy, 6))
                wires = [w for w in children(tree, 'wire') if any(tuple(round(float(v), 6) for v in p[1:3]) == point for p in child(w, 'pts')[1:])]
                assert len(wires) == 1, ('Unexpected sensing branch', reference(sym), number)
                tree.remove(wires[0])
            tree.remove(sym)
    path.write_text(dumps(tree) + '\n')
    parts = json.loads((out / 'components.json').read_text())
    frozen = json.loads((out / 'frozen-footprints.json').read_text())
    for ref in s['removed_electrodes']:
        # components.json lists purchased electronics only; the actual matrix
        # electrodes are represented by the native board/schematic/netlist.
        assert ref not in parts
        name = frozen.pop(ref)['id'].split(':')[-1] + '.kicad_mod'
        (out / 'YAECKB.pretty' / name).unlink()
    (out / 'components.json').write_text(json.dumps(parts, indent=2) + '\n')
    frozen['REF**']['baseline'] = 'Restored straight right edge for the E73 HHKB corner placement'
    required_libraries = {q['id'].split(':')[-1]+'.kicad_mod' for q in frozen.values()}
    for p in (out / 'YAECKB.pretty').glob('*.kicad_mod'):
        if p.name not in required_libraries:
            p.unlink()
    (out / 'frozen-footprints.json').write_text(json.dumps(frozen, indent=2) + '\n')
    # The earlier SH3 repair changed the land pattern but retained its old PH
    # filter. Update the cached and library filters without changing any pins.
    for path in [out / 'power.kicad_sch', out / 'YAECKB.kicad_sym']:
        text = path.read_text()
        old_filter = 'YAECKB:JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal__*'
        assert old_filter in text, ('Unexpected J2 symbol filter source', path.name)
        path.write_text(text.replace(old_filter, 'YAECKB:JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal__*'))
    # SWxx are copper electrodes, not purchased switches: assembly still needs
    # 60 NiZ housings, sliders, domes and conical springs.
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', str(out / 'netlist.xml'), str(out / (NAME + '.kicad_sch'))], check=True, capture_output=True)
    from check_schematic_current import signature
    components, nets = signature(source / 'netlist.xml')
    components = {r: v for r, v in components.items() if r not in s['removed_electrodes']}
    nets = {n: [v for v in nodes if v[0] not in s['removed_electrodes']] for n, nodes in nets.items()}
    assert signature(out / 'netlist.xml') == (components, nets), 'Relocation changed a retained electrical node'
    report = dict(status='placement-built-routing-open', manufacturing_released=False,
                  physical_verification=False, selected_for_development=True,
                  removed_electrodes=s['removed_electrodes'], removed_copper=removed,
                  relocated_cluster=s['rigid_cluster'], module_origin_PCB_mm=s['module_origin_PCB_mm'],
                  module_rotation_deg=s['rigid_rotation_deg'],
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in inputs},
                  pcb_sha256=sha(out / (NAME + '.kicad_pcb')),
                  open_gates=['Native electrical routing and DRC/parity', 'USB reference-ground closure and new C5 harness',
                              'Module/case/plate/fastener tolerance checks', 'Whole-board and firmware rebinding',
                              'Antenna region confirmation and physical BLE/EC/power acceptance'])
    (out / 'audit/placement-build.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['source_sha256', 'removed_copper']}, indent=2))


if __name__ == '__main__':
    main()
