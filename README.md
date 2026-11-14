English | [Chinese](README.zh-CN.md)

# YETI60

> **Active prototype: Raytac MDBT50Q-1MV2.** Start at [START-HERE.md](START-HERE.md) or the [ordering and build handbook](variants/raytac/BUILD.md) for PCB settings, inventory-adjusted materials, soldering, firmware, complete explosion and current review. E73 remains a separate option; see its [current review and build entry](BUILD.md) before using those files. Physical and supplier acceptance remain open.

A single-nRF52840 electrocapacitive keyboard PCB for the FELK60 case, derived from Cipulot EC60. The 60 effective sensing positions and mounts are retained. Raytac retains its RF wing; the E73 corner candidate restores the straight edge and front-mounts the module. C5 feeds USB through J4, with a J5/J1 power bridge.

**Wired operation:** after a computer accepts the USB configuration, the keyboard charges the battery and sends HID input over USB at the same time. USB automatically takes priority over a retained Bluetooth preference; unplugging lets ZMK fall back to the active Bluetooth profile. The E73 and Raytac options use the same policy. The 500 mA descriptor is an input budget, not a constant battery charging current.

> **P2 design checkpoint:** C5 JSH is retained. The default is now a custom 1600 mAh single-cell pack with a canonical recessed bottom, revised charger settings and USB500 firmware. Engineering sheets, PCB animation and assembly renders record their source hashes. See [checkpoint details](docs/design-checkpoint.md).

> **Acceptance hold:** E73 is now in the lower-right HHKB corner. Strict DRC has zero violation errors but zero unconnected items; earlier zero-open and firmware reports do not qualify this placement. See the [current migration review](docs/engineering/e73-hhkb-corner.md). Raytac has a separate [review](variants/raytac/BUILD.md). Neither is a production release.

## Current review

**The E73 corner version is still being routed and checked.** Start at [BUILD.md](BUILD.md). The results below describe the [corner candidate](docs/engineering/e73-hhkb-corner.md); earlier upper-right acceptance does not transfer.

| Scope | Current evidence and result |
|---|---|
| PCB | Strict DRC: 0 violation errors, zero unconnected items, 0 schematic-parity differences; 60 effective sensing positions and 43 module pad roles retained; fabrication remains on hold |
| Firmware | GPIO/ADC/mux roles retained; candidate calibration identity and normal/calibrator images still need rebuilding; old images are reference artifacts |
| Mechanical | NiZ, the 1.6 mm steel plate and 28 mounting sets retained; module/local body bounds passed, complete mechanism and harness motion still open |
| Battery | Protected 1S 1600 mAh, complete 85 × 43 × 4.8 mm envelope retained; mainboard uses a three-pin SH connector; supplier parameters and independent thermal protection remain open |
| Visualization | [Current native PCB placement](hardware/e73-hhkb-corner/audit/corner-layout.png); old 28-step guide and complete renders are pre-migration references, not this revision's assembly proof |

The remaining study and step-guide links below retain pre-migration reference records; use the corner reports above for this revision.

- [Internal connections and cable drawing](docs/engineering/interconnects.md)
- [Feasibility assessment response](docs/engineering/assessment-response.md)
- [Ordinary fabrication review package](docs/engineering/fabrication-review.md)
- [Engineering assembly sheets and sequence](docs/engineering/assembly.md)
- [28-step illustrated soldering and installation guide](docs/assembly/build-guide.md)
- [Battery recess feasibility](docs/engineering/battery-study.md)
- [Power, runtime and charging calculation](docs/engineering/power-budget.md)
- [Materials and procurement table](docs/engineering/materials.md)
- [PCB marking cleanup](docs/engineering/board-markings.md)
- [Complete review](docs/audit/yeti60-comprehensive-review.md)
- [Hardware and fabrication notes](hardware/ec60-nrf52840/README.md)
- [Firmware core, simulation and trace](firmware/yeti60/README.md)
- [Assembly renders](renders/yeti60-assembly/README.md)
- [PCB renders and 360° animation](renders/ec60-nrf52840/README.md)
- [Current audit index](docs/audit/README.md)

The case material is provisionally resin. SI/RF screening has started; antenna layout blockers and physical qualification remain open. Project-owned prose defaults to English with a parallel `.zh-CN.md`; machine-readable field names stay stable.

