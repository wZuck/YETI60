#!/usr/bin/env python3
"""Independently screen actual relocated USB copper and connected reference.

This is a geometry/connectivity screen, not signal-integrity or hardware USB
acceptance. It does not use the planner's allowed-region or path evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
from shapely.geometry import Point, box
from shapely.ops import unary_union
from plan_e73_corner_usb import union

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ['F.Cu','In1.Cu','In2.Cu','B.Cu']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-pass',action='store_true')
    args = parser.parse_args()
    spec_path = ROOT/'hardware/e73-corner-spec.json'
    s = json.loads(spec_path.read_text())
    base = ROOT/s['output_directory']
    data_path = ROOT/'.assembly-work/e73-corner/copper.json'
    d = json.loads(data_path.read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name,digest in d['source_sha256'].items():
        assert sha(ROOT/name) == digest, ('Stale actual copper export',name)
    # Merge touching polygons on each layer, preserving every interior hole.
    # 2 um accommodates the independently exported 1 um polygon approximation.
    grounds = {l:union(d['ground_copper'][l]).buffer(.002) for l in LAYERS}
    nodes = []
    for l,g in grounds.items():
        nodes.extend((l,p) for p in (list(g.geoms) if hasattr(g,'geoms') else [g]) if not p.is_empty)
    parent = list(range(len(nodes)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for via in d['ground_vertical_connectors']:
        hit = []
        for i,(l,p) in enumerate(nodes):
            if l in via['by_layer'] and p.intersects(union(via['by_layer'][l])):
                hit.append(i)
        for i in hit[1:]:
            parent[find(i)] = find(hit[0])
    anchor = d['ground_anchors']['J4.4']
    anchors = [i for i,(l,p) in enumerate(nodes) if l==anchor['layer'] and p.covers(Point(anchor['xy']))]
    assert len(anchors) == 1, 'USB connector ground anchor is absent or ambiguous'
    root = find(anchors[0])
    connected = {l:unary_union([p for i,(layer,p) in enumerate(nodes) if layer==l and find(i)==root]) for l in LAYERS}
    detached = {}
    for i,(layer,p) in enumerate(nodes):
        if find(i)!=root:
            detached.setdefault(find(i),{}).setdefault(layer,[]).append(p)
    detached = [{l:dict(area_mm2=unary_union(v).area,bounds_PCB_mm=list(unary_union(v).bounds)) for l,v in group.items()} for group in detached.values()]
    # Explicit, bounded launch exceptions; each receives a nearby grounded
    # through-via requirement below. They are disclosed, never called covered.
    module_launch = unary_union([Point(v).buffer(.9) for v in s['data_launch_vias_PCB_mm'].values()])
    header_launch = box(347.5,109.5,351,112.5)
    exceptions = module_launch.union(header_launch)
    records = []
    for net in ['USB_DM','USB_DP']:
        for q in d['USB_copper'].get(net,[]):
            if q['kind'] != 'trace':continue
            for layer,polygons in q['by_layer'].items():
                reference = 'In2.Cu' if layer=='B.Cu' else 'In1.Cu'
                assert layer in ['B.Cu','F.Cu'], ('Unexpected USB routing layer',layer)
                copper = union(polygons)
                required = copper.buffer(.1)
                outside = required.difference(exceptions)
                missing = outside.difference(connected[reference])
                records.append(dict(net=net,UUID=q['UUID'],layer=layer,reference_layer=reference,
                    copper_area_mm2=copper.area,launch_exception_area_mm2=required.intersection(exceptions).area,
                    uncovered_connected_reference_mm2=missing.area,
                    missing_bounds_PCB_mm=list(missing.bounds) if not missing.is_empty else None))
    assert records and set(s['data_paths_B_Cu_mm'])=={'USB_DM','USB_DP'}, 'USB route is incomplete'
    launches = []
    for net,xy in s['data_launch_vias_PCB_mm'].items():
        nearest = []
        for v in d['ground_through_vias']:
            pt = Point(v['xy'])
            if all(connected[l].covers(pt) for l in LAYERS):
                nearest.append(Point(xy).distance(pt))
        launches.append(dict(net=net,nearest_connected_ground_through_via_mm=min(nearest) if nearest else None))
    back = {n:unary_union([union(q['by_layer']['B.Cu']) for q in d['USB_copper'][n] if 'B.Cu' in q['by_layer']]) for n in ['USB_DM','USB_DP']}
    pair_clearance = back['USB_DM'].distance(back['USB_DP'])
    mask = union(d['B_mask_openings'])
    mask_clearance = min(back[n].distance(mask) for n in back)
    reference_ok = all(q['uncovered_connected_reference_mm2']<.00001 for q in records)
    launch_ok = all(q['nearest_connected_ground_through_via_mm'] is not None and q['nearest_connected_ground_through_via_mm']<=1.5 for q in launches)
    passed = reference_ok and launch_ok and pair_clearance>=.198 and mask_clearance>=.2 and not detached
    report = dict(status='actual-USB-reference-screen-passed' if passed else 'actual-USB-reference-hold',
        manufacturing_released=False,physical_verification=False,checks_passed=passed,
        reference_passed=reference_ok,launch_ground_passed=launch_ok,
        detached_ground_components=detached,whole_ground_network_connected=not detached,
        reference_reserve_mm=.1,polygon_contact_allowance_mm=.002,
        back_pair_minimum_actual_copper_clearance_mm=pair_clearance,
        back_pair_to_existing_mask_opening_clearance_mm=mask_clearance,segments=records,launches=launches,
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [spec_path,data_path,Path(__file__),ROOT/'scripts/plan_e73_corner_usb.py']},
        limits=['Launch regions are explicitly excluded from planar coverage, not proven impedance-controlled',
                'Ground connectivity uses actual polygons and ground-only vertical conductors',
                'Impedance, eye diagram, EMC, all routed-board integrity and physical USB remain unqualified'])
    (base/'audit/USB-reference.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','reference_passed','launch_ground_passed','back_pair_minimum_actual_copper_clearance_mm','launches']},indent=2))
    return 2 if args.require_pass and not passed else 0


if __name__=='__main__':raise SystemExit(main())
