#!/usr/bin/env python3
"""Build a connected SLA print coupon and a matched M05 floor sample."""

import argparse
import json
import math
from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS_Compound
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf

from build_e73_m05_harness import matched_spec
from cad_geometry import bounds, intersection_volume, load
from check_e73_corner_harness import datums
from check_e73_delivery import retainer_mesh
from check_e73_retainer_recess import AUDIT, CASE_DIR, ROOT, common, modified_case, read, sha
from check_e73_service_leads import STATES
from check_yeti60_assembly import box, distance, move
from check_yeti60_interconnects import write_step
from e73_corner_harness_paths import envelope_wire, paired_data
from e73_corner_retention import boolean, slot
from e73_fit_geometry import volume
from e73_retention_channels import bond_areas, capture
from e73_service_leads import flex_routes, position_exits
from export_e73_retention_prints import mesh

DIRECTORY = Path("02-mechanical/front-retainer-coupon")
RECESS_REPORT = Path("06-validation/m05-usb-retainer-recess.json")
REPORT = Path("06-validation/m05-usb-retainer-coupon.json")
GUIDES_STL = DIRECTORY / "M05-front-guides-SLA-COUPON.stl"
FLOOR_STL = DIRECTORY / "M05-front-floor-SLA-COUPON.stl"
REFERENCE = DIRECTORY / "fit-reference-DO-NOT-UPLOAD.step"
DRAWING = DIRECTORY / "cut-map.svg"
STOCK_MM = .30
NECK_MM = 2.0
RAW_X = 6.0
LID_SPLIT_GAP_MM = .05


def rounded(items):
    return [round(value, 6) for value in items]


def solid(shape):
    pieces = TopExp_Explorer(shape, TopAbs_SOLID)
    assert pieces.More(), "Missing guide or coupon solid"
    pieces.Next()
    assert not pieces.More() and BRepCheck_Analyzer(shape).IsValid(), "Expected one valid solid"
    return shape


def front_profiles(datum, seat, radii, web, depth, bond, stock):
    x, y, z = datum
    pair, single = radii
    width = 1.5 + single + web + stock
    z_ranges = ((seat + bond - stock, z), (z + LID_SPLIT_GAP_MM, z + pair + web + stock))
    parts = []
    for bottom, top in z_ranges:
        part = box([x - width, y - depth / 2, bottom, x + width, y + depth / 2, top])
        for offset, radius in ((0, pair), (-1.5, single), (1.5, single)):
            part = slot(part, (0, 1, 0), (x + offset, y - depth / 2 - .01, z), depth + .02, radius)
        parts.append(solid(part))
    return parts


def print_layout(parts):
    carrier = box([0, 0, 0, 2.5, 22, NECK_MM])
    flip = gp_Trsf()
    flip.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi)
    records = []
    for index, (name, (finished, raw)) in enumerate(parts.items()):
        if name.endswith("-lid"):
            raw = BRepBuilderAPI_Transform(raw, flip, True).Shape()
            finished = BRepBuilderAPI_Transform(finished, flip, True).Shape()
        station_y = 3 + index * 5
        x, y, z, _, _, _ = bounds(raw)
        shift = (RAW_X - x, station_y - NECK_MM / 2 - y, -z)
        raw = move(raw, *shift)
        finished = move(finished, *shift)
        neck = box([2.25, station_y - NECK_MM / 2, 0,
                    RAW_X + STOCK_MM / 2, station_y + NECK_MM / 2, NECK_MM])
        carrier = boolean(carrier, neck, BRepAlgoAPI_Fuse)
        assert intersection_volume(raw, neck) > .5
        carrier = boolean(carrier, raw, BRepAlgoAPI_Fuse)
        assert bounds(neck)[3] < bounds(finished)[0]
        records.append((name, raw, finished))
    solid(carrier)
    rows = {}
    for name, raw, finished in records:
        bb = bounds(finished)
        trimmed = solid(common(carrier, box(bb)))
        difference = abs(volume(trimmed) - volume(finished))
        overlap = intersection_volume(trimmed, finished)
        assert difference < 1e-6 and abs(overlap - volume(finished)) < 1e-6, name
        rows[name] = {
            "raw_layout_bounds_mm": rounded(bounds(raw)),
            "finished_layout_bounds_mm": rounded(bb),
            "finished_size_mm": rounded(bb[i + 3] - bb[i] for i in range(3)),
            "trim_recovery_volume_error_mm3": round(difference, 9),
        }
    return carrier, rows


