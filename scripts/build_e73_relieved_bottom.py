#!/usr/bin/env python3
"""Build the full M05 relieved trial bottom from the verified coupon geometry."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import json
import math
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

from build_e73_m05_harness import PORT_FAMILIES, matched_spec
from build_e73_retainer_coupon import REFERENCE, REPORT as COUPON_REPORT
import build_e73_service_case as case_export
from cad_geometry import bounds, intersection_volume, load
from check_e73_corner_harness import cut, datums
from check_e73_delivery import retainer_mesh
from check_e73_print_fit import hole, vertical_cylinders
from check_e73_retainer_recess import (
    AUDIT, CASE_DIR, ROOT, apply_recess, common, modified_case, read, sha, verified_underside,
)
from check_e73_service_leads import STATES, check_guide_channels
from check_yeti60_assembly import box, distance
from e73_corner_harness_paths import envelope_wire, length, paired_data
from e73_corner_retention import build as build_guides
from e73_fit_geometry import external_faces, volume
from e73_service_leads import BATTERY_GUIDE_STATIONS, flex_routes, position_exits

DIRECTORY = Path("02-mechanical/service-case-m05/relieved-trial")
NAME = "bottom-m05-relieved-REVIEW"
REPORT = Path("06-validation/m05-relieved-bottom.json")
RECESS_REPORT = Path("06-validation/m05-usb-retainer-recess.json")


def nominal_lengths(inputs):
    thickness, report, spec, native, assembly, cutters = inputs
    bottom, exits = datums(native, assembly, spec)
    delta = assembly["stack"]["pcb_thickness"] - thickness
    case = modified_case(cutters)
    installed, center, _ = flex_routes(spec, exits, exits, 0)
    installed["usb"].update(paired_data(center, spec)[0])
    rigid, films = build_guides(spec, case, installed, exits, bottom)
    retained = [part for part in rigid + films if not part["name"].startswith("USB-F")]
    assert len(retained) == 25
    guide_envelopes = report["USB_service_motion_trial"]["larger_USB_guide_envelopes_case_mm"]
    front = {name: box(bb) for name, bb in guide_envelopes.items()}
    wire_limits = spec["wire"]
    diameter = wire_limits["insulation_od_max"] + 2 * wire_limits["case_and_route_position_allowance"]
    lengths, checks = {}, []
    for label, state in STATES.items():
        parked = position_exits(exits, *state)
        routes, center, _ = flex_routes(spec, exits, parked, delta)
        routes["usb"].update(paired_data(center, spec)[0])
        checked = check_guide_channels(installed, routes, spec, retained, delta)
        if label == "seated":
            lengths = {f"{family}.{pin}": round(length(path), 9)
                       for family, leads in routes.items() for pin, path in leads.items()}
        foreign = {f"{family}.{pin}": envelope_wire(path, diameter)
                   for family in ("battery", "power") for pin, path in routes[family].items()}
        gap, guide, wire = min((distance(part, lead), name, pin)
                              for name, part in front.items() for pin, lead in foreign.items())
        assert gap >= wire_limits["minimum_air_gap_after_allowance"], (thickness, label, guide, wire, gap)
        checks.append(dict(checked, state=label, front_guide_to_foreign_wire_gap_mm=round(gap, 9),
                           nearest_front_guide=guide, nearest_foreign_wire=wire))
    return {"PCB_thickness_mm": thickness, "seated_free_lengths_mm": lengths, "guide_checks": checks}


def csv_lengths(output, reference, lengths):
    tables = {}
    shared = (lengths["usb.2"] + lengths["usb.3"]) / 2
    differences = {}
    for suffix, status in ((".csv", "M05 relieved trial target"), (".zh-CN.csv", "M05 让位版试装目标")):
        before = reference / "harness" / ("wire-lengths-m05" + suffix)
        rel = DIRECTORY / ("wire-lengths-relieved" + suffix)
        after = output / rel
        with before.open(newline="") as source, after.open("w", newline="") as destination:
            header, *rows = csv.reader(source)
            writer = csv.writer(destination, lineterminator="\n")
            writer.writerow(header)
            seen = set()
            for row in rows:
                port, pin = row[1:3]
                key = f"{PORT_FAMILIES[port]}.{pin}"
                value = shared if key in ("usb.2", "usb.3") else lengths[key]
                text = f"{value:.3f}"
                delta = round(float(text) - float(row[6]), 3)
                assert key.startswith("usb.") or delta == 0, (port, pin, delta)
                assert delta == differences.setdefault(key, delta)
                row[6], row[-1] = text, status
                writer.writerow(row)
                seen.add(key)
            assert seen == lengths.keys() and len(rows) == len(seen)
        tables[rel.as_posix()] = before
    return tables, differences


def verify_relief(original, exact, trial, cover_record, assembly, report, coupon_record, coupon_reference, skin_allowance):
    assert case_export.solid_count(trial) == 1
    assert max(abs(a - b) for a, b in zip(bounds(original), bounds(trial))) < 1e-6
    # Compare original and edited solids before STEP re-parameterizes the
    # thousands of coincident outer faces. Test the stored STEP separately
    # with its volume, feature metrology and the cut region itself.
    removed = cut(original, exact)
    assert volume(cut(exact, original)) < 1e-6 and volume(removed) > 0
    assert math.isclose(volume(exact), volume(trial), abs_tol=1e-5)
    proof = report["USB_service_motion_trial"]
    expected = math.fsum([proof["motion_floor_relief_removed_volume_mm3"],
                          *(row["trial_removed_volume_mm3"] for row in report["stations"])])
    assert math.isclose(volume(removed), expected, abs_tol=1e-5)
    # Recheck the wall and mounting witnesses on the delivered STEP.
    faces = external_faces(original)
    faces.append(verified_underside(original, 203, -151))
    minimum_nominal_wall = min(distance(removed, face) for face in faces)
    residual_skin = minimum_nominal_wall - skin_allowance
    assert math.isclose(residual_skin, proof["minimum_wall_to_selected_exterior_after_allowances_mm"], abs_tol=1e-5)

    fits = []
    stock_features = vertical_cylinders(original)
    trial_features = vertical_cylinders(trial)
    features = assembly["case"]
    axes = [("M3 lower passage", xy, 3.4) for xy in features["top_screw_axes"]]
    axes += [("C5 insert", xy, features["daughterboard_insert"]["bore_diameter"])
             for xy in features["daughterboard_screw_axes"]]
    cover_shapes = {}
    for port in cover_record["ports"]:
        ref = port["ref"]
        cover_shapes[ref] = load(CASE_DIR / f"cover-{ref}-REVIEW.step")
        axes += [(ref + " cover insert", row["xy_mm"], 3.35) for row in port["fasteners"]]
        assert intersection_volume(trial, cover_shapes[ref]) < 1e-6
        assert intersection_volume(trial, box(port["original_checked_window_case_bounds_mm"])) < 1e-6
        x, y, X, Y = port["cover_pocket_bounds_xy_mm"]
        assert intersection_volume(removed, box([x, y, -35, X, Y, 30])) < 1e-6
    for name, center, dia in axes:
        before = hole(stock_features, center, dia)
        after = hole(trial_features, center, dia)
        assert before == after, (name, before, after)
        fits.append(dict(after, interface=name))

    pack = assembly["battery"]
    x, y, X, Y = pack["bounds_xy"]
    p = pack["position_tolerance"]
    z = pack["top_z"]
    pack_proxy = box([x - p, y - p, z - pack["full_envelope_including_growth"][2] - p, X + p, Y + p, z + p])
    assert distance(removed, pack_proxy) > 1
    floor = common(trial, box(coupon_record["floor_crop_case_mm"]))
    solid = TopExp_Explorer(coupon_reference, TopAbs_SOLID)
    parts = []
    while solid.More():
        parts.append(solid.Current())
        solid.Next()
    assert len(parts) == 5
    coupon_floor = max(parts, key=volume)
    assert math.isclose(intersection_volume(removed, box(coupon_record["floor_crop_case_mm"])),
                        volume(removed), abs_tol=1e-5)
    assert math.isclose(volume(coupon_floor), volume(floor), abs_tol=1e-4)
    assert math.isclose(intersection_volume(coupon_floor, floor), volume(floor), abs_tol=1e-4)
    return {
        "removed_volume_mm3": round(volume(removed), 6),
        "removed_bounds_case_mm": [round(value, 6) for value in bounds(removed)],
        "outer_case_bounds_mm": [round(value, 6) for value in bounds(trial)],
        "m05_holes_read_back": fits,
        "cover_interfaces_clear": sorted(cover_shapes),
        "nominal_minimum_leftover_skin_mm": round(minimum_nominal_wall, 6),
        "minimum_leftover_skin_after_allowances_mm": round(residual_skin, 6),
        "identical_to_crop_in_coupon_reference": True,
    }


def build(output):
    evidence, coupon_evidence = output / RECESS_REPORT, output / COUPON_REPORT
    recess, coupon = read(evidence), read(coupon_evidence)
    assert recess["status"] == "USB-front-recess-service-poses-and-parked-lift-checked"
    assert coupon["status"] == "m05-front-retainer-sla-coupons-exported-and-cad-checked"
    assert coupon["recess_report_sha256"] == sha(evidence)
    for status in (recess, coupon):
        assert status["selected_for_assembly"] is False and status["physical_verification"] is False
        assert all(sha(ROOT / name) == digest for name, digest in status["source_sha256"].items())
    original_step = CASE_DIR / "bottom-m05-REVIEW.step"
    case_report = AUDIT / "service-case-m05.json"
    cover_record = read(case_report)
    checked_paths = [original_step, *(CASE_DIR / f"cover-{ref}-REVIEW.step" for ref in ("J2", "J4"))]
    for path in checked_paths:
        assert sha(path) == cover_record["outputs"][path.relative_to(ROOT).as_posix()]
    assembly_path = ROOT / "mechanical/assembly-spec.json"
    assembly = read(assembly_path)
    wire_path = ROOT / "hardware/e73-corner-harness-spec.json"
    retention_path = ROOT / "hardware/e73-corner-retention-spec.json"
    retention = read(retention_path)
    fit_path = ROOT / assembly["geometry"]["fit_spec"]
    skin_allowance = (2 * math.sqrt(3) * retention["tolerance_contract"]["case_maximum_coordinate_error_each_axis_mm"]
                      + read(fit_path)["geometric_computation_guard_mm"])
    native_path = AUDIT / "harness-native.json"
    native = read(native_path)
    spec = matched_spec(read(wire_path))
    spec["guides"] = dict(retention["guides"], battery_x=BATTERY_GUIDE_STATIONS)
    spec["usb"]["front_z"] = math.nextafter(spec["usb"]["front_z"] - recess["trial_axis_drop_mm"], math.inf)
    proof = recess["USB_service_motion_trial"]
    cutters = [*(row["trial_recess_bounds_case_mm"] for row in recess["stations"]),
               proof["motion_floor_relief_bounds_case_mm"]]
    exact = original = load(original_step)
    for cutter in cutters:
        exact, _ = apply_recess(original, exact, cutter)
    (output / DIRECTORY).mkdir(parents=True, exist_ok=True)
    step, stl = (DIRECTORY / (NAME + ext) for ext in (".step", ".stl"))
    scratch = ROOT / ".assembly-work/e73-corner"
    scratch.mkdir(parents=True, exist_ok=True)
    # Reuse the original shell mesher's 0.01 µm weld and degenerate-face
    # cleanup. Its audit paths are relative to the checkout.
    with tempfile.TemporaryDirectory(prefix="relieved-export-", dir=scratch) as folder:
        with patch.object(case_export, "OUT", Path(folder)):
            _, mesh = case_export.export_part(NAME, exact)
        for path in (step, stl):
            shutil.copyfile(Path(folder) / path.name, output / path)
    triangles, dimensions = retainer_mesh((output / stl).read_bytes(), weld_digits=5)
    assert triangles == mesh["triangles"] and mesh["two_faces_per_welded_edge"]
    reference = output / REFERENCE
    assert coupon["files_sha256"][REFERENCE.as_posix()] == sha(reference)
    geometry = verify_relief(original, exact, load(output / step), cover_record, assembly, recess,
                             coupon, load(reference), skin_allowance)
    spec_variants = [(row["PCB_thickness_mm"], recess, spec, native, assembly, cutters) for row in proof["variants"]]
    with ProcessPoolExecutor(max_workers=len(spec_variants)) as pool:
        configurations = list(pool.map(nominal_lengths, spec_variants))
    nominal = next(v for v in configurations if v["PCB_thickness_mm"] == assembly["stack"]["pcb_thickness"])
    tables, differences = csv_lengths(output, CASE_DIR, nominal["seated_free_lengths_mm"])
    sources = [Path(__file__), case_report, *checked_paths, assembly_path, wire_path, retention_path, fit_path, native_path,
               *tables.values(), *(ROOT / "scripts" / name for name in (
                   "build_e73_service_case.py", "build_e73_retainer_coupon.py", "check_e73_print_fit.py",
                   "check_e73_retainer_recess.py", "check_e73_service_leads.py", "check_e73_delivery.py",
               ))]
    result = {
        "status": "m05-relieved-trial-bottom-exported-and-verified",
        "selected_for_assembly": False,
        "manufacturing_released": False,
        "physical_verification": False,
        "source_reports_sha256": {path.as_posix(): sha(output / path) for path in (RECESS_REPORT, COUPON_REPORT)},
        "geometry": geometry,
        "mesh": dict(mesh, dimensions_xyz_mm=dimensions, connected_closed_shells=1, weld_decimal_places=5),
        "variants": configurations,
        "seated_free_length_target_delta_from_m05_mm": differences,
        "files_sha256": {path: sha(output / path) for path in (step.as_posix(), stl.as_posix(), *tables)},
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in sources},
        "limits": [
            "A matched engineering trial. Existing cover, screw, pack and guide process acceptance still applies.",
            "The model checks the retained 12 rigid guides and associated films in prescribed poses.",
            "Physical assembly, finished resins, cable motion between poses and the pack, BLE and USB first article remain open.",
        ],
    }
    (output / REPORT).write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    build(parser.parse_args().output.resolve())
