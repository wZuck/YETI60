#!/usr/bin/env python3
"""Run software/CAD checks and report unfinished production gates explicitly.

python3 scripts/run_audit.py
KiCad CLI/Python, clang and uv are required. Runtime dependencies are pinned.
A failed upstream DRC is a blocked production gate, not a reason to skip CAD.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "docs/audit"


def main():
    if not __debug__:
        raise SystemExit("Run without -O: audit checks must not be optimized away")
    REPORTS.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
    kicad_python = os.environ.get("KICAD_PYTHON", "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3")
    cad = [uv, "run", "--with-requirements", str(ROOT / "requirements-audit.txt"), "python"]
    stages = [
        ("single-nrf-connectivity", [sys.executable, "scripts/check_single_nrf.py"], []),
        ("single-nrf-native-pcb", [kicad_python, "scripts/audit_single_nrf.py"], ["single-nrf-connectivity"]),
        ("pcb-metadata", [kicad_python, "scripts/extract_pcb_metadata.py"], []),
        ("generated-interface", [sys.executable, "scripts/check_generated_interface.py"], []),
        ("interface-erc", [sys.executable, "scripts/check_ble_interface.py"], ["generated-interface"]),
        ("scanner-sanitizers", [sys.executable, "scripts/check_firmware.py", "--output", "docs/audit/firmware.json"], []),
        ("plate-dxf", cad + ["scripts/check_plate.py"], ["pcb-metadata"]),
        ("step-solids", cad + ["scripts/check_mechanical.py"], ["plate-dxf"]),
        ("case-registration-rear-port", cad + ["scripts/check_case_assembly.py"], ["pcb-metadata", "step-solids"]),
        ("rear-port-datums", [sys.executable, "scripts/check_typec_location.py"], ["pcb-metadata"]),
        ("bom-cpl", [sys.executable, "scripts/check_manufacturing_reference.py"], ["pcb-metadata"]),
        ("gerber-profile-drills", cad + ["scripts/check_gerber_reference.py"], []),
        ("upstream-pcb-drc", [sys.executable, "scripts/check_pcb.py"], []),
    ]
    results = []
    states = {}
    for name, command, dependencies in stages:
        if any(states[d] != "passed" for d in dependencies):
            record = {"stage": name, "state": "skipped-dependency-failed"}
        else:
            try:
                process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                record = {"stage": name, "state": "passed" if process.returncode == 0 else "failed",
                          "exit_code": process.returncode}
                if process.returncode:
                    record["output_tail"] = (process.stdout + process.stderr)[-4000:]
            except OSError as error:
                record = {"stage": name, "state": "failed", "error": str(error)}
        states[name] = record["state"]
        results.append(record)
        print(name + ": " + record["state"], flush=True)

    # Hash coverage is a source inventory, not evidence of semantic review.
    command = ["rg", "--files", "--hidden", "-g", "!.git", "-g", "!docs/audit/**"]
    filenames = subprocess.check_output(command, cwd=ROOT, text=True).splitlines()
    inventory = []
    for name in sorted(filenames):
        path = ROOT / name
        inventory.append({"path": name, "bytes": path.stat().st_size,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "coverage": "inventoried-not-automatically-approved"})
    inventory_path = REPORTS / "source-inventory.json"
    inventory_path.write_text(json.dumps({"files": inventory,
                                         "excluded": "Git internals, ignored local state, and audit outputs to avoid self-hashing",
                                         "semantic_review_complete": False}, ensure_ascii=False, indent=2) + "\n")
    pending = [
        "single nRF52840 target build and on-device EC scanning/USB/BLE behaviour",
        "signal interference simulation after single-MCU PCB design completion",
        "rear USB daughterboard, actual connector/plug and cable assembled fit",
        "resin-ready insert geometry, validated print mesh and full mechanical tolerance stack",
        "PCB/plate/switch/gasket/battery/module/antenna/cable complete assembly",
        "copper/mask/paste Gerber parity and procurement ratings",
        "physical EC calibration, charging, runtime, wake and enclosed RF tests",
    ]
    if states.get("single-nrf-native-pcb") != "passed":
        pending.insert(0, "routed BLE PCB and complete nRF52840/power/charge circuit with final ERC/DRC")
    outcome = {"status": "audit-incomplete-production-not-approved", "stages": results,
               "pending_requirements": pending, "production_approved": False,
               "inventory": str(inventory_path.relative_to(ROOT))}
    (REPORTS / "outcome.json").write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n")
    print("Audit reports updated; production remains blocked by unfinished requirements.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
