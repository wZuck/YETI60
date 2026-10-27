#!/usr/bin/env python3
"""Cross-check the upstream BOM/CPL against PCB source, never approve fabrication."""
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ROOT / "EC60/Production/EC60_PCB"
    metadata = json.loads((ROOT / "docs/audit/pcb-metadata.json").read_text())
    board = next(b for b in metadata if b["source"].endswith("/EC60.kicad_pcb"))
    if board.get("source_sha256") != digest(ROOT / board["source"]):
        raise ValueError("PCB metadata is stale; rerun extract_pcb_metadata.py first")
    parts = {p["reference"]: p for p in board["footprints"]}
    origin_x, origin_y = board["aux_origin_mm"]
    with (source / "POS-EC60.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames, cpl = reader.fieldnames, list(reader)
    with (source / "BOM-EC60.csv").open(newline="") as stream:
        bom = list(csv.DictReader(stream))
    expected_refs = [ref.strip() for row in bom for ref in row["Designator"].split(",")]
    if len(set(expected_refs)) != len(expected_refs):
        raise ValueError("Duplicate reference in BOM")
    for row in bom:
        for ref in row["Designator"].split(","):
            part = parts[ref.strip()]
            if part["value"] != row["Comment"] or part["footprint"] != row["Footprint"]:
                raise ValueError(f"BOM/PCB mismatch: {ref}")

    def matches(row, part):
        distance = math.hypot(part["xy_mm"][0] - origin_x - float(row["Mid X"]),
                              -(part["xy_mm"][1] - origin_y) - float(row["Mid Y"]))
        angle = (part["rotation_degrees"] - float(row["Rotation"]) + 180) % 360 - 180
        layer = "bottom" if part["layer"] == "B.Cu" else "top"
        return (part["value"] == row["Val"] and part["footprint"] == row["Package"]
                and distance <= 0.002 and abs(angle) <= 0.001 and layer == row["Layer"])

    corrections = []
    corrected = []
    for row in cpl:
        candidates = [p for p in parts.values() if matches(row, p)]
        if len(candidates) != 1:
            raise ValueError(f"No unique physical match for CPL row: {row}")
        match = candidates[0]
        if row["Designator"] != match["reference"]:
            corrections.append({"original_reference": row["Designator"],
                                "correct_reference": match["reference"], "value": row["Val"],
                                "evidence": "unique match of value, package, XY, rotation and side"})
        corrected.append({**row, "Designator": match["reference"]})
    corrected_refs = [r["Designator"] for r in corrected]
    if len(set(corrected_refs)) != len(corrected_refs) or set(corrected_refs) != set(expected_refs):
        raise ValueError("Corrected CPL does not cover BOM references exactly once")

    destination = ROOT / "hardware/reference-production"
    destination.mkdir(parents=True, exist_ok=True)
    cpl_path = destination / "POS-EC60.corrected.csv"
    with cpl_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(corrected)
    archive_path = source / "GERBER-EC60.zip"
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupt upstream Gerber archive")
        archive_members = archive.namelist()
        if len(archive_members) != len(set(archive_members)):
            raise ValueError("Duplicate Gerber archive paths")
    duplicates = [r for r, count in Counter(row["Designator"] for row in cpl).items() if count > 1]
    report = {"status": "upstream-CPL-defect-confirmed-reference-copy-corrected-not-fabrication-approved",
              "bom_references": len(expected_refs), "cpl_rows": len(cpl),
              "original_CPL_duplicates": duplicates, "corrections": corrections,
              "corrected_CPL_BOM_coverage": "exactly-once",
              "position_tolerance_mm": 0.002, "rotation_tolerance_degrees": 0.001,
              "gerber_zip_crc": "passed", "gerber_members": archive_members,
              "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in
                                (source / "BOM-EC60.csv", source / "POS-EC60.csv", archive_path,
                                 ROOT / "EC60/PCB/EC60_PCB/EC60.kicad_pcb", cpl_path)},
              "unverified": ["Gerber geometry vs PCB source", "LCSC component ordering and electrical ratings",
                             "board DRC findings and final BLE production files"]}
    (ROOT / "docs/audit/manufacturing-reference.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
