#!/usr/bin/env python3
"""E73-specific bounded USB body/axial-motion screen and internal floor repair.

This does not qualify tools, flexible wires, other part models or the complete
assembly. Nominal models and measured acceptance requirements remain distinct.
"""
import hashlib
import json
import math
from pathlib import Path
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from cad_geometry import bounds, intersection_volume, load
from check_yeti60_assembly import box, distance
from check_yeti60_interconnects import write_step
from build_yeti60_mechanical import cut, rounded_box
from build_e73_fit_candidate import insert_guards
from e73_fit_geometry import external_faces, volume

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/e73-usb-repair'
SPEC = ROOT / 'hardware/e73-usb-local-fit-spec.json'


def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(mapping):
    for name, digest in mapping.items():
        assert sha(ROOT / name) == digest, ('Stale local fit input', name)


def expand(bb, xy=0, down=0, up=0):
    return [bb[0]-xy, bb[1]-xy, bb[2]-down, bb[3]+xy, bb[4]+xy, bb[5]+up]


def sweep_bounds(bb, axis, stroke):
    assert axis in [(0, 1), (0, -1), (1, 1), (1, -1)] and stroke > 0
    index, direction = axis
    parked = bb[:]
    parked[index] += direction*stroke; parked[index+3] += direction*stroke
    return [min(bb[i], parked[i]) for i in range(3)] + [max(bb[i], parked[i]) for i in range(3, 6)], parked


def housing(ref, native, spec, z):
    """Native XY transformed into case XY, retaining the actual J4 rotation."""
    from kicad_sexpr import child, children, loads
    tree = loads((BASE / 'EC60-nRF52840.kicad_pcb').read_text())
    footprint = next(f for f in children(tree, 'footprint')
                     if any(p[1:3] == ['Reference', ref] for p in children(f, 'property')))
    x, y, *angle = [float(v) for v in child(footprint, 'at')[1:]]
    assert (ref == 'J4' and angle == [90]) or (ref == 'J5' and (not angle or angle == [0])), (ref, angle)
    count = 4 if ref == 'J4' else 2
    assert Path(native['parts'][ref]['model_source']['path']).name.startswith(f'JST_SH_SM0{count}B-SRSS-TB_')
    y = -y
    s = spec['supplier_drawing']; w = s['housing_widths_mm'][ref]
    front = s['header_rear_local_y_mm'] + s['side_entry_assembly_depth_reference_mm']
    rear = front - s['housing_depth_mm']
    h = spec['maximum_height_below_local_PCB_mm'][ref]
    if ref == 'J4':
        bb = [x-front, y-w/2, z-h, x-rear, y+w/2, z]
        axis = (0, -1)
    else:
        bb = [x-w/2, y+rear, z-h, x+w/2, y+front, z]
        axis = (1, 1)
    header = native['parts'][ref]['bounds_native_mm']
    assert bb[0] < header[3] and bb[3] > header[0] and bb[1] < header[4] and bb[4] > header[1], 'Unmated housing datum'
    return bb, axis


