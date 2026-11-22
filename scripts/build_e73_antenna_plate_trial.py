#!/usr/bin/env python3
"""Extract an antenna-window trial from the exact E73 M01 plate."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import ezdxf
from ezdxf.path import make_path
from shapely.geometry import Point, Polygon, box


ROOT = Path(__file__).resolve().parents[1]
PLATE = ROOT / "mechanical/e73-fit/yeti60-e73-niz-m01.dxf"
FIT = ROOT / "mechanical/e73-fit-spec.json"
RADIO = ROOT / "hardware/e73-hhkb-corner/audit/radio-path.json"
KEY_MAP = ROOT / "docs/assembly/e73-corner/calibration-keys.csv"
WINDOW_TOP_BOTTOM_MARGIN_MM = .60
WINDOW_SIDE_MARGIN_MM = 1.50
WINDOW_RADIUS_MM = .60
RELATIVE_XY_SCREEN_MM = .30


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outline(entity):
    assert entity.closed
    return Polygon([(-vertex.x, -vertex.y) for vertex in make_path(entity).flattening(.002)])


def circle(entity):
    return Point(-entity.dxf.center.x, -entity.dxf.center.y).buffer(entity.dxf.radius, quad_segs=32)


def svg_preview(path, outer, other_openings, window, antenna, key_label):
    def points(polygon):
        return " ".join(f"{x:.4f},{-y:.4f}" for x, y in polygon.exterior.coords)

    preview_bounds = box(327, -209, 362, -157)
    visible_openings = "\n".join(
        f'  <polygon points="{points(poly)}" fill="#f5f4ed" stroke="#38574c" stroke-width=".18"/>'
        for poly in other_openings if poly.intersects(preview_bounds)
    )
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="327 157 35 52" width="490" height="728">\n'
        '  <rect x="327" y="157" width="35" height="52" fill="#f5f4ed"/>\n'
        f'  <polygon points="{points(outer)}" fill="#aeb8b1" stroke="#38574c" stroke-width=".18"/>\n'
        f'{visible_openings}\n'
        f'  <polygon points="{points(window)}" fill="#f5f4ed" stroke="#38574c" stroke-width=".18"/>\n'
        f'  <polygon points="{points(antenna)}" fill="#c06538" fill-opacity=".48" stroke="#904624" stroke-width=".11"/>\n'
        '  <g fill="#1d3b30" font-family="sans-serif" font-size="1.45" text-anchor="middle">\n'
        f'    <text x="347.66" y="170.8">{key_label}</text>\n'
        '    <text x="336" y="187.7">6.00 × 14.20 mm</text>\n'
        '    <text x="336" y="191">E73</text>\n'
        '  </g>\n'
        '  <path d="M342.2 187.2 H345.5 M338.1 190.5 H347" stroke="#38574c" stroke-width=".13"/>\n'
        '</svg>\n'
    )


def build(output):
    radio = json.loads(RADIO.read_text())
    assert radio["source_sha256"][str(PLATE.relative_to(ROOT))] == sha(PLATE)
    antenna_x0, antenna_y0, antenna_x1, antenna_y1 = radio["antenna_band_PCB_mm"]
    x0, y0, x1, y1 = antenna_x0, -antenna_y1, antenna_x1, -antenna_y0
    antenna = box(x0, y0, x1, y1)
    side, ends, radius = WINDOW_SIDE_MARGIN_MM, WINDOW_TOP_BOTTOM_MARGIN_MM, WINDOW_RADIUS_MM
    window = box(x0 - side + radius, y0 - ends + radius,
                 x1 + side - radius, y1 + ends - radius).buffer(radius, quad_segs=16)
    shift = RELATIVE_XY_SCREEN_MM
    shifted_antenna_envelope = box(x0 - shift, y0 - shift, x1 + shift, y1 + shift)

    drawing = ezdxf.readfile(PLATE)
    assert drawing.units == 4
    modelspace = drawing.modelspace()
    original, *keys = [outline(entity) for entity in modelspace.query("LWPOLYLINE")]
    mounts = [circle(entity) for entity in modelspace.query("CIRCLE")]
    assert len(keys) == 60 and len(mounts) == 28
    assert all(poly.is_valid for poly in [original, *keys, *mounts])
    bearing = json.loads(FIT.read_text())["gaskets"]
    gasket_error = bearing["maximum_cut_and_placement_point_error_XY_each_axis_mm"]
    dx, dy = [size / 2 + gasket_error for size in bearing["finished_size_XY_mm"]]
    gasket_rectangles = [box(x - dx, y - dy, x + dx, y + dy) for x, y in bearing["centers_case_XY_mm"]]

    ezdxf.options.write_fixed_meta_data_for_testing = True
    modelspace.add_lwpolyline([(-x, -y) for x, y in list(window.exterior.coords)[:-1]], close=True)
    mechanical = output / "02-mechanical/antenna-trial"
    mechanical.mkdir(parents=True, exist_ok=True)
    dxf = mechanical / "M01-antenna-window-TRIAL.dxf"
    drawing.saveas(dxf)
    restored = ezdxf.readfile(dxf)
    audit = restored.audit()
    assert restored.units == 4 and not audit.errors and not audit.fixes
    *original_contours, cut = [outline(entity) for entity in restored.modelspace().query("LWPOLYLINE")]
    assert len(original_contours) == 61
    assert all(a.equals_exact(b, 1e-8) for a, b in zip([original, *keys], original_contours))
    saved_mounts = [circle(entity) for entity in restored.modelspace().query("CIRCLE")]
    assert len(saved_mounts) == 28 and all(a.equals_exact(b, 1e-8) for a, b in zip(mounts, saved_mounts))
    assert cut.equals_exact(window, 1e-8) and original.contains(cut)

    closest_key = min(range(len(keys)), key=lambda index: keys[index].distance(cut))
    assert closest_key == 54
    with KEY_MAP.open(newline="") as stream:
        key_rows = list(csv.DictReader(stream))
    closest = key_rows[closest_key]
    assert int(closest["Index"]) == closest_key
    assert keys[closest_key].contains(Point(float(closest["Plate_X_mm"]), float(closest["Plate_Y_mm"])))
    key_label = closest["Electrode"]
    assert key_label == "SW62"
    gaskets_gap = min(gasket.distance(cut) for gasket in gasket_rectangles)
    key_web = keys[closest_key].distance(cut)
    mount_web = min(mount.distance(cut) for mount in mounts)
    edge_web = original.boundary.distance(cut)
    assert gaskets_gap > 5 and key_web > 4.08 and mount_web > 30 and edge_web > 2.50
    original_steel = Polygon(original.exterior, [poly.exterior for poly in (*keys, *mounts)])
    finished = original_steel.difference(cut)
    assert original_steel.is_valid and finished.geom_type == "Polygon" and finished.is_valid
    assert len(finished.interiors) == 89
    original_overlap = original_steel.intersection(antenna).area
    assert abs(original_overlap - radio["steel_projection_intersection_mm2"]) < 1e-6
    assert finished.intersection(shifted_antenna_envelope).is_empty
    preview = mechanical / "M01-antenna-window-TRIAL.svg"
    svg_preview(preview, original, [*keys, *mounts], cut, antenna, key_label)
    record = output / "06-validation/antenna-window-trial.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "alternate-plate-geometry-checked-ab-trial-only",
        "physical_verification": False,
        "electromagnetic_field_solution": False,
        "selected_as_default_plate": False,
        "window_case_bounds_mm": [round(value, 6) for value in cut.bounds],
        "window_internal_corner_radius_mm": radius,
        "window_area_mm2": round(cut.area, 6),
        "steel_over_antenna_before_after_mm2": [round(original_overlap, 6), 0],
        "relative_antenna_motion_screen_each_axis_mm": shift,
        "minimum_remaining_web_mm": {
            "plate_edge": round(edge_web, 6),
            "switch_opening": round(key_web, 6),
            "mounting_pilot": round(mount_web, 6),
        },
        "closest_switch_reference": key_label,
        "minimum_distance_to_expanded_gasket_mm": round(gaskets_gap, 6),
        "preserved_openings_and_mounts": [len(keys), len(mounts)],
        "default_plate_sha256": sha(PLATE),
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in (
            PLATE, FIT, RADIO, KEY_MAP, Path(__file__).resolve()
        )},
        "trial_sha256": {str(path.relative_to(output)): sha(path) for path in (dxf, preview)},
    }
    record.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output.resolve())
