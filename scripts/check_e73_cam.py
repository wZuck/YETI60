#!/usr/bin/env python3
"""Match the KiCad 10 X2 and Excellon fabrication ZIP to the native E73 PCB."""
from collections import Counter, defaultdict
import argparse
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import re
from zipfile import ZipFile

import pcbnew as pcb

from check_e73_copper_lands import check_copper_lands

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "hardware/e73-hhkb-corner"
STEM = "EC60-nRF52840"
BOARD = BASE / f"{STEM}.kicad_pcb"
PROFILE = ROOT / "mechanical/pcb-fabrication-spec.json"
POWER = BASE / "audit/power-process.json"
ZIP_NAME = "YETI60-E73-gerbers-REVIEW.zip"
NETLIST_NAME = f"{STEM}.d356"
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
GERBER_COORDINATE = re.compile(GERBER_POINT + r"(?:I(-?\d+)J(-?\d+))?D(0[123])\*")
ARC_ENDPOINT_TOLERANCE_NM = 100
# Excellon uses three decimal places. Retain both nearest positions on exact ties.
DRILL_ROUNDING_NM = 500
# The KiCad IPC header selects CUST 0, with coordinates in 0.0001 inches.
IPC_UNIT_NM = 2540
IPC_ROUNDING_NM = IPC_UNIT_NM // 2


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plot_point(vector):
    return (vector.x, -vector.y)


def check_ipc(data, board, vias):
    """Compare each KiCad IPC-D-356A test site with the original native board."""
    lines = data.decode("ascii").splitlines()
    assert all(len(line) == 80 for line in lines)
    assert lines[-1].strip() == "999"
    headers = [line.rstrip() for line in lines if line.startswith("P  ")]
    assert {"P  UNITS CUST 0", "P  VER   IPC-D-356A", "P  IMAGE PRIMARY"} <= set(headers)
    aliases = {}
    for line in headers:
        if line.startswith("P  NNAME"):
            alias, net = line.removeprefix("P  NNAME").split(maxsplit=1)
            assert alias not in aliases
            aliases[alias] = net

    native = defaultdict(list)
    for via in vias:
        native["317", "VIA", "", 0].append(
            (plot_point(via.GetPosition()), via.GetNetname(), via.GetDrillValue()))
    for footprint in board.GetFootprints():
        ref = footprint.GetReference()
        for pad in footprint.Pads():
            drill = pad.GetDrillSize()
            pin = pad.GetNumber()
            net = pad.GetNetname()
            point = plot_point(pad.GetPosition())
            if drill.x or drill.y:
                kind = {pcb.PAD_ATTRIB_PTH: "317", pcb.PAD_ATTRIB_NPTH: "367"}[pad.GetAttribute()]
                native[kind, ref, pin, 0].append((point, net, min(drill.x, drill.y)))
            else:
                sides = [access for layer, access in ((pcb.F_Cu, 1), (pcb.B_Cu, 4))
                         if pad.IsOnLayer(layer)]
                assert sides or (not pin and not net), ("Missing IPC access policy", ref, pin)
                for access in sides:
                    native["327", ref, pin, access].append((point, net, 0))
    names = {net for sites in native.values() for _, net, _ in sites if net}
    assert len({name.casefold() for name in names}) == len(names), "IPC net name case collision"
    assert "n/c" not in {name.casefold() for name in names}

    matches = Counter()
    worst_axis_error = 0
    seen_aliases = set()
    for line in lines[:-1]:
        if line.startswith("P  "):
            continue
        kind = line[:3]
        assert kind in {"317", "327", "367"} and (line[38], line[41], line[49]) == ("A", "X", "Y")
        key = (kind, line[20:26].strip(), line[27:31].strip(), int(line[39:41]))
        point = (int(line[42:49]) * IPC_UNIT_NM, int(line[50:57]) * IPC_UNIT_NM)
        tag = line[3:17].strip()
        net = "" if tag == "N/C" else aliases.get(tag, tag)
        if tag in aliases:
            seen_aliases.add(tag)
        candidates = []
        for site in native[key]:
            expected_point, expected_net, expected_drill = site
            error = max(abs(a - b) for a, b in zip(point, expected_point))
            if error <= IPC_ROUNDING_NM and net.casefold() == expected_net.casefold():
                candidates.append((site, error, expected_drill))
        assert len(candidates) == 1, ("IPC site or net mismatch", key, point, net)
        site, error, expected_drill = candidates[0]
        if expected_drill:
            assert line[32] == "D" and line[37] == ("U" if kind == "367" else "P")
            assert abs(int(line[33:37]) * IPC_UNIT_NM - expected_drill) <= IPC_ROUNDING_NM, ("IPC drill mismatch", key)
        else:
            assert line[32] == line[37] == " ", ("Unexpected IPC drill", key)
        native[key].remove(site)
        worst_axis_error = max(worst_axis_error, error)
        matches["vias" if key[1] == "VIA" else kind] += 1
    assert not any(native.values()), "IPC is missing one or more native test records"
    assert seen_aliases == set(aliases)
    return {
        "format": "IPC-D-356A",
        "file": NETLIST_NAME,
        "sha256": hashlib.sha256(data).hexdigest(),
        "records_checked": sum(matches.values()),
        "through_vias_checked": matches["vias"],
        "SMD_pad_records_checked": matches["327"],
        "plated_component_records_checked": matches["317"],
        "nonplated_hole_records_checked": matches["367"],
        "native_named_nets_checked": len(names),
        "long_net_aliases": len(aliases),
        "coordinate_frame": "KiCad absolute X and negative Y, same as the Gerbers",
        "coordinate_unit_mm": IPC_UNIT_NM / 1e6,
        "maximum_coordinate_axis_error_mm": worst_axis_error / 1e6,
        "physical_verification": False,
    }


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


