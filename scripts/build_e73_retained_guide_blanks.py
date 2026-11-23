#!/usr/bin/env python3
"""Build two connected SLA blanks for the 12 retained M05 guides."""

import argparse
import csv
import json
import math
from pathlib import Path

from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepGProp import BRepGProp
from OCP.GeomAbs import GeomAbs_Plane
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf

from build_e73_retainer_coupon import solid
from cad_geometry import bounds, intersection_volume, load
from check_e73_corner_harness import cut
from check_e73_delivery import retainer_mesh
from check_e73_retainer_recess import AUDIT, BASE, ROOT, common, read, sha
from check_yeti60_assembly import box, move
from e73_corner_retention import boolean
from e73_fit_geometry import volume
from export_e73_retention_prints import mesh

DIRECTORY = Path("02-mechanical/retained-guide-blanks")
REPORT = Path("06-validation/m05-retained-guide-blanks.json")
LAYOUT = DIRECTORY / "cut-map.svg"
BODY_X = 6.0
BACKING_Z = 2.40
SIDE_Y = .60
BRANCH = 2.0
PART_GAP = 1.50
GROUPS = {
    "M05-case-guides-SLA-BLANKS.stl": ("USB-R1", "USB-R2", "USB-R3", "BAT-R1", "BAT-R2"),
    "M05-power-guides-SLA-BLANKS.stl": ("PWR-R1", "PWR-R2", "PWR-R3", "PWR-R4", "PWR-R5", "PWR-F-upper", "PWR-F-lower"),
}


def rounded(values):
    return [round(value, 6) or 0.0 for value in values]


def print_orientation(shape, rotation):
    if rotation:
        assert rotation == 180
        flip = gp_Trsf()
        flip.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi)
        shape = BRepBuilderAPI_Transform(shape, flip, True).Shape()
    return move(shape, *(-v for v in bounds(shape)[:3]))


def underside_planes(shape):
    """Read the machinable rectangular planes on the back of the grooves."""
    faces = TopExp_Explorer(shape, TopAbs_FACE)
    planes = []
    while faces.More():
        face = TopoDS.Face(faces.Current())
        faces.Next()
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() != GeomAbs_Plane:
            continue
        normal = surface.Plane().Axis().Direction().Z()
        if face.Orientation() == TopAbs_REVERSED:
            normal = -normal
        if normal > -.999999:
            continue
        x, y, z, X, Y, Z = rounded(bounds(face))
        properties = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, properties)
        assert z == Z and math.isclose((X - x) * (Y - y), properties.Mass(), abs_tol=1e-6)
        planes.append({"region_xy_mm": [x, y, X, Y], "height_above_finished_base_mm": z})
    planes.sort(key=lambda plane: plane["region_xy_mm"][1])
    width, length, _ = rounded(bounds(shape)[3:])
    assert all(plane["region_xy_mm"][0] == 0 and plane["region_xy_mm"][2] == width for plane in planes)
    edges = [plane["region_xy_mm"][3] for plane in planes]
    assert edges and edges[-1] == length
    assert [plane["region_xy_mm"][1] for plane in planes] == [0, *edges[:-1]]
    return planes


def blank(shape, planes):
    width, length, height = rounded(bounds(shape)[3:])
    # The 2 mm branches join this sacrificial plate below the finished part.
    result = boolean(shape, box([0, -SIDE_Y, -BACKING_Z, width, length + SIDE_Y, 0]), BRepAlgoAPI_Fuse)
    for plane in planes:
        x, y, X, Y = plane["region_xy_mm"]
        z = plane["height_above_finished_base_mm"]
        if z > 0:
            stock = box([x, y, -.10, X, Y, z])
            result = boolean(result, stock, BRepAlgoAPI_Fuse)
    for lo, hi in ((-SIDE_Y, 0), (length, length + SIDE_Y)):
        stock = box([0, lo, -.10, width, hi, height])
        result = boolean(result, stock, BRepAlgoAPI_Fuse)
    return solid(result)


