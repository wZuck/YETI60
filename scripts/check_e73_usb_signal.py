#!/usr/bin/env python3
"""Screen the ordinary-stack USB pair and the length of the installed M05 path."""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
import scipy
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import spsolve

from kicad_sexpr import child, children, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "hardware/e73-hhkb-corner"
AUDIT = BASE / "audit"
BOARD = BASE / "EC60-nRF52840.kicad_pcb"
PROFILE = ROOT / "mechanical/pcb-fabrication-spec.json"
C5 = ROOT / "docs/audit/yeti60-daughterboard.json"
LIGHT_SPEED = 299792458
EPSILON_0 = 8.8541878188e-12


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def axis(breaks, step):
    edges = np.concatenate([
        np.linspace(start, end, max(1, int(np.ceil((end - start) / step))), endpoint=False)
        for start, end in zip(breaks[:-1], breaks[1:])
    ] + [breaks[-1:]])
    return (edges[:-1] + edges[1:]) / 2, np.diff(edges)


def capacitance(width, gap, height, copper, er, step, domain=2.5, mask=True):
    """Finite-volume electrostatic energy per unit length at 1 V differential."""
    half_gap = gap / 2
    edge = half_gap + width
    # Align the grid to the copper, ground plane and coating boundaries.
    # JLC's representative mask thicknesses are 1.2 mil in the gap and
    # 0.6 mil above the trace. The substrate surface is at z=height.
    trace_top = height + copper
    mask_gap, mask_top = height + .03048, trace_top + .01524
    x, dx = axis([-domain, -edge, -half_gap, half_gap, edge, domain], step)
    z, dz = axis(sorted({0, height, mask_gap, trace_top, mask_top, domain}), step)
    shape = (len(z), len(x))
    zz, xx = np.meshgrid(z, x, indexing="ij")
    trace = (abs(xx) >= half_gap) & (abs(xx) <= edge) & (zz >= height) & (zz < trace_top)
    dielectric = np.where(zz < height, er, 1.)
    if mask:
        dielectric[(zz >= height) & ((zz < mask_gap) |
                   ((abs(xx) >= half_gap) & (abs(xx) <= edge) & (zz < mask_top)))] = 3.8
    indices = np.arange(np.prod(shape)).reshape(shape)
    horizontal = np.broadcast_to(dx[None, :], shape)
    vertical = np.broadcast_to(dz[:, None], shape)
    pairs, weights = [], []
    for left, right, length, span in [
        ((slice(None), slice(None, -1)), (slice(None), slice(1, None)), horizontal, vertical),
        ((slice(None, -1), slice(None)), (slice(1, None), slice(None)), vertical, horizontal),
    ]:
        face_path = np.where(trace, 0, length / (2 * dielectric))
        path = face_path[left] + face_path[right]
        coefficient = np.divide(span[left], path, out=np.zeros_like(path), where=path > 0)
        pairs.append((indices[left].ravel(), indices[right].ravel()))
        weights.append(coefficient.ravel())
    left, right = map(np.concatenate, zip(*pairs))
    coeff = np.concatenate(weights)
    boundary = np.zeros(shape)
    for side in (0, -1):
        boundary[:, side] += 2 * dielectric[:, side] * dz / dx[side]
        boundary[side, :] += 2 * dielectric[side, :] * dx / dz[side]
    size = indices.size
    laplace = coo_matrix(
        (np.tile(coeff, 4) * np.repeat([1, 1, -1, -1], len(coeff)),
         (np.concatenate([left, right, left, right]), np.concatenate([left, right, right, left]))),
        shape=(size, size),
    ).tocsr() + diags(boundary.ravel())
    fixed = trace.ravel()
    voltage = np.zeros(size)
    voltage[fixed] = np.sign(xx.ravel()[fixed]) * .5
    voltage[~fixed] = spsolve(laplace[~fixed][:, ~fixed], -(laplace[~fixed][:, fixed] @ voltage[fixed]))
    return EPSILON_0 * float(voltage @ (laplace @ voltage))