def main():
    report_path = BASE / 'audit/local-fit.json'
    report_path.unlink(missing_ok=True)
    spec = read(SPEC)
    assert not spec['selected_by_assembly'] and not spec['manufacturing_released']
    assembly_path = ROOT / 'docs/audit/yeti60-assembly.json'
    assembly = read(assembly_path); hashes(assembly['source_sha256'])
    hashes(assembly['verification_recipe_sha256'])
    assert sha(ROOT/'docs/audit/yeti60-pcb-mechanical-metadata.json') == assembly['mechanical_metadata_sha256']
    native_path = BASE / 'audit/native-check.json'; native = read(native_path)
    hashes(native['source_sha256'])
    assert native['status'] == 'e73-usb-native-candidate-checks-passed'
    model_path = BASE / 'audit/local-models.json'; models = read(model_path)
    hashes(models['source_sha256'])
    assert models['status'] == 'local-native-model-and-landing-passed'
    for part in models['parts'].values():
        assert sha(ROOT/part['path']) == part['sha256']
        assert sha(Path(part['model_source']['path'])) == part['model_source']['sha256']
    mechanical = read(ROOT/'mechanical/assembly-spec.json')
    fit = read(ROOT/'mechanical/e73-fit-spec.json')
    fabrication = read(ROOT/'mechanical/pcb-fabrication-spec.json')
    assert assembly['selected_geometry'] == mechanical['geometry']
    z = assembly['nominal_stack']['pcb_bottom_z']
    nominal = fabrication['CAD_finished_envelope_mm']
    assert abs(nominal - mechanical['stack']['pcb_thickness']) < 1e-8
    terms = dict(plate=fit['plate']['maximum_installed_surface_error_Z_mm'],
                 shoulder=mechanical['pcb_fastener']['shoulder_length_tolerance'],
                 film=mechanical['pcb_fastener']['top_insulator_thickness_tolerance'],
                 bow=spec['maximum_additional_mounted_PCB_bow_Z_mm'])
    z_error = math.fsum(terms.values())
    xy = spec['maximum_body_growth_XY_each_axis_mm'] + spec['maximum_installed_board_point_error_XY_each_axis_mm']
    case_error = math.sqrt(3)*fit['case_maximum_coordinate_error_each_axis_mm']
    reserve = fit['minimum_residual_air_gap_mm']
    guard = fit['geometric_computation_guard_mm']
    original_path = ROOT/mechanical['geometry']['bottom']; top_path = ROOT/mechanical['geometry']['top']
    original = load(original_path); top = load(top_path)
    relief = spec['floor_relief']
    bottom = cut(original, rounded_box(relief['bounds_case_mm'], relief['corner_radius_mm']))
    removed = cut(original, bottom)
    assert volume(removed) > 1e-6
    assert max(abs(a-b) for a,b in zip(bounds(original),bounds(bottom))) < 1e-6
    skin = external_faces(original)
    nominal_wall = min(distance(removed, f) for f in skin)
    # Inside and outside are different case surfaces; both may move toward
    # each other within the per-surface coordinate acceptance requirement.
    wall = nominal_wall-2*case_error-guard
    assert wall >= relief['minimum_remaining_exterior_wall_mm'], ('Exterior wall', wall)
    # The relief stays well below both gasket/plate bearing ledges.
    assert bounds(removed)[5] < assembly['nominal_stack']['bottom_gasket_ledge_z']-.2
    inserts = insert_guards(removed, mechanical)
    output = ROOT/spec['bottom_output']; output.parent.mkdir(exist_ok=True)
    write_step(bottom, output)
    exported=load(output); solids=TopExp_Explorer(exported,TopAbs_SOLID); count=0
    while solids.More(): count+=1; solids.Next()
    assert count==1, ('Repaired shell is not a single exported solid',count)
    assert max(abs(a-b) for a,b in zip(bounds(bottom),bounds(exported)))<1e-6
    BRepMesh_IncrementalMesh(bottom,.015,False,.08,True).Perform()
    writer=StlAPI_Writer(); writer.ASCIIMode=False
    assert writer.Write(bottom,str(output.with_suffix('.stl')))

    byref={p['ref']:p for p in assembly['component_envelopes']}
    retained=[]
    for ref,p in byref.items():
        if ref in ['D1','R30','R31','C32']: continue
        # These are the declared canonical proxies, not newly accepted models.
        retained.append((ref,box(p['bounds_case_mm'])))
    for h in assembly['mounting_hole_matches']:
        x,y=h['pcb_center_case_mm']; r=mechanical['pcb_fastener']['washer_od_max']/2+.15
        retained.append(('mount-'+h['pcb_ref'],box([x-r,y-r,-3.9,x+r,y+r,z])))
    pack = box(assembly['battery_candidates'][0]['bounds_case_mm'])
    bodies={}
    for ref,part in models['parts'].items():
        bb=part['bounds_native_mm'][:]
        assert spec['maximum_height_below_local_PCB_mm'][ref] >= -bb[2], (ref,'Model exceeds required installed height')
        bb[2]=z-spec['maximum_height_below_local_PCB_mm'][ref];bb[5]=z
        bodies[ref]=bb
    plugs={ref:housing(ref,models,spec,z) for ref in ['J4','J5']}
    checks=[]; baseline_failures=[]
    low,high=fabrication['ordinary_thickness_acceptance_range_mm']
    cases=[(t,nominal-t,nominal-t) for t in [nominal,low,high]]
    # The fourth case encloses the whole continuous board-thickness interval,
    # rather than inferring interval acceptance from three sampled positions.
    cases.append(([low,high],nominal-high,nominal-low))
    for thickness,delta_low,delta_high in cases:
        def positioned(bb):
            result=bb[:];result[2]+=delta_low;result[5]+=delta_high
            return result
        static={ref:expand(positioned(bb),xy,z_error,z_error)
                for ref,bb in bodies.items()}
        installed={ref:expand(positioned(bb),xy,z_error,z_error)
                   for ref,(bb,_) in plugs.items()}
        for mode in ['static','withdrawal']:
            references=['J4','J5','C32'] if mode=='static' else spec['withdrawal_order']
            for index,ref in enumerate(references):
                targets=[('body',static[ref])] if mode=='static' else []
                if ref in plugs:
                    plug=installed[ref]
                    if mode=='withdrawal':
                        plug,parked=sweep_bounds(plug,plugs[ref][1],spec['withdrawal_stroke_mm'])
                        axis,direction=plugs[ref][1]
                        header=expand(bodies[ref],xy=xy)
                        separation=(header[axis]-parked[axis+3]) if direction<0 else (parked[axis]-header[axis+3])
                        # The two global XY allowances represent the same PCB
                        # datum and cancel here; part growth remains independent.
                        separation += 2*spec['maximum_installed_board_point_error_XY_each_axis_mm']
                        assert separation >= spec['minimum_detached_housing_to_header_gap_mm']-1e-6
                    targets.append(('housing' if mode=='static' else 'housing-sweep',plug))
                for kind,bb in targets:
                    shape=box(bb)
                    gaps={name:distance(shape,c) for name,c in [('bottom',bottom),('top',top)]}
                    residual=min(gaps.values())-case_error-guard
                    assert residual >= reserve-1e-6, (ref,mode,kind,thickness,'Case reserve',residual)
                    other=[(name,box(positioned(bounds(s)))) for name,s in retained]
                    other.append(('pack',pack))
                    other += [('body-'+r,box(b)) for r,b in static.items() if r!=ref]
                    removed_plugs=set(spec['withdrawal_order'][:index]) if mode=='withdrawal' else set()
                    other += [('housing-'+r,box(b)) for r,b in installed.items() if r!=ref and r not in removed_plugs]
                    nearest=min((distance(shape,s),name) for name,s in other)
                    assert nearest[0] >= spec['minimum_foreign_part_air_gap_mm']-1e-6, (ref,mode,kind,'Part obstruction',nearest)
                    old_gap=distance(shape,original)
                    if old_gap-case_error-guard < reserve:
                        baseline_failures.append(dict(ref=ref,mode=mode,kind=kind,pcb_thickness_mm=thickness,original_case_gap_mm=old_gap,remaining_gap_mm=old_gap-case_error-guard))
                    checks.append(dict(ref=ref,mode=mode,kind=kind,pcb_thickness_mm=thickness,bounds_case_mm=bb,
                                       case_gaps_mm=gaps,remaining_case_air_gap_mm=residual,
                                       nearest_foreign_part=nearest[1],minimum_foreign_part_gap_mm=nearest[0],
                                       detached_housing_to_header_gap_mm=separation if mode=='withdrawal' else None,
                                       proxy_components_and_mounts_checked=len(retained)))
    assert any(r['pcb_thickness_mm']==max(fabrication['ordinary_thickness_acceptance_range_mm']) for r in baseline_failures), 'Original floor regression did not reproduce'
    # A real unsafe service sequence: moving J4 while J5's housing is installed.
    bad_sweep,_=sweep_bounds(expand(plugs['J4'][0],xy,z_error,z_error),plugs['J4'][1],spec['withdrawal_stroke_mm'])
    order_overlap=intersection_volume(box(bad_sweep),box(expand(plugs['J5'][0],xy,z_error,z_error)))
    assert order_overlap > 1e-6, 'Wrong-order envelope fault was not reproduced'
    inputs=[Path(__file__),SPEC,assembly_path,native_path,model_path,
            ROOT/'mechanical/assembly-spec.json',ROOT/'mechanical/e73-fit-spec.json',
            ROOT/'mechanical/pcb-fabrication-spec.json',original_path,top_path,
            BASE/'EC60-nRF52840.kicad_pcb',ROOT/'scripts/check_yeti60_interconnects.py',
            ROOT/'scripts/build_e73_fit_candidate.py',ROOT/'scripts/build_yeti60_mechanical.py',
            ROOT/'scripts/e73_fit_geometry.py',ROOT/'scripts/check_yeti60_assembly.py',
            ROOT/'scripts/cad_geometry.py',ROOT/'scripts/kicad_sexpr.py',ROOT/'scripts/draw_e73_usb_local_fit.py']
    report=dict(status='e73-local-usb-body-and-ordered-withdrawal-screen-passed',
                selected_by_assembly=False,manufacturing_released=False,physical_verification=False,
                complete_assembly_qualified=False,source_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},
                outputs={str(p.relative_to(ROOT)):sha(p) for p in [output,output.with_suffix('.stl')]},
                vertical_error_terms_mm=terms,vertical_error_sum_mm=z_error,
                PCB_nominal_thickness_mm=nominal,PCB_thickness_acceptance_interval_mm=[low,high],
                geometric_computation_guard_mm=guard,minimum_required_case_air_gap_mm=reserve,
                body_and_board_XY_allowance_each_axis_mm=xy,case_coordinate_error_L2_mm=case_error,
                required_body_bounds_case_mm=bodies,
                mating_housings={ref:dict(bounds_case_mm=bb,axis=axis) for ref,(bb,axis) in plugs.items()},
                checks=checks,original_floor_failed_checks=baseline_failures,
                wrong_order_expanded_housing_overlap_mm3=order_overlap,
                withdrawal_order=spec['withdrawal_order'],withdrawal_stroke_mm=spec['withdrawal_stroke_mm'],
                case_repair=dict(bounds_unchanged=True,removed_volume_mm3=volume(removed),
                                 exported_solid_count=count,nominal_removed_to_selected_exterior_wall_mm=nominal_wall,
                                 two_surface_case_error_deduction_mm=2*case_error,
                                 minimum_remaining_selected_exterior_wall_after_allowances_mm=wall,
                                 exterior_faces_checked=len(skin),insert_supports=inserts),
                limits=['Only J4/J5/C32 bodies and J4/J5 rigid axial housing motion; flexible wires/tools and connected service are not checked',
                        'Other retained components and fasteners use inherited proxy envelopes; complete model and tolerance closure is open',
                        'Body, placement, bow and case error bounds are measured acceptance requirements, not qualified supplier tolerances',
                        'No PCB installation/removal, NiZ full-travel, C5 cable, battery connector, USB SI, RF or electrical/thermal acceptance'])
    from draw_e73_usb_local_fit import draw
    report['outputs'].update(draw(report,spec))
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(checks),'checks; minimum case reserve',min(r['remaining_case_air_gap_mm'] for r in checks),flush=True)


if __name__=='__main__': main()
