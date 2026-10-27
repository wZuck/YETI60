#!/usr/bin/env python3
"""Check the baseline PCB port against explicit rear/front key datums."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    constraint_path = ROOT / "design-constraints.json"
    constraints = json.loads(constraint_path.read_text())
    rules = constraints["external_usb_c"]
    if rules["required_face"] != "rear" or rules["front_port_allowed"]:
        raise ValueError("Type-C must be on the rear; front ports are forbidden")
    if rules["connector_path"] != "rear-daughterboard-to-J1" or rules["onboard_USB1_external_port_allowed"]:
        raise ValueError("The external connector must use the rear daughterboard, not onboard USB1")
    if constraints["wireless_controller"] != "nRF52840":
        raise ValueError("The approved radio controller baseline is nRF52840")
    metadata = json.loads((ROOT / "docs/audit/pcb-metadata.json").read_text())
    board = next(b for b in metadata if b["source"].endswith("/EC60.kicad_pcb"))
    if board["source_sha256"] != hashlib.sha256((ROOT / board["source"]).read_bytes()).hexdigest():
        raise ValueError("Stale PCB metadata")
    parts = {p["reference"]: p for p in board["footprints"]}
    rear = [parts[r]["xy_mm"][1] for r in rules["baseline_rear_row_references"]]
    front = [parts[r]["xy_mm"][1] for r in rules["baseline_front_row_references"]]
    port = parts[rules["baseline_port_reference"]]
    if not max(rear) < min(front):
        raise ValueError("Rear/front datum order is invalid")
    if not port["xy_mm"][1] < min(rear):
        raise ValueError("USB-C center is not behind the rear key row")
    report = {"status": "baseline-PCB-rear-center-checked-final-assembly-unverified",
              "constraints_sha256": hashlib.sha256(constraint_path.read_bytes()).hexdigest(),
              "pcb_source_sha256": board["source_sha256"],
              "rear_key_y_mm": rear, "front_key_y_mm": front,
              "port_reference": port["reference"], "port_center_mm": port["xy_mm"],
              "port_rotation_degrees": port["rotation_degrees"],
              "external_connector_path": rules["connector_path"],
              "baseline_USB1_is_final_external_connector": False,
              "unverified": ["final BLE PCB or USB daughterboard port position",
                             "connector mouth direction and case opening alignment",
                             "plug overmould/cable clearance and strain relief",
                             "assembled STEP/STL rear-face location"]}
    (ROOT / "docs/audit/typec-location.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
