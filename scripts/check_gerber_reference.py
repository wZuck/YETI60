#!/usr/bin/env python3
"""Compare archived profile/drills with fresh plots of the same PCB source.

Run: uv run --with gerbonara python scripts/check_gerber_reference.py
Copper, mask and paste geometries remain separate, unverified gates.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import warnings
import zipfile

from gerbonara import ExcellonFile, GerberFile
from gerbonara.utils import MM

ROOT = Path(__file__).resolve().parents[1]


def geometry(obj):
    convert = lambda value: obj.unit.convert_to(MM, value)
    kind = type(obj).__name__
    if kind == "Flash":
        return kind, [convert(obj.x), convert(obj.y), obj.aperture.unit.convert_to(MM, obj.aperture.diameter)]
    start, end = (convert(obj.x1), convert(obj.y1)), (convert(obj.x2), convert(obj.y2))
    reverse = start > end
    if reverse:
        start, end = end, start
    values = [*start, *end, obj.aperture.unit.convert_to(MM, obj.aperture.diameter)]
    if kind == "Arc":
        values.extend([convert(obj.x1 + obj.cx), convert(obj.y1 + obj.cy)])
        kind += ":cw" if bool(obj.clockwise) != reverse else ":ccw"
    elif kind != "Line":
        raise ValueError(f"Unreviewed geometry type: {kind}")
    if not obj.polarity_dark:
        raise ValueError("Unexpected clear primitive in mechanical profile")
    return kind, values


def compare(original, fresh, tolerance, diameter_tolerance=None):
    old, new = [geometry(o) for o in original.objects], [geometry(o) for o in fresh.objects]
    if len(old) != len(new):
        raise ValueError(f"Object count differs: {len(old)} vs {len(new)}")
    unused = set(range(len(new)))
    max_delta = 0.0
    for kind, values in old:
        candidates = []
        for i in unused:
            new_kind, new_values = new[i]
            if kind != new_kind:
                continue
            differences = [abs(a - b) for a, b in zip(values, new_values)]
            limits = [tolerance] * len(values)
            if diameter_tolerance is not None:
                limits[-1] = diameter_tolerance
            if all(d <= limit for d, limit in zip(differences, limits)):
                candidates.append((max(differences), i))
        if not candidates:
            raise ValueError(f"No matching primitive: {kind} {values}")
        delta, index = min(candidates)
        max_delta = max(max_delta, delta)
        unused.remove(index)
    return {"objects": len(old), "max_coordinate_or_diameter_delta_mm": max_delta,
            "coordinate_tolerance_mm": tolerance, "diameter_tolerance_mm": diameter_tolerance}


def main():
    cli = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    board = ROOT / "EC60/PCB/EC60_PCB/EC60.kicad_pcb"
    archive_path = ROOT / "EC60/Production/EC60_PCB/GERBER-EC60.zip"
    with tempfile.TemporaryDirectory(prefix="yaeckb-gerber-") as folder:
        work = Path(folder)
        for p in board.parent.glob("*.kicad_*"):
            if p.suffix in (".kicad_pcb", ".kicad_pro"):
                shutil.copyfile(p, work / p.name)
        plots = work / "plots"
        def run(*args):
            result = subprocess.run([cli, *map(str, args)], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
        run("pcb", "export", "gerbers", "--layers", "Edge.Cuts", "--use-drill-file-origin",
            "-o", plots, work / board.name)
        run("pcb", "export", "drill", "--drill-origin", "plot", "--excellon-separate-th",
            "--excellon-units", "mm", "-o", plots, work / board.name)
        names = ("EC60-Edge_Cuts.gbr", "EC60-PTH.drl", "EC60-NPTH.drl")
        with zipfile.ZipFile(archive_path) as archive:
            for name in names:
                matches = [p for p in archive.namelist() if Path(p).name == name]
                if len(matches) != 1:
                    raise ValueError(f"Missing or ambiguous archive member: {name}")
                (work / name).write_bytes(archive.read(matches[0]))
        profile = compare(GerberFile.open(work / names[0]),
                          GerberFile.open(next(plots.glob("*Edge_Cuts*"))), 0.00002)
        drill_checks = {}
        with warnings.catch_warnings(record=True) as messages:
            warnings.simplefilter("always")
            for name in names[1:]:
                drill_checks[name] = compare(ExcellonFile.open(work / name),
                                             ExcellonFile.open(plots / name), 0.0026, 0.0013)
        report = {"status": "reference-profile-and-drills-match-within-export-precision-not-fabrication-approved",
                  "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in (board, archive_path)},
                  "gerbonara_version": importlib.metadata.version("gerbonara"),
                  "profile": profile, "drills": drill_checks,
                  "rounding_note": "archive drills use 0.0001 inch increments; fresh drills use 0.001mm increments",
                  "parser_warnings": sorted({str(m.message).split(':', 1)[-1].strip() for m in messages}),
                  "unverified": ["copper, mask, paste and silkscreen geometry",
                                 "DRC defects, parts ratings and BLE revision fabrication files"]}
        path = ROOT / "docs/audit/gerber-reference.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
