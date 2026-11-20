#!/usr/bin/env python3
"""Record the host-port budget separately from the BQ24074 input limit."""

import hashlib
import json
from pathlib import Path

from kicad_sexpr import child, children, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "hardware/e73-hhkb-corner"
BOARD = BASE / "EC60-nRF52840.kicad_pcb"
FIRMWARE = BASE / "firmware"
TARGET = FIRMWARE / "yeti60-target-check.json"
BUILD = FIRMWARE / "manifest.json"
C5 = ROOT / "docs/audit/yeti60-daughterboard.json"
POLICY = ROOT / "firmware/target/src/usb_policy.c"
PORT_CONFIGURED_MA = 500
PORT_UNCONFIGURED_MA = 100
# Planning allocations for the combined port budget. They are acceptance
# targets to measure, since the installed board does not have a bound for them.
OUT_ALLOWANCE_MA = 40
CHARGER_HOUSEKEEPING_ALLOWANCE_MA = 2
BYPASS_ALLOWANCE_MA = 10


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def pad_nets(part):
    return {pad[1]: child(pad, "net")[1] for pad in children(part, "pad")
            if child(pad, "net")}


def value(part):
    return next(item[2] for item in children(part, "property") if item[1] == "Value")


def charge_corner(resistance_ohm):
    current_min = 1000 * 797 / (resistance_ohm * 1.01)
    current_typ = 1000 * 890 / resistance_ohm
    current_max = 1000 * 975 / (resistance_ohm * .99)
    port_planning_max = (current_max + OUT_ALLOWANCE_MA +
                         CHARGER_HOUSEKEEPING_ALLOWANCE_MA + BYPASS_ALLOWANCE_MA)
    return {
        "R40_ohm": resistance_ohm,
        "programmed_charge_min_typ_max_mA": [round(i, 4) for i in (current_min, current_typ, current_max)],
        "estimated_port_mA_at_charge_tolerance_max": round(port_planning_max, 4),
        "margin_to_500_mA_in_planning_case": round(PORT_CONFIGURED_MA - port_planning_max, 4),
        "fast_charge_equivalent_1600mAh_hours_at_typical_setting": round(1600 / current_typ, 4),
    }


def main():
    parts = {item[2]: part for part in children(loads(BOARD.read_text()), "footprint")
             for item in children(part, "property") if item[1] == "Reference"}
    expected = {
        "F1": {"1": "USB_5V", "2": "VBUS"},
        "U1": {"27": "USB_5V"},
        "U5": {"12": "ILIM_SET", "13": "USB_5V", "16": "ICHG_SET", "10": "VSYS"},
        "C32": {"1": "USB_5V", "2": "GND"},
        "C40": {"1": "USB_5V", "2": "GND"},
        "R40": {"1": "ICHG_SET", "2": "GND"},
        "R41": {"1": "ILIM_SET", "2": "GND"},
    }
    for ref, assignments in expected.items():
        actual = pad_nets(parts[ref])
        assert all(actual[pad] == net for pad, net in assignments.items()), ("Port path changed", ref)
    assert value(parts["R40"]) == "2.21k/1%" and value(parts["R41"]) == "7.50k/1%"
    assert value(parts["C32"]) == "4.7u/16V" and value(parts["C40"]) == "2.2u/25V"
    firmware = read(BUILD)
    assert firmware["source_PCB_sha256"] == sha(BOARD)
    for path in (TARGET, POLICY):
        rel = str(path.relative_to(ROOT))
        assert sha(path) in [group.get(rel) for group in (firmware["source_sha256"], firmware["evidence"])]
    target = read(TARGET)
    assert target["status"] == "passed" and set(target["variants"]) == {"normal", "calibrator"}
    assert all(v["USB_configuration_mA"] == PORT_CONFIGURED_MA for v in target["variants"].values())
    assert read(C5)["connector_pin_contract"]["1"] == "VBUS through F1"

    inputs = [BOARD, BUILD, TARGET, POLICY, C5, Path(__file__), ROOT / "scripts/kicad_sexpr.py"]
    report = {
        "status": "source-bound-planning-budget-first-article-open",
        "physical_verification": False,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in inputs},
        "host_current_limits_mA": {"before_configuration": PORT_UNCONFIGURED_MA,
                                  "configured": PORT_CONFIGURED_MA},
        "pin_assignments": expected,
        "BQ24074_input_limit_mA": {"USB100_min_typ_max": [90, 95, 100],
                                   "USB500_min_typ_max": [450, 475, 500]},
        "nRF52840_VBUS_typical_mA": {"active": 2.4, "suspend": .262},
        "mainboard_direct_VBUS_nominal_capacitance_uF": {"C32": 4.7, "C40": 2.2},
        "mainboard_nominal_direct_capacitor_charge_at_5V_uC": 5 * (4.7 + 2.2),
        "assumed_non_battery_current_mA": {"U5_OUT": OUT_ALLOWANCE_MA,
                                          "U5_internal": CHARGER_HOUSEKEEPING_ALLOWANCE_MA,
                                          "U1_and_other_bypass": BYPASS_ALLOWANCE_MA},
        "CORNER_07_R40": charge_corner(2210),
        "unqualified_R40_derating_trial": charge_corner(2490),
        "references": {
            "charger": "https://www.ti.com/lit/ds/symlink/bq24074.pdf",
            "nRF52840_USBD_running": "https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/_tmp/nrf52840/autodita/current/parameters.i_usbd.html?contentId=0~r9OOfQs0Fo3SLnXciN~A",
            "USB_host_port": "https://compliance.usb.org/index.asp?Format=Standard&UpdateFile=Policies",
            "USB_inrush_test": "https://www.usb.org/sites/default/files/USB-IFTestProc1_3.pdf",
        },
    }
    output = BASE / "audit/usb-host-current.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])


if __name__ == "__main__":
    main()
