#!/usr/bin/env python3
"""Screen added depth for larger USB front retainers on the M05 case."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from contextlib import redirect_stdout
import hashlib
from itertools import product
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

import ezdxf
from OCP.BRep import BRep_Builder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.gp import gp_Pnt

from build_e73_m05_harness import matched_spec
from build_e73_service_case import cylinder, skin_z
from cad_geometry import bounds, intersection_volume, load
import check_e73_corner_harness as harness
import check_e73_corner_service as service
from check_e73_corner_harness import cut, datums
from check_e73_service_leads import STATES
from check_yeti60_assembly import box, distance, move
from check_yeti60_interconnects import surface_z
from e73_corner_harness_paths import envelope_wire, length, paired_data
from e73_corner_retention import build
from e73_fit_geometry import external_faces, plate_envelope, volume
from e73_service_leads import BATTERY_GUIDE_STATIONS, flex_routes, position_exits


ROOT = Path(__file__).resolve().parents[1]
CORNER = ROOT / "hardware/e73-hhkb-corner"
BASE = CORNER / "mechanical"
AUDIT = CORNER / "audit"
CASE_DIR = BASE / "service-case-m05"
C5_REPORT = "docs/audit/yeti60-daughterboard.json"
C5_STEP = "hardware/usb-daughterboard/C5-JSH-clearance.step"
KICAD_PYTHON = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"
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


def floor_cutter(floor, routes, diameter, nominal_gap):
    hits = []
    for route in routes:
        for path in route.values():
            protected = envelope_wire(path, diameter + 2 * (nominal_gap + .01))
            hit = common(floor, protected)
            if volume(hit) > 1e-6:
                hits.append(bounds(hit))
    lower = [min(item[i] for item in hits) - .03 for i in range(3)]
    upper = [max(item[i] for item in hits) + .03 for i in (3, 4)] + [0]
    return lower + upper


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
    cutter = floor_cutter(front_floor, [paths["usb"]], diameter, nominal_gap)
    trial, removed = apply_recess(case, recessed, cutter)
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
        "continuous_floor_relief_bounds_case_mm": cutter,
        "continuous_floor_relief_removed_volume_mm3": volume(removed),
        "worst_wire_to_bottom_gap_after_allowances_mm": min(residuals.values()),
        "wire_to_bottom_gaps_after_allowances_mm": residuals,
        "PCB_thickness_endpoint_gaps_after_allowances": endpoint_gaps,
        "minimum_wall_to_selected_exterior_after_allowances_mm": wall,
        "minimum_wire_to_bottom_gap_required_mm": target_gap,
        "USB_pair_geometric_skew_mm": abs(length(paths["usb"]["2"]) - length(paths["usb"]["3"])),
    }, trial, spec


def clearance_witness(moving, fixed, allowances):
    """Find the closest pair, pruning only with a lower bound on solid distance."""
    worst = (math.inf, "", "")
    fixed_bounds = {name: bounds(shape) for name, shape in fixed.items()}
    for name, shape in moving.items():
        a = bounds(shape)
        for other, stationary in fixed.items():
            b = fixed_bounds[other]
            allowance = allowances.get(other, 0)
            box_gap = math.hypot(*(max(0, a[i] - b[i + 3], b[i] - a[i + 3]) for i in range(3)))
            if box_gap - allowance <= worst[0] + 1e-6:
                gap = round(distance(shape, stationary) - allowance, 9)
                worst = min(worst, (gap, name, other))
    gap, name, other = worst
    return {"clearance_mm": gap, "moving_part": name, "stationary_part": other}


def check_parked_lift(spec, native, assembly, case, bottom, delta, exits, parked, routes,
                      guide_boxes, retention, fit, shell_allowance):
    """Raise the open-case deck and power bridge from the final parked pose."""
    spec = dict(spec, guides=dict(retention["guides"], battery_x=BATTERY_GUIDE_STATIONS))
    limits = retention["tolerance_contract"]
    guide_error = limits["guide_maximum_surface_point_error_L2_mm"] + limits["guide_installed_datum_error_L2_mm"]
    seated, _, _ = flex_routes(spec, exits, exits, 0)
    guides, films = build(spec, case, seated, exits, bottom)
    fitted = harness.bodies(native, assembly, spec, bottom, delta)
    fixed = {name: shape for name, shape in fitted.items() if name.startswith("C5")}
    moving = {name: shape for name, shape in fitted.items() if name not in fixed}
    fixed["bottom"] = case
    wire_allowances = {"bottom": shell_allowance}
    for part in guides + films:
        name, shape = part["name"], part["shape"]
        if name.startswith("USB-F"):
            continue  # The enlarged envelopes below replace both front assemblies.
        if part["mount"].startswith("PCB"):
            moving[name] = move(shape, z=delta)
        else:
            fixed[name] = shape
            wire_allowances[name] = guide_error

    battery = assembly["battery"]
    x, y, X, Y = battery["bounds_xy"]
    z, error = battery["top_z"], battery["position_tolerance"]
    fixed["pack"] = box([x - error, y - error, z - battery["full_envelope_including_growth"][2] - error,
                         X + error, Y + error, z + error])
    fixed.update({name: box(bb) for name, bb in guide_boxes.items()})
    for ref in service.PORTS:
        x, y, z = parked[ref]
        fixed[ref + "-plug"] = box(service.plug_bounds((x, y, z + (0 if ref == "C5" else delta)), *service.PORTS[ref]))
    for ref, count, vx, vy in (("J1", 4, 1, 0), ("J5", 2, 0, -1)):
        x, y, z = exits[ref]
        moving[ref + "-plug"] = box(service.plug_bounds((x, y, z + delta), count, vx, vy))

    travel = (0, 0, service.LIFT_MM)
    swept = {name: box(service.translated_union_bounds(bounds(shape), travel)) for name, shape in moving.items()}
    swept["PCB"] = harness.pcb_solid(bottom + delta, assembly["stack"]["pcb_thickness"] - delta + service.LIFT_MM)
    stack = dict(assembly["stack"], plate_thickness_mm=assembly["stack"]["plate_thickness"])
    swept["steel plate"] = plate_envelope(ezdxf.readfile(ROOT / assembly["geometry"]["plate"]),
                                          fit, stack, travel=service.LIFT_MM)

    rigid_allowances = dict(wire_allowances)
    rigid_allowances.update({name: shell_allowance + limits["PCB_installed_pose_Z_error_mm"] for name in guide_boxes})
    rigid = clearance_witness(swept, fixed, rigid_allowances)
    assert rigid["clearance_mm"] >= service.MIN_GAP_MM, ("rigid lift", rigid)

    housings = {}
    for ref in ("J2", "J4"):
        name = ref + "-plug"
        others = {key: shape for key, shape in fixed.items() if key != name}
        deck = clearance_witness(swept, {name: fixed[name]}, {})
        rest = clearance_witness({name: fixed[name]}, others, rigid_allowances)
        assert deck["clearance_mm"] > .50 and rest["clearance_mm"] >= service.MIN_GAP_MM, (ref, deck, rest)
        housings[ref] = {"deck_clearance_mm": deck["clearance_mm"],
                         "closest_moving_part": deck["moving_part"], "fixed_objects": rest}

    wire = spec["wire"]
    diameter = wire["insulation_od_max"] + 2 * wire["case_and_route_position_allowance"]
    wire_shapes = {f"{family}.{pin}": envelope_wire(path, diameter)
                   for family, leads in routes.items() for pin, path in leads.items()}
    fixed_wires = {name: shape for name, shape in wire_shapes.items() if not name.startswith("power.")}
    deck_to_wire = clearance_witness(swept, fixed_wires, {})
    assert deck_to_wire["clearance_mm"] >= service.MIN_GAP_MM, ("deck to fixed wires", deck_to_wire)
    fixed.update(fixed_wires)
    moving_wires = {name: shape for name, shape in wire_shapes.items() if name not in fixed_wires}
    wire_results = []
    for left, right in product(moving_wires, fixed):
        allowance = wire_allowances.get(right, 0)
        with patch.object(service, "MIN_GAP_MM", service.MIN_GAP_MM + allowance):
            proof = service.certify_lift_pair(moving_wires[left], fixed[right])
        gap = round(proof["certified_gap_mm"] - allowance, 9)
        assert gap >= service.MIN_GAP_MM, (left, right, gap)
        wire_results.append({"moving_wire": left, "stationary_part": right, "certified_residual_gap_mm": gap,
                             "distance_evaluations": proof["evaluations"]})
    return {
        "moving_rigid_envelopes": len(swept),
        "stationary_rigid_envelopes": len(fixed) - len(fixed_wires),
        "stationary_wire_envelopes": len(fixed_wires),
        "rigid_deck_to_stationary_objects": rigid,
        "rigid_deck_to_stationary_wires": deck_to_wire,
        "parked_housings": housings,
        "moving_wire_checks": wire_results,
    }


def check_thickness(inputs):
    thickness, cutter, station_cutters, spec, native, assembly, outline, shell_allowance, lift_inputs = inputs
    case = modified_case(station_cutters + [cutter])
    builder = BRep_Builder()
    closed = TopoDS_Compound()
    builder.MakeCompound(closed)
    for part in (case, *(load(CASE_DIR / f"cover-{ref}-REVIEW.step") for ref in ("J2", "J4"))):
        builder.Add(closed, part)
    bottom, exits = datums(native, assembly, spec)
    delta = assembly["stack"]["pcb_thickness"] - thickness
    original_read = harness.read
    c5 = dict(original_read(C5_REPORT), exported_step=C5_STEP)

    def read_geometry(path):
        if path == ".assembly-work/e73-corner/copper.json":
            return {"outline": outline}
        if path == C5_REPORT:
            return c5
        return original_read(path)

    with patch.object(harness, "read", read_geometry):
        pcb = harness.pcb_solid(bottom + delta, thickness)
    seated_lengths = {}
    results = []
    for name, state in STATES.items():
        shifted = position_exits(exits, *state)
        routes, centre, _ = flex_routes(spec, exits, shifted, delta)
        with (patch.object(harness, "paths", return_value=(routes, centre)),
              patch.object(harness, "read", read_geometry),
              patch.object(harness, "pcb_solid", return_value=pcb)):
            # The baseline evaluator prints every evaluated wire. Keep the
            # per-pose summary plus any exception in the parent process.
            with open(os.devnull, "w") as quiet, redirect_stdout(quiet):
                checked = harness.evaluate(spec, native, assembly, shifted, bottom, closed, delta)
        gaps = []
        lengths = {}
        for wire in checked["wires"]:
            label = f'{wire["family"]}.{wire["pin"]}'
            lengths[label] = wire["free_length_mm"]
            for obstacle, gap in wire["clearances_mm"].items():
                allowance = shell_allowance if obstacle in ("top", "bottom") else 0
                gaps.append((round(gap - allowance, 9), label, obstacle))
        crossings = [(round(row["gap_mm"], 9), " / ".join(".".join(wire) for wire in row["wires"]), "crossing")
                     for row in checked["crossings"]]
        worst, wire, obstacle = min(gaps + crossings)
        bend = min(row["minimum_bend_radius_mm"] for row in checked["wires"])
        if name == "seated":
            seated_lengths = lengths
        length_change = max(abs(value - seated_lengths[key]) for key, value in lengths.items())
        skew = checked["USB_geometric_pair_skew_mm"]
        assert worst >= spec["wire"]["minimum_air_gap_after_allowance"], (thickness, name, worst, wire, obstacle)
        assert bend >= spec["wire"]["minimum_static_bend_radius"] - 1e-6, (thickness, name, bend)
        assert length_change < .06 and skew < .005, (thickness, name, length_change, skew)
        results.append({
            "state": name,
            "minimum_residual_air_gap_mm": worst,
            "closest_wire": wire,
            "closest_obstacle": obstacle,
            "minimum_USB_to_other_harness_gap_mm": min(gap for gap, pair, _ in crossings if "usb." in pair),
            "minimum_USB_to_fitted_body_gap_mm": min(
                gap for gap, key, ref in gaps if key.startswith("usb.") and ref not in ("top", "bottom", "PCB", "pack")
            ),
            "minimum_static_bend_radius_mm": round(bend, 9),
            "largest_free_length_change_from_seated_mm": round(length_change, 9),
            "USB_pair_geometric_skew_mm": round(skew, 9),
        })
    assert name == "both-parked"
    with patch.object(harness, "read", read_geometry):
        lift = check_parked_lift(spec, native, assembly, case, bottom, delta, exits, shifted, checked["routes"],
                                 *lift_inputs, shell_allowance)
    return {"PCB_thickness_mm": thickness, "states": results, "parked_lift": lift}


def modified_case(cutters):
    trial = original = load(CASE_DIR / "bottom-m05-REVIEW.step")
    for cutter in cutters:
        trial, _ = apply_recess(original, trial, cutter)
    return trial


def screen_usb_motion(original, recessed, seated, exterior, station_cutters, spec, native, assembly,
                      shell_error, guard, outline, minimum_wall, lift_inputs):
    _, exits = datums(native, assembly, spec)
    wire = spec["wire"]
    diameter = wire["insulation_od_max"] + 2 * wire["case_and_route_position_allowance"]
    target_gap = wire["minimum_air_gap_after_allowance"]
    shell_allowance = shell_error + guard
    stack = assembly["stack"]
    nominal = stack["pcb_thickness"]
    thin, thick = stack["ordinary_manufacturer_finished_thickness_range_mm"]
    thicknesses = (thin, nominal, thick)
    routes = []
    # J2 moves alone in the first four configurations. Their USB geometry is
    # identical and represented by the J2-parked pose for deriving the relief.
    for thickness in thicknesses:
        for name in ("J2-parked", "J4-halfway", "J4-axial-end", "both-parked"):
            shifted = position_exits(exits, *STATES[name])
            leads, centre, _ = flex_routes(spec, exits, shifted, nominal - thickness)
            routes.append(dict(leads["usb"], **paired_data(centre, spec)[0]))
    probes = []
    for name, pin in (("J4-halfway", "4"), ("J4-axial-end", "2")):
        shifted = position_exits(exits, *STATES[name])
        leads, centre, _ = flex_routes(spec, exits, shifted, 0)
        leads["usb"].update(paired_data(centre, spec)[0])
        residual = distance(seated, envelope_wire(leads["usb"][pin], diameter)) - shell_allowance
        assert residual < target_gap, (name, pin, residual)
        probes.append({"state": name, "USB_wire_pin": pin, "residual_gap_mm": round(residual, 9)})
    floor = common(recessed, box([188, -180, -13, 219, -126, 0]))
    cutter = floor_cutter(floor, routes, diameter, target_gap + shell_allowance)
    trial, removed = apply_recess(original, recessed, cutter)
    all_removed = cut(original, trial)
    wall = min(distance(all_removed, face) for face in exterior) - 2 * shell_error - guard
    assert wall >= minimum_wall
    case_spec = assembly["case"]
    checked_axes = 0
    for group in ("top", "daughterboard"):
        insert = case_spec[group + "_insert"]
        radius = ((insert["bore_diameter"] + insert["bore_tolerance"]) / 2 +
                  case_spec["finished_bore_position_tolerance"] + 2)
        for x, y in case_spec[group + "_screw_axes"]:
            assert intersection_volume(all_removed, cylinder(x, y, -25, radius, 35)) < 1e-6
            checked_axes += 1
    for ref in ("J2", "J4"):
        cover = load(CASE_DIR / f"cover-{ref}-REVIEW.step")
        assert not common(all_removed, cover).NbChildren(), ref

    configurations = [(t, cutter, station_cutters, spec, native, assembly, outline, shell_allowance, lift_inputs)
                      for t in thicknesses]
    print("Checking seven M05 service poses and the 25 mm open-case lift at three PCB thicknesses", flush=True)
    with ProcessPoolExecutor(max_workers=len(configurations)) as pool:
        results = list(pool.map(check_thickness, configurations))
    return {
        "seated_only_relief_failure_witnesses": probes,
        "motion_floor_relief_bounds_case_mm": cutter,
        "motion_floor_relief_removed_volume_mm3": volume(removed),
        "minimum_wall_to_selected_exterior_after_allowances_mm": wall,
        "existing_main_and_daughterboard_insert_guards_checked": checked_axes,
        "bottom_covers_untouched_by_cut": ["J2", "J4"],
        "minimum_wire_to_obstacle_gap_required_mm": target_gap,
        "vertical_lift_travel_mm": service.LIFT_MM,
        "larger_USB_guide_envelopes_case_mm": lift_inputs[0],
        "variants": results,
    }


def screen(copper_export):
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
        "service": AUDIT / "service-motion.json",
        "local_models": AUDIT / "local-models.json",
        "daughterboard": ROOT / C5_REPORT,
        "daughterboard_step": ROOT / C5_STEP,
    }
    rel = lambda path: path.relative_to(ROOT).as_posix()
    case_outputs = read(paths["case_report"])["outputs"]
    for ref in ("J2", "J4"):
        paths[f"cover-{ref}"] = CASE_DIR / f"cover-{ref}-REVIEW.step"
    for part in ("case", "cover-J2", "cover-J4"):
        assert case_outputs[rel(paths[part])] == sha(paths[part])
    copper = read(copper_export)
    assert read(paths["service"])["derived_copper_export_sha256"] == sha(copper_export)
    copper_sources = {ROOT / name for name in copper["source_sha256"]}
    assert all(sha(ROOT / name) == digest for name, digest in copper["source_sha256"].items())
    assembly, fit = read(paths["assembly"]), read(paths["fit"])
    paths["top"] = ROOT / assembly["geometry"]["top"]
    paths["plate"] = ROOT / assembly["geometry"]["plate"]
    assert sha(paths["daughterboard_step"]) == read(paths["daughterboard"])["exported_step_sha256"]
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

    native = read(paths["native"])
    route, seated, lowered_wire_spec = screen_usb_floor(case, candidate, exterior, wires, native, assembly,
                                                        trial_axis_z, shell_error, guard)
    assert route["minimum_wall_to_selected_exterior_after_allowances_mm"] >= minimum_wall
    guide_error = TRIAL_SURFACE_ERROR_MM + limits["guide_installed_datum_error_L2_mm"]
    half_width = section_half_width + guide_error + guides["retention_film_thickness"] + limits["film_edge_error_L2_mm"]
    half_depth = guides["depth"] / 2 + guide_error
    envelopes = {}
    for row in checks:
        x, y = row["center_case_xy_mm"]
        envelopes[row["station"] + "-envelope"] = [
            x - half_width, y - half_depth, seat_z + guides["bond_gap"] - guide_error,
            x + half_width, y + half_depth, trial_axis_z + section_half_height + guide_error,
        ]
    motion = screen_usb_motion(case, candidate, seated, exterior,
                               [row["trial_recess_bounds_case_mm"] for row in checks],
                               lowered_wire_spec, native, assembly, shell_error, guard,
                               copper["outline"], minimum_wall, (envelopes, spec, fit))
    dependencies = {
        Path(__file__), *paths.values(), *copper_sources,
        *(ROOT / "scripts" / name for name in (
            "build_e73_m05_harness.py", "build_e73_service_case.py", "cad_geometry.py",
            "check_e73_corner_harness.py", "check_e73_corner_service.py", "check_e73_service_leads.py", "check_yeti60_assembly.py",
            "check_yeti60_interconnects.py", "export_e73_usb_ground.py",
            "e73_corner_harness_paths.py", "e73_corner_retention.py", "e73_fit_geometry.py", "e73_service_leads.py",
            "e73_service_route.py", "interconnect_geometry.py",
        )),
    }
    return {
        "status": "USB-front-recess-service-poses-and-parked-lift-checked",
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
        "USB_service_motion_trial": motion,
        "native_copper_export_sha256": sha(copper_export),
        "source_sha256": {rel(path): sha(path) for path in sorted(dependencies)},
        "limits": [
            "0.20 mm is a hypothetical L2 surface-error budget, not a qualified supplier surface limit.",
            "Nine wire envelopes are checked at seven defined service poses across three PCB thicknesses.",
            "The 25 mm fixed-XY lift starts after the top and access covers have been removed and J2/J4 have been parked. The modeled deck includes the tolerance-expanded steel plate, PCB, fitted bodies, mounts, guides and bridge wires. The larger front guides are conservative external envelopes.",
            "Guide profiles, bonding, pull force, intermediate cable positions during plug movement and hand/tool operation remain open.",
            "The chosen M05 files and wire lengths are untouched. No manufacturing data is generated by this study.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="yeti60-recess-outline-") as folder:
        export = Path(folder) / "copper.json"
        subprocess.run([KICAD_PYTHON, str(ROOT / "scripts/export_e73_corner_geometry.py"),
                        "--output", str(export)], check=True)
        report = screen(export)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])
