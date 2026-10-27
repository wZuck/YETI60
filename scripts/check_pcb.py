#!/usr/bin/env python3
"""Run full DRC on scratch copies of every source PCB; retain reviewable reports."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    cli = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    report_dir = ROOT / "docs/audit/drc"
    report_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    sources = sorted((ROOT / "EC60/PCB").rglob("*.kicad_pcb"))
    if not sources:
        raise ValueError("No PCB files found")
    for source in sources:
        with tempfile.TemporaryDirectory(prefix="yaeckb-drc-") as folder:
            work = Path(folder)
            for pattern in ("*.kicad_pcb", "*.kicad_pro", "*.kicad_sch"):
                for path in source.parent.glob(pattern):
                    shutil.copyfile(path, work / path.name)
            report_path = report_dir / (source.stem + ".json")
            result = subprocess.run([cli, "pcb", "drc", "--refill-zones", "--all-track-errors",
                                     "--severity-all", "--format", "json", "-o", str(report_path),
                                     str(work / source.name)], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            report = json.loads(report_path.read_text())
            counts = Counter(v["severity"] + ":" + v["type"] for v in report["violations"])
            summaries.append({"source": str(source.relative_to(ROOT)),
                              "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                              "drc": dict(sorted(counts.items())),
                              "unconnected": len(report["unconnected_items"]),
                              "schematic_parity_checked": False,
                              "report": str(report_path.relative_to(ROOT))})
    blocked = any(any(k.startswith("error:") for k in s["drc"]) or s["unconnected"] for s in summaries)
    summary = {"status": "fabrication-blocked-by-DRC" if blocked else "DRC-passed-other-gates-unverified",
               "boards": summaries,
               "limitations": ["these are upstream boards, not the final BLE PCB",
                               "DRC is not assembly, component-rating or Gerber-parity proof"]}
    (ROOT / "docs/audit/pcb-drc.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if blocked:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
