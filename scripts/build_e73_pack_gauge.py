#!/usr/bin/env python3
"""Export an inert M05 trial gauge from the fitted pack and harness datums."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt

from cad_geometry import bounds, intersection_volume, load
from check_yeti60_assembly import box, distance, move
from check_yeti60_interconnects import write_step
from e73_fit_geometry import volume
from export_e73_retention_prints import mesh


ROOT = Path(__file__).resolve().parents[1]
ASSEMBLY = ROOT / "mechanical/assembly-spec.json"
HARNESS = ROOT / "hardware/e73-corner-harness-spec.json"
CORNER = ROOT / "hardware/e73-hhkb-corner"
ROUTES = CORNER / "audit/harness-study.json"
CASE_REPORT = CORNER / "audit/service-case-m05.json"
M05 = CORNER / "mechanical/service-case-m05"
CASE_PARTS = tuple(M05 / f"{name}-REVIEW.step" for name in ("bottom-m05", "cover-J2", "cover-J4"))
WIRE_LENGTHS = M05 / "harness/wire-lengths-m05.csv"
M05_HARNESS_REPORT = CORNER / "audit/m05-harness.json"
GAUGE_DIR = Path("02-mechanical/service-case-m05/pack-gauge")
GAUGE_NAME = "M05-inert-pack-gauge"
REPORT = Path("06-validation/m05-pack-gauge.json")
CHANNEL_WIDTH_MM = .90
CHANNEL_LENGTH_MM = 6.0


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def rounded(values):
    return [round(value, 6) for value in values]


def floor_supports(case, pack_origin, dimensions):
    """Find the nominal floor below three widely separated support points."""
    floor = IntCurvesFace_ShapeIntersector()
    floor.Load(case, 1e-7)
    supports = []
    for i, j in ((.1, .2), (.9, .2), (.5, .8)):
        x, y = (pack_origin[0] + i * dimensions[0], pack_origin[1] + j * dimensions[1])
        ray = gp_Lin(gp_Pnt(x, y, pack_origin[2]), gp_Dir(0, 0, 1))
        floor.Perform(ray, bounds(case)[2] - pack_origin[2] - 1, 0)
        assert floor.IsDone() and floor.NbPnt(), (x, y)
        support_z = max(floor.Pnt(index).Z() for index in range(1, floor.NbPnt() + 1))
        supports.append({"xy_case_mm": rounded((x, y)), "floor_z_mm": round(support_z, 6),
                         "nominal_support_thickness_mm": round(pack_origin[2] - support_z, 6)})
    assert len({support["floor_z_mm"] for support in supports}) == 1
    assert supports[0]["nominal_support_thickness_mm"] > 0
    return supports


def build(output):
    battery = read(ASSEMBLY)["battery"]
    harness = read(HARNESS)
    layout = harness["battery"]
    wire_od = harness["wire"]["insulation_od_max"]
    dimensions = battery["full_envelope_including_growth"]
    x, y, X, Y = battery["bounds_xy"]
    pack_origin = (x, y, battery["top_z"] - dimensions[2])
    exit_x, exit_y, exit_z = layout["pack_exit_local"]
    assert rounded([X - x, Y - y]) == dimensions[:2]
    assert exit_x == 0 and layout["pack_exit_axis"].startswith("-X;")
    assert CHANNEL_LENGTH_MM >= layout["minimum_pack_lead_transition_zone_length"]
    assert CHANNEL_LENGTH_MM < dimensions[0] and CHANNEL_WIDTH_MM > wire_od
    channel_floor = exit_z - wire_od / 2
    assert 0 < channel_floor < exit_z < dimensions[2]

    routes = read(ROUTES)["variants"][0]["routes"]["battery"]
    m05_harness = read(M05_HARNESS_REPORT)
    assert m05_harness["case"] == "M05"
    assert m05_harness["outputs"][str(WIRE_LENGTHS.relative_to(ROOT))] == sha(WIRE_LENGTHS)
    nominal_lengths = m05_harness["trial_variants"][0]["seated_free_lengths_mm"]
    with WIRE_LENGTHS.open(newline="") as handle:
        wire_rows = [row for row in csv.DictReader(handle) if row["MainboardReference"] == "J2"]
    assert [row["MainboardPin"] for row in wire_rows] == list(layout["pin_map"])
    leads = []
    block = box([0, 0, 0, *dimensions])
    gauge = block
    for pin, offset in enumerate(layout["lateral_offsets"], 1):
        pin = str(pin)
        center_y = exit_y + offset
        local_exit = [exit_x, center_y, exit_z]
        case_exit = rounded(a + b for a, b in zip(pack_origin, local_exit))
        assert case_exit == rounded(routes[pin][-1]["end"]), pin
        y0, y1 = center_y - CHANNEL_WIDTH_MM / 2, center_y + CHANNEL_WIDTH_MM / 2
        assert 0 < y0 < y1 < dimensions[1]
        cutter = box([-1, y0, channel_floor, CHANNEL_LENGTH_MM, y1, dimensions[2] + 1])
        op = BRepAlgoAPI_Cut(gauge, cutter)
        op.Build()
        assert op.IsDone()
        gauge = op.Shape()
        row = wire_rows[int(pin) - 1]
        length = float(row["FreeLength_mm"])
        assert row["FarReference"] == "pack" and row["FarPin"] == layout["pin_map"][pin]
        assert length == round(nominal_lengths[f"battery.{pin}"], 3)
        leads.append({"J2_pin": pin, "lead": layout["pin_map"][pin], "exit_local_mm": local_exit,
                      "exit_case_mm": case_exit, "free_length_mm": length})
    assert BRepCheck_Analyzer(gauge).IsValid()
    solids = TopExp_Explorer(gauge, TopAbs_SOLID)
    assert solids.More()
    solids.Next()
    assert not solids.More()
    assert rounded(bounds(gauge)) == [0, 0, 0, *dimensions]
    removed = len(leads) * CHANNEL_WIDTH_MM * CHANNEL_LENGTH_MM * (dimensions[2] - channel_floor)
    assert math.isclose(volume(block) - volume(gauge), removed, abs_tol=1e-6)

    native_case = read(CASE_REPORT)
    placed_envelope = move(block, *pack_origin)
    clearances = {}
    for path in CASE_PARTS:
        assert native_case["outputs"][str(path.relative_to(ROOT))] == sha(path)
        case_part = load(path)
        gap = distance(placed_envelope, case_part)
        assert intersection_volume(placed_envelope, case_part) < 1e-6 and gap > 0, path.name
        clearances[path.name] = round(gap, 6)

    directory = output / GAUGE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    step = directory / f"{GAUGE_NAME}.step"
    stl = directory / f"{GAUGE_NAME}.stl"
    write_step(gauge, step)
    restored = load(step)
    assert rounded(bounds(restored)) == rounded(bounds(gauge))
    assert math.isclose(volume(restored), volume(gauge), abs_tol=1e-6)
    metrics = mesh(restored, stl)

    sources = [Path(__file__), ASSEMBLY, HARNESS, ROUTES, CASE_REPORT, WIRE_LENGTHS, M05_HARNESS_REPORT, *CASE_PARTS,
               *(ROOT / "scripts" / name for name in ("cad_geometry.py", "check_yeti60_assembly.py",
                  "check_yeti60_interconnects.py", "e73_fit_geometry.py", "export_e73_retention_prints.py"))]
    result = {
        "status": "cad-only-m05-inert-pack-gauge",
        "physical_verification": False,
        "pack_envelope_mm": dimensions,
        "case_origin_of_gauge_mm": rounded(pack_origin),
        "body_clearance_to_nominal_case_parts_mm": clearances,
        "nominal_support_points": floor_supports(load(CASE_PARTS[0]), pack_origin, dimensions),
        "lead_exits": leads,
        "maximum_surrogate_lead_od_mm": wire_od,
        "channel_nominal_width_mm": CHANNEL_WIDTH_MM,
        "channel_nominal_length_mm": CHANNEL_LENGTH_MM,
        "channel_floor_local_z_mm": round(channel_floor, 6),
        "nominal_wire_protrusion_at_maximum_od_mm": round(max(0, exit_z + wire_od / 2 - dimensions[2]), 6),
        "mesh": metrics,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in sources},
        "files_sha256": {str(path.relative_to(output)): sha(path) for path in (step, stl)},
        "limits": [
            "The finished gauge dimensions and position must be measured on the actual parts.",
            "The gauge models the bounded pack shape and surrogate lead origins for an unpowered dry fit.",
            "Wire/adhesive behavior, connector release, assembled tolerances, physical operation and actual pack compliance still need verification.",
        ],
    }
    (output / REPORT).parent.mkdir(parents=True, exist_ok=True)
    (output / REPORT).write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(build(parser.parse_args().output)["status"])