def draw_layout(target, rows):
    # Raw outlines and finished boxes are projected from the verified solids.
    items = []
    for name, row in rows.items():
        x, y, _, X, Y, _ = row["raw_layout_bounds_mm"]
        left, _, _, right, _, _ = row["finished_layout_bounds_mm"]
        items.append(f'<path d="M2.5 {y}H{x}v{Y-y}H2.5Z" fill="#9c7741"/>')
        items.append(f'<rect x="{x}" y="{y}" width="{X-x:.2f}" height="{Y-y}" fill="#b2d9cc"/>')
        items.append(f'<path d="M{left} {y-.25}V{Y+.25} M{right} {y-.25}V{Y+.25}" stroke="#773c1d" stroke-width=".13"/>')
        items.append(f'<text x="14" y="{y+1.4}" font-size="1.3">{name}</text>')
    target.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 29 24" width="696" height="576">\n'
        '<rect x="-1" y="-1" width="29" height="24" fill="#f8f5e9"/>\n'
        '<rect x="0" y="0" width="2.5" height="22" fill="#9c7741"/>\n'
        '<g font-family="sans-serif" fill="#18382d">\n'
        + "\n".join(items)
        + '\n<path d="M14 21h5m-5 -.25v.5m5 -.5v.5" stroke="#18382d" stroke-width=".1"/>'
          '<text x="20" y="21.4" font-size="1.1">5 mm</text></g></svg>\n'
    )


def check_cables(recess, installed, sections, retention, wires, assembly, native):
    spec = matched_spec(wires)
    spec["usb"]["front_z"] = math.nextafter(wires["usb"]["front_z"] - recess["trial_axis_drop_mm"], math.inf)
    error = recess["hypothetical_surface_point_error_L2_mm"]
    spec["guides"] = dict(retention["guides"], guide_print_tolerance=error,
                          groove_radius=recess["minimum_single_wire_groove_radius_mm"],
                          pair_groove_radius=recess["trial_usb_pair_groove_radius_mm"])
    _, exits = datums(native, assembly, spec)
    finished_od = wires["wire"]["insulation_od_max"] + 2 * spec["guides"]["local_wire_position_allowance"]
    checks = []
    nominal = assembly["stack"]["pcb_thickness"]
    for variant in recess["USB_service_motion_trial"]["variants"]:
        thickness = variant["PCB_thickness_mm"]
        for label, state in STATES.items():
            routes, center, _ = flex_routes(spec, exits, position_exits(exits, *state), nominal - thickness)
            routes["usb"].update(paired_data(center, spec)[0])
            envelopes = {("usb", pin): envelope_wire(route, finished_od) for pin, route in routes["usb"].items()}
            for section in sections:
                station = section["name"]
                results = capture(section, envelopes, routes, spec)
                assert all(row["captured"] for row in results), (thickness, label, station, results)
                contact = max(intersection_volume(installed[station + side][0], envelope)
                              for side in ("-base", "-lid") for envelope in envelopes.values())
                assert contact < 1e-6, (thickness, label, station, contact)
                checks.append({"PCB_thickness_mm": thickness, "state": label, "station": station,
                               "pins_captured_after_groove_shrink": sorted(row["pin"] for row in results),
                               "maximum_wire_overlap_with_finished_guide_mm3": round(contact, 9)})
    return checks


