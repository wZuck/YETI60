#!/usr/bin/env python3
"""Read-only placement proof for the actual E73 right HHKB corner candidate.

Run with KiCad Python. A passing placement proof never implies routed or RF
acceptance. The independent strict DRC is recorded even while routing is open.
"""
from collections import Counter
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET
import pcbnew as pcb
from screen_yeti60_interference import rect, rings
from kicad_sexpr import child, children, loads

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'hardware/e73-corner-spec.json'
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
NAME = 'EC60-nRF52840'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pads(f):
    return {p.m_Uuid.AsString(): (p.GetNumber(), p.GetNetname(), p.GetPosition().x, p.GetPosition().y,
                                  p.GetSize().x, p.GetSize().y, p.GetShape(), p.GetOrientationDegrees()) for p in f.Pads()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-routed', action='store_true', help='Return 2 while errors, opens or parity differences remain')
    args = parser.parse_args()
    s = json.loads(SPEC.read_text())
    base, source = ROOT / s['output_directory'], ROOT / s['source_directory']
    path = base / (NAME + '.kicad_pcb')
    report_path = base / 'audit/placement-check.json'
    report_path.unlink(missing_ok=True)
    build_path = base / 'audit/placement-build.json'
    build = json.loads(build_path.read_text())
    assert build['source_sha256'].get(str(SPEC.relative_to(ROOT))) == sha(SPEC), 'Placement specification was not used by the build'
    for name, digest in build['source_sha256'].items():
        assert sha(ROOT / name) == digest, ('Stale placement build input', name)
    assert sha(path) == build['pcb_sha256'], 'Rebuild placement proof or provide a separately verified routing import'
    b, old = pcb.LoadBoard(str(path)), pcb.LoadBoard(str(source / path.name))
    now = {f.GetReference(): f for f in b.GetFootprints()}
    before = {f.GetReference(): f for f in old.GetFootprints()}
    assert set(now) == set(before) - set(s['removed_electrodes'])
    active_path = ROOT / 'docs/audit/yeti60-key-geometry.json'
    active = json.loads(active_path.read_text())['matches']
    active_refs = {q['electrode'] for q in active}
    assert len(active) == 60 and not active_refs.intersection(s['removed_electrodes'])
    changed = set(s['rigid_cluster']) | set(s['other_placements_PCB_mm']) | {'REF**'}
    for ref in set(now) - changed:
        assert pads(before[ref]) == pads(now[ref]), ('Changed retained lands', ref)
        assert before[ref].GetPosition() == now[ref].GetPosition(), ('Moved retained part', ref)
        assert before[ref].GetLayer() == now[ref].GetLayer(), ('Flipped retained part', ref)
    for ref in changed - {'REF**'}:
        old_pads, new_pads = pads(before[ref]), pads(now[ref])
        assert set(old_pads) == set(new_pads)
        for key in old_pads:
            assert old_pads[key][:2] == new_pads[key][:2], ('Changed pin identity or role', ref, key)
            assert old_pads[key][4:7] == new_pads[key][4:7], ('Changed land size/shape', ref, key)
    for ref, pose in s['other_placements_PCB_mm'].items():
        assert list(pcb.ToMM(now[ref].GetPosition())) == pose[:2], ('Changed intended part position', ref)
        assert abs((now[ref].GetOrientationDegrees()-pose[2]+180)%360-180) < 1e-6
        assert now[ref].GetLayer() == (pcb.F_Cu if ref in s['front_parts'] else pcb.B_Cu)
    def mounts(board):
        return {p.m_Uuid.AsString():dict(reference=f.GetReference(),
                xy=list(pcb.ToMM(p.GetPosition())),drill=list(pcb.ToMM(p.GetDrillSize())),
                attribute=p.GetAttribute(),net=p.GetNetname())
                for f in board.GetFootprints() for p in f.Pads()
                if f.GetReference().startswith('H') or
                (f.GetReference()=='REF**' and min(pcb.ToMM(p.GetDrillSize()))>=2.2)}
    old_mounts,new_mounts=mounts(old),mounts(b)
    assert len(old_mounts)==len(new_mounts)==29 and old_mounts==new_mounts, 'Changed mount/slot geometry'
    retired = {q['uuid'] for q in build['removed_copper']}
    retained_tracks = {t.m_Uuid.AsString(): t for t in old.GetTracks() if t.m_Uuid.AsString() not in retired}
    actual_tracks = {t.m_Uuid.AsString(): t for t in b.GetTracks()}
    def signature(t):
        key = (t.GetClass(), t.GetNetname(), t.GetStart().x, t.GetStart().y,
               t.GetEnd().x, t.GetEnd().y, t.GetLayer(), t.GetWidth(pcb.F_Cu) if t.GetClass() == 'PCB_VIA' else t.GetWidth())
        if t.GetClass() == 'PCB_VIA':
            key += (t.GetDrillValue(), t.GetViaType())
        elif t.GetClass() == 'PCB_ARC':
            key += (t.GetMid().x, t.GetMid().y)
        return key
    for uid, t in retained_tracks.items():
        assert uid in actual_tracks and signature(actual_tracks[uid]) == signature(t), ('Changed retained copper', uid)
    assert len(list(now['U1'].Pads())) == 43 and now['U1'].GetLayer() == pcb.F_Cu
    assert list(pcb.ToMM(now['U1'].GetPosition())) == s['module_origin_PCB_mm']
    assert abs(now['U1'].GetOrientationDegrees() - s['rigid_rotation_deg']) < 1e-6
    source_origin = pcb.ToMM(before['U1'].GetPosition())
    original_module_pads = {p.m_Uuid.AsString():p for p in before['U1'].Pads()}
    for pad in now['U1'].Pads():
        old_xy = pcb.ToMM(original_module_pads[pad.m_Uuid.AsString()].GetPosition())
        expected = [s['module_origin_PCB_mm'][0]+old_xy[0]-source_origin[0],
                    s['module_origin_PCB_mm'][1]-old_xy[1]+source_origin[1]]
        assert math.dist(pcb.ToMM(pad.GetPosition()),expected)<.000002, ('Changed transformed module land',pad.GetNumber())
    angle = math.radians(now['U1'].GetOrientationDegrees())
    ox, oy = pcb.ToMM(now['U1'].GetPosition())
    def project(local):
        points = [(ox+math.cos(angle)*x+math.sin(angle)*y, oy-math.sin(angle)*x+math.cos(angle)*y)
                  for x in [local[0], local[2]] for y in [local[1], local[3]]]
        return [min(v[i] for v in points) for i in [0, 1]]+[max(v[i] for v in points) for i in [0, 1]]
    body, antenna, formal = project([0,-13,18,0]), project([15,-13,18,0]), False
    assert max(abs(a-z) for a, z in zip(body, s['module_body_PCB_mm'])) < 1e-6
    assert max(abs(a-z) for a, z in zip(antenna, s['provisional_antenna_PCB_mm'])) < 1e-6 and not formal
    overlap = []
    for ref in sorted(active_refs):
        q = pcb.SHAPE_POLY_SET()
        for p in now[ref].Pads():
            if p.IsOnLayer(pcb.F_Cu):
                q.BooleanAdd(p.GetEffectivePolygon(pcb.F_Cu))
        q.BooleanIntersection(rect(body))
        area = q.Area()/1e12
        assert area < .000001, ('Module overlaps effective sensing copper', ref, area)
        overlap.append({'reference': ref, 'module_projection_overlap_mm2': area})
    outline = pcb.SHAPE_POLY_SET()
    assert b.GetBoardPolygonOutlines(outline, False)
    land_edge = []
    for p in now['U1'].Pads():
        poly = pcb.SHAPE_POLY_SET(p.GetEffectivePolygon(pcb.F_Cu))
        outside = pcb.SHAPE_POLY_SET(poly)
        outside.BooleanSubtract(outline)
        assert outside.Area() < 1, ('Unsupported module land', p.GetNumber())
        bb = p.GetBoundingBox()
        poly = rect([pcb.ToMM(bb.GetLeft())-.7, pcb.ToMM(bb.GetTop())-.7,
                     pcb.ToMM(bb.GetRight())+.7, pcb.ToMM(bb.GetBottom())+.7])
        poly.BooleanSubtract(outline)
        assert poly.Area() < 1, ('Module copper closer than .5 mm rule plus .2 mm outline allowance', p.GetNumber())
        land_edge.append(p.GetNumber())
    new_data = {t.m_Uuid.AsString(): t for t in b.GetTracks() if t.GetNetname() in ['USB_DM', 'USB_DP']}
    key = lambda a, z: tuple(sorted([tuple(round(float(v),6) for v in a), tuple(round(float(v),6) for v in z)]))
    pair = {}
    for net, points in s['data_paths_B_Cu_mm'].items():
        expected = Counter(key(a,z) for a,z in zip(points,points[1:]))
        tracks = [t for t in new_data.values() if t.GetNetname() == net and t.GetClass() == 'PCB_TRACK']
        back = [t for t in tracks if t.GetLayer() == pcb.B_Cu]
        front = [t for t in tracks if t.GetLayer() == pcb.F_Cu]
        vias = [t for t in new_data.values() if t.GetNetname() == net and t.GetClass() == 'PCB_VIA']
        assert len(front) == len(vias) == 1
        assert all(t.GetWidth() == pcb.FromMM(.3) for t in tracks)
        assert Counter(key(pcb.ToMM(t.GetStart()), pcb.ToMM(t.GetEnd())) for t in back) == expected
        pin, hpin = ('29', '2') if net == 'USB_DM' else ('31', '3')
        module_pad = next(p for p in now['U1'].Pads() if p.GetNumber() == pin)
        header_pad = next(p for p in now['J4'].Pads() if p.GetNumber() == hpin)
        assert front[0].GetStart() == module_pad.GetPosition()
        assert list(pcb.ToMM(front[0].GetEnd())) == points[-1] == s['data_launch_vias_PCB_mm'][net]
        assert vias[0].GetPosition() == front[0].GetEnd()
        assert list(pcb.ToMM(header_pad.GetPosition())) == points[0], ('USB path misses header', net)
        pair[net] = dict(track_length_mm=sum(t.GetLength() for t in tracks)/1e6,
                         back_length_mm=sum(t.GetLength() for t in back)/1e6,
                         vias=1, layers=['B.Cu', 'F.Cu'], width_mm=.3)
    assert set(s['data_paths_B_Cu_mm']) == {'USB_DM','USB_DP'}, 'USB pair has not been planned'
    repair = s['reference_corridor_repair']
    assert set(repair['removed_In2_UUIDs']).issubset(retired)
    for i, (a,z) in enumerate(zip(repair['points_PCB_mm'], repair['points_PCB_mm'][1:])):
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, 'yeti60-e73-corner/reference-repair/'+str(i)))
        t = actual_tracks[uid]
        assert t.GetNetname() == repair['net'] and b.GetLayerName(t.GetLayer()) == repair['layer']
        assert t.GetWidth() == pcb.FromMM(repair['width_mm'])
        assert key(pcb.ToMM(t.GetStart()),pcb.ToMM(t.GetEnd())) == key(a,z)
    escape = []
    native_tree = loads(path.read_text())
    via_forms = {str(child(v, 'uuid')[1]): v for v in children(native_tree, 'via')}
    def verify_via(identifier, position, net, reference, pin, destination=escape, diameter=.5):
        via = actual_tracks[identifier]
        assert via.GetClass() == 'PCB_VIA' and via.GetNetname() == net
        assert list(pcb.ToMM(via.GetPosition())) == position
        assert via.GetViaType() == pcb.VIATYPE_THROUGH and via.GetDrillValue() == pcb.FromMM(.3)
        assert via.GetWidth(pcb.F_Cu) == pcb.FromMM(diameter)
        form = via_forms[identifier]
        assert child(form, 'layers')[1:] == ['F.Cu', 'B.Cu']
        assert child(child(form, 'tenting'), 'front')[1] == 'yes' and child(child(form, 'tenting'), 'back')[1] == 'yes'
        overlaps = []
        for layer in [pcb.F_Cu, pcb.B_Cu]:
            circle = pcb.SHAPE_POLY_SET()
            via.TransformShapeToPolygon(circle, layer, 0, pcb.FromMM(.001), pcb.ERROR_OUTSIDE)
            for f in b.GetFootprints():
                for p in f.Pads():
                    if p.GetAttribute() != pcb.PAD_ATTRIB_SMD or not p.IsOnLayer(layer):
                        continue
                    if not p.GetBoundingBox().Intersects(via.GetBoundingBox()):
                        continue
                    q = pcb.SHAPE_POLY_SET(p.GetEffectivePolygon(layer))
                    q.BooleanIntersection(circle)
                    if q.Area() > 1:
                        overlaps.append((f.GetReference(), p.GetNumber(), b.GetLayerName(layer)))
        assert not overlaps, ('Escape via overlaps SMD copper', reference, pin, overlaps)
        destination.append(dict(reference=reference, pin=pin, net=via.GetNetname(), center_PCB_mm=position,
                           diameter_mm=diameter, drill_mm=.3, both_faces_tented=True, SMD_land_overlap=False))
    for ref, pins in s['front_escape_vias'].items():
        for number, position in pins.items():
            prefix = 'yeti60-e73-corner/escape/'+ref+'/'+number
            pad = next(p for p in now[ref].Pads() if p.GetNumber() == number)
            width = .3 if pad.GetNetname() in ['GND', '+3.3V', 'USB_5V', 'USB_FEED'] else .127
            points = [list(pcb.ToMM(pad.GetPosition())), *s.get('front_escape_bends',{}).get(ref,{}).get(number,[]), position]
            for i,(a,z) in enumerate(zip(points,points[1:])):
                track = actual_tracks[str(uuid.uuid5(uuid.NAMESPACE_URL,prefix+'/track/'+str(i)))]
                assert track.GetClass() == 'PCB_TRACK' and track.GetLayer() == pcb.F_Cu
                assert track.GetNetname() == pad.GetNetname() and track.GetWidth() == pcb.FromMM(width)
                assert key(pcb.ToMM(track.GetStart()),pcb.ToMM(track.GetEnd())) == key(a,z)
            verify_via(str(uuid.uuid5(uuid.NAMESPACE_URL,prefix+'/via')),position,pad.GetNetname(),ref,number)
    for net, position in s['data_launch_vias_PCB_mm'].items():
        verify_via(str(uuid.uuid5(uuid.NAMESPACE_URL,'yeti60-e73-corner/data/'+net+'/via')),position,net,'U1','29' if net=='USB_DM' else '31')
    for i, position in enumerate(s['ground_stitch_vias_PCB_mm']):
        verify_via(str(uuid.uuid5(uuid.NAMESPACE_URL,'yeti60-e73-corner/USB-GND/'+str(i))),position,'GND','USB-return',str(i))
    assert len(escape) == sum(len(p) for p in s['front_escape_vias'].values())+len(s['data_launch_vias_PCB_mm'])+len(s['ground_stitch_vias_PCB_mm'])
    routed_vias=[]
    if s.get('routing_patch'):
        patch_path=ROOT/s['routing_patch']
        patch=json.loads(patch_path.read_text())
        for text in patch['items']:
            q=loads(text);identifier=str(child(q,'uuid')[1]);actual=actual_tracks[identifier]
            assert actual.GetNetname()==child(q,'net')[1], ('Changed routed net',identifier)
            if q[0]=='via':
                verify_via(identifier,list(map(float,child(q,'at')[1:3])),child(q,'net')[1],
                           'routed',str(len(routed_vias)),routed_vias,float(child(q,'size')[1]))
            else:
                assert b.GetLayerName(actual.GetLayer())==child(q,'layer')[1]
                assert key(pcb.ToMM(actual.GetStart()),pcb.ToMM(actual.GetEnd()))==key(child(q,'start')[1:3],child(q,'end')[1:3])
                assert actual.GetWidth()==pcb.FromMM(float(child(q,'width')[1]))
    copper = []
    roi = rect(antenna)
    roi_bb = roi.BBox()
    for layer in [pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu]:
        total = pcb.SHAPE_POLY_SET()
        for f in b.GetFootprints():
            for p in f.Pads():
                if p.IsOnLayer(layer) and p.GetBoundingBox().Intersects(roi_bb):
                    q = pcb.SHAPE_POLY_SET(p.GetEffectivePolygon(layer))
                    q.BooleanIntersection(roi)
                    total.BooleanAdd(q)
        for t in b.GetTracks():
            if t.IsOnLayer(layer) and t.GetBoundingBox().Intersects(roi_bb):
                poly = pcb.SHAPE_POLY_SET()
                t.TransformShapeToPolygon(poly, layer, 0, pcb.FromMM(.002), pcb.ERROR_INSIDE)
                poly.BooleanIntersection(roi)
                total.BooleanAdd(poly)
        for z in b.Zones():
            if not z.GetIsRuleArea() and z.IsOnLayer(layer):
                q = pcb.SHAPE_POLY_SET(z.GetFilledPolysList(layer))
                q.BooleanIntersection(roi)
                total.BooleanAdd(q)
        assert total.Area()/1e12 < .000001, ('Copper in provisional antenna band', b.GetLayerName(layer), total.Area()/1e12)
        copper.append({'layer': b.GetLayerName(layer), 'overlap_mm2': total.Area()/1e12})
    # Record failed electrical gates without converting a placement success
    # into a whole-board success. All ignored project rules are re-enabled.
    config = json.loads((base / (NAME + '.kicad_pro')).read_text())
    for key, severity in config['board']['design_settings']['rule_severities'].items():
        if severity == 'ignore':
            config['board']['design_settings']['rule_severities'][key] = 'warning'
    with tempfile.TemporaryDirectory(prefix='e73-corner-drc-') as folder:
        scratch = Path(folder)
        for p in base.glob('*.kicad_sch'):
            shutil.copyfile(p, scratch / p.name)
        for name in [path.name, 'YAECKB.kicad_sym', 'sym-lib-table', 'fp-lib-table']:
            shutil.copyfile(base / name, scratch / name)
        (scratch / 'YAECKB.pretty').symlink_to((base / 'YAECKB.pretty').resolve(), target_is_directory=True)
        (scratch / (NAME + '.kicad_pro')).write_text(json.dumps(config))
        command = [CLI, 'pcb', 'drc', '--all-track-errors', '--schematic-parity', '--severity-all', '--refill-zones', '--format', 'json', '-o', str(base / 'audit/DRC-routing-open.json'), str(scratch / path.name)]
        subprocess.run(command, check=True, capture_output=True)
    drc = json.loads((base / 'audit/DRC-routing-open.json').read_text())
    failures = Counter(q['type'] for q in drc['violations'])
    electrically_complete = (not drc['unconnected_items'] and not drc['schematic_parity']
                             and not any(q['severity'] == 'error' for q in drc['violations']))
    d = dict(status='native-routing-and-placement-checks-passed' if electrically_complete else 'placement-geometry-passed-electrical-routing-open', manufacturing_released=False,
             physical_verification=False, selected_for_development=True,
             electrical_routing_complete=electrically_complete,
             module_body_PCB_mm=body, provisional_antenna_PCB_mm=antenna,
             module_pin_count=43, unchanged_effective_keys=60,
             unchanged_retained_copper_items=len(retained_tracks),
             ordinary_front_escape_vias=escape,ordinary_routed_vias=routed_vias,
             removed_electrodes=s['removed_electrodes'], effective_electrode_overlaps=overlap,
             supported_module_lands_with_0p7mm_enlargement=land_edge,
             preserved_mount_references=sorted(r for r in now if r.startswith('H')),
             preserved_mount_holes_and_slots=list(new_mounts.values()),
             USB_pair=pair, USB_track_count=len(new_data), antenna_copper=copper,
             DRC_violations_by_type=dict(failures), unconnected_items=len(drc['unconnected_items']),
             schematic_parity_items=len(drc['schematic_parity']),
             source_sha256={str(p.relative_to(ROOT)): sha(p) for p in [SPEC, path, build_path, source / path.name, active_path, Path(__file__), ROOT / 'scripts/screen_yeti60_interference.py']},
             limits=['Native geometry/connectivity checks only; no manufacturing or physical release',
                     'Antenna projection is provisional; retained metal plate remains above the antenna',
                     'C5 harness lengths and case/connector tolerance/service checks must be redone',
                     'Whole-board RF, EC noise and hardware power/USB/BLE acceptance remain open'])
    report_path.write_text(json.dumps(d, indent=2) + '\n')
    # Geometry for a drawing comes from native objects, never from a mock PCB.
    work = ROOT / '.assembly-work/e73-corner' if SPEC == ROOT / 'hardware/e73-corner-spec.json' else base / 'audit'
    work.mkdir(parents=True, exist_ok=True)
    drawing = dict(pcb_sha256=sha(path), outline=rings(outline), body=body, antenna=antenna, electrodes=[], parts=[],mounts=list(new_mounts.values()))
    for ref, f in now.items():
        if ref.startswith('SW') and ref != 'SW100':
            polygons = []
            for p in f.Pads():
                if p.IsOnLayer(pcb.F_Cu):
                    polygons.extend(rings(p.GetEffectivePolygon(pcb.F_Cu)))
            drawing['electrodes'].append(dict(ref=ref, active=ref in active_refs, polygons=polygons))
        elif ref in ['J4', 'J5', 'C31', 'C32', 'R24', 'R25'] or ref.startswith('H'):
            bb = f.GetBoundingBox(False, False)
            drawing['parts'].append(dict(ref=ref, xy=list(pcb.ToMM(f.GetPosition())), bbox=[pcb.ToMM(v) for v in [bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()]]))
    (work / 'native-layout.json').write_text(json.dumps(drawing) + '\n')
    print(json.dumps({k: d[k] for k in ['status', 'module_body_PCB_mm', 'antenna_copper', 'DRC_violations_by_type', 'unconnected_items', 'schematic_parity_items']}, indent=2))
    if args.require_routed and not electrically_complete:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
