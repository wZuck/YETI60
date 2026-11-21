#!/usr/bin/env python3
"""Compare a documented 28 AWG wire with the M05 fit and power requirements."""

import hashlib
import json
from math import isclose, pi
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "hardware/e73-hhkb-corner"
AUDIT = BASE / "audit"
BOARD = BASE / "EC60-nRF52840.kicad_pcb"
HARNESS = AUDIT / "m05-harness.json"
POWER = AUDIT / "power-process.json"
FIT_SPEC = ROOT / "hardware/e73-corner-harness-spec.json"
WIRE_DATASHEET = "https://www.cnctech.us/pdfs/10064-XX-1-0500-0XX-1-TS.pdf"
WIRE_CHANGE_NOTICE = "https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/6791/Change%20Notice%20Hook-up-Wire%203-2025.pdf"
JST_DATASHEET = "https://www.jst.com/wp-content/uploads/2025/06/eSH.pdf"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    harness, power, limits = map(read, (HARNESS, POWER, FIT_SPEC))
    board_key = str(BOARD.relative_to(ROOT))
    for report in (harness, power):
        assert report["source_sha256"][board_key] == sha(BOARD)
    wire_od = (0.55, 0.65)
    jst_od = (0.4, 0.8)
    jst_area = (0.032, 0.081)
    copper_area = 7 * pi * (.12 / 2) ** 2
    assert jst_area[0] <= copper_area <= jst_area[1]
    assert jst_od[0] <= wire_od[0] <= wire_od[1] <= jst_od[1]
    assert wire_od[1] <= limits["wire"]["insulation_od_max"]
    seated = harness["trial_variants"][0]["seated_free_lengths_mm"]
    conductors = [
        ("red", "004", ("usb.1", "power.1"), .75),
        ("black", "001", ("usb.4", "power.2"), .75),
        ("white", "002", ("usb.2",), .50),
        ("green", "007", ("usb.3",), .50),
    ]
    purchase = []
    for color, code, uses, order_m in conductors:
        length_mm = sum(seated[key] for key in uses)
        assert length_mm / 1000 < order_m
        purchase.append({"color": color, "MPN": f"10064-28-1-0500-{code}-1-TS",
                         "positions": uses, "combined_free_length_mm": round(length_mm, 3),
                         "suggested_purchase_length_m": order_m})
    power_positions = conductors[0][2] + conductors[1][2]
    loop_mm = sum(seated[key] for key in power_positions)
    ideal = harness["charging_path_sensitivity"]
    assert isclose(loop_mm, ideal["AWG28_wire_length_mm"], abs_tol=1e-9)
    max_wire_20C = loop_mm / 1000 * .239
    pcb_20C = power["charge_headroom"]["positive_PCB_centerline_20C_ohm"]
    assert ideal["copper_temperature_C"] == 60
    combined_60C = (max_wire_20C + pcb_20C) * (1 + .00393 * 40)
    dpm_max = power["charge_headroom"]["BQ24074_VIN_DPM_min_typ_max_V"][-1]
    inputs = (BOARD, HARNESS, POWER, FIT_SPEC, Path(__file__))
    result = {
        "status": "published_wire_dimensions_and_M05_headroom_checked",
        "physical_verification": False,
        "differential_impedance_qualified": False,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in inputs},
        "vendor_references": {"wire_datasheet": WIRE_DATASHEET, "wire_change_notice": WIRE_CHANGE_NOTICE,
                              "JST_SH_datasheet": JST_DATASHEET},
        "wire": {"AWG": 28, "tinned_copper_strands": 7, "nominal_strand_diameter_mm": .12,
                 "insulation": "FEP", "insulation_OD_mm_min_max": wire_od,
                 "nominal_geometric_conductor_section_mm2": copper_area,
                 "manufacturer_maximum_20C_resistance_ohm_per_km": 239},
        "contact": {"MPN": "SSH-003T-P0.2-H", "conductor_area_mm2_min_max": jst_area,
                    "insulation_OD_mm_min_max": jst_od, "fitted_non_pack_contacts": 12,
                    "fitted_non_pack_housings": {"SHR-04V-S": 3, "SHR-02V-S": 1}},
        "purchase_for_USB_and_bridge": purchase,
        "M05_charge_path": {"four_lead_free_length_mm": loop_mm, "max_wire_resistance_20C_ohm": max_wire_20C,
                            "positive_trace_resistance_20C_ohm": pcb_20C,
                            "estimated_combined_60C_ohm": combined_60C,
                            "estimated_included_drop_at_500mA_V": combined_60C / 2,
                            "estimated_current_at_4p75V_input_and_U5_DPM_max_mA": (4.75 - dpm_max) * 1000 / combined_60C,
                            "excluded": ideal["excluded"] + ["wire captured inside the two connectors at each lead"]},
    }
    (AUDIT / "m05-wire-spec.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
