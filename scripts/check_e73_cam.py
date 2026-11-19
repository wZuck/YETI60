#!/usr/bin/env python3
"""Match the KiCad 10 X2 and Excellon fabrication ZIP to the native E73 PCB."""
from collections import Counter
import argparse
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import re
from zipfile import ZipFile

import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "hardware/e73-hhkb-corner"
STEM = "EC60-nRF52840"
BOARD = BASE / f"{STEM}.kicad_pcb"
PROFILE = ROOT / "mechanical/pcb-fabrication-spec.json"
POWER = BASE / "audit/power-process.json"
ZIP_NAME = "YETI60-E73-gerbers-REVIEW.zip"
LAYERS = {
    "F_Cu.gtl": "Copper,L1,Top",
    "In1_Cu.g1": "Copper,L2,Inr",
    "In2_Cu.g2": "Copper,L3,Inr",
    "B_Cu.gbl": "Copper,L4,Bot",
    "F_Mask.gts": "Soldermask,Top",
    "B_Mask.gbs": "Soldermask,Bot",
    "F_Paste.gtp": "Paste,Top",
    "B_Paste.gbp": "Paste,Bot",
    "F_Silkscreen.gto": "Legend,Top",
    "B_Silkscreen.gbo": "Legend,Bot",
    "Edge_Cuts.gm1": "Profile,NP",
}
COPPER = (pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu)
DRILL_POINT = r"X(-?\d+(?:\.\d+)?)Y(-?\d+(?:\.\d+)?)"
GERBER_POINT = r"X(-?\d+)Y(-?\d+)"
# Excellon uses three decimal places. Retain both nearest positions on exact ties.
DRILL_ROUNDING_NM = 500


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plot_point(vector):
    return (vector.x, -vector.y)


def parse_drills(data, plating):
    header, body = data.split("\n%\n")
    assert header.startswith("M48\n") and "\nMETRIC\n" in header
    assert "absolute / metric / decimal" in header and body.startswith("G90\nG05\n")
    expected_role = "Plated,1,4,PTH" if plating == "PTH" else "NonPlated,1,4,NPTH"
    assert f"; #@! TF.FileFunction,{expected_role}\n" in header
    tools = {}
    tool_plating = "Plated,PTH" if plating == "PTH" else "NonPlated,NPTH"
    for kind, tool, diameter in re.findall(
        rf"; #@! TA.AperFunction,{tool_plating},(ViaDrill|ComponentDrill)\n(T\d+)C(\d+\.\d+)", header
    ):
        assert tool not in tools
        tools[tool] = (kind, round(float(diameter) * 1e6))
    assert len(tools) == len(re.findall(r"^T\d+C", header, re.M))
    records = []
    selected = None
    for line in body.splitlines()[:-1]:
        if line in tools:
            selected = tools[line]
        elif line not in {"G90", "G05"}:
            hit = re.fullmatch(DRILL_POINT + r"(?:G85" + DRILL_POINT + ")?", line)
            assert hit and selected, ("Unexpected Excellon drill command", line)
            coordinates = [round(float(v) * 1e6) for v in hit.groups() if v is not None]
            assert all(value % 1000 == 0 for value in coordinates), ("Unexpected Excellon precision", line)
            points = tuple(sorted(zip(coordinates[::2], coordinates[1::2])))
            records.append((*selected, points))
    assert body.strip().endswith("\nM30")
    return records


def drill_points(pad):
    center = pad.GetPosition()
    size = pad.GetDrillSize()
    if size.x == size.y:
        return (plot_point(center),)
    theta = math.radians(-pad.GetOrientationDegrees()) + (math.pi / 2 if size.x < size.y else 0)
    half = abs(size.x - size.y) / 2
    offset_x, offset_y = half * math.cos(theta), half * math.sin(theta)
    return tuple(sorted((round(center.x + sign * offset_x), -round(center.y + sign * offset_y))
                        for sign in (-1, 1)))


