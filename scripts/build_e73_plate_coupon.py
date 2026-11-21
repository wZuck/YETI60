#!/usr/bin/env python3
"""Extract inspection openings from the E73 M01 plate without rescaling them."""

import argparse
import json
from itertools import combinations
from pathlib import Path

import ezdxf
from shapely.geometry import Polygon, box

from check_yeti60_plate_mount import ROOT, SOURCE, SPEC, TARGET, keys, sha, verify


WIDTH, HEIGHT = 120, 64
OPENINGS = [
    ("1U", (86, 47), (0,)),
    ("2.25U", (27, 47), (41, 42)),
    ("6U", (60, 17), (57,)),
]


def read_contours(drawing):
    assert drawing.units == 4, "Expected millimetres"
    contours = []
    for entity in drawing.modelspace():
        assert entity.dxftype() == "LWPOLYLINE" and entity.closed
        points = list(entity.get_points("xyb"))
        assert all(bulge == 0 for _, _, bulge in points)
        contours.append(Polygon([(float(x), float(y)) for x, y, _ in points]))
    assert all(contour.is_valid for contour in contours)
    return contours


def svg_preview(path, contours):
    def points(polygon):
        return " ".join(f"{x:.6f},{HEIGHT-y:.6f}" for x, y in polygon.exterior.coords)

    outlines = "\n".join(f'  <polygon points="{points(poly)}"/>' for poly in contours)
    labels = "\n".join(
        f'  <text x="{x}" y="{HEIGHT-y-10}">{label}</text>'
        for label, (x, y), _ in OPENINGS
    )
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-5 -5 130 74" width="720" height="410">\n'
        '  <rect x="-5" y="-5" width="130" height="74" fill="#f5f4ed"/>\n'
        '  <g stroke="#213b32" stroke-width=".35" fill="none">\n'
        f'{outlines}\n'
        '  </g>\n'
        '  <g fill="#213b32" font-family="sans-serif" font-size="3" text-anchor="middle">\n'
        f'{labels}\n'
        '  </g>\n'
        '</svg>\n'
    )


def build(output):
    baseline = ezdxf.readfile(SOURCE)
    plate = ezdxf.readfile(TARGET)
    spec = json.loads(SPEC.read_text())
    verify(baseline, plate, spec)
    active = keys(baseline)
    plate_cuts = list(plate.modelspace().query("LWPOLYLINE"))[1:]
    stabilized = {part["active_index"]: part for part in spec["stabilized_keys"]}
    coupon_contours = [box(0, 0, WIDTH, HEIGHT)]
    details = []
    for label, (x, y), indexes in OPENINGS:
        translated = []
        for index in indexes:
            cut = plate_cuts[index]
            assert cut.closed and all(bulge == 0 for _, _, bulge in cut.get_points("xyb"))
            # The source drawing uses the sign-reversed case XY coordinates.
            # Translate about the original key datum, preserving the cut's orientation.
            translated.append(Polygon([
                (float(px + active[index]["x"] + x), float(py + active[index]["y"] + y))
                for px, py in cut.get_points("xy")
            ]))
        profile = translated[0]
        for other in translated[1:]:
            assert profile.hausdorff_distance(other) < 1e-8
        coupon_contours.append(profile)
        details.append({
            "opening": label,
            "datum_mm": [x, y],
            "m01_active_indexes_zero_based": list(indexes),
            "stabilizer_stem_spacing_mm": (
                stabilized[indexes[0]]["stem_spacing_mm"] if indexes[0] in stabilized else None
            ),
        })

    ezdxf.options.write_fixed_meta_data_for_testing = True
    fabrication = ezdxf.new("R2018")
    fabrication.units = 4
    for contour in coupon_contours:
        fabrication.modelspace().add_lwpolyline(list(contour.exterior.coords)[:-1], close=True)
    dxf = output / "02-mechanical/plate-fit-coupon.dxf"
    drawing = output / "02-mechanical/plate-fit-coupon.svg"
    evidence = output / "06-validation/plate-fit-coupon.json"
    dxf.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    # The exporter discovers these class names through a set.
    for name in sorted(fabrication.entitydb.dxf_types_in_use()):
        fabrication.classes.add_class(name)
    fabrication.saveas(dxf)
    readback = ezdxf.readfile(dxf)
    audit = readback.audit()
    assert not audit.errors and not audit.fixes
    actual = read_contours(readback)
    assert len(actual) == len(coupon_contours) == 4
    for from_disk, planned in zip(actual, coupon_contours):
        assert from_disk.equals_exact(planned, 1e-8)
    perimeter, *holes = actual
    assert all(perimeter.contains(hole) for hole in holes)
    assert all(not a.intersects(b) for a, b in combinations(holes, 2))
    edge_web = min(perimeter.boundary.distance(hole) for hole in holes)
    between_web = min(a.distance(b) for a, b in combinations(holes, 2))
    assert edge_web >= 8 and between_web >= 12
    svg_preview(drawing, actual)
    report = {
        "status": "m01-opening-profiles-translated-and-read-back",
        "physical_fit_verified": False,
        "outline_mm": [WIDTH, HEIGHT],
        "material": spec["plate_material"],
        "finished_thickness_mm": spec["finished_plate_thickness_range_mm"],
        "minimum_edge_web_mm": round(edge_web, 6),
        "minimum_opening_to_opening_web_mm": round(between_web, 6),
        "openings": details,
        "source_plate_sha256": sha(TARGET),
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (
            SOURCE, SPEC, TARGET, Path(__file__).resolve(), ROOT / "scripts/check_yeti60_plate_mount.py"
        )},
        "files_sha256": {str(p.relative_to(output)): sha(p) for p in (dxf, drawing)},
    }
    evidence.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output.resolve())
