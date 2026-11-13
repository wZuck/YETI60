#!/usr/bin/env python3
"""Bounded body-envelope fit for the front-mounted E73 HHKB corner cluster.

Run with requirements-audit.txt. Nominal vendor body and conservative native
footprint boxes are proxies; this does not qualify complete STEP models,
flexible harnesses, module antenna performance or structural strength.
"""
import hashlib
import json
import math
from pathlib import Path
from cad_geometry import intersection_volume, load
from check_yeti60_assembly import box, build_plate, distance

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec_path = ROOT / 'hardware/e73-corner-spec.json'
    s = json.loads(spec_path.read_text())
    base = ROOT / s['output_directory']
    report_path = base / 'audit/corner-fit.json'
    report_path.unlink(missing_ok=True)
    native_path = base / 'audit/placement-check.json'
    native = json.loads(native_path.read_text())
    for name, digest in native['source_sha256'].items():
        assert sha(ROOT / name) == digest, ('Stale placement evidence', name)
    layout = json.loads((ROOT / '.assembly-work/e73-corner/native-layout.json').read_text())
    pcb_path = base / 'EC60-nRF52840.kicad_pcb'
    assert layout['pcb_sha256'] == sha(pcb_path)
    assembly_path = ROOT / 'mechanical/assembly-spec.json'
    fit_path = ROOT / 'mechanical/e73-fit-spec.json'
    fab_path = ROOT / 'mechanical/pcb-fabrication-spec.json'
    a = json.loads(assembly_path.read_text())
    fit = json.loads(fit_path.read_text())
    fab = json.loads(fab_path.read_text())
    source = ROOT / s['bottom_source']
    top_path = ROOT / a['geometry']['top']
    bottom, top = load(source), load(top_path)
    repaired = bottom
    case_error = math.sqrt(3)*fit['case_maximum_coordinate_error_each_axis_mm']
    guard = fit['geometric_computation_guard_mm']
    xy = .1 + .25
    z_error = (fit['plate']['maximum_installed_surface_error_Z_mm']
               + a['pcb_fastener']['shoulder_length_tolerance']
               + a['pcb_fastener']['top_insulator_thickness_tolerance'] + .15)
    pcb_top = a['stack']['plate_bottom_z'] - a['stack']['pcb_to_plate_gap']
    low, high = fab['ordinary_thickness_acceptance_range_mm']
    parts = {q['ref']: q for q in layout['parts']}
    models_path = base/'audit/local-models.json'
    models = json.loads(models_path.read_text())
    for name,digest in models['source_sha256'].items():
        assert sha(ROOT/name)==digest, ('Stale connector model geometry',name)
    heights = s['maximum_installed_component_height_mm']
    records = []
    plate, _ = build_plate(a['stack']['plate_bottom_z'])
    for ref, height in heights.items():
        bb = layout['body'] if ref == 'U1' else parts[ref]['bbox']
        if ref in models['parts']:
            # Model union includes native Fab details and solder feet, while
            # the courtyard is an assembly clearance rather than solid body.
            mb = models['parts'][ref]['nominal_model_and_Fab_union_bounds_native_mm']
            bb = [mb[0],-mb[4],mb[3],-mb[1]]
        x, y, X, Y = bb
        front = ref in s['front_parts']
        if front:
            envelope = [x-xy, -Y-xy, pcb_top-z_error,
                        X+xy, -y+xy, pcb_top+height+z_error]
        else:
            envelope = [x-xy, -Y-xy, pcb_top-high-z_error-height,
                        X+xy, -y+xy, pcb_top-low+z_error]
        body = box(envelope)
        gaps = {name: distance(body, solid) for name, solid in [('bottom', repaired), ('top', top), ('plate', plate)]}
        overlaps = {name: intersection_volume(body, solid) for name, solid in [('bottom', repaired), ('top', top), ('plate', plate)]}
        residual = min(gaps.values()) - case_error - guard
        assert max(overlaps.values()) < 1e-6 and residual >= .15, (ref, overlaps, gaps, residual)
        original_gap = min(distance(body, solid) for solid in [bottom, top]) - case_error - guard
        records.append(dict(reference=ref, proxy='nominal vendor module body' if ref == 'U1' else ('native STEP/Fab union' if ref in models['parts'] else 'native courtyard/graphics XY bounds'),
                            installed_height_limit_mm=height, bounded_envelope_case_mm=envelope,
                            overlap_mm3=overlaps, gaps_mm=gaps, residual_gap_mm=residual,
                            original_case_gap_excluding_plate_mm=original_gap))
    # The steel plate is intentionally retained. Its projected overlap must be
    # measured and disclosed, never described as an antenna-clear installation.
    x, y, X, Y = layout['antenna']
    projection = box([x, -Y, a['stack']['plate_bottom_z'], X, -y,
                      a['stack']['plate_bottom_z'] + a['stack']['plate_thickness']])
    antenna_metal = intersection_volume(projection, plate)/a['stack']['plate_thickness']
    assert antenna_metal > 0
    # Deliberately shift the accepted envelope into the right wall. If this
    # negative witness passes, the shape/case test is not detecting interference.
    wrong = records[0]['bounded_envelope_case_mm'][:]
    wrong[0] += 30
    wrong[3] += 30
    assert max(intersection_volume(box(wrong), q) for q in [repaired, top]) > 1e-6
    sources = [spec_path, native_path, pcb_path, assembly_path, fit_path, fab_path,
               source, top_path, models_path, ROOT / 'scripts/check_e73_usb_local_models.py', ROOT / a['geometry']['plate'], Path(__file__),
               ROOT / 'scripts/cad_geometry.py', ROOT / 'scripts/check_yeti60_assembly.py',
               ROOT / 'scripts/check_yeti60_plate_mount.py']
    d = dict(status='bounded-corner-body-proxies-passed-harness-and-RF-open', manufacturing_released=False,
             physical_verification=False, complete_keyboard_tolerance_qualified=False,
             continuous_PCB_thickness_range_mm=[low, high], body_and_board_XY_each_axis_mm=xy,
             combined_stack_bow_Z_mm=z_error, case_each_axis_mm=fit['case_maximum_coordinate_error_each_axis_mm'],
             case_L2_allowance_mm=case_error, computation_guard_mm=guard, minimum_required_gap_mm=.15,
             parts=records, antenna_metal_plate_projection_overlap_mm2=antenna_metal,
             plate_material='304 stainless steel, unchanged',
             front_mount=True, bottom_changed=False,
             bottom_source=s['bottom_source'],
             wrong_30mm_translation_rejected=True,
             source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
             limits=['Conservative body boxes are engineering acceptance envelopes; received parts require inspection',
                     'Module remains a nominal body proxy; only J4/J5/C32 have STEP and solder-foot checks',
                     'No flexible harness, insertion/removal, adjacent NiZ housing/clip model, resin strength or key-mechanism load qualification',
                     'Retained metal plate overlaps the provisional antenna band; 2-3 m BLE operation remains unverified',
                     'No electromagnetic field solve or EC interference acceptance'])
    report_path.write_text(json.dumps(d, indent=2) + '\n')
    print(json.dumps({k: d[k] for k in ['status', 'antenna_metal_plate_projection_overlap_mm2', 'bottom_changed']}, indent=2))


if __name__ == '__main__':
    main()
