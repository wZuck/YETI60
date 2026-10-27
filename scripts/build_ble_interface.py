#!/usr/bin/env python3
"""Derive a USB-powered SPI bring-up schematic from the EC60 submodule.

This is an interface prototype, not the battery-powered production revision.
The original PCB, matrix electrodes and scanning circuits are left untouched.
"""

from pathlib import Path
import re
import shutil
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EC60/PCB/EC60_PCB"
DEST = ROOT / "hardware/ec60-ble-interface"

# Signal, STM32 pin number, schematic pin endpoint. SPI2 AF5; CS is GPIO.
SIGNALS = (
    ("BLE_CS_N", "25", 109.22, 132.08),
    ("BLE_SCK", "26", 109.22, 134.62),
    ("BLE_MISO", "27", 109.22, 137.16),
    ("BLE_MOSI", "28", 109.22, 139.70),
    ("BLE_IRQ_N", "2", 109.22, 93.98),
    ("BLE_RESET_N", "3", 109.22, 96.52),
)
CONNECTOR = ("SYS_3V3", "GND", "BLE_SCK", "BLE_MOSI", "BLE_MISO",
             "BLE_CS_N", "BLE_IRQ_N", "BLE_RESET_N")


def form_at(text, offset):
    """Return one balanced KiCad form, respecting quoted strings."""
    depth, quoted, escaped = 0, False, False
    for index in range(offset, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[offset:index + 1]
    raise ValueError("Unbalanced KiCad form")


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "yaeckb/ec60-ble-interface/" + name))


def label(name, x, y):
    return f'''  (global_label "{name}" (shape bidirectional) (at {x:g} {y:g} 180)
    (effects (font (size 1 1)) (justify right))
    (uuid {uid(f'label/{name}/{x}/{y}')}))
'''


def wire(x1, y1, x2, y2, name):
    return f'''  (wire (pts (xy {x1:g} {y1:g}) (xy {x2:g} {y2:g}))
    (stroke (width 0) (type default) (color 0 0 0 0))
    (uuid {uid(name)}))
'''


