#!/usr/bin/env python3
"""Reproduce the ordinary-process aperture repair on an isolated CORNER-06 copy."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pcbnew as pcb

from e73_corner_charge_repair import copper
from kicad_sexpr import child, children, dumps, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "hardware/e73-hhkb-corner"
WORK = ROOT / ".assembly-work/e73-corner/aperture-replay"
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
BASELINE = "3fe9b9ce5fae01da567351a1b676287ba82e2f354f8d52c5045d09e781c0dac7"
BASELINE_COMMIT = "e94fe4ee2e16914f796e27543dccfbd14cb4bbc7"
CHECKED_PCB = "b648911a5f099118ff034f7e53112beef2d1d6a609550604f88e4c478d20b08e"
BOARD = BASE / "EC60-nRF52840.kicad_pcb"
REFS = {"C42", "SW1", "U5", "U6"}
D2_VIA = "2fbc09c8-3af4-4563-8086-fe4bd03b626d"
D2_TRACK = "4631e8d9-6ecf-41ff-af6a-6b7201efc21b"
D2_CENTER_MM = [315.51642, 122.07]
CAM_COMMAND = ["uv", "run", "--offline", "--python", "3.14.7", "--with", "gerbonara==1.6.3",
               "--with", "shapely==2.1.2", "python", str(ROOT / "scripts/check_e73_apertures.py")]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def footprints(tree):
    return {next(p[2] for p in children(fp, "property") if p[1] == "Reference"): fp
            for fp in children(tree, "footprint")}


def split_pads(ref, fp):
    # Keep every copper land at its original size and datum. C42 moves only
    # the inner edge of each opening. SW1 moves only its outer Y edges.
    for pad in children(fp, "pad"):
        if pad[1] not in {"1", "2"}:
            continue
        aperture = deepcopy(pad)
        aperture[1] = ""
        aperture.remove(child(aperture, "net"))
        child(pad, "layers")[1:] = ["B.Cu"]
        child(aperture, "layers")[1:] = ["B.Mask", "B.Paste"]
        at, size = child(aperture, "at"), child(aperture, "size")
        if ref == "C42":
            at[1] = -1 if float(at[1]) < 0 else 1
            size[1] = .8
        else:
            assert abs(float(at[2])) == .85
            at[2] = -.82 if float(at[2]) < 0 else .82
            size[2] = .94
        child(aperture, "uuid")[1] = str(uuid5(NAMESPACE_URL, f"yeti60/{ref}/aperture/{pad[1]}/{at[1]}/{at[2]}"))
        fp.append(aperture)


def thermal_windows(ref, fp):
    xmin, xmax, edge_x, edge_y = (-.73, .03, .89, .89) if ref == "U5" else (-.38, .38, .65, 1.05)
    mask = [q for q in children(fp, "fp_rect") if child(q, "layer")[1] == "B.Mask"]
    assert len(mask) == 4
    rects = [(-edge_x, -edge_y, xmin, edge_y), (xmin, -edge_y, xmax, -.38),
             (xmin, .38, xmax, edge_y), (xmax, -edge_y, edge_x, edge_y)]
    for q, (x, y, X, Y) in zip(mask, rects):
        child(q, "start")[1:] = [x, y]
        child(q, "end")[1:] = [X, Y]
    paste = [q for q in children(fp, "pad") if q[1] == "" and child(q, "layers")[1:] == ["B.Paste"]]
    assert len(paste) == 4
    for q in paste:
        x, y = map(float, child(q, "at")[1:])
        if ref == "U6" and x > 0:
            fp.remove(q)
            continue
        if ref == "U6":
            cx, cy, w, h = 0, .685, 1.10, .59
        elif x < 0:
            cx, cy, w, h = -.42, .605, .80, .43
        else:
            cx, cy, w, h = .485, .46, .67, .72
        child(q, "at")[1:] = [cx, cy if y > 0 else -cy]
        child(q, "size")[1:] = [w, h]
        child(q, "roundrect_rratio")[1] = .04 / min(w, h)


def apply(path):
    assert sha(path) == BASELINE, "The repair starts from the checked CORNER-06 PCB"
    tree = loads(path.read_text())
    source_pads = electrical_pads(tree)
    items = copper(tree)
    before = deepcopy(items)
    via, track = items[D2_VIA], items[D2_TRACK]
    assert child(via, "net")[1] == child(track, "net")[1] == "GND"
    assert child(via, "at")[1:] == child(track, "start")[1:]
    child(via, "at")[1:] = child(track, "start")[1:] = D2_CENTER_MM.copy()
    child(via, "size")[1], child(via, "drill")[1] = .60, .30
    parts = footprints(tree)
    for ref in ("C42", "SW1"):
        split_pads(ref, parts[ref])
    for ref in ("U5", "U6"):
        thermal_windows(ref, parts[ref])
    path.write_text(dumps(tree) + "\n")
    board = pcb.LoadBoard(str(path))
    board.BuildConnectivity()
    assert pcb.ZONE_FILLER(board).Fill(board.Zones())
    assert pcb.SaveBoard(str(path), board)
    assert sha(path) == CHECKED_PCB, "The replay differs from the audited aperture repair"
    result = loads(path.read_text())
    assert electrical_pads(result) == source_pads
    after = copper(result)
    assert set(before) == set(after)
    assert {uid for uid in before if before[uid] != after[uid]} == {D2_VIA, D2_TRACK}
    plugin = pcb.PCB_IO_MGR.FindPlugin(pcb.PCB_IO_MGR.KICAD_SEXP)
    for fp in board.GetFootprints():
        if fp.GetReference() not in REFS:
            continue
        library = pcb.FOOTPRINT(fp)
        library.Flip(library.GetPosition(), pcb.FLIP_DIRECTION_TOP_BOTTOM)
        library.SetPosition(pcb.VECTOR2I(0, 0))
        library.SetOrientationDegrees(0)
        plugin.FootprintSave(str(path.parent / "YAECKB.pretty"), library)
    return [{"uuid": key, "net": "GND"} for key in (D2_VIA, D2_TRACK)]


def electrical_pads(tree):
    result = {}
    for ref, fp in footprints(tree).items():
        landed = []
        for pad in children(fp, "pad"):
            cu = [layer for layer in child(pad, "layers")[1:] if layer.endswith(".Cu")]
            if cu:
                geometry = deepcopy(pad)
                child(geometry, "layers")[1:] = cu
                landed.append(dumps(geometry))
        # Sort the signatures because KiCad orders pads again when saving.
        result[ref] = (dumps(child(fp, "at")), tuple(sorted(landed)))
    return result


def command(*args):
    return subprocess.run([CLI, "pcb", *map(str, args)], check=True, capture_output=True)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    assert not (WORK / "YAECKB.pretty").is_symlink(), "The trial needs a private footprint library"
    for source in sorted(BASE.iterdir()):
        if source.suffix in {".kicad_pro", ".kicad_sch", ".kicad_sym"} or source.name in {"fp-lib-table", "sym-lib-table"}:
            shutil.copyfile(source, WORK / source.name)
    shutil.copytree(BASE / "YAECKB.pretty", WORK / "YAECKB.pretty", dirs_exist_ok=True)
    trial = WORK / BOARD.name
    trial.write_bytes(subprocess.check_output(
        ["git", "show", f"{BASELINE_COMMIT}:{BOARD.relative_to(ROOT)}"], cwd=ROOT))
    apply(trial)
    drc_path = WORK / "drc.json"
    config_path = trial.with_suffix(".kicad_pro")
    config = json.loads(config_path.read_text())
    rules = config["board"]["design_settings"]["rule_severities"]
    for key in rules:
        if rules[key] == "ignore":
            rules[key] = "warning"
    config_path.write_text(json.dumps(config))
    command("drc", "--all-track-errors", "--schematic-parity", "--refill-zones", "--severity-all",
            "--format", "json", "-o", drc_path, trial)
    drc = json.loads(drc_path.read_text())
    assert not [v for v in drc["violations"] if v["severity"] == "error"], drc_path
    assert not drc["unconnected_items"] and not drc["schematic_parity"]
    warnings = Counter(v["type"] for v in drc["violations"])
    assert set(warnings) <= {"missing_courtyard"}, warnings

    artwork = WORK / "cam"
    artwork.mkdir(exist_ok=True)
    command("export", "gerbers", "--check-zones", "--layers", "F.Mask,B.Mask,F.Paste,B.Paste", "-o", artwork, trial)
    command("export", "drill", "--format", "excellon", "--excellon-units", "mm", "--excellon-separate-th", "-o", artwork, trial)
    archive = WORK / "aperture-trial.zip"
    with ZipFile(archive, "w") as bundle:
        for p in sorted(artwork.iterdir()):
            info = ZipInfo(p.name, (2000, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            data = re.sub(r"20\d\d-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:[.+Z0-9:-]*)",
                          "2000-01-01T00:00:00", p.read_text())
            bundle.writestr(info, data)
    temp_report = WORK / "aperture-result.json"
    subprocess.run([*CAM_COMMAND, "--board", str(trial), "--archive", str(archive),
                    "--output", str(temp_report)], check=True)
    proof = json.loads(temp_report.read_text())
    assert proof["vias"] == 852
    assert all(layer["min_nominal_gap_mm"] >= .229 for layer in proof["layers"].values())
    assert all(not layer["holes_below_conservative_reserve"] for layer in proof["layers"].values())
    for pad in proof["thermal_lands"].values():
        assert .50 <= pad["paste_fraction"] <= .70
        assert pad["paste_fraction"] == pad["paste_on_open_mask_fraction"]
        assert pad["minimum_stencil_web_mm"] >= .15 and pad["minimum_area_ratio_at_0p125mm"] > .66
    source_paths = [Path(__file__), ROOT / "scripts/check_e73_apertures.py",
                    ROOT / "scripts/kicad_sexpr.py", ROOT / "scripts/e73_corner_charge_repair.py",
                    BOARD.with_suffix(".kicad_pro"), BASE / "fp-lib-table", BASE / "sym-lib-table",
                    *sorted(BASE.glob("*.kicad_sch")), BASE / "YAECKB.kicad_sym"]
    result = dict(status="ordinary-process-aperture-trial-passed-digital-checks",
                  baseline_commit=BASELINE_COMMIT, baseline_PCB_sha256=BASELINE,
                  selected_for_order=False, physical_verification=False,
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in source_paths},
                  candidate_PCB_sha256=proof["source_PCB_sha256"],
                  candidate_aperture_archive_sha256=proof["archive_sha256"],
                  native_DRC_errors=0, unconnected_items=0, schematic_parity_differences=0,
                  native_DRC_warnings=dict(warnings),
                  copper_lands_unchanged=True, changed_track_or_via_UUIDs=[D2_VIA, D2_TRACK],
                  modified_footprints=sorted(REFS), layers=proof["layers"], thermal_lands=proof["thermal_lands"])
    (WORK / "aperture-trial.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
