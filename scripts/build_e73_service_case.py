#!/usr/bin/env python3
"""Build the M05 access prototype from the original M04 exterior surfaces."""

import json
from pathlib import Path
import struct

import numpy as np
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakePrism
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Vec
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from shapely.geometry import Point, box as rectangle

from cad_geometry import bounds, intersection_volume, load
from check_e73_corner_harness import cut
from check_e73_corner_service import AUDIT, BASE, ROOT, read, sha, verify
from check_yeti60_assembly import box, distance, wire
from check_yeti60_interconnects import write_step
from e73_fit_geometry import volume


OUT = BASE/'mechanical/service-case-m05'
PLANS = {
    'J2': {'pocket': [149.6, -139.0, 161.4, -106.20],
           'screws': [(155.5, -135.35), (155.5, -110.0)]},
    'J4': {'pocket': [308.85, -122.50, 355.95, -104.90],
           'screws': [(331.5, -118.65), (348.5, -118.65)]},
}
FOOT_BOUNDS = [310.6377, -114.18, 352.6377, -107.98]
POCKET_DEPTH = 4.0
SEAM = .35
HEAD_DIA = 4.5
HEAD_HEIGHT_MAX = 1.5
SCREW_LENGTH = 4.0
SCREW_SEAT_TO_SHELF = 1.55
INSERT_RECESS = .30


def skin_z(x, y):
    """M04 exterior bearing plane, derived from the native underside face."""
    return (-7.103162571506
            + (1.7345173336995853e-8*(x-464.31271622946)
               -.12186934340504113*(y+202.8165976086))/.992546151641335)


def prism(plan, bottom_z, height):
    loop = wire([(x, y, bottom_z(x, y)) for x, y in plan.exterior.coords], True)
    face = BRepBuilderAPI_MakeFace(loop, True)
    assert face.IsDone()
    return BRepPrimAPI_MakePrism(face.Face(), gp_Vec(0, 0, height)).Shape()


def common(a, b):
    operation = BRepAlgoAPI_Common(a, b)
    operation.Build()
    assert operation.IsDone() and BRepCheck_Analyzer(operation.Shape()).IsValid()
    return operation.Shape()


def solid_count(shape):
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    count = 0
    while explorer.More():
        count += 1
        explorer.Next()
    return count


def cylinder(x, y, z, radius, height):
    axis = gp_Ax2(gp_Pnt(x, y, z), gp_Dir(0, 0, 1))
    return BRepPrimAPI_MakeCylinder(axis, radius, height).Shape()


def rounded(bounds_xy, radius):
    x, y, X, Y = bounds_xy
    return rectangle(x+radius, y+radius, X-radius, Y-radius).buffer(radius, quad_segs=16)


