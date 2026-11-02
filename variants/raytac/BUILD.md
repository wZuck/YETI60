English | [Chinese](BUILD.zh-CN.md)

# YETI60 Raytac: ordering and build handbook

Use only **MDBT50Q-1MV2**, this directory's mainboard and its firmware. Quantities are per keyboard, excluding spares and factory minimums. Recompute stock allocation for multiple units; do not spend the same received item twice.

**Release state: all 52 implemented software/CAD audit stages passed; not released for ordering.** USB repair, C5 channel checks, full regression, four rendered views and fabrication outputs are synchronized. The mechanism is NiZ with separate plate-mounted stabilizers and a new 1.6 mm plate; first-article fit, custom pack and supplier acceptance remain open. Do not mix old archives with this revision.

| Task | Open |
|---|---|
| PCB files and order selections | [Ordering table](docs/build/ordering.md) |
| All materials and existing inventory | [Complete checklist](README.md#complete-materials-for-one-keyboard), [net-purchase CSV](hardware/bom/mainboard-purchase.csv), [materials](docs/engineering/materials.md) |
| Selected housings, domes, stabilizers and caps | [NiZ / plate-mount purchases and installation](docs/build/key-mechanism.md) |
| Solder from a bare board | [Execution order and inspection stops](docs/build/soldering.md), [28 illustrated steps](docs/assembly/build-guide.md) |
| Assemble a bare C5 | [Seven parts with stock allocation](hardware/bom/daughterboard.csv), illustrated steps 12–13 |
| Internal cables | [Pinout, lengths and routing](docs/engineering/interconnects.md) |
| Case, plate and standoffs | [Dimensions and assembly](docs/engineering/assembly.md), [mechanical outputs](../../mechanical/generated/) |
| Assembly appearance | [Complete explosion and 75-part index](docs/engineering/exploded.md), [assembly renders](renders/yeti60-assembly/README.md), [PCB animation](renders/ec60-nrf52840/README.md) |
| Flash and calibrate | [Wiring, flash commands and serial capture](docs/build/flashing.md), [firmware details](firmware/target/README.md), [60-key commands](firmware/target/calibration-keys.csv) |
| Acceptance | [Physical test procedure](docs/testing/README.md), [variant audit](docs/audit/outcome.json) |
| Battery and consumption | [Pack specification](docs/engineering/battery-pack-specification.md), [calculations and assumptions](docs/engineering/power-budget.md) |

Direct mechanical outputs: [top STEP](../../mechanical/generated/yeti60-top.step), [bottom STEP](../../mechanical/generated/yeti60-bottom.step), [standoff STEP](../../mechanical/generated/yeti60-standoff-46.step), [plate DXF](../../mechanical/felk60_plate_hhkb.plate-mount.dxf), [five guides](../../mechanical/generated/interconnect-guides/).

## Prepare per unit

Prepare two mainboards for the prototype campaign if practical; assemble and test the first before soldering the second.

- One mainboard and bottom stencil; 75 fitted parts, with 10 planned from received inventory and 65 net purchases. JP1 stays empty. Mainboard D1 is removed; do not purchase PRTR5V0U2X for this revision.
- One populated C5 JSH. Alternatively one bare C5 and seven parts: two inventory 5.1 kohm resistors and five purchases. Do not buy both options. **C5 D1 and U1 remain mandatory.**
- One internal four-wire USB harness, one external USB data cable, and one protected pack with three-wire harness. Verify each pin; colors do not establish polarity.
- K01-K07 from the [NiZ / steel-plate stabilizer shopping list](docs/build/key-mechanism.md): 60 ordinary NiZ housings/sliders and original rings, 60 NiZ springs, one 45g dome sheet, three GMK Plate mount pairs, one separate Cherry-compatible 6U wire, one NicePBT BoW centered-6U cap kit and the new plate. These are separate purchases.
- Top and bottom shells, one 1.6 mm stainless plate, 28 custom brass standoffs, 28 polyimide rings, 28 PEEK washers and 28 M1.6x5 screws; four each of M3 inserts/case screws/shims and M2 inserts/daughterboard screws/insulating washers; four feet, five routing-guide pieces, gasket/insulation/retention supplies. Use the complete checklist for exact dimensions. Leave H26 empty; use 2.0 mm lower and 1.2 mm upper gasket stock.
- Shared ESD setup, microscope, tweezers, meter, controlled reflow and compatible paste, soldering iron, current-limited supply, battery simulator, SWD probe and six-pad J3 fixture, calipers, current and temperature logging; correct crimp tools for self-made harnesses.

Count unused stock physically before purchasing. Use only matching values, footprints and ratings. Charging resistors cannot be substituted by nearby values.

## Execution sequence

1. Match PCB/archive provenance, freeze exact parts and stencil/profile, and obtain manufacturing review.
2. Fabricate the mainboard and obtain a C5; defer bulk custom packs and mechanism parts.
3. Inspect dimensions, thickness, 29 holes, RF wing and sensing faces. Practise hidden-pad assembly before the mainboard.
4. Start illustrated step 01 and follow the soldering procedure. Keep the battery disconnected; inspect unpowered before current-limited power.
5. Flash the calibrator through J3 and verify rails/communications. Real released/pressed capture requires matched housings, domes and springs.
6. Verify concurrent charging and USB typing after host configuration, suspend/resume, detach-to-BLE and repeated attachment. Resolve faults before closing the case.
7. Fit standoffs, insulation, mechanisms and harnesses. Centre the PCB within the imposed +/-0.2 mm placement budget before tightening; screw clearance does not guarantee position. Inspect the RF recess and harnesses without forcing the shell shut.
8. Repeat all 60 keys and RF/interference tests after closing the shell. Flash normal firmware preserving the last 64 KiB settings partition; PCB/firmware fingerprint changes require recalibration.
9. Use a real pack only after supplier approval of the complete envelope, 4.16–4.23 V CV range, >=500 mA continuous charge rating, independent thermal interruption and three-wire pinout.

## Open work

[This review](docs/audit/raytac-review.md) confirms synchronized native PCB, firmware, images, fabrication outputs and provenance; physical acceptance remains open. Some capacitors, LED and fuse still require exact-part/derating approval, especially effective C45/C46 capacitance; nominal 20 uF does not prove regulator stability. Mechanism suppliers/local samples, resin cavity tolerances, standoffs and signed complete-pack limits remain open. No physical USB enumeration/eye, charging/thermal, key calibration or enclosed RF acceptance has occurred. Engineering prototypes provide this evidence; they are not production approval.

NiZ ordinary housings and separate steel-plate-mounted stabilizers are selected. The plate is 1.6 mm with three Cherry frame openings and 28 mounting axes; H26 is unused to clear the 6U opening. All 60 sensing centers and the case exterior are preserved. Actual clips, nominal 4.6 mm stack, housing skirt relief, wire bends and cap travel require first-article fitting.