def match_drills(actual, expected):
    unmatched = set(range(len(expected)))
    for kind, diameter, points in actual:
        matches = [
            index for index in unmatched
            if expected[index][:2] == (kind, diameter) and len(expected[index][2]) == len(points)
            and all(max(abs(a - b) for a, b in zip(p, q)) <= DRILL_ROUNDING_NM
                    for p, q in zip(points, expected[index][2]))
        ]
        assert len(matches) == 1, ("Unexpected, duplicated or misplaced drill", kind, diameter, points)
        unmatched.remove(matches[0])
    assert not unmatched, ("Missing drills", [expected[index] for index in sorted(unmatched)])


def via_flashes(data):
    apertures = {}
    via_aperture = False
    active = None
    result = Counter()
    for line in data.splitlines():
        if line.startswith("%TA.AperFunction,"):
            via_aperture = line == "%TA.AperFunction,ViaPad*%"
        elif line == "%TD*%":
            via_aperture = False
        elif line.startswith("%ADD") and via_aperture:
            definition = re.fullmatch(r"%ADD(\d+)C,(\d+\.\d+)\*%", line)
            assert definition, ("Noncircular via land", line)
            apertures[definition[1]] = round(float(definition[2]) * 1e6)
        elif selection := re.fullmatch(r"D(\d+)\*", line):
            active = apertures.get(selection[1])
        elif active and (flash := re.fullmatch(GERBER_POINT + r"D03\*", line)):
            result[(int(flash[1]), int(flash[2])), active] += 1
    return result


def profile_geometry(data, board):
    # KiCad emits one move per line/arc. Arc end points are evaluated by the
    # Gerber writer and can differ slightly from the adjacent line end point.
    segments = []
    nodes = []
    orientation = "01"
    start = None
    for line in data.splitlines():
        if line in {"G01*", "G02*", "G03*"}:
            orientation = line[1:3]
            continue
        hit = re.fullmatch(GERBER_POINT + r"(?:I(-?\d+)J(-?\d+))?D(0[12])\*", line)
        if not hit:
            assert not line.startswith("X"), ("Unexpected profile command", line)
            continue
        point = (int(hit[1]), int(hit[2]))
        if hit[5] == "02":
            start = point
        else:
            assert start is not None and (hit[3] is None) == (orientation == "01")
            center = (start[0] + int(hit[3]), start[1] + int(hit[4])) if hit[3] else None
            # Represent arcs as counterclockwise in the Gerber coordinate frame.
            segments.append((point, start, center) if orientation == "02" else (start, point, center))
            start = None
    native = list(board.GetDrawings())
    native.extend(item for footprint in board.GetFootprints() for item in footprint.GraphicalItems())
    outlines = [item for item in native if item.GetLayer() == pcb.Edge_Cuts]
    assert len(segments) == len(outlines)
    for start, end, center in segments:
        for item in outlines:
            points = (plot_point(item.GetStart()), plot_point(item.GetEnd()))
            same_ends = any(math.dist(start, a) <= 100 and math.dist(end, b) <= 100
                            for a, b in (points, points[::-1]))
            is_arc = item.GetShapeStr() == "Arc"
            if same_ends and is_arc == (center is not None) and (
                    not is_arc or math.dist(plot_point(item.GetCenter()), center) <= 100):
                if is_arc:
                    sa, ea, mid = [
                        math.atan2(y - center[1], x - center[0])
                        for x, y in (start, end, plot_point(item.GetArcMid()))
                    ]
                    assert 0 < (mid - sa) % math.tau < (ea - sa) % math.tau, "Arc follows the wrong sweep"
                outlines.remove(item)
                break
        else:
            raise AssertionError(("Unexpected Gerber profile segment", start, end, center))
    neighbors = {}
    for start, end, _ in segments:
        indices = []
        for point in (start, end):
            match = next((i for i, node in enumerate(nodes) if math.dist(point, node) <= 100), None)
            if match is None:
                match = len(nodes)
                nodes.append(point)
            indices.append(match)
        a, b = indices
        neighbors.setdefault(a, []).append(b)
        neighbors.setdefault(b, []).append(a)
    assert all(len(adjacent) == 2 for adjacent in neighbors.values()), "Open profile"
    pending, visited = [0], set()
    while pending:
        node = pending.pop()
        if node not in visited:
            visited.add(node)
            pending.extend(neighbors[node])
    assert len(visited) == len(nodes), "Disconnected profile"
    width, height = [round((max(axis) - min(axis)) / 1e6, 6) for axis in zip(*nodes)]
    return {"width_mm": width, "height_mm": height,
            "lines": sum(center is None for _, _, center in segments),
            "arcs": sum(center is not None for _, _, center in segments), "closed_contours": 1}


