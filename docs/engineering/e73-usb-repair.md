English | [Chinese](e73-usb-repair.zh-CN.md)

# E73 USB repair checkpoint

**This is an isolated, unreleased candidate.** The selected E73 mainboard, fabrication ZIPs, firmware images and assembly instructions have not been replaced. The [complete E73 review](../audit/e73-review.md) remains on design hold. The existing UDB-C-JSH C5 is unchanged.

The candidate is a real [KiCad project](../../hardware/e73-usb-repair/EC60-nRF52840.kicad_pro), with all five schematic sheets, frozen footprints, an exported netlist and a [replay specification](../../hardware/e73-usb-repair-spec.json). Run it through its own checks; a passing Raytac report does not accept this board.

## Electrical change

The original E73 mainboard routes USB about 255 mm and has long mainboard TVS branches. This candidate removes D1, R30 and R31, adds a four-pin J4 beside the E73 module, and returns input power to the existing left circuit through J5 and J1. C5's real protected data channels and both protection grounds are checked independently. Removing mainboard D1 does not itself prove ESD protection.

| Connection | Candidate assignment |
|---|---|
| C5 J2.1, VBUS | J4.1, USB_FEED |
| C5 J2.2, DN | J4.2, USB_DM → E73 U1.29 |
| C5 J2.3, DP | J4.3, USB_DP → E73 U1.31 |
| C5 J2.4, GND | J4.4, GND |
| J5.1, USB_FEED | J1.1, VBUS, existing left power input |
| J5.2, GND | J1.4, GND |
| J1.2 / J1.3 | Intentionally unconnected; do not populate these cable contacts |

J4 is at PCB **(346.1, 110.7) mm, 90°**, opening toward decreasing PCB X. This provides a side exit to study instead of moving the plug toward the front wall. J5 is at **(335.5, 117.5) mm, 0°**. C32 moves only **0.3 mm in X**, retaining its original grounding fanout; its local USB_5V connection is rerouted. A redundant upper ROW_DRV4 loop is removed including its unused junction and stem, and the RESET_N track detours around the J4 mounting land. Their logical nodes and MCU GPIO assignments remain unchanged. COL14 now bypasses the USB reference region on In2, retaining its sensing lands and adding no via. USB_FEED uses In1 locally and In2 farther left so it does not cut the data reference. The controlled specification lists every retired control-copper UUID.

All 43 E73 lands, sensing lands, board outline and mounting locations remain preserved. The data paths use 0.3 mm B.Cu traces with no data vias. The added USB_FEED route uses a 0.25 mm neck/path and ordinary 0.5 / 0.3 mm through vias. Its complete voltage-drop/current/thermal qualification is still open.

## Native evidence and limits

The [native report](../../hardware/e73-usb-repair/audit/native-check.json) records zero strict DRC errors, zero opens, zero schematic-parity errors, **266** connected signal/power pairs and **143** connected ground pairs. Both contact-aware mainboard USB paths measure approximately **9.96919 mm**; their difference is below **0.000002 mm**. These are geometric centerline results, not electrical delay, impedance or eye-diagram measurements; C5, cable and module-internal routing are excluded.

There are 102 inherited virtual-courtyard warnings. Existing non-module SMD-land/through-via overlaps are explicitly listed in the report and remain a solder-wicking/DFM issue. No new land-overlapping via, module via-in-pad, blind/buried via, filling or copper capping is introduced. The check preserves the original project rules and enables ignored categories in a disposable copy.

The [fault tests](../../tests/audit/test_e73_usb_repair.py) exercise an actual missing power component/netlist hierarchy, swapped data pins, a cut USB route, a moved E73 land, a changed retained control net, a new module via-in-pad, incorrect J1 data reconnection, and missing C5 protected I/O/ground. Their [result](../../hardware/e73-usb-repair/audit/fault-tests.json) is separate from physical acceptance.

The [reference and local-model checkpoint](e73-usb-return.md) evaluates the complete native data copper, independent ground connectivity, real pre-repair/fault cases and J4/J5/C32 native STEP landing. These companion reports supply results not assessed by the native-only stage.

## Material difference

Use the candidate's [stock-adjusted purchase table](../../hardware/e73-usb-repair/mainboard-purchase.csv) only to review this candidate. The canonical mainboard list describes a different PCB.

| Change | Quantity per candidate mainboard |
|---|---:|
| Remove D1, PRTR5V0U2X / SOT-143 | 1 |
| Remove R30 / R31, 0 Ω / 0402 | 2 |
| Add J4, JST SM04B-SRSS-TB(LF)(SN), SH 1.0 mm side-entry four-pin | 1 |
| Add J5, JST SM02B-SRSS-TB(LF)(SN), SH 1.0 mm side-entry two-pin | 1 |

The resulting mainboard has **75 fitted parts: 8 planned stock uses and 67 purchases**. This does not include the battery, C5, mating housings, contacts, cables or mechanical parts. Complete E73 housing/contact choices, cable cut lengths, routing guides and assembly drawings must be finalized together. The original inventory workbook is not modified or published.

## Reproduce

Use KiCad's bundled Python for these commands, from the repository root:

```sh
python scripts/build_e73_usb_repair.py
python scripts/check_e73_usb_repair.py
python tests/audit/test_e73_usb_repair.py
python scripts/export_e73_usb_ground.py
```

The builder checks the source-board hash, copies the complete hierarchy, refills zones and rejects automatic reassignment of retained copper nets. Its ledger hashes the source and candidate libraries, sheets, netlist and purchase CSV. The ground exporter reads actual filled polygons without editing the PCB; its export alone does not accept return continuity.

Remaining work includes cable/module return and full USB SI qualification, the full plug-withdrawal/tolerance envelopes, nine-wire harness and service motion, battery connector repair, left power layout and thermal/package closure, native 3D-model closure, matched firmware/calibration identity, new CAM and supplier/physical testing. **Do not order this candidate as an accepted board or use the canonical firmware/CAM as its matched release.**
