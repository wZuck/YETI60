#!/usr/bin/env python3
"""Publish solder-side probe locations and M05 charge-headroom calculations."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "hardware/e73-hhkb-corner"
AUDIT = BASE / "audit"
ROLE_NETS = {
    "F1": ("USB_5V", "VBUS"),
    "J1": ("VBUS", None, None, "GND"),
    "J2": ("BAT_CELL", "GND", "BAT_NTC"),
    "J4": ("USB_FEED", "USB_DM", "USB_DP", "GND"),
    "J5": ("USB_FEED", "GND"),
    "C32": ("USB_5V", "GND"),
    "C40": ("USB_5V", "GND"),
    "C41": ("BAT_CELL", "GND"),
    "C42": ("VSYS", "GND"),
    "C45": ("+3.3V", "GND"),
    "R42": ("CHG_EN1", "GND"),
    "R43": ("CHG_EN2", "GND"),
    "R44": ("CHG_CE_N", "GND"),
}
DIAGNOSTIC = {
    "U1": {"27": "USB_5V", "24": "GND"},
    "U5": {"1": "BAT_NTC", "2": "BAT_CELL", "4": "CHG_CE_N", "5": "CHG_EN2",
           "6": "CHG_EN1", "10": "VSYS", "13": "USB_5V"},
}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_pads(geometry):
    result = {}
    for ref, nets in ROLE_NETS.items():
        part = geometry["parts"][ref]
        assert part["side"] == "back", ref
        pads = {p["number"]: p for p in part["pads"]}
        for i, expected in enumerate(nets, 1):
            if expected is None:
                continue
            pad = pads[str(i)]
            assert pad["net"] == expected, (ref, i, expected, pad["net"])
            result[f"{ref}.{i}"] = dict(net=expected, xy_PCB_mm=pad["position_mm"])
    for ref, nets in DIAGNOSTIC.items():
        pads = {p["number"]: p for p in geometry["parts"][ref]["pads"]}
        assert all(pads[number]["net"] == net for number, net in nets.items()), ref
    return result


def path_model():
    power_path = AUDIT / "power-process.json"
    m05_path = AUDIT / "m05-harness.json"
    reports = [read(path) for path in (power_path, m05_path)]
    board_path = BASE / "EC60-nRF52840.kicad_pcb"
    for report in reports:
        assert report["source_sha256"][str(board_path.relative_to(ROOT))] == sha(board_path)
    baseline = reports[0]["charge_headroom"]
    m05 = reports[1]["charging_path_sensitivity"]
    lengths = reports[1]["trial_variants"][0]["seated_free_lengths_mm"]
    supply_span = sum(lengths[k] for k in ("usb.1", "usb.4", "power.1", "power.2"))
    assert abs(supply_span - m05["AWG28_wire_length_mm"]) < 1e-8
    wire_r20 = baseline["wire_loop_20C_ohm"] * supply_span / baseline["four_wire_free_lengths_sum_mm"]
    hot_r = (wire_r20 + baseline["positive_PCB_centerline_20C_ohm"]) * (
        1 + .00393 * (m05["copper_temperature_C"] - 20))
    assert abs(hot_r - m05["model_R_at_temperature_ohm"]) < 1e-12
    rows = []
    dpm_max = baseline["BQ24074_VIN_DPM_min_typ_max_V"][-1]
    for v_jack, milliamps in ((4.75, 100), (4.75, 450), (4.75, 500), (5, 450), (5, 500)):
        drop = hot_r * milliamps / 1000
        rows.append(dict(jack_V=v_jack, input_mA=milliamps, included_drop_V=round(drop, 6),
                         U5_IN_before_omitted_losses_V=round(v_jack - drop, 6)))
    return (dict(four_wire_mm=supply_span, model_R_60C_ohm=hot_r,
                 v_drop_at_500mA_V=hot_r / 2, example_rows=rows,
                 theoretical_limit_at_4p75V_and_max_DPM_mA=round(1000 * (4.75 - dpm_max) / hot_r, 3),
                 omitted_losses=m05["excluded"]), [power_path, m05_path])


def draw(geometry, zh):
    plt.rcParams["font.family"] = ["Arial Unicode MS", "DejaVu Sans"]
    fig = plt.figure(figsize=(11.5, 8.3), layout="constrained")
    grid = fig.add_gridspec(3, 2, height_ratios=[1.3, 1, 1], width_ratios=[2.45, 1])
    top = fig.add_subplot(grid[0, :])
    axes = [fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1]),
            fig.add_subplot(grid[2, 0]), fig.add_subplot(grid[2, 1])]
    fig.suptitle("YETI60 E73 · 主板背面测点" if zh else "YETI60 E73 · Solder-side probe map",
                 fontsize=19, color="#163b36")
    ring = geometry["outline"][0]["outer"]
    xs, ys = zip(*(ring + [ring[0]]))
    top.fill(xs, ys, color="#edf2eb", edgecolor="#44635c")
    for part in geometry["parts"].values():
        if part["side"] == "back":
            x, y, X, Y = part["bbox"]
            top.add_patch(Rectangle((x, y), X - x, Y - y, color="#c3cfca", lw=0))
    details = [
        ((84, 162, 106, 135), ("F1", "J1", "J2"),
         "保险丝与主板接口" if zh else "Fuse and two mainboard connectors"),
        ((332.0, 350.7, 105.2, 119.6), ("J4", "J5"), "USB 与电源桥" if zh else "USB and power bridge"),
        ((109.5, 136.0, 136.6, 149.5), ("C40", "C41", "C42", "C45", "R42", "R43", "R44"),
         "充电器与稳压电路" if zh else "Charger and regulator"),
        ((333.5, 340.0, 192.0, 196.4), ("C32",), "模组附近供电" if zh else "USB supply beside U1"),
    ]
    for index, (ax, (bb, refs, title)) in enumerate(zip(axes, details), 1):
        x, X, y, Y = bb
        top.add_patch(Rectangle((x, y), X - x, Y - y, fill=False, ec="#b05d32", lw=1))
        top.annotate(str(index), ((x + X) / 2, (y + Y) / 2), ha="center", va="center",
                     color="#934420", weight="bold", bbox={"fc": "white", "ec": "none", "pad": 1})
        for ref in refs:
            part = geometry["parts"][ref]
            a, b, c, d = part["bbox"]
            ax.add_patch(Rectangle((a, b), c-a, d-b, edgecolor="#62726a", facecolor="#e1eae2", lw=.6))
            label_at = (a, (b+d)/2) if ref in {"C40", "C42"} else ((a+c)/2, b)
            offset = (10, -3) if ref in {"C40", "C42"} else (0, 5)
            ax.annotate(ref, label_at, xytext=offset, textcoords="offset points",
                        ha="center", color="#163b36", weight="bold", size=8)
            for pad in part["pads"]:
                number = pad["number"]
                expected = ROLE_NETS[ref]
                if not number.isdigit() or not 1 <= int(number) <= len(expected) or expected[int(number)-1] is None:
                    continue
                p = pad["position_mm"]
                color = "#555f61" if pad["net"] == "GND" else "#b64a29"
                ax.scatter(*p, s=10, color=color, zorder=3)
                ax.annotate(number, p, xytext=(0, -8), ha="center",
                            textcoords="offset points", color=color, size=6, zorder=4)
        ax.set(xlim=(X, x), ylim=(Y, y), aspect="equal", title=f"{index}  {title}")
    top.set(xlim=(358, 70), ylim=(201, 101), aspect="equal",
            xlabel="KiCad X（mm，背面视角）" if zh else "KiCad X (mm), viewed from the back")
    top.set_ylabel("Y (mm)")
    for ax in [top, *axes]:
        ax.grid(alpha=.12)
        ax.tick_params(labelsize=8)
    path = AUDIT / ("bench-probe-map.zh-CN.png" if zh else "bench-probe-map.png")
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def main():
    geometry = read(ROOT / ".assembly-work/e73-corner/solder-map.json")
    inputs = dict(geometry["source_sha256"])
    assert all(sha(ROOT / path) == digest for path, digest in inputs.items()), "Regenerate the native solder map"
    points = check_pads(geometry)
    model, paths = path_model()
    paths.append(Path(__file__))
    inputs.update({str(path.relative_to(ROOT)): sha(path) for path in paths})
    drawings = [draw(geometry, zh) for zh in (False, True)]
    report = {
        "status": "native-bench-pad-map-and-M05-headroom-checked",
        "physical_verification": False,
        "source_sha256": inputs,
        "outputs": {str(path.relative_to(ROOT)): sha(path) for path in drawings},
        "pcb_sha256": geometry["source_PCB_sha256"],
        "solder_side_probe_pads": points,
        "charge_headroom_M05": model,
    }
    (AUDIT / "bench-power-plan.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(points), "probe pads")


if __name__ == "__main__":
    main()
