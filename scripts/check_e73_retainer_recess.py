#!/usr/bin/env python3
"""Screen added depth for larger USB front retainers on the M05 case."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pnt

from build_e73_m05_harness import matched_spec
from build_e73_service_case import skin_z
from cad_geometry import bounds, load
from check_e73_corner_harness import cut, datums
from check_yeti60_assembly import box, distance
from check_yeti60_interconnects import surface_z
from e73_corner_harness_paths import envelope_wire, length, paired_data
from e73_fit_geometry import external_faces, volume
from e73_service_leads import flex_routes


ROOT = Path(__file__).resolve().parents[1]
CORNER = ROOT / "hardware/e73-hhkb-corner"
BASE = CORNER / "mechanical"
AUDIT = CORNER / "audit"
STATIONS = ("USB-F1", "USB-F2")
REFERENCE_RECESS_ALLOWANCE_MM = .30
TRIAL_SURFACE_ERROR_MM = .20


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_recess(original, shape, cutter):
    result = cut(shape, box(cutter))
    removed = cut(shape, result)
    assert volume(removed) > 0
    assert all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(bounds(original), bounds(result)))
    solids = TopExp_Explorer(result, TopAbs_SOLID)
    assert solids.More()
    solids.Next()
    assert not solids.More() and BRepCheck_Analyzer(result).IsValid()
    return result, removed


def verified_underside(case, x, y):
    # The sloped native underside can extend above the legacy global
    # exterior-Z filter. Independently locate its trimmed face at the station.
    vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(x, y, skin_z(x, y))).Vertex()
    faces = TopExp_Explorer(case, TopAbs_FACE)
    underside = []
    while faces.More():
        face = TopoDS.Face(faces.Current())
        if distance(vertex, face) < .00001:
            underside.append(face)
        faces.Next()
    assert len(underside) == 1, "M05 underside bearing face not uniquely matched"
    return underside[0]


def common(shape, envelope):
    tool = BRepAlgoAPI_Common(shape, envelope)
    tool.Build()
    assert tool.IsDone()
    return tool.Shape()


def screen_usb_floor(case, recessed, exterior, wires, native, assembly, axis_z, shell_error, guard):
    """Try a localized relief for the seated USB route."""
    spec = matched_spec(wires)
    _, exits = datums(native, assembly, spec)
    # The legacy route builder asserts exact floating point equality at the
    # transition into the front run. The adjacent machine value matches it.
    spec["usb"]["front_z"] = math.nextafter(axis_z, math.inf)
    paths, centre, _ = flex_routes(spec, exits, exits, 0)
    paths["usb"].update(paired_data(centre, spec)[0])
    wire = wires["wire"]
    diameter = wire["insulation_od_max"] + 2 * wire["case_and_route_position_allowance"]
    target_gap = wire["minimum_air_gap_after_allowance"]
    nominal_gap = target_gap + shell_error + guard
    envelopes = {pin: envelope_wire(path, diameter) for pin, path in paths["usb"].items()}
    overlap = {pin: volume(common(recessed, shape)) for pin, shape in envelopes.items()}
    assert overlap["2"] > 1e-6 and overlap["3"] > 1e-6, "Station-only collision witness did not reproduce"

    # Restrict the experiment to the front U-run. Derive the rectangle from
    # the part of the lower shell within wire clearance distance.
    front_floor = common(recessed, box([188, -174, -13, 219, -126, 0]))
    hit_bounds = []
    for path in paths["usb"].values():
        protected = envelope_wire(path, diameter + 2 * (nominal_gap + .01))
        hit = common(front_floor, protected)
        if volume(hit) > 1e-6:
            hit_bounds.append(bounds(hit))
    lower = [min(item[i] for item in hit_bounds) - .03 for i in range(3)]
    upper = [max(item[i] for item in hit_bounds) + .03 for i in (3, 4)] + [0]
    trial, removed = apply_recess(case, recessed, lower + upper)
    residuals = {pin: distance(trial, shape) - shell_error - guard for pin, shape in envelopes.items()}
    assert min(residuals.values()) >= target_gap
    stack = assembly["stack"]
    endpoint_gaps = []
    for thickness in stack["ordinary_manufacturer_finished_thickness_range_mm"]:
        delta = stack["pcb_thickness"] - thickness
        endpoint_paths, centre, _ = flex_routes(spec, exits, exits, delta)
        endpoint_paths["usb"].update(paired_data(centre, spec)[0])
        gaps = {
            pin: distance(trial, envelope_wire(path, diameter)) - shell_error - guard
            for pin, path in endpoint_paths["usb"].items()
        }
        assert min(gaps.values()) >= target_gap
        endpoint_gaps.append({"PCB_thickness_mm": thickness, "wire_to_bottom_gaps_mm": gaps})
    wall = min(distance(removed, face) for face in exterior) - 2 * shell_error - guard
    return {
        "nominal_PCB_thickness_mm": assembly["stack"]["pcb_thickness"],
        "wire_collision_volume_after_station_recesses_mm3": overlap,
        "continuous_floor_relief_bounds_case_mm": lower + upper,
        "continuous_floor_relief_removed_volume_mm3": volume(removed),
        "worst_wire_to_bottom_gap_after_allowances_mm": min(residuals.values()),
        "wire_to_bottom_gaps_after_allowances_mm": residuals,
        "PCB_thickness_endpoint_gaps_after_allowances": endpoint_gaps,
        "minimum_wall_to_selected_exterior_after_allowances_mm": wall,
        "minimum_wire_to_bottom_gap_required_mm": target_gap,
        "USB_pair_geometric_skew_mm": abs(length(paths["usb"]["2"]) - length(paths["usb"]["3"])),
    }


def screen():
    paths = {
        "case": BASE / "service-case-m05/bottom-m05-REVIEW.step",
        "case_report": AUDIT / "service-case-m05.json",
        "assembly": ROOT / "mechanical/assembly-spec.json",
        "fit": ROOT / "mechanical/e73-fit-spec.json",
        "wires": ROOT / "hardware/e73-corner-harness-spec.json",
        "guides": ROOT / "hardware/e73-corner-retention-spec.json",
        "baseline": AUDIT / "retention-study.json",
        "reuse": AUDIT / "m05-harness.json",
        "native": AUDIT / "harness-native.json",
        "print_report": AUDIT / "retention-prints.json",
    }
    rel = lambda path: path.relative_to(ROOT).as_posix()
    assert read(paths["case_report"])["outputs"][rel(paths["case"])] == sha(paths["case"])
    assembly, fit = read(paths["assembly"]), read(paths["fit"])
    wires, spec = read(paths["wires"]), read(paths["guides"])
    limits, guides = spec["tolerance_contract"], spec["guides"]
    baseline = read(paths["baseline"])
    assert not baseline["failures"]
    reused = read(paths["reuse"])["reused_M04_parts"]
    print_outputs = read(paths["print_report"])["outputs"]
    case = load(paths["case"])
    shell_error = math.sqrt(3) * limits["case_maximum_coordinate_error_each_axis_mm"]
    guard = fit["geometric_computation_guard_mm"]
    target_gap = limits["minimum_foreign_air_gap_mm"]
    axis_z = wires["usb"]["front_z"]

    # Keep the existing shrunk USB pair groove envelope, and separately
    # calculate the straight single-wire diameter from the wire/pose budget.
    error_growth = TRIAL_SURFACE_ERROR_MM - guides["guide_print_tolerance"]
    pair_radius = guides["pair_groove_radius"] + error_growth
    wire_radius = wires["wire"]["insulation_od_max"] / 2
    single_radius = wire_radius + guides["local_wire_position_allowance"] + TRIAL_SURFACE_ERROR_MM
    nominal_web = limits["minimum_finished_web_mm"] + 2 * TRIAL_SURFACE_ERROR_MM
    section_half_height = pair_radius + nominal_web
    section_half_width = 1.5 + single_radius + nominal_web
    board_budget = (TRIAL_SURFACE_ERROR_MM + limits["guide_installed_datum_error_L2_mm"] +
                    limits["PCB_installed_pose_Z_error_mm"] + shell_error + guard)
    stack = assembly["stack"]
    thicknesses = stack["ordinary_manufacturer_finished_thickness_range_mm"]
    board_top = stack["plate_bottom_z"] - stack["pcb_to_plate_gap"]
    bottom_z = board_top - max(thicknesses)
    min_axis_drop = axis_z + section_half_height + board_budget + target_gap - bottom_z
    assert min_axis_drop > 0
    axis_drop = math.ceil(min_axis_drop * 20) / 20  # 0.05 mm design step
    trial_axis_z = axis_z - axis_drop
    seat_z = trial_axis_z - section_half_height - guides["bond_gap"]
    half_x = section_half_width + REFERENCE_RECESS_ALLOWANCE_MM
    half_y = guides["depth"] / 2 + REFERENCE_RECESS_ALLOWANCE_MM

    checks = []
    candidate = case
    exterior = external_faces(case)
    exterior.append(verified_underside(case, 203, -151))
    minimum_wall = fit["switch_floor_relief"]["minimum_remaining_wall_mm"]
    for station in STATIONS:
        housing = {}
        for side in ("base", "lid"):
            name = f"{station}-{side}"
            path = BASE / "retention/assembly-reference" / f"{name}.step"
            assert name in reused and print_outputs[rel(path)] == sha(path)
            paths[name] = path
            housing[side] = bounds(load(path))
        x0, y0, _, x1, y1, old_roof_z = housing["lid"]
        x, y = (x0 + x1) / 2, (y0 + y1) / 2
        nominal_floor = surface_z(case, x, y)
        assert math.isclose(housing["base"][2], nominal_floor + guides["bond_gap"], abs_tol=1e-6)
        assert math.isclose(old_roof_z, axis_z + guides["pair_groove_radius"] + guides["lid_roof_nominal"])
        # Confirm the simple vertical PCB clearance at this XY using the
        # full-outline native clearance study before changing section heights.
        pcb_gaps = [
            next(part for part in variant["parts"] if part["name"] == f"{station}-lid")
            ["clearances"]["PCB"]["nominal_gap_mm"]
            for variant in baseline["variants"]
        ]
        assert math.isclose(min(pcb_gaps), bottom_z - old_roof_z, abs_tol=1e-6)
        box_bounds = [x - half_x, y - half_y, seat_z, x + half_x, y + half_y, 0]
        # Temporary in-memory subtraction only. The rectangular cutter tests
        # the larger section footprint and never changes the selected shell.
        result, removed = apply_recess(case, candidate, box_bounds)
        assert math.isclose(surface_z(result, x, y), seat_z, abs_tol=1e-6)
        skin_gap = min(distance(removed, face) for face in exterior)
        remaining_wall = skin_gap - 2 * shell_error - guard
        assert remaining_wall >= minimum_wall
        no_recess_floor_deficit = nominal_floor - (axis_z - section_half_height - guides["bond_gap"])
        assert no_recess_floor_deficit > 0
        trial_gap_after_allowances = bottom_z - (trial_axis_z + section_half_height) - board_budget
        assert trial_gap_after_allowances >= target_gap
        checks.append({
            "station": station,
            "center_case_xy_mm": [x, y],
            "original_floor_z_mm": nominal_floor,
            "original_roof_Z_mm": old_roof_z,
            "original_PCB_nominal_gap_at_max_thickness_mm": min(pcb_gaps),
            "larger_section_fixed_axis_floor_deficit_mm": no_recess_floor_deficit,
            "larger_section_fixed_axis_PCB_gap_after_allowances_mm": bottom_z - (
                axis_z + section_half_height) - board_budget,
            "trial_floor_Z_mm": seat_z,
            "trial_recess_depth_mm": nominal_floor - seat_z,
            "trial_recess_bounds_case_mm": box_bounds,
            "trial_removed_volume_mm3": volume(removed),
            "trial_min_wall_to_selected_exterior_after_allowances_mm": remaining_wall,
            "trial_bare_PCB_gap_after_allowances_mm": trial_gap_after_allowances,
        })
        candidate = result

    route = screen_usb_floor(case, candidate, exterior, wires, read(paths["native"]), assembly,
                             trial_axis_z, shell_error, guard)
    assert route["minimum_wall_to_selected_exterior_after_allowances_mm"] >= minimum_wall
    dependencies = {
        Path(__file__), *paths.values(),
        *(ROOT / "scripts" / name for name in (
            "build_e73_m05_harness.py", "build_e73_service_case.py", "cad_geometry.py",
            "check_e73_corner_harness.py", "check_yeti60_assembly.py", "check_yeti60_interconnects.py",
            "e73_corner_harness_paths.py", "e73_fit_geometry.py", "e73_service_leads.py",
            "e73_service_route.py", "interconnect_geometry.py",
        )),
    }
    return {
        "status": "USB-front-recess-local-witness-only",
        "selected_for_assembly": False,
        "physical_verification": False,
        "hypothetical_surface_point_error_L2_mm": TRIAL_SURFACE_ERROR_MM,
        "minimum_single_wire_groove_radius_mm": single_radius,
        "trial_usb_pair_groove_radius_mm": pair_radius,
        "minimum_nominal_web_mm": nominal_web,
        "minimum_axis_drop_to_clear_bare_PCB_mm": min_axis_drop,
        "trial_axis_drop_mm": axis_drop,
        "PCB_finished_thickness_range_mm": thicknesses,
        "minimum_target_bare_PCB_gap_mm": target_gap,
        "minimum_screened_exterior_wall_mm": minimum_wall,
        "stations": checks,
        "seated_USB_nominal_trial": route,
        "source_sha256": {rel(path): sha(path) for path in sorted(dependencies)},
        "limits": [
            "0.20 mm is a hypothetical L2 surface-error budget, not a qualified supplier surface limit.",
            "In-memory geometry tests only local floor thickness, bare PCB gap and the seated cable-to-bottom gap. Component clearances, guide profiles and the full harness motion remain open.",
            "The chosen M05 files and wire lengths are untouched. No manufacturing data is generated by this study.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output
    report = screen()
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])