def build_port(ref, raw_window, case, original, insert):
    x, y, _, X, Y, _ = raw_window
    plan = PLANS[ref]
    # Round all four stress corners while retaining the entire checked window.
    tunnel = rounded((x-.30, y-.30, X+.30, Y+.30), .8)
    assert tunnel.contains(rectangle(x, y, X, Y))
    tunnel_solid = prism(tunnel, lambda *_: -25, 22)
    pocket = rounded(plan['pocket'], 1.)
    cap_profile = pocket.buffer(-SEAM)
    assert cap_profile.contains(tunnel)
    flat_tool = lambda x, y: skin_z(x, y)-5
    pocket_cutter = prism(pocket, flat_tool, 5+POCKET_DEPTH)
    case = cut(cut(case, pocket_cutter), tunnel_solid)
    # Copy the original exterior skin, including the right rear foot pocket.
    # Its mounting height stays on the same datum as the other three feet.
    cap = common(original, prism(cap_profile, flat_tool, 5+POCKET_DEPTH))
    assert solid_count(cap) == 1
    assert intersection_volume(cap, case)<1e-6 and volume(cap)>100
    if ref == 'J4':
        assert cap_profile.contains(rectangle(*FOOT_BOUNDS)), 'Cover seam crosses the rear foot'

    fasteners = []
    bore_radius = insert['bore_diameter']/2
    for cx, cy in plan['screws']:
        assert cap_profile.contains(Point(cx, cy).buffer(HEAD_DIA/2+.65))
        shelf = skin_z(cx, cy)+POCKET_DEPTH
        seat = shelf-SCREW_SEAT_TO_SHELF
        bore_end = shelf+insert['bore_depth']
        head_recess = cylinder(cx, cy, -25, HEAD_DIA/2, seat+25)
        screw_hole = cylinder(cx, cy, -25, 1.20, 25+shelf+1)
        minimum_support = cylinder(cx, cy, shelf+.55, bore_radius+2.15, bore_end-shelf+1.6)
        assert abs(volume(minimum_support)-intersection_volume(case, minimum_support))<1e-5, (
            'Insert support insufficient', ref, cx, cy)
        assert intersection_volume(minimum_support, tunnel_solid)<1e-6
        cap = cut(cut(cap, head_recess), screw_hole)
        bore = cylinder(cx, cy, shelf-.30, bore_radius, bore_end-shelf+.30)
        case = cut(case, bore)
        head = cylinder(cx, cy, seat-HEAD_HEIGHT_MAX, 1.95, HEAD_HEIGHT_MAX)
        assert intersection_volume(cap, head)<1e-6
        assert intersection_volume(original, head) >= volume(head)-1e-6, ('Head protrudes', ref)
        if ref == 'J4':
            assert not rectangle(*FOOT_BOUNDS).intersects(rectangle(
                cx-HEAD_DIA/2, cy-HEAD_DIA/2, cx+HEAD_DIA/2, cy+HEAD_DIA/2))
        fasteners.append({'xy_mm': [cx, cy], 'shelf_center_z_mm': shelf,
                          'head_seat_z_mm': seat, 'insert_bore_end_z_mm': bore_end,
                          'screw_tip_to_blind_bottom_mm': bore_end-seat-SCREW_LENGTH,
                          'insert_face_recess_from_shelf_at_axis_mm': INSERT_RECESS,
                          'nominal_thread_overlap_mm': SCREW_LENGTH-SCREW_SEAT_TO_SHELF-INSERT_RECESS})
    assert solid_count(case) == solid_count(cap) == 1
    assert intersection_volume(case, cap)<1e-6
    return case, cap, {
        'ref': ref, 'clear_aperture_bounds_xy_mm': list(tunnel.bounds),
        'original_checked_window_case_bounds_mm': raw_window,
        'cover_pocket_bounds_xy_mm': plan['pocket'],
        'fasteners': fasteners,
    }


def export_part(name, shape):
    step = OUT/(name+'.step')
    stl = step.with_suffix('.stl')
    write_step(shape, step)
    restored = load(step)
    assert max(abs(a-b) for a,b in zip(bounds(shape),bounds(restored)))<.0001
    assert abs(volume(restored)/volume(shape)-1)<.0001
    mesh = BRepMesh_IncrementalMesh(shape, .025, False, .10, True)
    mesh.Perform()
    assert mesh.IsDone()
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    assert writer.Write(shape, str(stl))
    data = stl.read_bytes()
    count = struct.unpack_from('<I', data, 80)[0]
    assert len(data) == 84+50*count
    layout = np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attr', '<u2')])
    facets = np.frombuffer(data, dtype=layout, offset=84)
    rounded = np.round(facets['vertices'].reshape(-1, 3).astype('float64'), 5)
    _, node_ids = np.unique(rounded, axis=0, return_inverse=True)
    faces = node_ids.reshape(-1, 3)
    keep = ((faces[:,0]!=faces[:,1]) & (faces[:,1]!=faces[:,2]) & (faces[:,2]!=faces[:,0]))
    remaining = faces[keep]
    edges = np.sort(np.concatenate([remaining[:,[0,1]], remaining[:,[1,2]], remaining[:,[2,0]]]), axis=1)
    _, incidence = np.unique(edges, axis=0, return_counts=True)
    assert np.all(incidence == 2), ('Non-manifold STL edge', name)
    kept_facets = facets[keep]
    if len(kept_facets) != count:
        stl.write_bytes(data[:80]+struct.pack('<I', len(kept_facets))+kept_facets.tobytes())
    triangles = kept_facets['vertices'].astype('float64')
    coords = triangles.reshape(-1,3)
    assert np.max(np.abs(np.r_[coords.min(axis=0),coords.max(axis=0)]-bounds(shape)))<.055
    v = abs(np.einsum('ij,ij->i', triangles[:,0], np.cross(triangles[:,1],triangles[:,2])).sum()/6)
    assert abs(v/volume(shape)-1) < .015
    return {str(p.relative_to(ROOT)):sha(p) for p in (step, stl)}, {
        'part': name, 'triangles': len(triangles), 'removed_degenerate_facets': count-len(triangles),
        'mesh_volume_mm3': v, 'STEP_volume_mm3': volume(restored), 'two_faces_per_welded_edge': True,
    }