def make_carrier(parts):
    layout_length = (2 * PART_GAP + sum(row["dimensions"][1] + 2 * SIDE_Y for row in parts.values())
                     + (len(parts) - 1) * PART_GAP)
    carrier = box([0, 0, 0, 2.5, layout_length, BRANCH])
    y = PART_GAP
    placements = {}
    for index, (name, row) in enumerate(parts.items(), 1):
        width, length, height = row["dimensions"]
        shift_y = y + SIDE_Y
        placed = move(blank(row["shape"], row["planes"]), BODY_X, shift_y, BACKING_Z)
        center_y = shift_y + length / 2
        branch = box([2.25, center_y - BRANCH / 2, 0, BODY_X + .25, center_y + BRANCH / 2, BRANCH])
        assert intersection_volume(placed, branch) > .9
        carrier = boolean(carrier, branch, BRepAlgoAPI_Fuse)
        carrier = boolean(carrier, placed, BRepAlgoAPI_Fuse)
        placements[name] = {"order": index, "untrimmed_layout_bounds_mm": rounded(bounds(placed)),
                            "finished_layout_bounds_mm": rounded([BODY_X, shift_y, BACKING_Z,
                                                                    BODY_X + width, shift_y + length, BACKING_Z + height])}
        y += length + 2 * SIDE_Y + PART_GAP
    solid(carrier)
    for name, item in placements.items():
        row = parts[name]
        x, y, z, X, Y, Z = item["finished_layout_bounds_mm"]
        # Remove the backing, both transverse stock bands, and each local
        # stepped seat from the already joined printable solid.
        finished = solid(common(carrier, box([x, y, z, X, Y, Z])))
        for plane in row["planes"]:
            step = plane["height_above_finished_base_mm"]
            if step > 0:
                a, b, A, B = plane["region_xy_mm"]
                finished = solid(cut(finished, box([x + a - .01, y + b, z - .01, x + A + .01, y + B, z + step])))
        design = move(row["shape"], x, y, z)
        expected = volume(design)
        lost = expected - intersection_volume(finished, design)
        added = volume(finished) - expected + lost
        assert abs(lost) < 1e-6 and abs(added) < 1e-6, (name, lost, added)
        item.update({
            "finished_dimensions_mm": row["dimensions"],
            "underside_planes": row["planes"],
            "finished_reference": row["bundle_path"],
            "finished_reference_sha256": row["digest"],
            "trim_removed_from_finished_mm3": round(max(0, lost), 9),
            "trim_stock_remaining_mm3": round(max(0, added), 9),
        })
    return carrier, placements


def draw_layout(path, carriers):
    body = []
    for i, carrier in enumerate(carriers.values()):
        x = 34 * i
        dimensions = carrier["dimensions_xyz_mm"]
        title = "USB-R / BAT-R" if i == 0 else "PWR-R / PWR-F"
        body.append(f'<g transform="translate({x + 2} 6)">')
        body.append(f'<text x="0" y="-2" font-size="2">{title}</text>')
        body.append(f'<rect width="2.5" height="{dimensions[1]}" fill="#b88e53"/>')
        for name, row in carrier["parts"].items():
            a, y, _, A, Y, _ = row["untrimmed_layout_bounds_mm"]
            _, lo, _, _, hi, _ = row["finished_layout_bounds_mm"]
            mid = (y + Y) / 2
            body.append(f'<rect x="2.5" y="{mid-1:.3f}" width="{a-2.5}" height="2" fill="#b88e53"/>')
            body.append(f'<rect x="{a}" y="{y}" width="{A-a}" height="{Y-y:.3f}" fill="#a4d5c5"/>')
            body.append(f'<path d="M{a-.2} {lo}H{A+.2} M{a-.2} {hi}H{A+.2}" stroke="#213c35" stroke-width=".15"/>')
            body.append(f'<text x="10" y="{mid+.6:.3f}" font-size="1.6">{row["order"]}. {name}</text>')
        body.append('</g>')
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 68 60" width="748" height="660">\n'
        '<rect width="68" height="60" fill="#f8f6ed"/>\n'
        '<g font-family="sans-serif" fill="#193830">\n'
        + "\n".join(body)
        + '\n<path d="M2 56h5m-5 -.3v.6m5 -.6v.6" stroke="#193830" stroke-width=".16"/>'
          '<text x="8" y="56.5" font-size="1.4">5 mm</text></g></svg>\n'
    )


def finishing_table(path, carriers, zh):
    with path.open("w", newline="") as stream:
        out = csv.writer(stream, lineterminator="\n")
        out.writerow(
            ["上传文件", "顺序", "零件", "成品X_mm", "成品Y_mm", "成品Z_mm", "去背板区域Y起点_mm",
             "去背板区域Y终点_mm", "该区域相对主底面高差_mm", "成品STEP"]
            if zh else
            ["Upload file", "Order", "Part", "Finished X mm", "Finished Y mm", "Finished Z mm",
             "Trim region Y start mm", "Trim region Y end mm", "Trim step above base plane mm", "Finished STEP"]
        )
        for file, carrier in carriers.items():
            for name, row in carrier["parts"].items():
                for plane in row["underside_planes"]:
                    _, y, _, Y = plane["region_xy_mm"]
                    out.writerow([Path(file).name, row["order"], name, *row["finished_dimensions_mm"],
                                  y, Y, plane["height_above_finished_base_mm"], row["finished_reference"]])


