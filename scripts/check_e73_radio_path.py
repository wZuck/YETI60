#!/usr/bin/env python3
"""Measure the M05 antenna surroundings and compute a BLE path-loss reference."""

import hashlib
import json
from math import log10, pi
from pathlib import Path

from OCP.gp import gp_Dir, gp_Lin, gp_Pnt
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector

from cad_geometry import load
from check_yeti60_assembly import build_plate

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "hardware/e73-hhkb-corner"
AUDIT = BASE / "audit"
BOARD = BASE / "EC60-nRF52840.kicad_pcb"
BUILD = BASE / "firmware/yeti60-target-build.json"
FIRMWARE = BASE / "firmware/manifest.json"
CONFIG = ROOT / "firmware/target/config/yeti60.conf"
ZEPHYR = ROOT / ".assembly-work/e73-corner/firmware-build/.firmware-work"
SOURCES = {
    "module_manual_pdf": "https://www.ebyte.com/downpdf/444.html",
    "module_specifications": "https://www.cdebyte.com/products/E73-2G4M08S1C/1",
    "Nordic_receiver_operation": "https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/radio.html",
    "Bluetooth_LE_channels": "https://www.bluetooth.com/wp-content/uploads/2023/03/bluetooth-le-regulatory-aspects-document.pdf",
    "free_space_attenuation": "https://www.itu.int/rec/R-REC-P.525-5-202411-I/en",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def extract_radio_config():
    firmware = read(FIRMWARE)
    assert firmware["source_PCB_sha256"] == sha(BOARD)
    assert firmware["source_sha256"][str(CONFIG.relative_to(ROOT))] == sha(CONFIG)
    assert firmware["evidence"][str(BUILD.relative_to(ROOT))] == sha(BUILD)
    variants = read(BUILD)["variants"]
    radios = {}
    assert set(variants) == {"normal", "calibrator"}
    for name, settings in variants.items():
        built_config = ZEPHYR / name / "zephyr/.config"
        digest = sha(built_config)
        assert digest == settings["configuration_sha256"]
        assert "CONFIG_BT_CTLR_TX_PWR_DBM=0" in built_config.read_text().splitlines()
        radios[name] = {"Zephyr_config_sha256": digest, "configured_TX_power_dBm": 0}
    return radios


def east_wall_paths(shapes, antenna, pcb_top_z):
    _, y_min, x_max, y_max = antenna
    center = -(y_min + y_max) / 2
    probes = []
    for y in (center - 5, center, center + 5):
        for height in (.8, 1.6, 2.4):
            z = pcb_top_z + height
            ray = gp_Lin(gp_Pnt(x_max, y, z), gp_Dir(1, 0, 0))
            walls = {}
            for part, analyzer in shapes.items():
                analyzer.Perform(ray, 0, 50)
                assert analyzer.IsDone(), part
                cuts = sorted({round(analyzer.WParameter(i), 6) for i in range(1, analyzer.NbPnt() + 1)})
                assert len(cuts) % 2 == 0, (part, cuts)
                walls[part] = list(zip(cuts[::2], cuts[1::2]))
            assert not walls.pop("steel_plate"), "A lateral ray intersects the steel plate"
            assert walls["top"] and walls["bottom-m05"], walls
            probes.append({
                "origin_case_mm": [x_max, y, round(z, 6)],
                "resin_intervals_from_origin_mm": walls,
                "resin_total_mm": round(sum(end - start for material in walls.values()
                                            for start, end in material), 6),
                "outer_exit_from_origin_mm": max(end for material in walls.values() for _, end in material),
            })
    return probes


def link_budget():
    reserve = 15
    example_host_sensitivity = -85
    rows = []
    for distance in (2, 3):
        loss = [20 * log10(4 * pi * distance * frequency * 1e6 / 299792458)
                for frequency in (2402, 2480)]
        rows.append({
            "distance_m": distance,
            "free_space_loss_at_band_edges_dB": [round(x, 3) for x in loss],
            "remaining_additional_loss_after_15dB_reserve_dB": {
                "toward_E73_1M_typical_-95dBm": round(95 - loss[-1] - reserve, 3),
                "toward_E73_2M_typical_-92dBm": round(92 - loss[-1] - reserve, 3),
                "toward_example_host_-85dBm": round(-example_host_sensitivity - loss[-1] - reserve, 3),
            },
        })
    return {"reference_TX_dBm": 0, "reference_antenna_gain_each_dBi": 0,
            "assumed_host_RX_dBm": example_host_sensitivity, "planning_reserve_dB": reserve, "rows": rows}


def main():
    native_path = AUDIT / "placement-check.json"
    fit_path = AUDIT / "corner-fit.json"
    case_path = AUDIT / "service-case-m05.json"
    assembly_path = ROOT / "mechanical/assembly-spec.json"
    native, fit, case, assembly = map(read, (native_path, fit_path, case_path, assembly_path))
    board_key = str(BOARD.relative_to(ROOT))
    assert all(report["source_sha256"][board_key] == sha(BOARD) for report in (native, fit, case))
    copper = native["antenna_copper"]
    assert {row["layer"] for row in copper} == {"F.Cu", "In1.Cu", "In2.Cu", "B.Cu"}
    assert all(row["overlap_mm2"] == 0 for row in copper)
    stack = assembly["stack"]
    top = ROOT / assembly["geometry"]["top"]
    m05 = {Path(name).stem.removesuffix("-REVIEW"): ROOT / name
           for name in case["outputs"] if name.endswith(".step")}
    assert set(m05) == {"bottom-m05", "cover-J2", "cover-J4"}
    assert all(sha(path) == case["outputs"][str(path.relative_to(ROOT))] for path in m05.values())
    shapes = {name: load(path) for name, path in {"top": top, **m05}.items()}
    shapes["steel_plate"], _ = build_plate(stack["plate_bottom_z"])
    intersectors = {}
    for name, shape in shapes.items():
        intersectors[name] = IntCurvesFace_ShapeIntersector()
        intersectors[name].Load(shape, 1e-5)
    pcb_top_z = stack["plate_bottom_z"] - stack["pcb_to_plate_gap"]
    antenna = native["provisional_antenna_PCB_mm"]
    paths = east_wall_paths(intersectors, antenna, pcb_top_z)
    u1 = next(part for part in fit["parts"] if part["reference"] == "U1")
    inputs = [BOARD, native_path, fit_path, case_path, assembly_path, top, *m05.values(),
              ROOT / assembly["geometry"]["plate"], BUILD, FIRMWARE, CONFIG, Path(__file__),
              ROOT / "scripts/cad_geometry.py", ROOT / "scripts/check_yeti60_assembly.py"]
    report = {
        "status": "M05_antenna_geometry_and_reference_link_budget_checked",
        "physical_verification": False,
        "electromagnetic_field_solution": False,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in inputs},
        "references": SOURCES,
        "antenna_band_PCB_mm": antenna,
        "host_board_copper_in_keepout": copper,
        "steel_projection_intersection_mm2": round(fit["antenna_metal_plate_projection_overlap_mm2"], 6),
        "bounded_U1_envelope_to_steel_plate_mm": round(u1["gaps_mm"]["plate"], 6),
        "east_ray_direction_case": [1, 0, 0],
        "east_paths_through_case": paths,
        "controller_profiles": extract_radio_config(),
        "reference_link_budget": link_budget(),
    }
    (AUDIT / "radio-path.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])


if __name__ == "__main__":
    main()