def cross_section(width, gap, height, copper, er, step, domain=2.5):
    vacuum = capacitance(width, gap, height, copper, 1., step, domain, mask=False)
    loaded = capacitance(width, gap, height, copper, er, step, domain)
    impedance = 1 / (LIGHT_SPEED * np.sqrt(loaded * vacuum))
    velocity = LIGHT_SPEED * np.sqrt(vacuum / loaded)
    return dict(impedance_ohm=float(impedance), velocity_m_per_s=float(velocity),
                capacitance_pF_per_m=float(loaded * 1e12))


def verify_c5():
    c5 = read(C5)
    directory = ROOT / "hardware/usb-daughterboard/upstream"
    pcb = subprocess.check_output(
        ["git", "-C", str(directory), "show", f"{c5['source_commit']}:UDB.kicad_pcb"])
    assert digest(pcb) == c5["source_sha256"][str((directory / "UDB.kicad_pcb").relative_to(ROOT))]
    tvs = next(part for part in children(loads(pcb.decode()), "footprint")
               if ["reference", "U1"] in [item[1:3] for item in children(part, "fp_text")])
    assert ["value", "TPD4E05U06DQAR"] in [item[1:3] for item in children(tvs, "fp_text")]
    pins = {pad[1]: child(pad, "net")[-1] for pad in children(tvs, "pad") if child(pad, "net")}
    assert (pins["1"], pins["2"], pins["3"], pins["4"], pins["5"], pins["8"]) == (
        "DP", "DN", "GND", "DP", "DN", "GND")
    return {"source_commit": c5["source_commit"], "source_pcb_sha256": digest(pcb),
            "tvs_diode_channels_per_conductor": 2, "typical_C_per_channel_pF": .5,
            "equivalent_differential_shunt_pF": .5}


def edge_model(directory, segments, direction):
    sections = segments if direction == "host_to_U1" else segments[::-1]
    lines = []
    for i, (name, z0, delay_ns) in enumerate(sections):
        lines.append(f"T{name} n{i} 0 n{i+1} 0 Z0={z0:.8f} TD={delay_ns:.8f}n")
    c5_node = 1 if direction == "host_to_U1" else len(sections) - 1
    end = f"n{len(sections)}"
    circuit = "\n".join([
        "Full-speed differential transition reference", "Vedge drive 0 PWL(0 -3.3 10n -3.3 15n 3.3 95n 3.3)",
        "Rdrive drive n0 90", *lines, f"Cc5 n{c5_node} 0 .5p",
        f"Cinput {end} 0 15p", f"Rinput {end} 0 15k", ".control", "set wr_vecnames", "set wr_singlescale",
        "tran .025n 100n 0 .025n", f"wrdata edge.txt v({end})", "quit", ".endc", ".end", "",
    ])
    bench = directory / "edge.cir"
    bench.write_text(circuit)
    output = directory / "edge.txt"
    output.unlink(missing_ok=True)
    run = subprocess.run(["ngspice", "-b", bench.name], cwd=directory, capture_output=True, text=True, timeout=45)
    log = run.stdout + run.stderr
    assert run.returncode == 0 and not any(item in log.lower() for item in ("error", "aborted", "timestep too small")), log
    time, voltage = np.loadtxt(output, skiprows=1, unpack=True)
    assert len(time) > 2000 and np.isfinite(voltage).all()
    dc_high = 3.3 * 15000 / 15090
    assert abs(voltage[0] + dc_high) < .005 and abs(voltage[-1] - dc_high) < .15, (
        direction, voltage[0], voltage[-1])
    half = np.flatnonzero(voltage >= 0)[0]
    assert half > 0 and np.count_nonzero(np.signbit(voltage[:-1]) != np.signbit(voltage[1:])) == 1
    crossing_ns = np.interp(0., voltage[half-1:half+1], time[half-1:half+1]) * 1e9
    after = voltage[half:np.searchsorted(time, time[half] + 60e-9)]
    return {"half_swing_from_source_start_ns": round(float(crossing_ns) - 10, 4),
            "peak_above_DC_differential_V": round(max(0., float(np.max(after) - dc_high)), 5),
            "largest_reverse_excursion_after_half_swing_V": round(float(np.max(np.maximum.accumulate(after) - after)), 5)}


