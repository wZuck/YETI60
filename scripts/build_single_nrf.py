#!/usr/bin/env python3
"""Generate the single-nRF52840 EC60 schematic and component contract.

The old dual-MCU interface is retained only as historical reference.
Signal-interference simulation is intentionally deferred until PCB completion.
"""
import copy
import json
from pathlib import Path
import shutil
import uuid

from kicad_sexpr import Atom as A, child, children, dumps, form as F, loads, symbol_pins
from schematic_metadata import reconcile, extend_filters

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EC60/PCB/EC60_PCB"
DEST = ROOT / "hardware/ec60-nrf52840"
FROZEN = json.loads((DEST / "frozen-footprints.json").read_text()) if (DEST / "frozen-footprints.json").exists() else {}
APPROVED_FILTERS = {}
LIBRARIES = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols")
PROJECT = "EC60-nRF52840"
LIB_CACHE = {}
SYMBOLS = {}
PARTS = {}
ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, "yaeckb/single-nrf/root"))


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "yaeckb/single-nrf/" + name))


def library_symbol(identifier):
    library, name = identifier.split(":")
    if library not in LIB_CACHE:
        LIB_CACHE[library] = loads((LIBRARIES / (library + ".kicad_sym")).read_text())
    original = copy.deepcopy(next(s for s in children(LIB_CACHE[library], "symbol") if s[1] == name))
    extends = child(original, "extends")
    if extends:
        parent = library_symbol(library + ":" + str(extends[1]))
        parent = copy.deepcopy(parent)
        parent_name = str(parent[1]).split(":")[-1]
        replacements = {p[1]: p for p in children(original, "property")}
        parent[1] = name
        parent[:] = [v for v in parent if not (isinstance(v, list) and v and v[0] == "property" and v[1] in replacements)]
        parent.extend(replacements.values())
        for unit in children(parent, "symbol"):
            unit[1] = str(unit[1]).replace(parent_name + "_", name + "_", 1)
        original = parent
    original[1] = "YAECKB:" + name
    SYMBOLS[name] = copy.deepcopy(original)
    return original


def effects(size=1):
    return F("effects", F("font", F("size", size, size)))


def prop(name, value, x, y, hidden=False):
    e = effects()
    if hidden:
        e.append(A("hide"))
    return F("property", name, value, F("at", x, y, 0), e)


def label(name, x, y, angle, key):
    return F("global_label", name, F("shape", A("bidirectional")), F("at", x, y, angle),
             F("effects", F("font", F("size", 1, 1)), F("justify", A("right") if angle in (180, 270) else A("left"))),
             F("uuid", A(uid(key))))