def build(output):
    print_report = AUDIT / "retention-prints.json"
    m05_report = AUDIT / "m05-harness.json"
    spec_file = ROOT / "hardware/e73-corner-retention-spec.json"
    printing, m05, spec = (read(path) for path in (print_report, m05_report, spec_file))
    models = {row["name"]: row for row in printing["rigid_parts"]}
    group_names = {name for names in GROUPS.values() for name in names}
    assert group_names == {name for name in models if not name.startswith("USB-F")}
    assert len(group_names) == 12 and sum(map(len, GROUPS.values())) == len(group_names)
    (output / DIRECTORY).mkdir(parents=True, exist_ok=True)
    (output / REPORT.parent).mkdir(parents=True, exist_ok=True)
    m05_dir = "02-mechanical/service-case-m05/harness/"
    original_dir = "02-mechanical/retention/assembly-reference/"
    parsed = {}
    dependencies = [Path(__file__), print_report, m05_report, spec_file]
    for name in group_names:
        if name.startswith("BAT-"):
            relative = m05["shifted_battery_parts"][name]["source"]
            digest = m05["outputs"][relative]
            bundle_path = m05_dir + Path(relative).name
        else:
            relative = (BASE / "retention/assembly-reference" / f"{name}.step").relative_to(ROOT).as_posix()
            digest = printing["outputs"][relative]
            bundle_path = original_dir + Path(relative).name
        path = ROOT / relative
        assert sha(path) == digest
        if (output / bundle_path).exists():
            assert sha(output / bundle_path) == digest
        dependencies.append(path)
        final = print_orientation(load(path), models[name]["X_rotation_deg"])
        dimensions = rounded(bounds(final)[3:])
        parsed[name] = {"shape": final, "dimensions": dimensions, "planes": underside_planes(final),
                        "bundle_path": bundle_path, "digest": digest}

    carriers = {}
    for filename, names in GROUPS.items():
        relative = (DIRECTORY / filename).as_posix()
        shape, parts = make_carrier({name: parsed[name] for name in names})
        metrics = mesh(shape, output / relative)
        triangles, dimensions = retainer_mesh((output / relative).read_bytes())
        largest, middle, smallest = sorted(dimensions, reverse=True)
        assert largest >= 10 and middle >= 2 and smallest >= 2
        assert triangles == metrics["triangles"] and len(parts) <= 10
        carriers[relative] = {"parts": parts, "triangles": triangles, "dimensions_xyz_mm": dimensions,
                              "connected_closed_shells": 1}
    assert BRANCH - 2 * .20 > 1.5 and BACKING_Z - BRANCH > .20
    assert all(carrier["dimensions_xyz_mm"][1] < 50 for carrier in carriers.values())
    draw_layout(output / LAYOUT, carriers)
    tables = [DIRECTORY / ("finishing" + language + ".csv") for language in ("", ".zh-CN")]
    for path, zh in zip(tables, (False, True)):
        finishing_table(output / path, carriers, zh)
    dependencies += [ROOT / "scripts" / name for name in (
        "build_e73_retainer_coupon.py", "cad_geometry.py", "check_e73_corner_harness.py",
        "check_e73_delivery.py", "e73_corner_retention.py", "export_e73_retention_prints.py",
    )]
    contract = spec["tolerance_contract"]
    report = {
        "status": "m05-retained-guide-connected-blank-meshes-and-trim-checked",
        "physical_verification": False,
        "factory_process_qualified": False,
        "manufacturing_released": False,
        "selected_for_assembly": False,
        "finished_guide_count": len(group_names),
        "branch_cross_section_mm": [BRANCH, BRANCH],
        "backing_stock_mm": BACKING_Z,
        "stock_on_each_transverse_side_mm": SIDE_Y,
        "minimum_finished_web_mm": contract["minimum_finished_web_mm"],
        "maximum_finished_surface_point_error_L2_mm": contract["guide_maximum_surface_point_error_L2_mm"],
        "maximum_printed_parts_per_connected_file": 10,
        "published_connection_web_mm_must_exceed": 1.5,
        "carriers": carriers,
        "files_sha256": {path: sha(output / path) for path in
                         [*carriers, LAYOUT.as_posix(), *(table.as_posix() for table in tables)]},
        "source_sha256": {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(dependencies)},
        "limits": [
            "The carrier meshes pass the published connected-part count, model-size and connector-section screens.",
            "Trim reconstruction recovers the existing M05 STEP geometry. The printed side faces, wire grooves and steps require physical measurements.",
            "The published SLA size tolerance does not guarantee 0.05 mm local surface accuracy. The current grooves require a process sample.",
        ],
    }
    (output / REPORT).write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    build(parser.parse_args().output.resolve())