def build(output):
    evidence = output / RECESS_REPORT
    recess = read(evidence)
    assert recess["status"] == "USB-front-recess-service-poses-and-parked-lift-checked"
    assert not recess["selected_for_assembly"] and not recess["physical_verification"]
    assert all(sha(ROOT / name) == digest for name, digest in recess["source_sha256"].items())
    retention_file = ROOT / "hardware/e73-corner-retention-spec.json"
    retention = read(retention_file)
    wire_file = ROOT / "hardware/e73-corner-harness-spec.json"
    wires = read(wire_file)
    fit_file = ROOT / "mechanical/e73-fit-spec.json"
    fit = read(fit_file)
    assembly_file = ROOT / "mechanical/assembly-spec.json"
    assembly = read(assembly_file)
    native_file = AUDIT / "harness-native.json"
    native = read(native_file)
    stations = recess["stations"]
    lift = recess["USB_service_motion_trial"]
    case = modified_case([*(row["trial_recess_bounds_case_mm"] for row in stations),
                          lift["motion_floor_relief_bounds_case_mm"]])
    # Keep the real two seats, U-loop floor and underlying external surface.
    crop = [188, -176, bounds(case)[2] - 1, 219, -127, 0]
    floor = solid(common(case, box(crop)))
    guides, limits = retention["guides"], retention["tolerance_contract"]
    pair = recess["trial_usb_pair_groove_radius_mm"]
    single = recess["minimum_single_wire_groove_radius_mm"]
    web = recess["minimum_nominal_web_mm"]
    depth, bond = guides["depth"], guides["bond_gap"]
    axis = wires["usb"]["front_z"] - recess["trial_axis_drop_mm"]
    shell_allowance = math.sqrt(3) * limits["case_maximum_coordinate_error_each_axis_mm"] + fit["geometric_computation_guard_mm"]
    parts = {}
    sections = []
    fits = []
    for row in stations:
        name = row["station"]
        datum = [*row["center_case_xy_mm"], axis]
        seat = row["trial_floor_Z_mm"]
        finished = front_profiles(datum, seat, (pair, single), web, depth, bond, 0)
        blanks = front_profiles(datum, seat, (pair, single), web, depth, bond, STOCK_MM)
        part_names = [name + "-base", name + "-lid"]
        assert intersection_volume(*finished) < 1e-6
        for label, piece, blank in zip(part_names, finished, blanks):
            assert intersection_volume(piece, floor) < 1e-6, label
            gap = distance(piece, floor)
            if label.endswith("-base"):
                assert math.isclose(gap, bond, abs_tol=1e-6), label
            else:
                assert gap > bond, label
            assert all(crop[i] < bounds(piece)[i] and bounds(piece)[i+3] < crop[i+3] for i in range(3))
            parts[label] = (piece, blank)
        sections.append({"name": name, "family": "usb", "mount": "case-floor", "datum_case_mm": datum})
        x, y = row["center_case_xy_mm"]
        mate = {label: {"shape": piece} for label, piece in zip(part_names, finished)}
        tape = guides["retention_film_thickness"]
        half = 1.5 + single + web
        contacts = []
        for index, (a, b) in enumerate(((x - half - tape, x - half), (x + half, x + half + tape)), 1):
            film = {"name": f"{name}-seam-{index}", "bond_pair": part_names, "folded_strap": False,
                    "shape": box([a, y - depth / 2, axis - .7, b, y + depth / 2, axis + .7])}
            contact = bond_areas(film, mate)
            assert all(item["bonded"] for item in contact)
            contacts.extend(contact)
        # Trim the matched bearing floor out of this horizontal fit check.
        # The expanded guide/film XY envelope must clear all remaining walls.
        above = common(floor, box([*crop[:2], seat + .00001, *crop[3:]]))
        bb = list(lift["larger_USB_guide_envelopes_case_mm"][name + "-envelope"])
        bb[2] = seat + bond
        residual = distance(box(bb), above) - shell_allowance
        assert residual >= recess["minimum_target_seat_lateral_gap_mm"], (name, residual)
        fits.append({"station": name, "lateral_gap_after_allowances_mm": round(residual, 9),
                     "base_bondline_mm": bond, "tape_contact_areas_mm2": [round(s["estimated_contact_area_mm2"], 6) for s in contacts]})

    part_print, rows = print_layout(parts)
    (output / DIRECTORY).mkdir(parents=True, exist_ok=True)
    (output / REPORT.parent).mkdir(parents=True, exist_ok=True)
    meshes = {}
    for path, shape in ((GUIDES_STL, part_print), (FLOOR_STL, floor)):
        local = move(shape, *(-coordinate for coordinate in bounds(shape)[:3]))
        metrics = mesh(local, output / path)
        triangles, dimensions = retainer_mesh((output / path).read_bytes())
        a, b, c = sorted(dimensions, reverse=True)
        assert (a >= 5 and b >= 5 and c >= 5) or (a >= 10 and b >= 2 and c >= 2)
        assert triangles == metrics["triangles"]
        meshes[path.as_posix()] = {"triangles": triangles, "dimensions_xyz_mm": dimensions, "closed_connected_shells": 1}
    builder = BRep_Builder()
    reference = TopoDS_Compound()
    builder.MakeCompound(reference)
    builder.Add(reference, floor)
    for piece, _ in parts.values():
        builder.Add(reference, piece)
    write_step(reference, output / REFERENCE)
    assert math.isclose(volume(load(output / REFERENCE)), volume(reference), abs_tol=1e-6)
    draw_layout(output / DRAWING, rows)

    capture_rows = check_cables(recess, parts, sections, retention, wires, assembly, native)
    assert len({row["station"] for row in capture_rows}) == 2 and len(capture_rows) == 42
    assert web - 2 * recess["hypothetical_surface_point_error_L2_mm"] >= limits["minimum_finished_web_mm"] - 1e-6
    assert web + STOCK_MM >= 1.0
    assert NECK_MM - 2 * recess["hypothetical_surface_point_error_L2_mm"] > 1.5
    dependencies = (
        Path(__file__), retention_file, wire_file, fit_file, assembly_file, native_file,
        CASE_DIR / "bottom-m05-REVIEW.step",
        *(ROOT / "scripts" / name for name in (
            "check_e73_retainer_recess.py", "check_e73_delivery.py", "e73_corner_retention.py",
            "export_e73_retention_prints.py", "e73_retention_channels.py",
        )),
    )
    report = {
        "status": "m05-front-retainer-sla-coupons-exported-and-cad-checked",
        "selected_for_assembly": False,
        "manufacturing_released": False,
        "physical_verification": False,
        "factory_process_qualified": False,
        "recess_report_sha256": sha(evidence),
        "hypothetical_surface_point_error_L2_mm": recess["hypothetical_surface_point_error_L2_mm"],
        "published_connected_part_count_max": 10,
        "published_connection_web_mm_must_exceed": 1.5,
        "connection_square_mm": NECK_MM,
        "machining_stock_mm_per_outer_X_side_and_outer_Z_face": STOCK_MM,
        "nominal_print_web_mm": round(web + STOCK_MM, 6),
        "nominal_finished_web_mm": web,
        "minimum_finished_web_mm": limits["minimum_finished_web_mm"],
        "wire_OD_max_mm": wires["wire"]["insulation_od_max"],
        "groove_radii_mm": {"outer_single": single, "center_pair": pair},
        "nominal_split_gap_mm": LID_SPLIT_GAP_MM,
        "guide_print_parts": rows,
        "floor_crop_case_mm": rounded(crop),
        "measurements": fits,
        "wire_capture_checks": capture_rows,
        "print_meshes": meshes,
        "files_sha256": {path.as_posix(): sha(output / path) for path in (GUIDES_STL, FLOOR_STL, REFERENCE, DRAWING)},
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in dependencies},
        "limits": [
            "Print the carrier and floor sample as two separate models. The STEP is a post-trim fit reference.",
            "The nominal channels overlap and share an opening. The capture checks cover prescribed cable poses, not free lateral movement, pull strength or abrasion.",
            "A matched bond surface, measured surfaces, retained webs and physical guide/film tests are required before keyboard installation.",
        ],
    }
    (output / REPORT).write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output.resolve())
