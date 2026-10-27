#!/usr/bin/env python3
"""Check exported electrical connectivity against upstream and compare ERC."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from build_ble_interface import ROOT, DEST, SOURCE, SIGNALS, CONNECTOR, form_at


def run(cli, *args):
    subprocess.run([cli, *map(str, args)], check=True, capture_output=True, text=True)


def nets(path):
    tree = ET.parse(path).getroot()
    return tree, {n.get("name"): {(v.get("ref"), v.get("pin")) for v in n.findall("node")}
                  for n in tree.findall("./nets/net")}


def erc_summary(path):
    data = json.loads(path.read_text())
    return Counter(f'{v["severity"]}:{v["type"]}'
                   for s in data["sheets"] for v in s["violations"])


def erc_fingerprints(path):
    data = json.loads(path.read_text())
    return {(v["type"], v["severity"], tuple(sorted(i["uuid"] for i in v["items"])))
            for s in data["sheets"] for v in s["violations"]}


def check():
    cli = shutil.which("kicad-cli")
    if not cli:
        cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    if not Path(cli).is_file():
        raise SystemExit("Install KiCad or add kicad-cli to PATH")
    with tempfile.TemporaryDirectory(prefix="yaeckb-netcheck-") as folder:
        temp = Path(folder)
        # KiCad may write project-local state while reading; keep the submodule clean.
        baseline = temp / "baseline"
        baseline.mkdir()
        for source in SOURCE.glob("*.kicad_sch"):
            shutil.copyfile(source, baseline / source.name)
        shutil.copyfile(SOURCE / "EC60.kicad_pro", baseline / "EC60.kicad_pro")
        for name, schematic in (("upstream", baseline / "EC60.kicad_sch"),
                                 ("interface", DEST / "EC60-BLE-Interface.kicad_sch")):
            run(cli, "sch", "export", "netlist", "--format", "kicadxml", "-o",
                temp / f"{name}.xml", schematic)
            run(cli, "sch", "erc", "--format", "json", "-o", temp / f"{name}.json", schematic)
        base_tree, base = nets(temp / "upstream.xml")
        new_tree, new = nets(temp / "interface.xml")
        extensions = {("U1", pin) for _, pin, _, _ in SIGNALS}
        for name, nodes in base.items():
            if len(nodes) == 1 and nodes <= extensions:
                assert name.startswith("unconnected-"), f"Not an unused pin: {name}"
                continue
            renamed = "SYS_3V3" if name == "VBAT" else name
            assert nodes == {v for v in new.get(renamed, set()) if v[0] != "J2"}, name
        for name, pin, _, _ in SIGNALS:
            upstream_nets = [(n, v) for n, v in base.items() if ("U1", pin) in v]
            assert len(upstream_nets) == 1
            upstream_name, upstream_nodes = upstream_nets[0]
            assert upstream_name.startswith("unconnected-") and upstream_nodes == {("U1", pin)}
            assert new[name] == {("U1", pin), ("J2", str(CONNECTOR.index(name) + 1))}, name
        for i, name in enumerate(CONNECTOR, 1):
            assert ("J2", str(i)) in new[name], f"J2 pin {i}"
        def components(tree):
            return {c.get("ref"): c.findtext("value") for c in tree.findall("./components/comp")}
        original_components, new_components = components(base_tree), components(new_tree)
        assert new_components.pop("J2") == "BLE_INTERFACE_3V3_ONLY"
        assert original_components == new_components, "Original component values changed"
        for name in ("analog.kicad_sch", "matrix.kicad_sch", "mounting.kicad_sch"):
            assert (SOURCE / name).read_bytes() == (DEST / name).read_bytes(), name
        base_erc = erc_summary(temp / "upstream.json")
        new_erc = erc_summary(temp / "interface.json")
        assert not any(k.startswith("error:") for k in new_erc), "ERC electrical errors remain"
        added = erc_fingerprints(temp / "interface.json") - erc_fingerprints(temp / "upstream.json")
        # Removing redundant #PWR06 changes which existing +3V3 marker KiCad
        # pairs with the deliberately renamed SYS_3V3 label. Connectivity above
        # must still match exactly; only this known pair is allowed to change.
        schematic_text = (DEST / "EC60-BLE-Interface.kicad_sch").read_text()
        rail_markers = set()
        pattern = r'\(global_label "(?:SYS_3V3|VDD[123]|VDDA)"|\(symbol \(lib_id "power:\+3\.3V"\)'
        for match in re.finditer(pattern, schematic_text):
            marker = form_at(schematic_text, match.start())
            rail_markers.update(re.findall(r'\(uuid ([^)]+)\)', marker))
        unexpected = {f for f in added if not (f[:2] == ("multiple_net_names", "warning")
                                               and set(f[2]) <= rail_markers)}
        assert not unexpected, f"Unexpected ERC findings: {sorted(unexpected)}"
        assert new_erc["warning:multiple_net_names"] <= base_erc["warning:multiple_net_names"]
        report = {
            "status": "interface-connectivity-verified-not-production-ready",
            "kicad": subprocess.check_output([cli, "version"], text=True).strip(),
            "checks": ["original connected nets preserved", "six formerly unused pins extended",
                       "J2 pin mapping verified", "original component values preserved",
                       "analog/matrix/mounting sheets byte-identical", "zero ERC errors",
                       "ERC warning changes restricted to explicit regulated-rail alias allowance"],
            "upstream_erc": dict(sorted(base_erc.items())),
            "interface_erc": dict(sorted(new_erc.items())),
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(DEST.glob("*.kicad_*")) if p.suffix != ".kicad_prl"},
            "limitations": ["upstream library/grid/naming warnings remain", "no PCB routing or mechanical fit verification",
                            "no battery circuit or BLE firmware implemented"],
        }
        path = DEST / "validation.json"
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # Assertions are safety gates here; never allow python -O to skip them.
    if not __debug__:
        raise SystemExit("Run without -O: electrical verification must not skip assertions")
    report_path = DEST / "validation.json"
    report_path.write_text('{"status":"verification-in-progress-not-valid"}\n')
    try:
        check()
    except Exception as error:
        report_path.write_text(json.dumps({"status": "verification-failed-not-valid", "error": str(error)},
                                         ensure_ascii=False, indent=2) + "\n")
        raise