def main():
    assembly_file = ROOT/'mechanical/assembly-spec.json'
    assembly = read(assembly_file)
    source = ROOT/assembly['geometry']['bottom']
    baseline = load(source)
    reference_path = AUDIT/'service-reference.json'
    reference = read(reference_path)
    verify(reference)
    windows = {entry['ref']:entry['trial_window_case_bounds_mm']
               for entry in reference['rigid_housing_travel']
               if entry['PCB_thickness_mm'] == assembly['stack']['pcb_thickness']}
    case = baseline
    caps = {}
    reports = []
    for ref, window in windows.items():
        case, caps[ref], details = build_port(ref, window, case, baseline, assembly['case']['daughterboard_insert'])
        reports.append(details)
        print(ref, details, flush=True)
    assert len(caps) == 2
    assert max(abs(a-b) for a,b in zip(bounds(baseline),bounds(case)))<.0001
    removed = cut(baseline, case)
    assert bounds(removed)[5] <= -3
    for window in windows.values():
        assert intersection_volume(case, box(window))<1e-6, 'Original checked access path blocked'
    for group in ('top', 'daughterboard'):
        features = assembly['case']
        insert = features[group+'_insert']
        radius = ((insert['bore_diameter']+insert['bore_tolerance'])/2
                  +features['finished_bore_position_tolerance']+2)
        for x, y in features[group+'_screw_axes']:
            assert intersection_volume(removed, cylinder(x, y, -25, radius, 35))<1e-6
    assert intersection_volume(case, caps['J2'])<1e-6
    assert intersection_volume(case, caps['J4'])<1e-6
    assert distance(caps['J2'], caps['J4'])>100
    for cap in caps.values():
        assert abs(volume(cap)-intersection_volume(cap, baseline))<1e-5
    # Verify the entire vertical withdrawal from the mating shelf, irrespective
    # of the shape of the cover's internal holes.
    for ref, cap in caps.items():
        plan = rounded(PLANS[ref]['pocket'], 1.).buffer(-SEAM)
        retraction = prism(plan,lambda *_: -35,30)
        outside = cut(retraction, prism(plan, lambda x,y:skin_z(x,y)+POCKET_DEPTH,20))
        assert intersection_volume(case, outside)<1e-6, ('Blocked cover withdrawal', ref)
    OUT.mkdir(parents=True, exist_ok=True)
    outputs, bottom_mesh = export_part('bottom-m05-REVIEW', case)
    meshes = [bottom_mesh]
    for ref, shape in caps.items():
        files, mesh = export_part(f'cover-{ref}-REVIEW', shape)
        outputs.update(files)
        meshes.append(mesh)
    files = [assembly_file, source, reference_path, Path(__file__)]
    result = {
        'status': 'M05-prototype-case-and-covers-exported',
        'selected_for_assembly': False,
        'manufacturing_released': False,
        'physical_verification': False,
        'source_sha256': dict(reference['source_sha256'], **{str(p.relative_to(ROOT)):sha(p) for p in files}),
        'outputs': outputs,
        'minimum_nominal_cover_side_gap_mm': SEAM,
        'original_underside_to_cover_offset_mm': 0,
        'cover_screw': 'M2x0.4 x 4 mm low head, max head diameter 3.9 mm and height 1.5 mm',
        'cover_screw_qty': 4,
        'cover_insert_qty': 4,
        'existing_insert_guards_preserved': 8,
        'ports': reports,
        'meshes': meshes,
        'removed_case_material_bounds_mm': bounds(removed),
        'limits': ['Prototype geometry only. Cold-bond inserts and validate fastener pull-out, cover rigidity and cycling on printed parts.',
                   'The cut shell uses the original upper case and PCB. Tool force, actual cable motion, and coupled system qualification remain open.'],
    }
    (AUDIT/'service-case-m05.json').write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'])


if __name__ == '__main__':
    main()
