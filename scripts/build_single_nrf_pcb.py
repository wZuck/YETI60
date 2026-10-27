#!/usr/bin/env python3
"""Derive and place the single-nRF board; run using KiCad's bundled Python.

Run build_single_nrf.py and export its XML netlist before calling this script.
Routing is a separate step so regeneration cannot overwrite a routed board.
"""
from collections import defaultdict
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import pcbnew as pcb
from kicad_sexpr import Atom as A, child, children, dumps, form as F, loads
from configure_single_nrf_rules import configure

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "hardware/ec60-nrf52840"
NAME = "EC60-nRF52840"
FP_ROOT = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
XML = DEST / "netlist.xml"
PLUGIN = pcb.PCB_IO_KICAD_SEXPR()


def xy(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def footprint_id(name):
    library, item = name.split(":", 1)
    return pcb.LIB_ID(library, item)


def pogo(board):
    fp = pcb.FOOTPRINT(board)
    fp.SetFPID(footprint_id("YAECKB:SWD_Pogo_2x03"))
    fp.SetAttributes(pcb.FP_SMD)
    for n in range(1, 7):
        pad = pcb.PAD(fp)
        pad.SetNumber(str(n))
        pad.SetAttribute(pcb.PAD_ATTRIB_SMD)
        pad.SetShape(pcb.PAD_SHAPE_CIRCLE)
        pad.SetSize(xy(0.9, 0.9))
        layers = pcb.LSET()
        layers.AddLayer(pcb.F_Cu)
        layers.AddLayer(pcb.F_Mask)
        pad.SetLayerSet(layers)
        pad.SetPosition(xy(-.635 if n % 2 else .635, ((n - 1) // 2 - 1) * 1.27))
        fp.Add(pad)
    return fp


def main():
    source_path = ROOT / "EC60/PCB/EC60_PCB/EC60.kicad_pcb"
    source_board = pcb.LoadBoard(str(source_path))
    original = {fp.GetReference(): fp for fp in source_board.GetFootprints()}
    document = ET.parse(XML).getroot()
    components = {c.get("ref"): c for c in document.findall("./components/comp")}
    if len(components) != len(document.findall("./components/comp")):
        raise ValueError("Duplicate component references in single-MCU schematic")
    contract = json.loads((DEST / "components.json").read_text())
    target_nodes = {}
    for net in document.findall("./nets/net"):
        for node in net.findall("node"):
            target_nodes[node.get("ref"), node.get("pin")] = net.get("name")
    source = loads(source_path.read_text())
    old_net_names = {str(n[1]): str(n[2]) for n in children(source, "net")}
    def reference(fp):
        return next(str(t[2]) for t in children(fp, "fp_text") if t[1] == "reference")
    old_to_new = defaultdict(set)
    for fp in children(source, "footprint"):
        target = components.get(reference(fp))
        if target is None or str(fp[1]).split(":")[-1] != target.findtext("footprint").split(":")[-1]:
            continue
        for pad in children(fp, "pad"):
            node = (reference(fp), str(pad[1]))
            if node in target_nodes:
                old_net = child(pad, "net")
                if old_net:
                    old_to_new[str(old_net[2])].add(target_nodes[node])
    net_codes = {name: index for index, name in enumerate(sorted(set(target_nodes.values())), 1)}
    removed_tracks = 0
    retained = [source[0]]
    for entry in source[1:]:
        tag = str(entry[0]) if isinstance(entry, list) else ""
        if tag == "net":
            continue
        if tag in ("segment", "arc", "via", "zone"):
            net = child(entry, "net")
            if net:
                mapping = old_to_new.get(old_net_names.get(str(net[1]), ""), set())
                if len(mapping) != 1:
                    removed_tracks += int(tag != "zone")
                    continue
                new_name = next(iter(mapping))
                net[1] = A(str(net_codes[new_name]))
                if tag == "zone":
                    child(entry, "net_name")[1] = new_name
        if tag == "footprint":
            ref = reference(entry)
            target = components.get(ref)
            if target is None and ref not in ("REF**", "G***"):
                continue
            if target is not None:
                expected = target.findtext("footprint").split(":")[-1]
                if str(entry[1]).split(":")[-1] != expected:
                    continue
                for pad in children(entry, "pad"):
                    pad[:] = [v for v in pad if not (isinstance(v, list) and v and v[0] == "net")]
                    target_net = target_nodes.get((ref, str(pad[1])))
                    if target_net:
                        pad.append(F("net", net_codes[target_net], target_net))
            if ref == "REF**":
                for text in children(entry, "fp_text"):
                    if text[1] == "reference":
                        child(text, "layer")[1] = "Dwgs.User"
                entry[:] = [v for v in entry if not (isinstance(v, list) and v and
                            v[0] in ("fp_line", "fp_arc", "fp_poly", "fp_curve") and
                            child(v, "layer")[1] in ("F.Cu", "B.Cu"))]
            if ref in ("SW60", "SW62"):
                # Narrow only the ground guard lines, preserving electrode geometry.
                for pad in children(entry, "pad"):
                    if pad[1] == "4":
                        child(pad, "size")[1:] = [.394, .394]
                        for primitive in children(child(pad, "primitives"), "gr_line"):
                            child(primitive, "width")[1] = .394
        retained.append(entry)
    insert_at = next(i for i, v in enumerate(retained) if isinstance(v, list) and v and v[0] == "footprint")
    retained[insert_at:insert_at] = [F("net", 0, "")] + [F("net", code, name) for name, code in net_codes.items()]
    with tempfile.TemporaryDirectory(prefix="yaeckb-pcb-base-") as folder:
        base_path = Path(folder) / "base.kicad_pcb"
        base_path.write_text(dumps(retained) + "\n")
        board = pcb.LoadBoard(str(base_path))
    nets = {name: board.FindNet(name) for name in net_codes}
    originals_in_board = {fp.GetReference(): fp for fp in board.GetFootprints()}
    library = DEST / "YAECKB.pretty"
    library.mkdir(exist_ok=True)
    for fp in original.values():
        if str(fp.GetFPID().GetLibNickname()) == "cipulot_parts":
            item = str(fp.GetFPID().GetLibItemName())
            clone = pcb.Cast_to_FOOTPRINT(fp.Duplicate(False))
            clone.SetFPID(footprint_id("YAECKB:" + item))
            if item in ("JST-SR-4", "TSSOP16"):
                clone.SetAttributes(pcb.FP_SMD)
            PLUGIN.FootprintSave(str(library), clone)
    placements = {
        "U1": [347, 125, 90, "B"], "U5": [118, 145, 0, "B"],
        "U6": [133, 145, 0, "B"], "U7": [144, 143, 0, "B"], "U8": [107, 143, 0, "B"],
        "L1": [128.5, 145, 90, "B"], "J2": [152, 125, 0, "B"],
        "J3": [320, 122.5, 0, "B"], "SW1": [326, 123, 0, "B"], "SW100": [112, 121, 0, "B"],
        "C30": [334, 119, 0, "B"], "C31": [337.5, 121, 0, "B"], "C32": [334.5, 122, 0, "B"],
        "R26": [332, 123, 0, "B"], "R30": [337.5, 126, 0, "B"], "R31": [337.5, 128, 0, "B"],
        "R32": [316, 125, 0, "B"], "D2": [316, 123, 0, "B"],
        "R40": [116, 141, 0, "B"], "R41": [113, 142, 0, "B"], "R42": [121, 141, 0, "B"],
        "R43": [123, 141, 0, "B"], "R44": [125, 141, 0, "B"], "R45": [127, 141, 0, "B"],
        "R46": [129, 139.5, 0, "B"], "R47": [137, 141, 0, "B"], "R48": [106, 116, 0, "B"],
        "C40": [116.5, 149, 0, "B"], "C41": [120, 149.5, 0, "B"], "C42": [122, 146.5, 0, "B"],
        "C43": [132, 141, 0, "B"], "C44": [137, 144, 0, "B"],
        "C45": [133, 148.5, 0, "B"], "C46": [136.2, 148.5, 0, "B"],
        "R49": [142, 141, 0, "B"], "R50": [105, 141, 0, "B"], "R51": [146, 146, 0, "B"],
        "R52": [146, 148, 0, "B"], "R53": [141, 145, 0, "B"], "R54": [109, 145, 0, "B"],
        "C47": [144, 148, 0, "B"], "C48": [107, 147, 0, "B"],
    }
    placed = {}
    for ref, component in components.items():
        fp_name = component.findtext("footprint")
        if not fp_name:
            raise ValueError("No footprint on " + ref)
        old = originals_in_board.get(ref)
        same = old is not None and str(old.GetFPID().GetLibItemName()) == fp_name.split(":")[-1]
        if same:
            fp = old
        else:
            if fp_name == "YAECKB:SWD_Pogo_2x03":
                fp = pogo(board)
            else:
                lib, item = fp_name.split(":", 1)
                path = library if lib == "YAECKB" else FP_ROOT / (lib + ".pretty")
                fp = PLUGIN.FootprintLoad(str(path), item)
                if fp is None:
                    raise ValueError("Cannot load footprint " + fp_name)
            board.Add(fp)
        fp.SetReference(ref)
        fp.SetValue(component.findtext("value"))
        fp.SetFPID(footprint_id(fp_name))
        path = component.find("sheetpath").get("tstamps") + component.findtext("tstamps")
        fp.SetPath(pcb.KIID_PATH(path))
        placement = placements.get(ref)
        if placement:
            x, y, angle, side = placement
            fp.SetPosition(xy(x, y))
            if (side == "B") != fp.IsFlipped():
                fp.Flip(fp.GetPosition(), False)
            fp.SetOrientationDegrees(angle)
        elif not same:
            raise ValueError("New component has no placement: " + ref)
        if ref in ("J1", "U2", "U4"):
            fp.SetAttributes(pcb.FP_SMD)
        for pad in fp.Pads():
            name = target_nodes.get((ref, pad.GetNumber()))
            pad.SetNet(nets[name] if name else board.FindNet(0))
            if name == "GND" and (ref in contract or ref == "C13"):
                pad.SetLocalZoneConnection(pcb.ZONE_CONNECTION_FULL)
        placed[ref] = fp
    for fp in board.GetFootprints():
        if fp.GetReference() == "REF**":
            fp.Reference().SetLayer(pcb.Dwgs_User)
            for item in list(fp.GraphicalItems()):
                if item.GetLayer() in (pcb.F_Cu, pcb.B_Cu):
                    fp.Remove(item)
    for ref in ():
        fp = placed[ref]
        for dx, dy in ((-2.5, -2.5), (2.5, 2.5)):
            via = pcb.PCB_VIA(board)
            via.SetPosition(pcb.VECTOR2I(fp.GetPosition().x + pcb.FromMM(dx), fp.GetPosition().y + pcb.FromMM(dy)))
            via.SetWidth(pcb.FromMM(.6))
            via.SetDrill(pcb.FromMM(.3))
            via.SetViaType(pcb.VIATYPE_THROUGH)
            via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
            via.SetNet(nets["GND"])
            board.Add(via)
    for fp in placed.values():
        if str(fp.GetFPID().GetLibNickname()) == "YAECKB":
            PLUGIN.FootprintSave(str(library), fp)
    (DEST / "fp-lib-table").write_text('(fp_lib_table (lib (name "YAECKB") (type "KiCad") (uri "${KIPRJMOD}/YAECKB.pretty") (options "") (descr "EC60 retained electrode geometry and service pads")))\n')
    project_path = DEST / (NAME + ".kicad_pro")
    config = json.loads((ROOT / "EC60/PCB/EC60_PCB/EC60.kicad_pro").read_text())
    config["meta"] = {"filename": NAME + ".kicad_pro", "version": 1}
    project_path.write_text(json.dumps(config, indent=2) + "\n")
    out = DEST / (NAME + ".unrouted.kicad_pcb")
    pcb.SaveBoard(str(out), board)
    (DEST / "pcb-placement-contract.json").write_text(json.dumps({fp.GetReference(): {
        "position_nm": [fp.GetPosition().x, fp.GetPosition().y],
        "angle": fp.GetOrientationDegrees(), "flipped": fp.IsFlipped()
        } for fp in board.GetFootprints()}, indent=2) + "\n")
    (DEST / "retained-copper.json").write_text(json.dumps({"uuids":
        [str(track.m_Uuid.AsString()) for track in board.GetTracks()]}, indent=2) + "\n")
    scratch_config = dict(config)
    scratch_config["meta"] = {"filename": NAME + ".unrouted.kicad_pro", "version": 1}
    (DEST / (NAME + ".unrouted.kicad_pro")).write_text(json.dumps(scratch_config, indent=2) + "\n")
    configure(project_path)
    configure(DEST / (NAME + ".unrouted.kicad_pro"))
    (DEST / "placement.json").write_text(json.dumps({"source": "EC60 original PCB",
        "mcu_count": 1, "mcu": "MDBT50Q-1MV2 / nRF52840", "removed_obsolete_tracks": removed_tracks,
        "placements": placements, "signal_interference_simulation": "deferred until PCB completion",
        "status": "placed-not-yet-routed"}, indent=2) + "\n")
    # Remove copper pours only from the temporary routing representation. GND
    # will be restored by filling the actual board after session import.
    for zone in list(board.Zones()):
        if not zone.GetIsRuleArea():
            board.Remove(zone)
    dsn = DEST / (NAME + ".dsn")
    if not pcb.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError("Specctra export failed")
    print("Placed", len(placed), "components; generated", out.name, "and", dsn.name)


if __name__ == "__main__":
    main()
