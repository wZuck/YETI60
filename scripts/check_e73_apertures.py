#!/usr/bin/env python3
"""Measure drill clearance and stencil aperture geometry in the fabrication ZIP."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import warnings
from zipfile import ZipFile

from gerbonara import ExcellonFile, GerberFile, MM
from gerbonara.graphic_objects import Flash
from shapely import union_all
from shapely.geometry import Point, Polygon, box
from shapely.strtree import STRtree

from kicad_sexpr import child, children, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "hardware/e73-hhkb-corner"
BOARD = BASE / "EC60-nRF52840.kicad_pcb"
LIMITS_URL = "https://jlcpcb.com/capabilities/Capabilities"
STENCIL_URL = "https://jlcpcb.com/capabilities/pcb-stencil-manufacturing"
STENCIL_THICKNESSES_MM = (0.10, 0.12, 0.15, 0.18, 0.20)
STENCIL_AREA_RATIO_SCREEN = 0.66
LAYER_SUFFIXES = {
    "F.Mask": ("F_Mask.gts", "Soldermask,Top", "Negative"),
    "B.Mask": ("B_Mask.gbs", "Soldermask,Bot", "Negative"),
    "F.Paste": ("F_Paste.gtp", "Paste,Top", "Positive"),
    "B.Paste": ("B_Paste.gbp", "Paste,Bot", "Positive"),
}
ARC_ERROR_MM = .0002
# Conservative planning assumptions based on the public through-hole values.
# Treat the advertised position figure as an allowance on each axis.
HOLE_POS_PER_AXIS_MM = .075
HOLE_DIAMETER_GROWTH_MM = .13
HOLE_RESERVE_MM = math.hypot(HOLE_POS_PER_AXIS_MM, HOLE_POS_PER_AXIS_MM) + HOLE_DIAMETER_GROWTH_MM / 2


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def match_vias(drill_text, native):
    assert "; #@! TF.FileFunction,Plated,1,4,PTH" in drill_text
    # Gerbonara warns about KiCad's conventional G90 immediately after the header.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r'.*G90.*header statement found.*', category=SyntaxWarning)
        drill = ExcellonFile.from_string(drill_text)
    assert drill.import_settings.unit == MM
    round_hits = [(obj.x, obj.y, obj.tool.diameter) for obj in drill.objects if isinstance(obj, Flash)]
    by_hit = {}
    for via in children(native, "via"):
        x, y = map(float, child(via, "at")[1:3])
        diameter = float(child(via, "drill")[1])
        matches = [pos for pos in round_hits
                   if pos[2] == diameter and max(abs(pos[0] - x), abs(pos[1] + y)) <= .000500001]
        assert len(matches) == 1, ("Missing or duplicate via hit", x, y, diameter)
        hit, = matches
        assert hit not in by_hit, ("One hit matched two vias", hit)
        by_hit[hit] = {"via_uuid": child(via, "uuid")[1], "net": child(via, "net")[1]}
    expected_sizes = {hit[2] for hit in by_hit}
    assert len(by_hit) == sum(hit[2] in expected_sizes for hit in round_hits), "Unused via-sized drill hits"
    return by_hit


def openings(artwork, role, polarity):
    # KiCad mask negative film: positive graphic objects are mask openings.
    assert f"%TF.FileFunction,{role}*%" in artwork
    assert f"%TF.FilePolarity,{polarity}*%" in artwork
    file = GerberFile.from_string(artwork)
    assert file.import_settings.unit == MM
    shapes, references = [], []
    for obj in file.objects:
        # The current fabrication outputs contain only additive objects and
        # aperture primitives. Reject a future clear exposure for explicit review.
        assert obj.polarity_dark, "Unsupported clear-polarity Gerber object"
        attrs = obj.attrs
        ref = attrs.get(".C", [None])[0] if isinstance(attrs, dict) else None
        for prim in obj.to_primitives(unit=MM):
            assert prim.polarity_dark, "Unsupported clear-polarity aperture primitive"
            outline = prim.to_arc_poly().approximate_arcs(max_error=ARC_ERROR_MM).outline
            if len(set(outline)) < 3:
                continue
            poly = Polygon(outline)
            assert poly.is_valid and poly.area > 0, ("Invalid tessellated aperture", prim)
            shapes.append(poly)
            references.append(ref)
    assert shapes, role
    return shapes, references


def check_layer(polygons, refs, vias):
    tree = STRtree(polygons)
    records = []
    for (x, y, diameter), record in vias.items():
        center = Point(x, y)
        index = tree.nearest(center)
        gap = center.distance(polygons[index]) - diameter / 2
        records.append(dict(**record, pcb_xy_mm=[x, -y], drill_mm=diameter,
                            artwork_reference=refs[index],
                            nominal_gap_mm=round(gap, 6),
                            drill_reserve_remaining_mm=round(gap - ARC_ERROR_MM - HOLE_RESERVE_MM, 6),
                            nominal_intersection=gap < -ARC_ERROR_MM))
    records.sort(key=lambda row: (row["nominal_gap_mm"], row["via_uuid"]))
    near = [row for row in records if row["drill_reserve_remaining_mm"] <= 0]
    return dict(min_nominal_gap_mm=records[0]["nominal_gap_mm"], constructed_shapes=len(polygons),
                nearest=records[0],
                holes_below_conservative_reserve=len(near),
                nominal_intersections=sum(row["nominal_intersection"] for row in near),
                tight_locations=near)


def thermal_coverage(native, artwork):
    """Measure paste and exposed copper on the two actual thermal lands."""
    result = {}
    targets = {"U5": "17", "U6": "11"}
    for fp in children(native, "footprint"):
        ref = next(prop[2] for prop in children(fp, "property") if prop[1] == "Reference")
        if ref not in targets:
            continue
        pad, = [pad for pad in children(fp, "pad") if pad[1] == targets[ref]]
        assert pad[3] == "rect" and list(map(float, child(pad, "at")[1:])) == [0, 0]
        x, y = map(float, child(fp, "at")[1:])
        w, h = map(float, child(pad, "size")[1:])
        land = box(x-w/2, -y-h/2, x+w/2, -y+h/2)
        regions = {}
        for layer in ("B.Mask", "B.Paste"):
            polygons, _ = artwork[layer]
            regions[layer] = union_all([g.intersection(land) for g in polygons if g.intersects(land)])
        paste = regions["B.Paste"]
        mask = regions["B.Mask"]
        apertures = list(paste.geoms) if paste.geom_type == "MultiPolygon" else [paste]
        assert len(apertures) >= 2 and all(item.geom_type == "Polygon" for item in apertures)
        web = min(a.distance(b) for i, a in enumerate(apertures) for b in apertures[:i])
        result[ref + "." + targets[ref]] = dict(
            land_mm2=round(land.area, 6), paste_apertures=len(apertures),
            paste_fraction=round(paste.area / land.area, 6),
            exposed_copper_fraction=round(mask.area / land.area, 6),
            paste_on_open_mask_fraction=round(paste.intersection(mask).area / land.area, 6),
            minimum_stencil_web_mm=round(web, 6),
            minimum_area_ratio_at_0p125mm=round(min(item.area / (item.length * .125)
                                                    for item in apertures), 6))
    assert len(result) == len(targets)
    return result


def stencil_openings(polygons, references):
    # Gerber macros can draw a single opening with several touching primitives.
    # Measure the boundary of the cut opening after joining those primitives.
    union = union_all(polygons)
    windows = list(union.geoms) if union.geom_type == "MultiPolygon" else [union]
    assert all(window.geom_type == "Polygon" and not window.interiors for window in windows)
    limiting = min(windows, key=lambda window: (window.area / window.length, window.bounds))
    x1, y1, x2, y2 = limiting.bounds
    tree = STRtree(polygons)
    limiting_references = {references[index] for index in tree.query(limiting, predicate="intersects")}
    assert len(limiting_references) == 1 and None not in limiting_references
    return dict(
        cuts=len(windows),
        component_references=sorted(set(references)),
        limiting_reference=limiting_references.pop(),
        limiting_bounds_pcb_mm=[round(value, 6) for value in (x1, -y2, x2, -y1)],
        limiting_area_mm2=round(limiting.area, 6),
        limiting_perimeter_mm=round(limiting.length, 6),
        standard_thicknesses={
            f"{thickness:.2f}": dict(
                minimum_area_ratio=round(limiting.area / (limiting.length * thickness), 6),
                cuts_below_screen=sum(
                    window.area / (window.length * thickness) < STENCIL_AREA_RATIO_SCREEN
                    for window in windows))
            for thickness in STENCIL_THICKNESSES_MM})


def run(archive, board=BOARD):
    native = loads(board.read_text())
    with ZipFile(archive) as bundle:
        vias = match_vias(bundle.read(f"{board.stem}-PTH.drl").decode("ascii"), native)
        artwork = {layer: openings(bundle.read(f"{board.stem}-{suffix}").decode("ascii"), role, polarity)
                   for layer, (suffix, role, polarity) in LAYER_SUFFIXES.items()}
    layers = {layer: check_layer(*geometry, vias) for layer, geometry in artwork.items()}
    return dict(status="gerber-mask-and-paste-clearance-measured", physical_verification=False,
                archive_sha256=sha(archive), source_PCB_sha256=sha(board),
                source_sha256={str(p.relative_to(ROOT)): sha(p)
                               for p in (board, Path(__file__), ROOT / "scripts/kicad_sexpr.py")},
                vias=len(vias), via_drills_mm=dict(sorted(Counter(hit[2] for hit in vias).items())),
                arc_geometry_allowance_mm=ARC_ERROR_MM,
                conservative_drill_reserve_mm=round(HOLE_RESERVE_MM, 6),
                hole_pos_per_axis_mm_assumed=HOLE_POS_PER_AXIS_MM,
                maximum_positive_diameter_tolerance_mm_used=HOLE_DIAMETER_GROWTH_MM,
                mask_and_stencil_registration_included=False,
                drilling_reference=LIMITS_URL, layers=layers,
                thermal_lands=thermal_coverage(native, artwork),
                stencil=dict(area_ratio_screen=STENCIL_AREA_RATIO_SCREEN,
                             standard_thickness_reference=STENCIL_URL,
                             sides={side: stencil_openings(*artwork[side])
                                    for side in ("F.Paste", "B.Paste")}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "delivery/YETI60-E73/01-pcb/YETI60-E73-gerbers-REVIEW.zip")
    parser.add_argument("--board", type=Path, default=BOARD)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.archive, args.board.resolve())
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    for layer, row in result["layers"].items():
        print(layer, row["min_nominal_gap_mm"], "mm,", row["holes_below_conservative_reserve"],
              "tight vias,", row["nominal_intersections"], "nominal overlaps")


if __name__ == "__main__":
    main()