def main():
    placement = AUDIT / "placement-check.json"
    harness_path = AUDIT / "m05-harness.json"
    return_path = AUDIT / "USB-reference.json"
    board_key = str(BOARD.relative_to(ROOT))
    board_sha = digest(BOARD.read_bytes())
    native, harness, reference, fab = map(read, (placement, harness_path, return_path, PROFILE))
    assert all(report["source_sha256"][board_key] == board_sha for report in (native, harness))
    assert reference["checks_passed"] and reference["whole_ground_network_connected"]
    pair = native["USB_pair"]
    assert all(row["vias"] == 1 and row["width_mm"] == .3 for row in pair.values())
    assert abs(reference["back_pair_minimum_actual_copper_clearance_mm"] - .2) < 1e-5
    assert fab["stackup"] == "JLC04161H-7628"
    h = fab["outer_dielectrics_mm"][-1]
    t = fab["outer_copper_mm"]
    nominal = cross_section(.30, .20, h, t, 4.4, .010)
    refined = cross_section(.30, .20, h, t, 4.4, .0075)
    extended = cross_section(.30, .20, h, t, 4.4, .010, domain=3.0)
    assert abs(nominal["impedance_ohm"] - refined["impedance_ohm"]) < 1.
    assert abs(nominal["impedance_ohm"] - extended["impedance_ohm"]) < 1.
    corners = {
        "0.27mm_width_0.23mm_gap_0.24mm_height_Dk4.2": cross_section(.27, .23, .24, t, 4.2, .010),
        "0.33mm_width_0.17mm_gap_0.18mm_height_Dk4.6": cross_section(.33, .17, .18, t, 4.6, .010),
    }
    pcb_length = max(row["track_length_mm"] for row in pair.values())
    harness_length = max(row["seated_free_lengths_mm"][pin]
                         for row in harness["trial_variants"] for pin in ("usb.2", "usb.3"))
    pcb_delay = pcb_length / 1000 / refined["velocity_m_per_s"] * 1e9
    harness_delay = harness_length / 1000 / (.65 * LIGHT_SPEED) * 1e9
    output = []
    cases = [(wire, "nominal", refined) for wire in (75, 90, 120, 150)]
    cases += [(90, corner, section) for corner, section in corners.items()]
    with tempfile.TemporaryDirectory(prefix="yeti60-usb-signal-") as tmp:
        for wire_impedance, board_case, section in cases:
            section_delay = pcb_length / 1000 / section["velocity_m_per_s"] * 1e9
            segments = [("external", 90, 15.), ("harness", wire_impedance, harness_delay),
                        ("pcb", section["impedance_ohm"], section_delay)]
            waveform = {direction: edge_model(Path(tmp), segments, direction)
                        for direction in ("host_to_U1", "U1_to_host")}
            output.append({"assumed_internal_Zdiff_ohm": wire_impedance,
                           "mainboard_cross_section": board_case, "reference_edge": waveform})
    inputs = [BOARD, placement, harness_path, return_path, PROFILE, C5, Path(__file__), ROOT / "scripts/kicad_sexpr.py"]
    report = {
        "status": "USB_pair_cross_section_and_link_sensitivity_checked",
        "physical_verification": False,
        "source_sha256": {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in inputs},
        "tools": {"scipy": scipy.__version__, "numpy": np.__version__,
                  "ngspice": next(row.strip() for row in subprocess.check_output(
                      ["ngspice", "--version"], text=True).splitlines() if "Circuit level" in row)},
        "C5_signals": verify_c5(),
        "PCB_and_wire": {"track_width_mm": .30, "minimum_edge_gap_mm": .20, "plane_height_mm": h,
                         "longest_PCB_trace_centerline_mm_excluding_via": pcb_length,
                         "longest_M05_data_conductor_mm": harness_length,
                         "mainboard_modeled_delay_ns": pcb_delay, "harness_modeled_delay_ns_at_0p65c": harness_delay},
        "cross_section": {"spacing_0p01mm": nominal, "spacing_0p0075mm": refined, "extended_domain": extended,
                          "illustrative_geometric_corners": corners},
        "transient_assumptions": {"external_Zdiff_ohm": 90, "external_3m_delay_ns": 15,
                                  "driver_diff_ohm": 90, "diff_load_pF": 15, "source_10_to_90_percent_ns": 4,
                                  "waveform_measurement_after_half_swing_ns": 60},
        "transient_sweep": output,
    }
    (AUDIT / "usb-signal.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"])


if __name__ == "__main__":
    main()