def check(archive):
    profile = json.loads(PROFILE.read_text())
    board = pcb.LoadBoard(str(BOARD))
    assert board.GetCopperLayerCount() == len(COPPER)
    vias = [item for item in board.GetTracks() if isinstance(item, pcb.PCB_VIA)]
    assert all((v.GetViaType(), v.TopLayer(), v.BottomLayer()) ==
               (pcb.VIATYPE_THROUGH, pcb.F_Cu, pcb.B_Cu) for v in vias)
    pads = [pad for footprint in board.GetFootprints() for pad in footprint.Pads()
            if pad.GetDrillSize().x]
    expected = {"PTH": [("ViaDrill", v.GetDrillValue(), (plot_point(v.GetPosition()),)) for v in vias],
                "NPTH": []}
    for pad in pads:
        assert pad.GetAttribute() in (pcb.PAD_ATTRIB_NPTH, pcb.PAD_ATTRIB_PTH)
        plating = "PTH" if pad.GetAttribute() == pcb.PAD_ATTRIB_PTH else "NPTH"
        size = pad.GetDrillSize()
        expected[plating].append(("ComponentDrill", min(size.x, size.y), drill_points(pad)))

    with ZipFile(archive) as bundle:
        names = {f"{STEM}-{suffix}" for suffix in (*LAYERS, "PTH.drl", "NPTH.drl", "job.gbrjob")}
        names.add("drill-report.txt")
        assert set(bundle.namelist()) == names and len(bundle.namelist()) == len(names)
        files = {suffix: bundle.read(f"{STEM}-{suffix}").decode("ascii") for suffix in LAYERS}
        job = json.loads(bundle.read(f"{STEM}-job.gbrjob"))
        drill = {role: parse_drills(bundle.read(f"{STEM}-{role}.drl").decode("ascii"), role)
                 for role in expected}
    frames = set()
    for suffix, data in files.items():
        role = LAYERS[suffix]
        assert f"%TF.FileFunction,{role}*%" in data
        assert "%MOMM*%" in data and "%FSLAX46Y46*%" in data and data.strip().endswith("M02*")
        frames.add(re.search(r"%TF.SameCoordinates,([^*]+)\*%", data)[1])
        if role != "Profile,NP":
            polarity = "Negative" if role.startswith("Soldermask,") else "Positive"
            assert f"%TF.FilePolarity,{polarity}*%" in data
    assert len(frames) == 1, "Gerber layer coordinate origins differ"
    job_layers = []
    for suffix, role in LAYERS.items():
        name = role.replace("Paste,", "SolderPaste,").replace("Soldermask,", "SolderMask,")
        job_layers.append((f"{STEM}-{suffix}", name.removesuffix(",NP"),
                           "Negative" if name.startswith("SolderMask,") else "Positive"))
    assert Counter(job_layers) == Counter((f["Path"], f["FileFunction"], f["FilePolarity"])
                                          for f in job["FilesAttributes"])
    general = job["GeneralSpecs"]
    assert (general["LayerNumber"], general["BoardThickness"], general["Finish"]) == (
        len(COPPER), profile["CAD_finished_envelope_mm"], "ENIG")
    stack = [layer for layer in job["MaterialStackup"] if layer["Type"] in {"Copper", "Dielectric"}]
    outer, inner = profile["outer_copper_mm"], profile["inner_copper_mm"]
    first, last = profile["outer_dielectrics_mm"]
    assert [layer["Thickness"] for layer in stack] == [outer, first, inner, profile["core_mm"],
                                                        inner, last, outer]
    assert [layer["Material"] for layer in stack if layer["Type"] == "Dielectric"] == ["7628", "FR4", "7628"]

    outline = profile_geometry(files["Edge_Cuts.gm1"], board)
    assert [outline["width_mm"], outline["height_mm"]] == [285.0, 94.6]
    for plating in drill:
        match_drills(drill[plating], expected[plating])
    for suffix, layer in zip(LAYERS, COPPER):
        expected_flashes = Counter((plot_point(v.GetPosition()), v.GetWidth(layer)) for v in vias)
        assert via_flashes(files[suffix]) == expected_flashes, ("Gerber via land mismatch", suffix)
    via_hits = [(diameter, points[0]) for kind, diameter, points in drill["PTH"] if kind == "ViaDrill"]
    spacing = min(math.dist(a, b) - (d + e) / 2 for (d, a), (e, b) in combinations(via_hits, 2)) / 1e6
    assert spacing >= .2
    sizes = Counter((v.GetDrillValue(), v.GetWidth(layer))
                    for v in vias for layer in COPPER)
    for diameter, land in sizes:
        assert diameter >= profile["minimum_via_drill_mm"] * 1e6
        assert land >= profile["minimum_via_diameter_mm"] * 1e6 and land - diameter >= 150_000
    assert all(diameter >= 500_000 for _, diameter, _ in drill["NPTH"])
    slots = [{"width_mm": diameter / 1e6, "length_mm": (math.dist(*points) + diameter) / 1e6}
             for _, diameter, points in drill["PTH"] if len(points) == 2]
    assert all(slot["width_mm"] >= .5 and slot["length_mm"] >= 2 * slot["width_mm"] for slot in slots)

    baked_power = json.loads(POWER.read_text())
    assert baked_power["source_sha256"][str(BOARD.relative_to(ROOT))] == sha(BOARD)
    switch = baked_power["repaired_apertures"]["SW1"]
    gap = switch["nominal_drill_to_own_opening_mm"]["B.Mask"]
    # Screen a conservative diagonal position error and half the finished-hole
    # diameter growth. The mask registration tolerance is a separate gate.
    drill_budget = math.hypot(.075, .075) + .13 / 2
    assert gap > drill_budget
    return {
        "status": "cam-geometry-matches-native-pcb",
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (BOARD, PROFILE, POWER, Path(__file__))},
        "archive_sha256": sha(archive),
        "ordinary_process_profile": profile["profile"],
        "layer_roles": LAYERS,
        "stackup": profile["stackup"],
        "pcb_order_thickness_mm": profile["nominal_order_thickness_mm"],
        "cad_stack_thickness_mm": general["BoardThickness"],
        "profile": outline,
        "through_via_count": len(via_hits),
        "via_copper_flashes_per_layer": len(vias),
        "minimum_via_drill_edge_gap_mm": round(spacing, 6),
        "via_sizes_mm": [
            {"drill": diameter / 1e6, "land": land / 1e6, "copper_flashes_all_layers": count}
            for (diameter, land), count in sorted(sizes.items())
        ],
        "plated_round_component_count": len(drill["PTH"]) - len(via_hits) - len(slots),
        "plated_slots": slots,
        "non_plated_round_counts_by_diameter_mm": dict(sorted(Counter(
            diameter / 1e6 for _, diameter, _ in drill["NPTH"]).items())),
        "SW1_pad2_registration": {
            "via_uuid": switch["via_uuid"],
            "nominal_native_mask_gap_mm": round(gap, 6),
            "published_drill_position_tolerance_mm": .075,
            "published_maximum_positive_hole_diameter_tolerance_mm": .13,
            "gap_after_drill_position_and_size_screen_mm": round(gap - drill_budget, 6),
            "status": "drill-tolerance-screen-passed-mask-registration-open",
        },
        "production_approved": False,
        "capabilities": "https://jlcpcb.com/capabilities/Capabilities",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "delivery/YETI60-E73/01-pcb" / ZIP_NAME)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check(args.archive)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], report["through_via_count"], "mechanical through vias")


if __name__ == "__main__":
    main()