class Sheet:
    def __init__(self, name, title, paper="A3"):
        self.name = name
        self.identifier = ROOT_UUID if name == PROJECT else uid("sheet/" + name)
        self.root = F("kicad_sch", F("version", 20250114), F("generator", A("eeschema")),
                      F("uuid", A(self.identifier)), F("paper", paper),
                      F("title_block", F("title", title), F("date", "2026-10-27"),
                        F("rev", "NRF-1.0-dev"), F("company", "YAECKB / EC60 by Cipulot")))
        self.libs = {}
        self.instances = []

    def add(self, ref, identifier, value, x, y, nets, footprint=None, pcb=None):
        symbol = library_symbol(identifier)
        name = str(symbol[1]).split(":")[-1]
        self.libs[name] = symbol
        props = {p[1]: p[2] for p in children(symbol, "property")}
        fp = footprint if footprint is not None else props.get("Footprint", "")
        fp = FROZEN.get(ref, {}).get("id", fp)
        pins = symbol_pins(symbol)
        unknown = set(nets) - set(pins)
        if unknown:
            raise ValueError(f"Unknown pins on {ref}: {unknown}")
        instance = F("symbol", F("lib_id", "YAECKB:" + name), F("at", x, y, 0), F("unit", 1),
                     F("in_bom", A("no") if ref.startswith("#") else A("yes")), F("on_board", A("yes")),
                     F("dnp", A("no")), F("uuid", A(uid(ref))),
                     prop("Reference", ref, x + 3.81, y - 5.08), prop("Value", value, x + 3.81, y - 2.54),
                     prop("Footprint", fp, x, y, True), prop("Datasheet", props.get("Datasheet", ""), x, y, True))
        self.instances.append((ref, value, fp))
        used_points = {}
        for number, pin in pins.items():
            dx, dy, direction = pin["at"]
            px, py = round(x + dx, 5), round(y - dy, 5)
            net = nets.get(number)
            instance.append(F("pin", number, F("uuid", A(uid(ref + "/pin/" + number)))))
            point = (px, py)
            if point in used_points:
                if used_points[point] != net:
                    raise ValueError(f"Stacked pins disagree at {ref}:{number}")
                continue
            used_points[point] = net
            if net is None:
                self.root.append(F("no_connect", F("at", px, py), F("uuid", A(uid(ref + "/nc/" + number)))))
                continue
            vx, vy = {0: (-2.54, 0), 180: (2.54, 0), 90: (0, 2.54), 270: (0, -2.54)}[int(direction)]
            lx, ly = round(px + vx, 5), round(py + vy, 5)
            self.root.append(F("wire", F("pts", F("xy", px, py), F("xy", lx, ly)),
                               F("stroke", F("width", 0), F("type", A("default"))),
                               F("uuid", A(uid(ref + "/wire/" + number)))))
            self.root.append(label(net, lx, ly, {0: 180, 180: 0, 90: 270, 270: 90}[int(direction)], ref + "/label/" + number))
        instance.append(F("instances", F("project", PROJECT,
                             F("path", "/" + ROOT_UUID if self.name == PROJECT else "/" + ROOT_UUID + "/" + uid("sheet-ref/" + self.name),
                               F("reference", ref), F("unit", 1)))))
        self.root.append(instance)
        PARTS[ref] = {"value": value, "symbol": identifier, "footprint": fp, "pins": nets,
                      "uuid": uid(ref), "sheet": self.name,
                      "datasheet": props.get("Datasheet", "")}

    def note(self, text, x, y):
        self.root.append(F("text", text, F("at", x, y, 0), effects(), F("uuid", A(uid(self.name + text)))))

    def write(self):
        libs = F("lib_symbols", *self.libs.values())
        self.root.insert(5, libs)
        reconcile(self.root, FROZEN, APPROVED_FILTERS)
        (DEST / (self.name + ".kicad_sch")).write_text("\n".join(
            ["(" + str(self.root[0]), *["  " + dumps(v) for v in self.root[1:]], ")", ""]))


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "EC60/LICENSE", DEST / "LICENSE.EC60")
    main_sheet = Sheet(PROJECT, "EC60 / single nRF52840 / rear USB daughterboard")
    power = Sheet("power", "Single-cell protected battery / power path / 3.3V / AFE", "A3")
    rf_nets = {"1": "GND", "2": "GND", "15": "GND", "33": "GND", "55": "GND",
               "28": "+3.3V", "30": "+3.3V", "32": "USB_5V", "34": "USB_DM", "35": "USB_DP",
               "37": "ROW_DRV0", "36": "ROW_DRV1", "39": "ROW_DRV2", "38": "ROW_DRV3", "41": "ROW_DRV4",
               "44": "AMUX_SEL_0", "46": "AMUX_SEL_1", "48": "AMUX_SEL_2",
               "47": "APLEX_EN_PIN_0", "50": "APLEX_EN_PIN_1", "19": "APLEX_OUT_PIN_0", "20": "ADC",
               "51": "SWDIO", "53": "SWDCLK", "40": "RESET_N", "16": "BAT_MEAS_EN", "21": "BAT_ADC",
               "22": "CHG_EN1", "23": "CHG_EN2", "24": "CHG_CE_N", "27": "CHG_N", "29": "PGOOD_N",
               "49": "STATUS_LED", "42": "AFE_EN"}
    main_sheet.add("U1", "RF_Module:MDBT50Q-1MV2", "MDBT50Q-1MV2", 76.2, 99.06, rf_nets,
                   pcb=[348.3, 119.0, 90, "B"])
    for ref, row in (("R6", 0), ("R7", 1), ("R3", 2), ("R5", 3), ("R4", 4)):
        row_nets = {"1": "ROW_DRV" + str(row), "2": "ROW" + str(row)}
        if ref in ("R4", "R6"):
            row_nets = {"2": "ROW_DRV" + str(row), "1": "ROW" + str(row)}
        main_sheet.add(ref, "Device:R", "100", 137.16, 38.1 + 25.4 * row,
                       row_nets,
                       "Resistor_SMD:R_0402_1005Metric")
    main_sheet.add("J1", "Connector_Generic:Conn_01x04", "REAR_USB_DAUGHTERBOARD", 193.04, 43.18,
                   {"1": "VBUS", "2": "D-", "3": "D+", "4": "GND"}, "YAECKB:JST-SR-4")
    main_sheet.add("F1", "Device:Polyfuse", "500mA", 193.04, 66.04,
                   {"1": "USB_5V", "2": "VBUS"}, "Fuse:Fuse_1206_3216Metric")
    # Keep the upstream USB ESD part, supplying its rail from fused USB power.
    main_sheet.add("D1", "Power_Protection:PRTR5V0U2X", "PRTR5V0U2X", 193.04, 91.44,
                   {"1": "GND", "2": "D+", "3": "D-", "4": "USB_5V"}, "Package_TO_SOT_SMD:SOT-143")
    for ref, net, resistor_net, y in (("R30", "D-", "USB_DM", 121.92), ("R31", "D+", "USB_DP", 142.24)):
        main_sheet.add(ref, "Device:R", "0", 193.04, y, {"1": net, "2": resistor_net},
                       "Resistor_SMD:R_0402_1005Metric", [337.5, 126 + (0 if ref == "R30" else 2), 0, "B"])
    for ref, value, net, x, y in (("C30", "10u/10V", "+3.3V", 40.64, 172.72),
                                  ("C31", "100n/16V", "+3.3V", 66.04, 172.72),
                                  ("C32", "4.7u/10V", "USB_5V", 91.44, 172.72),
                                  ("C13", "1u", "AFE_3V3", 187.96, 172.72)):
        main_sheet.add(ref, "Device:C", value, x, y, {"1": net, "2": "GND"},
                       "Capacitor_SMD:C_0603_1608Metric" if ref in ("C30", "C32") else "Capacitor_SMD:C_0402_1005Metric")
    main_sheet.add("R26", "Device:R", "10k", 40.64, 208.28, {"1": "+3.3V", "2": "RESET_N"}, "Resistor_SMD:R_0402_1005Metric")
    main_sheet.add("SW1", "Switch:SW_Push", "EVQPUC02K_RESET", 76.2, 208.28,
                   {"1": "RESET_N", "2": "GND"}, "Button_Switch_SMD:Panasonic_EVQPUL_EVQPUC",
                   [326, 119, 0, "B"])
    main_sheet.add("J3", "Connector_Generic:Conn_02x03_Odd_Even", "SWD_POGO", 137.16, 208.28,
                   {"1": "+3.3V", "2": "SWDIO", "3": "GND", "4": "SWDCLK", "5": "RESET_N", "6": "GND"},
                   "YAECKB:SWD_Pogo_2x03", [328, 132, 0, "B"])
    main_sheet.add("R32", "Device:R", "2.2k", 172.72, 208.28, {"1": "STATUS_LED", "2": "LED_A"}, "Resistor_SMD:R_0402_1005Metric")
    main_sheet.add("D2", "Device:LED", "STATUS", 208.28, 208.28, {"1": "GND", "2": "LED_A"}, "LED_SMD:LED_0603_1608Metric")
    main_sheet.add("#FLG01", "power:PWR_FLAG", "PWR_FLAG", 40.64, 241.3, {"1": "GND"})
    main_sheet.add("#FLG02", "power:PWR_FLAG", "PWR_FLAG", 76.2, 241.3, {"1": "VBUS"})
    main_sheet.add("#FLG03", "power:PWR_FLAG", "PWR_FLAG", 111.76, 241.3, {"1": "USB_5V"})
    main_sheet.note("ONE MCU ONLY / STM32 and inter-MCU SPI removed / LFCLK uses internal RC", 111.76, 256.54)
    main_sheet.note("External Type-C on REAR daughterboard only; J1 pin 1/2/3/4 = 5V / D- / D+ / GND", 111.76, 264.16)

    charger_nets = {"1": "BAT_NTC", "2": "BAT_CELL", "3": "BAT_CELL", "4": "CHG_CE_N",
                    "5": "CHG_EN2", "6": "CHG_EN1", "7": "PGOOD_N", "8": "GND", "9": "CHG_N",
                    "10": "VSYS", "11": "VSYS", "12": "ILIM_SET", "13": "USB_5V", "16": "ICHG_SET", "17": "GND"}
    power.add("U5", "Battery_Management:BQ24074RGT", "BQ24074RGT", 66.04, 60.96, charger_nets,
              pcb=[118, 145, 0, "B"])
    regulator_nets = {"1": "+3.3V", "2": "BUCK_L2", "3": "GND", "4": "BUCK_L1", "5": "VSYS",
                      "6": "REG_EN", "7": "GND", "8": "REG_VINA", "9": "GND", "10": "+3.3V", "11": "GND"}
    power.add("U6", "Regulator_Switching:TPS63031DSK", "TPS63031DSK", 180.34, 60.96, regulator_nets,
              pcb=[133, 145, 0, "B"])
    power.add("L1", "Device:L", "1.5uH_74438336015", 218.44, 60.96,
              {"1": "BUCK_L1", "2": "BUCK_L2"}, "Inductor_SMD:L_Wuerth_MAPI-3015", [133, 139, 0, "B"])
    for ref, value, net1, net2, x, y in (
        ("R40", "8.87k/1%", "ICHG_SET", "GND", 30.48, 104.14),
        ("R41", "7.50k/1%", "ILIM_SET", "GND", 60.96, 104.14),
        ("R42", "100k", "CHG_EN1", "GND", 91.44, 104.14),
        ("R43", "100k", "CHG_EN2", "GND", 121.92, 104.14),
        ("R44", "100k", "CHG_CE_N", "GND", 152.4, 104.14),
        ("R45", "100k", "CHG_N", "+3.3V", 182.88, 104.14),
        ("R46", "100k", "PGOOD_N", "+3.3V", 213.36, 104.14),
        ("R47", "100", "VSYS", "REG_VINA", 243.84, 104.14),
        ("R48", "100k", "REG_EN", "GND", 274.32, 104.14)):
        power.add(ref, "Device:R", value, x, y, {"1": net1, "2": net2}, "Resistor_SMD:R_0402_1005Metric")
    power.add("SW100", "Switch:SW_SPDT", "JS102011SAQN_POWER", 274.32, 60.96,
              {"1": "VSYS", "2": "REG_EN", "3": "GND"}, "Button_Switch_SMD:SW_SPDT_CK_JS102011SAQN",
              [109, 119, 0, "B"])
    for ref, value, net, x, y in (("C40", "1u/10V", "USB_5V", 30.48, 139.7),
                                  ("C41", "10u/10V", "BAT_CELL", 60.96, 139.7),
                                  ("C42", "10u/10V", "VSYS", 91.44, 139.7),
                                  ("C43", "10u/10V", "VSYS", 121.92, 139.7),
                                  ("C44", "100n/16V", "REG_VINA", 152.4, 139.7),
                                  ("C45", "10u/10V", "+3.3V", 182.88, 139.7),
                                  ("C46", "10u/10V", "+3.3V", 213.36, 139.7)):
        power.add(ref, "Device:C", value, x, y, {"1": net, "2": "GND"}, "Capacitor_SMD:C_0603_1608Metric")
    power.add("J2", "Connector_Generic:Conn_01x03", "PROTECTED_1S_4V2_NTC10K", 335.28, 60.96,
              {"1": "BAT_CELL", "2": "GND", "3": "BAT_NTC"},
              "Connector_JST:JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal", [152, 120, 0, "B"])
    for ref, vin, vout, en, x in (("U7", "BAT_CELL", "BAT_MEAS_TOP", "BAT_MEAS_EN", 71.12),
                                  ("U8", "+3.3V", "AFE_3V3", "AFE_EN", 208.28)):
        definition = library_symbol("Power_Management:TPS22919DCK")
        nets_by_name = {"IN": vin, "OUT": vout, "ON": en, "GND": "GND", "QOD": vout + "_QOD"}
        pins = {n: nets_by_name[p["name"]] for n, p in symbol_pins(definition).items() if p["name"] in nets_by_name}
        power.add(ref, "Power_Management:TPS22919DCK", "TPS22919DCK", x, 198.12, pins,
                  pcb=[144 if ref == "U7" else 107, 143, 0, "B"])
    for ref, value, first, second, x in (("R49", "100k", "BAT_MEAS_EN", "GND", 30.48),
                                        ("R50", "100k", "AFE_EN", "GND", 60.96),
                                        ("R51", "1M/1%", "BAT_MEAS_TOP", "BAT_ADC", 91.44),
                                        ("R52", "1M/1%", "BAT_ADC", "GND", 121.92),
                                        ("R53", "100", "BAT_MEAS_TOP_QOD", "BAT_MEAS_TOP", 152.4),
                                        ("R54", "100", "AFE_3V3_QOD", "AFE_3V3", 182.88)):
        power.add(ref, "Device:R", value, x, 241.3, {"1": first, "2": second}, "Resistor_SMD:R_0402_1005Metric")
    power.add("C47", "Device:C", "10n", 213.36, 241.3, {"1": "BAT_ADC", "2": "GND"}, "Capacitor_SMD:C_0402_1005Metric")
    power.add("C48", "Device:C", "1u/10V", 243.84, 241.3, {"1": "AFE_3V3", "2": "GND"}, "Capacitor_SMD:C_0402_1005Metric")
    power.note("Protected 1S 4.2V Li-ion pack with 10k 103AT-2-compatible NTC required; J2 is not an unprotected-cell input", 205, 270)
    power.note("Default USB100; firmware controls EN1/EN2 for enumeration/suspend. ICHG approx 100mA. TMR/ITERM NC = datasheet defaults", 205, 278)

    # Retain the original electrode, analog and mounting sheets, changing only
    # the analog supply to the controllable AFE rail.
    original = loads((SOURCE / "EC60.kicad_sch").read_text())
    for index, name in enumerate(("matrix", "analog", "mounting"), 2):
        content = loads((SOURCE / (name + ".kicad_sch")).read_text())
        if name == "analog":
            for instance in children(content, "symbol"):
                if child(instance, "lib_id")[1] == "power:+3.3V":
                    for p in children(instance, "property"):
                        if p[1] == "Value":
                            p[2] = "AFE_3V3"
            for group in children(content, "symbol_instances"):
                for path in children(group, "path"):
                    if child(path, "value")[1] == "+3.3V":
                        child(path, "value")[1] = "AFE_3V3"
        identifiers = {}
        for definition in children(child(content, "lib_symbols"), "symbol"):
            old_id = str(definition[1])
            old_name = old_id.split(":")[-1]
            local_name = "Source_" + old_id.replace(":", "_")
            identifiers[old_id] = "YAECKB:" + local_name
            definition[1] = identifiers[old_id]
            for unit in children(definition, "symbol"):
                unit[1] = str(unit[1]).replace(old_name + "_", local_name + "_", 1)
            SYMBOLS[local_name] = copy.deepcopy(definition)
        def relink(node):
            if not isinstance(node, list):
                return
            if node and node[0] == "lib_id":
                node[1] = identifiers[node[1]]
            elif len(node) >= 3 and node[0] == "property" and node[1] == "Footprint":
                node[2] = str(node[2]).replace("cipulot_parts:", "YAECKB:")
            elif len(node) >= 2 and node[0] == "footprint":
                node[1] = str(node[1]).replace("cipulot_parts:", "YAECKB:")
            for value in node:
                if isinstance(value, list):
                    relink(value)
        relink(content)
        reconcile(content, FROZEN, APPROVED_FILTERS)
        for instance in children(content, "symbol"):
            props = {p[1]: p for p in children(instance, "property")}
            ref = props.get("Reference", [None, None, None])[2]
            if ref in FROZEN and "Footprint" in props:
                props["Footprint"][2] = FROZEN[ref]["id"]
        for definition in children(child(content, "lib_symbols"), "symbol"):
            SYMBOLS[str(definition[1]).split(":")[-1]] = copy.deepcopy(definition)
        (DEST / (name + ".kicad_sch")).write_text(dumps(content) + "\n")
        old_sheet = next(s for s in children(original, "sheet")
                         if any(p[1] == "Sheet file" and p[2] == name + ".kicad_sch" for p in children(s, "property")))
        sheet = copy.deepcopy(old_sheet)
        old_at = child(sheet, "at")
        new_y = {"analog": 106.68, "matrix": 157.48, "mounting": 208.28}[name]
        dx, dy = 294.64 - float(old_at[1]), new_y - float(old_at[2])
        old_at[1:] = [294.64, new_y]
        for field in children(sheet, "property"):
            at = child(field, "at")
            at[1], at[2] = round(float(at[1]) + dx, 5), round(float(at[2]) + dy, 5)
        main_sheet.root.append(sheet)
    power_sheet = F("sheet", F("at", 294.64, 55.88), F("size", 63.5, 25.4),
                    F("fields_autoplaced"), F("stroke", F("width", 0), F("type", A("default"))),
                    F("fill", F("color", 0, 0, 0, 0)), F("uuid", A(uid("sheet-ref/power"))),
                    prop("Sheet name", "power", 294.64, 54.61), prop("Sheet file", "power.kicad_sch", 294.64, 82.55))
    main_sheet.root.append(power_sheet)
    main_sheet.root.append(F("sheet_instances", F("path", "/", F("page", "1"))))
    main_sheet.write()
    power.write()
    library = F("kicad_symbol_lib", F("version", 20250114), F("generator", A("kicad_symbol_editor")))
    for name, definition in SYMBOLS.items():
        sym = copy.deepcopy(definition)
        sym[1] = name
        extend_filters(sym, APPROVED_FILTERS)
        library.append(sym)
    (DEST / "YAECKB.kicad_sym").write_text(dumps(library) + "\n")
    (DEST / "sym-lib-table").write_text('(sym_lib_table (lib (name "YAECKB") (type "KiCad") (uri "${KIPRJMOD}/YAECKB.kicad_sym") (options "") (descr "Single nRF52840 design")))\n')
    project_file = DEST / (PROJECT + ".kicad_pro")
    if not project_file.exists():
        project_file.write_text(json.dumps({"meta": {"filename": PROJECT + ".kicad_pro", "version": 1}}, indent=2) + "\n")
    (DEST / "components.json").write_text(json.dumps(PARTS, ensure_ascii=False, indent=2) + "\n")
    (DEST / "pinmap.json").write_text(json.dumps({"mcu": "nRF52840", "module": "MDBT50Q-1MV2", "mcu_count": 1,
        "module_pin_nets": rf_nets, "lf_clock": "internal RC", "interference_analysis": "deferred-until-PCB-complete",
        "battery_ADC": "divider 1M/1M, 10nF; enable U7 then wait at least 50ms before sampling",
        "AFE_power": "enable U8 then settle/calibrate; GPIOs must not back-power disabled AFE",
        "USB": "rear daughterboard to J1; nRF native USB"}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