def copper_routing(data, board, layer, vias):
    """Match X2 conductor strokes and via lands, including their net attributes."""
    apertures = {}
    aperture_role = active = net = previous = None
    interpolation = "01"
    inside_region = False
    flashes, lines = Counter(), Counter()
    arcs = []
    for line in data.splitlines():
        if line.startswith("%TA.AperFunction,"):
            aperture_role = line.removeprefix("%TA.AperFunction,").removesuffix("*%")
        elif line == "%TD*%":
            aperture_role = net = None
        elif line == "%TD.AperFunction*%":
            aperture_role = None
        elif line.startswith("%TO.N,"):
            net = line.removeprefix("%TO.N,").removesuffix("*%")
        elif line.startswith("%ADD") and aperture_role in {"ViaPad", "Conductor"}:
            definition = re.fullmatch(r"%ADD(\d+)C,(\d+\.\d+)\*%", line)
            assert definition, ("Noncircular track or via aperture", line)
            apertures[definition[1]] = (aperture_role, round(float(definition[2]) * 1e6))
        elif selection := re.fullmatch(r"D(\d+)\*", line):
            active = apertures.get(selection[1])
        elif line in {"G01*", "G02*", "G03*"}:
            interpolation = line[1:3]
        elif line in {"G36*", "G37*"}:
            assert inside_region != (line == "G36*")
            inside_region = line == "G36*"
        elif line.startswith("%LP"):
            assert line == "%LPD*%", "Copper routing readback requires dark artwork"
        elif line.startswith("X"):
            hit = GERBER_COORDINATE.fullmatch(line)
            assert hit, ("Unexpected Gerber coordinate", line)
            point = (int(hit[1]), int(hit[2]))
            if active and not inside_region and hit[5] != "02":
                role, width = active
                assert net is not None, ("Copper routing has no net attribute", line)
                if role == "ViaPad":
                    assert hit[5] == "03" and hit[3] is None, ("Unexpected via command", line)
                    flashes[point, width, net] += 1
                else:
                    assert hit[5] == "01" and previous is not None
                    if interpolation == "01":
                        assert hit[3] is None
                        lines[(net, width, *sorted((previous, point)))] += 1
                    else:
                        assert hit[3] is not None
                        center = (previous[0] + int(hit[3]), previous[1] + int(hit[4]))
                        start, end = (point, previous) if interpolation == "02" else (previous, point)
                        arcs.append((net, width, start, end, center))
            previous = point
    assert not inside_region

    expected_flashes = Counter((plot_point(v.GetPosition()), v.GetWidth(layer), v.GetNetname())
                               for v in vias)
    assert flashes == expected_flashes, "Gerber via land or net mismatch"
    expected_lines = Counter()
    arc_groups = defaultdict(list)
    for track in board.GetTracks():
        if track.GetLayer() != layer or isinstance(track, pcb.PCB_VIA):
            continue
        endpoints = sorted((plot_point(track.GetStart()), plot_point(track.GetEnd())))
        key = (track.GetNetname(), track.GetWidth())
        if isinstance(track, pcb.PCB_ARC):
            arc_groups[key].append((endpoints, plot_point(track.GetCenter()), plot_point(track.GetMid())))
        else:
            expected_lines[(*key, *endpoints)] += 1
    assert lines == expected_lines, f"Gerber straight trace mismatch on {board.GetLayerName(layer)}"
    worst_endpoint = 0.0
    for net, width, start, end, center in arcs:
        group = arc_groups[net, width]
        candidates = []
        for arc in group:
            endpoints, native_center, _ = arc
            error = max(math.dist(gerber, native) for gerber, native in zip(sorted((start, end)), endpoints))
            if native_center == center and error <= ARC_ENDPOINT_TOLERANCE_NM:
                candidates.append((arc, error))
        assert len(candidates) == 1, ("Gerber arc geometry mismatch", net, start, end)
        arc, error = candidates[0]
        mid = arc[2]
        sa, ea, ma = [math.atan2(y - center[1], x - center[0]) for x, y in (start, end, mid)]
        assert 0 < (ma - sa) % math.tau < (ea - sa) % math.tau, ("Gerber arc sweep mismatch", net)
        group.remove(arc)
        worst_endpoint = max(worst_endpoint, error)
    assert not any(arc_groups.values()), f"Missing Gerber arcs on {board.GetLayerName(layer)}"
    return {
        "straight_traces": sum(lines.values()),
        "arc_traces": len(arcs),
        "via_lands": sum(flashes.values()),
        "maximum_arc_endpoint_delta_mm": round(worst_endpoint / 1e6, 9),
    }


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
        names.update(("drill-report.txt", NETLIST_NAME))
        assert set(bundle.namelist()) == names and len(bundle.namelist()) == len(names)
        files = {suffix: bundle.read(f"{STEM}-{suffix}").decode("ascii") for suffix in LAYERS}
        job = json.loads(bundle.read(f"{STEM}-job.gbrjob"))
        drill = {role: parse_drills(bundle.read(f"{STEM}-{role}.drl").decode("ascii"), role)
                 for role in expected}
        ipc = check_ipc(bundle.read(NETLIST_NAME), board, vias)
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
    copper_files = {layer: files[suffix] for suffix, layer in zip(LAYERS, COPPER)}
    routing = {board.GetLayerName(layer): copper_routing(artwork, board, layer, vias)
               for layer, artwork in copper_files.items()}
    lands = check_copper_lands(board, copper_files)
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
        "source_sha256": {str(p.relative_to(ROOT)): sha(p)
                          for p in (BOARD, PROFILE, POWER, Path(__file__),
                                    ROOT / "scripts/check_e73_copper_lands.py")},
        "archive_sha256": sha(archive),
        "electrical_test_netlist": ipc,
        "copper_routing": routing,
        "copper_lands": lands,
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
