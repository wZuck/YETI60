#!/usr/bin/env python3
"""Read the four printable shell STEP files and compare their fit with SLA capability."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

from cad_geometry import bounds, intersection_volume, load


ROOT = Path(__file__).resolve().parents[1]
CASE_REPORT = ROOT / "hardware/e73-hhkb-corner/audit/service-case-m05.json"
ASSEMBLY = ROOT / "mechanical/assembly-spec.json"
SUPPLIER_GUIDE = "https://jlc3dp.com/help/article/3d-printing-design-guideline"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vertical_cylinders(shape):
    faces = TopExp_Explorer(shape, TopAbs_FACE)
    result = []
    while faces.More():
        face = TopoDS.Face(faces.Current())
        faces.Next()
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        axis = cylinder.Axis()
        if abs(axis.Direction().Z()) < .999999:
            continue
        center = axis.Location()
        face_bounds = bounds(face)
        result.append(((center.X(), center.Y()), 2 * cylinder.Radius(),
                       face_bounds[2], face_bounds[5]))
    return result


def hole(cylinders, center, diameter):
    matching = [(xy, d, z0, z1) for xy, d, z0, z1 in cylinders
                if math.dist(xy, center) < .0001 and abs(d - diameter) < .0001]
    assert matching, (center, diameter)
    xy, d, _, _ = matching[0]
    return {
        "center_xy_mm": [round(value, 6) for value in xy],
        "diameter_mm": round(d, 4),
        "z_span_mm": [round(min(bore[2] for bore in matching), 6),
                      round(max(bore[3] for bore in matching), 6)],
    }


def vertical_cylinder(xy, z0, z1, radius):
    axis = gp_Ax2(gp_Pnt(*xy, z0), gp_Dir(0, 0, 1))
    return BRepPrimAPI_MakeCylinder(axis, radius, z1 - z0).Shape()


def annulus_material_fraction(shape, xy, z0, z1, inner, outer):
    outer_cylinder = vertical_cylinder(xy, z0, z1, outer)
    inner_cylinder = vertical_cylinder(xy, z0, z1, inner)
    annulus_volume = math.pi * (outer**2 - inner**2) * (z1 - z0)
    return ((intersection_volume(shape, outer_cylinder)
             - intersection_volume(shape, inner_cylinder)) / annulus_volume)


def closure_finish(lower_shape, lower_faces, closure, case):
    """Screen concentric machining of the lower shell, using the cured part as the reference."""
    passage_min, passage_max = 3.85, 3.95
    recess_min, recess_max = 6.75, 6.85
    washer_min, washer_max = 5.5, 5.8
    cutter_xy_each_axis = .05
    seat_depth_allowance = .05
    washer_eccentricity = .10
    cutter_center_offset = math.sqrt(2) * cutter_xy_each_axis
    maximum_existing_pilot = 3.70
    assert maximum_existing_pilot / 2 + cutter_center_offset < passage_min / 2
    offset = math.sqrt(2) * (
        case["linear_tolerance"] + case["finished_bore_position_tolerance"] + cutter_xy_each_axis
    )
    washer_offset = offset + washer_eccentricity
    minimum_shank_gap = (passage_min - 3.0) / 2 - offset
    minimum_head_gap = (recess_min - 5.6) / 2 - offset
    minimum_washer_gap = (recess_min - washer_max) / 2 - washer_offset
    minimum_washer_bearing = (washer_min - passage_max) / 2 - washer_offset
    assert min(minimum_shank_gap, minimum_head_gap, minimum_washer_gap) > 0
    assert minimum_washer_bearing > .30
    # Bound every cutter position by a containing cylinder in nominal lower-part coordinates.
    lower_axis_offset = math.sqrt(2) * (case["linear_tolerance"] + cutter_xy_each_axis)
    passage_envelope = passage_max / 2 + lower_axis_offset
    recess_envelope = recess_max / 2 + lower_axis_offset
    checks = []
    original_bounds = bounds(lower_shape)
    worst_case = lower_shape
    for location in closure:
        passage = location["passage"]
        xy = passage["center_xy_mm"]
        head = hole(lower_faces, xy, 5.8)
        entrance, seat = head["z_span_mm"]
        interface = passage["z_span_mm"][1]
        assert abs(passage["z_span_mm"][0] - seat) < .0001
        deepest_seat = seat + seat_depth_allowance
        outer_guard = annulus_material_fraction(
            lower_shape, xy, entrance + .01, deepest_seat, recess_envelope, recess_envelope + .50
        )
        seat_guard = annulus_material_fraction(
            lower_shape, xy, deepest_seat, interface, passage_envelope, recess_envelope
        )
        assert abs(outer_guard - 1) < .0001 and abs(seat_guard - 1) < .0001, xy
        outboard = original_bounds[2] - 1
        for radius, end in ((recess_envelope, deepest_seat), (passage_envelope, interface + .20)):
            operation = BRepAlgoAPI_Cut(worst_case, vertical_cylinder(xy, outboard, end, radius))
            operation.Build()
            assert operation.IsDone()
            worst_case = operation.Shape()
        checks.append({
            "center_xy_mm": xy,
            "original_head_recess": head,
            "outside_sleeve_material_fraction": round(outer_guard, 6),
            "seat_material_fraction": round(seat_guard, 6),
            "minimum_axial_seat_thickness_mm": round(interface - deepest_seat, 4),
        })
    assert BRepCheck_Analyzer(worst_case).IsValid()
    solids = TopExp_Explorer(worst_case, TopAbs_SOLID)
    assert solids.More()
    solids.Next()
    assert not solids.More()
    assert all(abs(a - b) < .0001 for a, b in zip(bounds(worst_case), original_bounds))
    return {
        "scope": "CAD screen of optional finishing on a matched, fully cured lower shell",
        "finished_passage_diameter_mm": [passage_min, passage_max],
        "finished_head_recess_diameter_mm": [recess_min, recess_max],
        "shim_outside_diameter_mm": [washer_min, washer_max],
        "shim_thickness_mm": .30,
        "shim_max_eccentricity_to_screw_mm": washer_eccentricity,
        "cutter_xy_allowance_per_axis_mm": cutter_xy_each_axis,
        "maximum_existing_pilot_diameter_mm": maximum_existing_pilot,
        "maximum_existing_recess_radius_plus_offset_to_pilot_mm": round(
            recess_min / 2 - cutter_center_offset, 4
        ),
        "maximum_seat_depth_change_mm": seat_depth_allowance,
        "bounded_screw_axis_offset_mm": round(offset, 4),
        "minimum_shank_gap_mm": round(minimum_shank_gap, 4),
        "minimum_head_gap_mm": round(minimum_head_gap, 4),
        "minimum_shim_gap_mm": round(minimum_washer_gap, 4),
        "minimum_shim_over_seat_radial_width_mm": round(minimum_washer_bearing, 4),
        "minimum_modeled_outside_sleeve_mm": .50,
        "worst_case_cut_model_is_one_valid_solid_with_original_bounds": True,
        "locations": checks,
    }


def run(bundle):
    mechanical = bundle / "02-mechanical"
    service_case = mechanical / "service-case-m05"
    paths = {
        "upper": mechanical / "top.step",
        "lower": service_case / "bottom-m05-REVIEW.step",
        "J2": service_case / "cover-J2-REVIEW.step",
        "J4": service_case / "cover-J4-REVIEW.step",
    }
    shapes = {name: load(path) for name, path in paths.items()}
    features = {name: vertical_cylinders(shape) for name, shape in shapes.items()}
    part_dimensions = {}
    for name, shape in shapes.items():
        extent = bounds(shape)
        sizes = [round(extent[axis + 3] - extent[axis], 4) for axis in range(3)]
        part_dimensions[name] = {
            "nominal_xyz_mm": sizes,
            "ordinary_sla_size_tolerance_mm": [
                round(size * .003, 4) if size > 100 else .20 for size in sizes
            ],
        }

    case = json.loads(ASSEMBLY.read_text())["case"]
    closure = []
    for axis in case["top_screw_axes"]:
        insert = hole(features["upper"], axis, case["top_insert"]["bore_diameter"])
        passage = hole(features["lower"], axis, 3.4)
        assert math.isclose(insert["z_span_mm"][1] - insert["z_span_mm"][0],
                            case["top_insert"]["bore_depth"], abs_tol=.0001)
        closure.append({"insert": insert, "passage": passage})
    daughterboard = []
    for axis in case["daughterboard_screw_axes"]:
        insert = hole(features["lower"], axis, case["daughterboard_insert"]["bore_diameter"])
        assert math.isclose(insert["z_span_mm"][1] - insert["z_span_mm"][0],
                            case["daughterboard_insert"]["bore_depth"], abs_tol=.0001)
        daughterboard.append(insert)

    reference = json.loads(CASE_REPORT.read_text())
    cover_fits = {}
    for port in reference["ports"]:
        name = port["ref"]
        positions = port["fasteners"]
        screw_axes = []
        for location in positions:
            axis = location["xy_mm"]
            insert = hole(features["lower"], axis, 3.35)
            passage = hole(features[name], axis, 2.4)
            head = hole(features[name], axis, 4.5)
            tip_gap = insert["z_span_mm"][1] - head["z_span_mm"][1] - 4
            assert abs(tip_gap - location["screw_tip_to_blind_bottom_mm"]) < .0001
            screw_axes.append({"insert": insert, "passage": passage,
                               "head_recess": head, "nominal_tip_gap_mm": round(tip_gap, 4)})
        nominal_xy = part_dimensions[name]["nominal_xyz_mm"][:2]
        pocket = port["cover_pocket_bounds_xy_mm"]
        gaps = [round((pocket[i + 2] - pocket[i] - nominal_xy[i]) / 2, 4) for i in range(2)]
        assert all(gap == reference["minimum_nominal_cover_side_gap_mm"] for gap in gaps)
        cover_fits[name] = {
            "hole_center_distance_mm": round(math.dist(*[f["xy_mm"] for f in positions]), 4),
            "nominal_per_side_xy_gap_mm": gaps,
            "screw_axes": screw_axes,
        }

    position = case["linear_tolerance"]
    insert_position = case["finished_bore_position_tolerance"]
    hole_tolerance = .30
    assembly_bores = {}
    for key in ("top_insert", "daughterboard_insert"):
        d = case[key]["bore_diameter"]
        tolerance = case[key]["bore_tolerance"]
        assembly_bores[key] = {
            "finished_diameter_range_mm": [round(d - tolerance, 4), round(d + tolerance, 4)],
            "ordinary_sla_diameter_range_mm": [round(d - hole_tolerance, 4), round(d + hole_tolerance, 4)],
        }
    report = {
        "status": "m05-step-readback-and-ordinary-sla-fit-screen",
        "physical_verification": False,
        "supplier_guide": SUPPLIER_GUIDE,
        "parts": part_dimensions,
        "nominal_passage_radial_clearance_mm": {
            "upper_lower_M3": round((closure[0]["passage"]["diameter_mm"] - 3) / 2, 4),
            "cover_M2": round((cover_fits["J2"]["screw_axes"][0]["passage"]["diameter_mm"] - 2) / 2, 4),
        },
        "example_M3_independent_xy_error_mm": {
            "lower_per_axis": position, "upper_finished_insert_per_axis": insert_position,
            "resultant_center_offset_mm": round(math.hypot(position + insert_position,
                                                          position + insert_position), 4),
        },
        "insert_diameter_comparison": assembly_bores,
        "lower_m3_finish": closure_finish(shapes["lower"], features["lower"], closure, case),
        "closure_passages_and_inserts": closure,
        "daughterboard_inserts": daughterboard,
        "covers": cover_fits,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in (
            ASSEMBLY, CASE_REPORT, Path(__file__).resolve(), ROOT / "scripts/cad_geometry.py"
        )},
        "STEP_sha256": {str(path.relative_to(bundle)): sha(path) for path in paths.values()},
    }
    path = bundle / "06-validation/m05-print-fit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    run(parser.parse_args().bundle.resolve())