Based on [Cipulot/EC60](https://github.com/Cipulot/EC60) and [fredlb/felk60](https://github.com/fredlb/felk60). Upstream authors, licenses and original project names are retained. Existing `EC60-nRF52840.*` filenames and `YAECKB` library identifiers remain for technical compatibility; the public project name is **YETI60**.

## Complete materials for one keyboard

**E73 design hold:** the list below now uses NiZ, a 1.6 mm plate and 28 mounting sets. USB routing and PH connector service remain unresolved, so mainboard manufacturing is still on hold. Read the [current E73 entry](BUILD.md) first; use the [separate Raytac list](variants/raytac/BUILD.md) for that candidate. Retain the already-made C5 daughterboard.

Quantities below are **net installed quantities for one complete keyboard, without spares**. Buy populated mainboard/daughterboard assemblies or their loose parts; do not count the same components twice. Unselected suppliers/MPNs are identified explicitly. A known quantity does not constitute procurement release.

**Fabrication constraint: JLC ordinary four-layer FR-4 only. The previous blind-via/filled-and-capped design has been converted to mechanically drilled through vias; do not order the old HDI files.** Use the latest fabrication review after conversion. No second controller, per-key diodes or MX hot-swap sockets are required.

### Use existing inventory first

The supplied order-derived inventory covers **8** of the 75 current corner mainboard parts by nominal value/package, leaving **67** to purchase for one keyboard. Count the actual unused stock and qualify capacitor effective capacitance before assembly. In-transit items are excluded. The original workbook is unchanged and is not published.

| Stock MPN | References | Planned use |
|---|---|---:|
| Samsung CL05B104KO5NNNC, 100 nF / 16 V / X7R / 0402 | C9, C11, C12, C31 | 4 |
| Samsung CL05A105KA5NQNC, 1 uF / 25 V / X5R / 0402 | C13, C48 | 2 |
| Uniroyal 0402WGF1001TCE, 1 kohm / 1% / 0402 | R17 | 1 |
| Uniroyal 0402WGF1002TCE, 10 kohm / 1% / 0402 | R26 | 1 |

Use the [stock-adjusted mainboard purchase CSV](hardware/e73-hhkb-corner/mainboard-purchase.csv) and [inventory decisions](docs/engineering/inventory-allocation.md) alongside the full preparation list below. Other assemblies and mechanical materials still require procurement or compatibility confirmation. A populated C5 includes its seven parts; if self-assembling a bare C5 instead, two stocked 5.1 kohm resistors can supply C5 R1/R2. The stock nice!nano, 110 mAh cell, 0805 capacitors and short PCB screws do not directly replace the specified parts. No board or case dimensions change for this allocation.

### Which PCBs to fabricate

Quantities are net boards per keyboard; the fabricator's minimum order quantity is separate. Fabricate **one mainboard** when buying a populated C5, or **one mainboard plus one C5 JSH bare board** when soldering the daughterboard yourself.

| PCB | Quantity | Specification | Files |
|---|---:|---|---|
| YETI60 E73 mainboard | 1 | 285.0 × 94.6 mm restored straight-edge outline; JLC ordinary four-layer FR-4, nominal 1.6 mm, through vias only | [Current KiCad PCB](hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pcb), [migration gates](docs/engineering/e73-hhkb-corner.md); no fabrication package released for this revision; do not substitute old Gerbers |
| Unified Daughterboard C5 JSH | 1 only for self-assembly; 0 if purchased populated | 18.0 x 16.5 mm; **four layers**, nominal 1.6 mm, ordinary through vias; 14 x 12.5 mm mounting rectangle | [Pinned upstream KiCad PCB](https://github.com/Unified-Daughterboard/UDB-C-JSH/blob/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/UDB.kicad_pcb), [download pinned Gerber/drill ZIP](https://raw.githubusercontent.com/Unified-Daughterboard/UDB-C-JSH/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/production/UDB-C-JSH_5.0_gerbers.zip), [seven loose parts](hardware/bom/daughterboard.csv) |

No fabrication package is released for this corner mainboard. Do not substitute an old mainboard archive. C5 uses separate, unchanged four-layer files; do not order it as two layers. Reuse the already-made C5. Final stencil and supplier acceptance remain open. J3 is part of the main PCB and needs a pogo fixture, not another PCB in this design. The stainless plate, resin shells and five routing guides are mechanical parts, not additional PCBs. For self-reflow, use mainboard **F.Paste and B.Paste** (E73 on front, other parts on back) and C5 **F.Paste** with a qualified stencil/profile.

### Electronic assemblies, battery and cables

| Material | Quantity | Detailed specification and included items |
|---|---:|---|
| Mainboard PCB | 1 | Current YETI60 native PCB; ordinary four-layer FR-4, target nominal thickness 1.6 mm; preserve EC electrodes and mounting centers; use the restored straight right edge; CAD envelope 1.6062 mm; wait for this revision to be released with matching fabrication files |
| Mainboard fitted parts | 75 | Every reference, value, package and specified/candidate MPN is listed below; included if buying a populated mainboard |
| USB daughterboard | 1 populated | Unified Daughterboard C5 JSH, commit `2b6c52a`; seven fitted components including USB-C receptacle and SH header; retain C rather than S |
| Internal USB harness | 1 four-wire | AWG28 stranded copper, insulation OD ≤0.8 mm; two SHR-04V-S housings and eight SSH-003T-P0.2-H contacts; C5 to J4: 1-to-1 power, 2-to-2 D−, 3-to-3 D+, 4-to-4 GND. Complete new routing remains unqualified; do not cut to the old 150 mm figure |
| J5-to-J1 power bridge | 1 two-wire | AWG28, insulation OD ≤0.8 mm; one SHR-02V-S, one SHR-04V-S and four SSH-003T-P0.2-H contacts; J5.1→J1.1 and J5.2→J1.4, J1.2/J1.3 empty; final lengths and retention remain open |
| Battery assembly | 1 pack | Custom single-cell YETI60-BAT-1600-1S, target minimum 1600 mAh; complete pack <=85 x 43 x 4.8 mm including PCM, sensors, wrap, tabs and growth; independent thermal interruption, actual charging window within 15–43 C; supplier must accept >=500 mA continuous charging capability and the 4.16–4.23 V regulation range |
| Battery leads and plug | 1 three-wire set, included in pack | AWG28, OD <=0.8 mm; one SHR-03V-S housing and three SSH-003T-P0.2-H contacts, mating with SM03B-SRSS-TB at 1.00 mm pitch; pin 1 red positive, 2 black negative, 3 yellow separate 10k NTC. Independent thermal protection and third-wire NTC feedback are separate requirements; supplier-signed envelope/lead-exit drawing required |
| External USB data cable | 1 | USB-C at keyboard; USB-A or USB-C at host as appropriate; data capable, not charge-only |

### Every fitted mainboard component

0402 resistors: 1%, >=50 mW; fit 0-ohm links where specified. The 220 pF capacitor is C0G; others X5R/X7R, 10% or better, >=10 V (16 V where specified), with effective DC-biased capacitance to be qualified. Values below are current circuit requirements; unselected MPNs are not frozen parts.

| References | Quantity | Value/function | Package | Specified/candidate MPN | Planned stock | To buy | Stock and qualification notes |
|---|---:|---|---|---|---:|---:|---|
| C9, C11, C12 | 3 | 100n | C_0402_1005Metric | Samsung CL05B104KO5NNNC | 3 | 0 | In inventory: Samsung CL05B104KO5NNNC; recorded received pool 100 (shared by source row, do not sum per BOM row); count before assembly; qualify effective capacitance |
| C10 | 1 | 220p | C_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| C13 | 1 | 1u | C_0402_1005Metric | Samsung CL05A105KA5NQNC | 1 | 0 | In inventory: Samsung CL05A105KA5NQNC; recorded received pool 50 (shared by source row, do not sum per BOM row); count before assembly; qualify effective capacitance |
| C30 | 1 | 10u/10V | C_0603_1608Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| C41 | 1 | 22u/10V | C_0805_2012Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required; 0805 X5R/X7R; require effective capacitance >= 4.7 uF at 4.23 V including tolerance/temperature/aging; nominal value alone is insufficient. Installed height below local PCB underside <= 1.6 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| C42 | 1 | 22u/10V | C_0805_2012Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required; 0805 X5R/X7R; require effective capacitance >= 4.7 uF at 4.5 V including tolerance/temperature/aging; nominal value alone is insufficient. Installed height below local PCB underside <= 1.6 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| C43 | 1 | 22u/10V | C_0805_2012Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required; 0805 X5R/X7R; require effective capacitance >= 4.7 uF at 4.5 V including tolerance/temperature/aging; nominal value alone is insufficient. Installed height below local PCB underside <= 1.6 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| C45 | 1 | 22u/10V | C_0805_2012Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required; 0805 X5R/X7R; require effective capacitance >= 5 uF at 3.6 V including tolerance/temperature/aging; nominal value alone is insufficient. Installed height below local PCB underside <= 1.6 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| C46 | 1 | 22u/10V | C_0805_2012Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required; 0805 X5R/X7R; require effective capacitance >= 5 uF at 3.6 V including tolerance/temperature/aging; nominal value alone is insufficient. Installed height below local PCB underside <= 1.6 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| C31 | 1 | 100n/16V | C_0402_1005Metric | Samsung CL05B104KO5NNNC | 1 | 0 | In inventory: Samsung CL05B104KO5NNNC; recorded received pool 100 (shared by source row, do not sum per BOM row); count before assembly; qualify effective capacitance |
| C32 | 1 | 4.7u/16V | C_0603_1608Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required; 0603 X5R/X7R; require effective capacitance >= 2.2 uF at 5.25 V including tolerance/temperature/aging; nominal value alone is insufficient. Installed height below local PCB underside <= 1 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| C40 | 1 | 2.2u/25V | C_0805_2012Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required; 0805 X5R/X7R; require effective capacitance >= 1 uF at 5.25 V including tolerance/temperature/aging; nominal value alone is insufficient. Installed height below local PCB underside <= 1.6 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| C44 | 1 | 100n/16V | C_0603_1608Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required. Installed height below local PCB underside <= 1 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| C47 | 1 | 10n | C_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| C48 | 1 | 1u/10V | C_0402_1005Metric | Samsung CL05A105KA5NQNC | 1 | 0 | In inventory: Samsung CL05A105KA5NQNC; recorded received pool 50 (shared by source row, do not sum per BOM row); count before assembly; qualify effective capacitance |
| D2 | 1 | STATUS | LED_0603_1608Metric | 0603 status LED; vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| F1 | 1 | 1A_FAST_0466001_NRHF | Fuse_Littelfuse_0466_1206 | Littelfuse 0466001.NRHF (1 A fast, not resettable) | 0 | 1 | No matched usable stock; purchase required. Installed height below local PCB underside <= 1.2 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| J1 | 1 | USB_POWER_IN | JST-SR-4 | JST SM04B-SRSS-TB(LF)(SN), candidate | 0 | 1 | No matched usable stock; purchase required |
| J2 | 1 | PROTECTED_1S_4V2_NTC10K | JST SH 1.0 mm side-entry 3-pin | JST SM03B-SRSS-TB(LF)(SN) | 0 | 1 | No matched usable stock; purchase required; SH3 revision: protected PACK+/PACK-/NTC on pins 1/2/3; housing SHR-03V-S. Installed height below local PCB underside <= 3.2 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| L1 | 1 | 1.5uH_74438336015 | WE-MAPI 3020, 3.0 x 3.0 x 2.0 mm | Wuerth 74438336015 | 0 | 1 | No matched usable stock; purchase required. Installed height below local PCB underside <= 2.2 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| R3 | 1 | 100 | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R4 | 1 | 100 | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R5 | 1 | 100 | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R6 | 1 | 100 | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R7 | 1 | 100 | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R47 | 1 | 100 | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required. Installed height below local PCB underside <= 0.6 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| R53 | 1 | 100 | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R54 | 1 | 100 | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R8 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R9 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R10 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R11 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R12 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R13 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R14 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R15 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R16 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R18 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R19 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R20 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R21 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R23 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R24 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R25 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R42 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R43 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R44 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R45 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required. Installed height below local PCB underside <= 0.6 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| R46 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required. Installed height below local PCB underside <= 0.6 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| R48 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R49 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R50 | 1 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R17 | 1 | 1k | R_0402_1005Metric | Uniroyal 0402WGF1001TCE | 1 | 0 | In inventory: Uniroyal 0402WGF1001TCE; recorded received pool 100 (shared by source row, do not sum per BOM row); count before assembly |
| R26 | 1 | 10k | R_0402_1005Metric | Uniroyal 0402WGF1002TCE | 1 | 0 | In inventory: Uniroyal 0402WGF1002TCE; recorded received pool 100 (shared by source row, do not sum per BOM row); count before assembly |
| R32 | 1 | 2.2k | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R40 | 1 | 2.21k/1% | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R41 | 1 | 7.50k/1% | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R51, R52 | 2 | 1M/1% | R_0402_1005Metric | Vendor MPN unselected | 0 | 2 | No matched usable stock; purchase required |
| R55 | 1 | 69.8k/1% | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| R56 | 1 | 1.69k/1% | R_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| SW1 | 1 | EVQPUC02K_RESET | Panasonic_EVQPUL_EVQPUC | Panasonic EVQPUC02K | 0 | 1 | No matched usable stock; purchase required |
| SW100 | 1 | JS102011SAQN_POWER | SW_SPDT_CK_JS102011SAQN | C&K JS102011SAQN | 0 | 1 | No matched usable stock; purchase required |
| U1 | 1 | E73-2G4M08S1C | E73-2G4M08S1C | Ebyte E73-2G4M08S1C | 0 | 1 | No matched usable stock; purchase required |
| U2, U4 | 2 | 74HC4051 | TSSOP16 | Nexperia 74HC4051PW,118 | 0 | 2 | No matched usable stock; purchase required |
| U3 | 1 | OPA350 | SOIC-8_3.9x4.9mm_P1.27mm | TI OPA350UA | 0 | 1 | No matched usable stock; purchase required |
| U5 | 1 | BQ24074RGT | VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm | TI BQ24074RGTR | 0 | 1 | No matched usable stock; purchase required. Installed height below local PCB underside <= 1.2 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| U6 | 1 | TPS63031DSK | WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm | TI TPS63031DSKR | 0 | 1 | No matched usable stock; purchase required. Installed height below local PCB underside <= 1 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| U7, U8 | 2 | TPS22919DCK | SOT-363_SC-70-6 | TI TPS22919DCKR | 0 | 2 | No matched usable stock; purchase required |
| J4 | 1 | USB_C5_INPUT | JST SH 1.0 mm side-entry 4-pin | JST SM04B-SRSS-TB(LF)(SN) | 0 | 1 | No inventory credit; USB repair candidate, fabrication release still on hold. Installed height below local PCB underside <= 3.2 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |
| J5 | 1 | USB_POWER_OUT | JST SH 1.0 mm side-entry 2-pin | JST SM02B-SRSS-TB(LF)(SN) | 0 | 1 | No inventory credit; USB repair candidate, fabrication release still on hold. Installed height below local PCB underside <= 3.2 mm including solder/seating; body and placement XY growth <= 0.1 mm per direction; remaining tolerances in local fit guide. |


### Optional: solder a bare C5 JSH daughterboard

Prepare **one bare C5 JSH PCB and the seven parts below** instead of buying a populated C5. [Local stock-adjusted CSV](hardware/bom/daughterboard.csv) · [Pinned upstream BOM](https://github.com/Unified-Daughterboard/UDB-C-JSH/blob/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/production/UDB-C-JSH_5.0_bom.csv) · [Pinned upstream Gerber archive](https://github.com/Unified-Daughterboard/UDB-C-JSH/blob/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/production/UDB-C-JSH_5.0_gerbers.zip).

| References | Quantity | Manufacturer and specified MPN | Package / connector footprint | LCSC code | Planned stock use | To buy | Inventory note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | 1 | FTR SMF6.0A | SOD-123FL | C708002 | 0 | 1 | No matched usable stock; purchase required |
| F1 | 1 | Shenzhen JDT Fuse ASMD1206-150 | F1206 | C135342 | 0 | 1 | No matched usable stock; purchase required |
| J2 | 1 | JST SM04B-SRSS-TB(LF)(SN) | SM04B-SRSS-TB(LF)(SN)_mounting-reliefs | C160404 | 0 | 1 | No matched usable stock; purchase required |
| J1 | 1 | Korean Hroparts TYPE-C-31-M-12 | TYPE-C-31-M-12 | C165948 | 0 | 1 | 6 domestic substitutes recorded received; geometry/pinout unconfirmed, no credit |
| R1, R2 | 2 | Uniroyal 0402WGF5101TCE | R0402 | C25905 | 2 | 0 | Matching stock; recorded received pool 100, plan to use 2; count before assembly |
| U1 | 1 | Texas Instruments TPD4E05U06DQAR | uSON-10 | C138714 | 0 | 1 | No matched usable stock; purchase required |

The stock 5.1 kohm resistors cover R1/R2, so this option needs **five more loose parts plus one bare PCB**. The stock domestic TYPE-C-31-M-12 is not credited until its geometry is confirmed. These are daughterboard reference numbers, separate from mainboard references. The USB harness, four M2 screws and washers are separate assembly items below. LCSC codes identify the pinned upstream entries, not current prices or stock guarantees. BOM data: Copyright (c) 2023 Unified Daughterboard Project, [MIT license](hardware/usb-daughterboard/LICENSE.upstream).

### Case, EC mechanism and fasteners

| ID | Material | Quantity | Detailed specification/acceptance |
|---|---|---:|---|
| M01 | Top shell | 1 | Derived FELK60 HHKB STEP, tough SLA resin, post-cured; no exterior scaling |
| M02 | Bottom shell | 1 | Selected [E73 M01 STEP](mechanical/e73-fit/yeti60-e73-bottom-m01.step), P2 1600 mAh recess and SW100 floor relief; original exterior |
| M03 | Plate | 1 | K07 E73 M01 NiZ plate-mount DXF, 304 stainless, CAD thickness 1.60 mm, finished 1.55-1.60 mm, 28 M2 x 0.4 axes; no H26 plate mounting hole |
| M04 | NiZ housings / sliders / original rings | 60 | K01 five per pack, buy 13 packs / 65; install 60, spare 5; ordinary center housings for big keys, no Deskeys wide assembly |
| M05 | Rubber domes | 60 positions | K03 NiZ 45g sheet, one sheet; use 60 complete positions trimmed for HHKB; not included in K01 |
| M06 | Conical EC springs | 60 | K02 NiZ five per pack, buy 13 packs / 65; install 60, spare 5; not helper springs |
| M07 | Plate-mounted stabilizers / wires | 1 matched set | K04 genuine GMK Plate mount / 2u, three sets / six side units; use two short wires and separate K05 6U wire, spare one short wire |
| M08 | Keycaps | 60 | K06 NicePBT BoW current complete kit, one kit including 6.0c Centered spacebar; MX mounts |
| M09 | Adapter standoffs | 28 | YETI60-STANDOFF-46, brass OD3.5, shoulder 4.50 +/-0.03; top M2 x0.4 stud 1.0; bottom M1.6 x0.35 female depth 3.2; H26 unused |
| M10 | Top insulating films | 28 | Polyimide 0.10 +/-0.02 mm, OD4.5 / ID1.8; between standoff and PCB; H26 unused |
| M11 | PCB screws | 28 | M1.6 x5 pan head; verify actual head/thread; H26 unused |
| M12 | PCB washers | 28 | PEEK OD <=4.0, ID2.2, thickness0.8 mm; H26 unused; no conductive metal substitution |
| M13 | Top-shell inserts | 4 | Cold-bonded knurled brass M3×0.5, OD 4.6, length 3.0; bores Ø4.85±0.05, depth 3.5 |
| M14 | Daughterboard inserts | 4 | Cold-bonded brass M2×0.4, OD 3.2, length 2.5; bores Ø3.35±0.05, depth 2.9 |
| M15 | Shell closure screws | 4 | M3×5 with 0.30 mm shim washer; proposed from CAD seat z=2.59 and insert entry z=4.79; nominal engagement 2.50 mm, verify head Ø≤5.6 in Ø5.8 recess |
| M16 | Daughterboard screws | 4 | M2×4 with 0.30 mm insulating washer; nominal thread engagement 4−1.6062−0.30=2.0938 mm in 2.5 mm insert; head clearance to connector requires check |
| M17 | Gasket stock | 1 set | Four 33 x 3 mm pads per layer; lower stock 2.0 mm, upper 1.2 mm; installed gaps 1.0162 /0.5838 mm; force/creep qualification open |
| M18 | Case feet | 4 | [SKUF silicone feet](https://keeb.io/products/skuf-silicone-rubber-keyboard-feet), 41.8 x 5.8 x 2 mm, 45A, adhesive backed; four approximately 42.2 x 6.2 mm case pockets. One 8-pack leaves four spares |
| M19 | Insert adhesive | As needed | Resin-compatible structural epoxy; cold-bond only, cure per adhesive/resin supplier, keep thread bores clear |
| M20 | Battery retention and insulation | 1 set | Nonconductive removable retention and edge protection; include tape thickness in the pocket budget; do not clamp the pouch |

**The selected mechanism is NiZ plus plate-mounted stabilizers.** Use the [E73 mechanism specification](docs/build/key-mechanism.md), including the 6U wire datum, 28 mounting sets and H26 omission. Supplier plastic dimensions, retention, dome preload and full travel require local samples before metal-part production.

### Additional retention parts and consumables

| Material | Quantity | Specification/inclusion |
|---|---:|---|
| Shell screw shims | 4 | 0.30 mm thick, M3 clearance, used with the four M3 x 5 screws above; OD must fit the screw seat |
| Daughterboard insulating washers | 4 | 0.30 mm thick, M2 clearance, for four M2 x 4 screws |
| Rear harness guide bases | 2 | One each of `mechanical/generated/interconnect-guides/rear-1-base` and `rear-2-base` STEP/STL; current width 5.4 and route-direction length 2 mm |
| Rear removable bridges | 2 | One each of `rear-1-bridge` and `rear-2-bridge`; three lower battery wires/four upper USB wires, groove radius 0.5 mm |
| Front USB guide | 1 | `front-base` STEP/STL, width 6 and route-direction length 1.8 mm; install in case coordinates without scaling |
| Polyimide insulation stock | 1 sheet | At least 100 x 100 x 0.10 mm; supplies the 28 insulating discs; do not double-count pre-cut parts. Upper harness retention uses the separately listed adhesive-backed film |
| Gasket stock | 2 sheets | One >=150 x 50 x 2.0 mm lower sheet and one >=150 x 50 x 1.2 mm upper sheet; cut four 33 x 3 mm pads from each. Replaces M17 stock allowance; force/creep and adhesive qualification open |
| Resin-compatible structural adhesive | 1 small two-part kit | For inserts and guides; qualify and cure per adhesive/resin suppliers; quantity denotes a purchase package, not measured consumption |
| Removable battery tape and edge insulation | 1 set | Nominal pack-to-pocket-floor space is only 0.20 mm; tape, insulation and assembly allowance must fit that total budget; do not compress the pouch |
| Upper harness retention tape | 1 small roll, cut 3 pieces | Adhesive-backed insulating film/tape, total thickness <=0.10 mm including adhesive; wrap over the upper wires and down the guide sides |
| Removable bridge tape | 1 small roll | Nonconductive removable double-sided tape, 0.05 mm total thickness, for the two rear bridge side lands; upper film plus adhesive must total <=0.10 mm |

### Tools (shared, not one set per keyboard)

| Tool | Quantity | Use/specification |
|---|---:|---|
| nRF52840-compatible SWD probe | 1 | 3.3 V target logic, SWDIO/SWDCLK/GND/reset |
| J3 pogo fixture | 1 set | Six pins to the J3 pad drawing; 3.3 V is target reference, avoid backfeeding an already powered board |
| Multimeter | 1 | Every wire's continuity/polarity and power short checks |
| Calipers and thickness gauge | 1 each | Complete pack envelope, PCB, standoffs and insulation |
| Low-torque driver and matching bits | 1 set | M1.6/M2/M3; qualify torque against sample threads |
| Insulated switch tool | 1 | SW100 access through underside service port |
| Cutting/deburring tools and tweezers | 1 set | Gaskets/guides/assembly, without damaging battery insulation |
| Soldering, hot-air/reflow equipment, solder, flux and cleaning supplies | 1 each (self-assembly only) | Must support 0402, module and exposed-pad assembly; not installed keyboard parts |
| Mainboard stencils | 1 front + 1 back (self-reflow only) | Laser cut from matching F.Paste and B.Paste Gerbers; 0.10 mm stainless prototype proposal, final thickness/thermal-pad apertures require assembly-process acceptance |
| Plate tapping tools | 1 set (self-machined plate only) | M2 x 0.4 tap and matching pilot-hole tools; do not retap a supplied finished plate unnecessarily |
| Insert-bore finishing tools | 1 set (unless supplied finished) | Finish to diameter 4.85 +/-0.05 and 3.35 +/-0.05 mm and specified depths; unmeasured printed bores are not equivalent |
| Current-limited supply, battery simulator, current logger and temperature probes | 1 each (prototype qualification) | Bring-up, charging/termination/thermal/runtime acceptance; not fitted parts |

See [materials](docs/engineering/materials.md) and [power/charging calculations](docs/engineering/power-budget.md) for purchasing limits. Supplier pack approval, unselected parts, key mechanism and ordinary-process conversion acceptance remain required before treating this preparation list as a production purchase order.