def build():
    DEST.mkdir(parents=True, exist_ok=True)
    for name in ("analog.kicad_sch", "matrix.kicad_sch", "mounting.kicad_sch"):
        shutil.copyfile(SOURCE / name, DEST / name)
    shutil.copyfile(ROOT / "EC60/LICENSE", DEST / "LICENSE.EC60")
    (DEST / "EC60-BLE-Interface.kicad_pro").write_text(
        '{"meta":{"filename":"EC60-BLE-Interface.kicad_pro","version":1}}\n')
    text = (SOURCE / "EC60.kicad_sch").read_text()
    text = text.replace('(title "EC60")', '(title "EC60 BLE interface")')
    text = text.replace('(date "2022-07-07")', '(date "2026-10-26")')
    text = text.replace('(rev "1")', '(rev "BLE-IF-0.2")')
    text = text.replace('(company "Cipulot PCB Design ")',
                        '(company "Cipulot PCB Design / YAECKB adaptation")')
    # Rename only global net labels. The physical MCU VBAT pin retains its name.
    assert text.count('(global_label "VBAT"') == 2
    text = text.replace('(global_label "VBAT"', '(global_label "SYS_3V3"')
    # VCAP1 is the internal regulator output in the UFQFPN48 package, not
    # an externally powered input. Keep a locally maintained corrected symbol.
    mcu_name = "MCU_ST_STM32F4:STM32F401CBUx"
    mcu = form_at(text, text.index('(symbol "' + mcu_name + '"'))
    corrected_mcu = mcu.replace('"' + mcu_name + '"', '"YAECKB:STM32F401CBUx_VCAP_OUT"')
    corrected_mcu = corrected_mcu.replace('(symbol "STM32F401CBUx_',
                                         '(symbol "STM32F401CBUx_VCAP_OUT_')
    expected_pin = '(pin power_in line (at -17.78 25.4 0)'
    if corrected_mcu.count(expected_pin) != 1:
        raise ValueError("Unexpected VCAP1 symbol definition")
    corrected_mcu = corrected_mcu.replace(expected_pin, '(pin power_out line (at -17.78 25.4 0)')
    text = text.replace(mcu, corrected_mcu, 1)
    text = text.replace('(lib_id "' + mcu_name + '")',
                        '(lib_id "YAECKB:STM32F401CBUx_VCAP_OUT")')
    # The USB connector is the external VBUS source. The existing 3V3 flag
    # duplicated U5's power output; move it to VBUS instead of adding a waiver.
    flag_start = text.index('  (symbol (lib_id "power:PWR_FLAG") (at 278.13 27.94 180)')
    old_flag = form_at(text, flag_start + 2)
    def move_flag(match):
        return f'(at {float(match[1]) - 173.99:g} {float(match[2]) - 1.27:g}'
    new_flag = re.sub(r'\(at (-?[\d.]+) (-?[\d.]+)', move_flag, old_flag)
    text = text.replace(old_flag, new_flag, 1)
    flag_wire = form_at(text, text.index('(wire (pts (xy 278.13 22.86) (xy 278.13 27.94))'))
    text = text.replace(flag_wire, "", 1)
    old_power = form_at(text, text.index('(symbol (lib_id "power:+3.3V") (at 278.13 22.86 0)'))
    power_uuid = re.search(r'\(uuid ([^)]+)\)', old_power)[1]
    text = text.replace(old_power, "", 1)
    power_instance = form_at(text, text.index(f'(path "/{power_uuid}"'))
    text = text.replace(power_instance, "", 1)
    additions = []
    for pin, x, y in (("PB8", 109.22, 124.46), ("PB9", 109.22, 127.0),
                      ("PA15", 142.24, 139.7)):
        additions.append(f'  (no_connect (at {x:g} {y:g}) (uuid {uid("unused/"+pin)}))\n')
    for name, _, x, y in SIGNALS:
        nc = rf'  \(no_connect \(at {x:g} {y:g}\) \(uuid [^)]+\)\)\n'
        text, count = re.subn(nc, "", text)
        assert count == 1, f"Expected one unused MCU endpoint for {name}"
        additions += [wire(96.52, y, x, y, "wire/mcu/" + name), label(name, 96.52, y)]

    lib = '''    (symbol "YAECKB:BLE_Interface_8" (pin_names (offset 1) hide)
      (in_bom yes) (on_board yes)
      (property "Reference" "J" (id 0) (at 0 5.08 0)
        (effects (font (size 1.27 1.27))))
      (property "Value" "BLE_Interface_8" (id 1) (at 0 2.54 0)
        (effects (font (size 1.27 1.27))))
      (symbol "BLE_Interface_8_1_1"
        (rectangle (start -1.27 1.27) (end 1.27 -19.05)
          (stroke (width 0.254) (type default) (color 0 0 0 0))
          (fill (type background)))
'''
    for i in range(8):
        lib += f'''        (pin passive line (at -5.08 {-i * 2.54:g} 0) (length 3.81)
          (name "Pin_{i+1}" (effects (font (size 1 1))))
          (number "{i+1}" (effects (font (size 1 1)))))
'''
    lib += "      )\n    )\n"
    (DEST / "YAECKB.kicad_sym").write_text(
        '(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\n'
        + lib.replace('"YAECKB:BLE_Interface_8"', '"BLE_Interface_8"')
        + corrected_mcu.replace('"YAECKB:STM32F401CBUx_VCAP_OUT"',
                                '"STM32F401CBUx_VCAP_OUT"') + '\n)\n')
    (DEST / "sym-lib-table").write_text(
        '(sym_lib_table\n  (lib (name "YAECKB") (type "KiCad") '
        '(uri "${KIPRJMOD}/YAECKB.kicad_sym") (options "") (descr "BLE interface"))\n)\n')
    text = text.replace("  (lib_symbols\n", "  (lib_symbols\n" + lib, 1)
    connector_uuid = uid("J2")
    additions.append(f'''  (symbol (lib_id "YAECKB:BLE_Interface_8") (at 187.96 76.2 0)
    (unit 1) (in_bom yes) (on_board yes) (uuid {connector_uuid})
    (property "Reference" "J2" (id 0) (at 187.96 71.12 0)
      (effects (font (size 1 1))))
    (property "Value" "BLE_INTERFACE_3V3_ONLY" (id 1) (at 193.675 86.36 90)
      (effects (font (size 1 1))))
    (property "Footprint" "" (id 2) (at 187.96 76.2 0)
      (effects (font (size 1 1)) hide))
''')
    for i in range(8):
        additions.append(f'    (pin "{i+1}" (uuid {uid("J2/pin/"+str(i+1))}))\n')
    additions.append("  )\n")
    for i, name in enumerate(CONNECTOR):
        y = 76.2 + i * 2.54
        additions += [wire(170.18, y, 182.88, y, "wire/J2/" + name), label(name, 170.18, y)]
    for i, note in enumerate(("SPI2 TO EXTERNAL nRF52840 / 3.3V LOGIC",
                              "USB-POWERED BRING-UP ONLY / NOT FOR FABRICATION",
                              "NO LIPO INPUT: SYS_3V3 IS THE REGULATED RAIL")):
        additions.append(f'''  (text "{note}" (at 158.75 {25.4 + i * 5.08:g} 0)
          (effects (font (size 0.85 0.85)) (justify left))
          (uuid {uid('note/'+str(i))}))
''')
    # Legacy instance table is required by the upstream KiCad 6 schematic format.
    text = text.replace("  (symbol_instances\n", f'''  (symbol_instances
    (path "/{connector_uuid}"
      (reference "J2") (unit 1) (value "BLE_INTERFACE_3V3_ONLY") (footprint ""))
''', 1)
    text = text.rstrip()[:-1] + "\n" + "".join(additions) + ")\n"
    (DEST / "EC60-BLE-Interface.kicad_sch").write_text(
        "\n".join(line.rstrip() for line in text.splitlines()) + "\n")


if __name__ == "__main__":
    if not __debug__:
        raise SystemExit("Run without -O: generation preconditions must be checked")
    build()
