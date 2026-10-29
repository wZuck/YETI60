English | [Chinese](README.zh-CN.md)

# YETI60

> **Two alternatives in this branch:** the main directories use Ebyte E73-2G4M08S1C; Raytac MDBT50Q-1MV2 is in [variants/raytac](variants/raytac/README.md). See [selection instructions](docs/engineering/module-options.md). Both alternatives pass their implemented CAD/build checks. See the [combined record](docs/audit/variants.json). Physical and supplier qualification remain open.

A single-nRF52840 electrocapacitive keyboard PCB for the FELK60 case, derived from Cipulot EC60. The sensing geometry, board outline and mounting locations are retained; a rear USB daughterboard connects to J1.

> **P2 design checkpoint:** C5 JSH is retained. The default is now a custom 1600 mAh single-cell pack with a canonical recessed bottom, revised charger settings and USB500 firmware. Engineering sheets, PCB animation and assembly renders record their source hashes. See [checkpoint details](docs/design-checkpoint.md).

> **Acceptance / RF hold:** the new layout screen found antenna copper and nearby plate-metal risks. Read the [test results and first-article procedure](docs/testing/README.md) before fabrication or assembly. DRC/build passes do not close these findings.

## Current review

**Both alternatives pass their current CAD, build and integration checks; production and physical operation remain unqualified.** The [comprehensive review](docs/audit/yeti60-comprehensive-review.md) documents the implemented P2 design and remaining supplier, tolerance, harness and physical acceptance.

| Scope | Evidence and result |
|---|---|
| PCB | E73: strict DRC 0 errors / 0 opens; 270 physical signal pairs and all critical paths pass; 114 warnings (102 virtual courtyards, 7 dangling stubs, 5 via alignment). Ordinary JLC four-layer, no blind/buried/module vias-in-pad |
| Firmware | New schematic-bound control core passes host ASan/UBSan simulation; normal/calibrator target binaries now build; on-device USB/BLE and EC calibration remain pending |
| Mechanical | Source PCB/plate/case nominal geometry has no overlap at the explicitly provisional Z stack; final dome/fastener/resin tolerances are unqualified |
| Battery | Default custom 1600 mAh, complete 85×43×4.8 mm; supplier drawing/current clarification and independent thermal protection approval pending |
| Visualization | Each alternative has its own checked 28-step bilingual guide, PCB animation and source-linked assembly renders |

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

Quantities below are **net installed quantities for one complete keyboard, without spares**. Buy populated mainboard/daughterboard assemblies or their loose parts; do not count the same components twice. Unselected suppliers/MPNs are identified explicitly. A known quantity does not constitute procurement release.

**Fabrication constraint: JLC ordinary four-layer FR-4 only. The previous blind-via/filled-and-capped design has been converted to mechanically drilled through vias; do not order the old HDI files.** Use the latest fabrication review after conversion. No second controller, per-key diodes or MX hot-swap sockets are required.

### Use existing inventory first

The supplied order-derived inventory covers **10** of the 76 mainboard parts by nominal value/package, leaving **66** to purchase for one keyboard. Count the actual unused stock and qualify capacitor effective capacitance before assembly. In-transit items are excluded. The original workbook is unchanged and is not published.

| Stock MPN | References | Planned use |
|---|---|---:|
| Samsung CL05B104KO5NNNC, 100 nF / 16 V / X7R / 0402 | C9, C11, C12, C31 | 4 |
| Samsung CL05A105KA5NQNC, 1 uF / 25 V / X5R / 0402 | C13, C48 | 2 |
| Uniroyal 0402WGF0000TCE, 0 ohm / 0402 | R30, R31 | 2 |
| Uniroyal 0402WGF1001TCE, 1 kohm / 1% / 0402 | R17 | 1 |
| Uniroyal 0402WGF1002TCE, 10 kohm / 1% / 0402 | R26 | 1 |

Use the [stock-adjusted mainboard purchase CSV](hardware/bom/mainboard-purchase.csv) and [inventory decisions](docs/engineering/inventory-allocation.md) alongside the full preparation list below. Other assemblies and mechanical materials still require procurement or compatibility confirmation. A populated C5 includes its seven parts; if self-assembling a bare C5 instead, two stocked 5.1 kohm resistors can supply C5 R1/R2. The stock nice!nano, 110 mAh cell, 0805 capacitors and short PCB screws do not directly replace the specified parts. No board or case dimensions change for this allocation.

### Which PCBs to fabricate

Quantities are net boards per keyboard; the fabricator's minimum order quantity is separate. Fabricate **one mainboard** when buying a populated C5, or **one mainboard plus one C5 JSH bare board** when soldering the daughterboard yourself.

| PCB | E73: strict DRC 0 errors / 0 opens; 270 physical signal pairs and all critical paths pass; 114 warnings (102 virtual courtyards, 7 dangling stubs, 5 via alignment). Ordinary JLC four-layer, no blind/buried/module vias-in-pad |
|---|---:|---|---|
| YETI60 E73 mainboard | 1 | 285.0 x 94.6 mm outline envelope; JLC ordinary four-layer FR-4, nominal 1.6 mm, through vias only | [Editable KiCad PCB](hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb), [E73 Gerber/drill review ZIP](hardware/fabrication/yeti60-e73-p2-dfm-review.zip), [fabrication requirements](hardware/ec60-nrf52840/fabrication-notes.md) |
| Unified Daughterboard C5 JSH | 1 only for self-assembly; 0 if purchased populated | 18.0 x 16.5 mm; **four layers**, nominal 1.6 mm, ordinary through vias; 14 x 12.5 mm mounting rectangle | [Pinned upstream KiCad PCB](https://github.com/Unified-Daughterboard/UDB-C-JSH/blob/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/UDB.kicad_pcb), [download pinned Gerber/drill ZIP](https://raw.githubusercontent.com/Unified-Daughterboard/UDB-C-JSH/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/production/UDB-C-JSH_5.0_gerbers.zip), [seven loose parts](hardware/bom/daughterboard.csv) |

These are separate fabrication orders/files: the mainboard ZIP does not contain C5. Both archives contain four copper layers; do not select a two-layer process for C5. The mainboard archive is for manufacturing review, with final component/stencil and supplier acceptance still pending. J3 is part of the main PCB and needs a pogo fixture, not another PCB in this design. The stainless plate, resin shells and five routing guides are mechanical parts, not additional PCBs. For self-reflow, use mainboard **B.Paste** and C5 **F.Paste** with a qualified stencil/profile.

### Electronic assemblies, battery and cables

| Material | Quantity | Detailed specification and included items |
|---|---:|---|
| Mainboard PCB | 1 | Current YETI60 native PCB; ordinary four-layer FR-4, target nominal thickness 1.6 mm; preserve EC electrodes, outline and mounting centers; CAD envelope 1.6062 mm; review the current ordinary-process archive before ordering |
| Mainboard fitted parts | 76 | Every reference, value, package and specified/candidate MPN is listed below; included if buying a populated mainboard |
| USB daughterboard | 1 populated | Unified Daughterboard C5 JSH, commit `2b6c52a`; seven fitted components including USB-C receptacle and SH header; retain C rather than S |
| Internal USB harness | 1 four-wire | AWG28 stranded copper, insulation OD <=0.8 mm; two SHR-04V-S housings and eight SSH-003T-P0.2-H contacts included; 1-to-1 VBUS, 2-to-2 D-, 3-to-3 D+, 4-to-4 GND. 150 mm is the route centerline; individual wire-exit lengths are about 147.64/149.21/150.79/152.36 mm; preform to the controlled route |
| Battery assembly | 1 pack | Custom single-cell YETI60-BAT-1600-1S, target minimum 1600 mAh; complete pack <=85 x 43 x 4.8 mm including PCM, sensors, wrap, tabs and growth; independent thermal interruption, actual charging window within 15–43 C; supplier must accept >=500 mA continuous charging capability and the 4.16–4.23 V regulation range |
| Battery leads and plug | 1 three-wire set, included in pack | AWG28, OD <=0.8 mm; one PHR-3 housing and three SPH-004T-P0.5S contacts; pin 1 red positive, 2 black negative, 3 yellow separate 10k NTC. Independent thermal protection and third-wire NTC feedback are separate requirements; supplier-signed envelope/lead-exit drawing required |
| External USB data cable | 1 | USB-C at keyboard; USB-A or USB-C at host as appropriate; data capable, not charge-only |

### Every fitted mainboard component

0402 resistors: 1%, >=50 mW; fit 0-ohm links where specified. The 220 pF capacitor is C0G; others X5R/X7R, 10% or better, >=10 V (16 V where specified), with effective DC-biased capacitance to be qualified. Values below are current circuit requirements; unselected MPNs are not frozen parts.

| References | Quantity | Value/function | Package | Specified/candidate MPN | Planned stock use | To buy | Inventory note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C9, C11, C12 | 3 | 100n | C_0402_1005Metric | Vendor MPN unselected | 3 | 0 | In inventory: Samsung CL05B104KO5NNNC; recorded received pool 100 (shared by source row, do not sum per BOM row); count before assembly; qualify effective capacitance |
| C10 | 1 | 220p | C_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| C13 | 1 | 1u | C_0402_1005Metric | Vendor MPN unselected | 1 | 0 | In inventory: Samsung CL05A105KA5NQNC; recorded received pool 50 (shared by source row, do not sum per BOM row); count before assembly; qualify effective capacitance |
| C30, C41, C42, C43, C45, C46 | 6 | 10u/10V | C_0603_1608Metric | Vendor MPN unselected | 0 | 6 | No matched usable stock; purchase required |
| C31 | 1 | 100n/16V | C_0402_1005Metric | Vendor MPN unselected | 1 | 0 | In inventory: Samsung CL05B104KO5NNNC; recorded received pool 100 (shared by source row, do not sum per BOM row); count before assembly; qualify effective capacitance |
| C32 | 1 | 4.7u/10V | C_0603_1608Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| C40 | 1 | 1u/10V | C_0603_1608Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| C44 | 1 | 100n/16V | C_0603_1608Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| C47 | 1 | 10n | C_0402_1005Metric | Vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| C48 | 1 | 1u/10V | C_0402_1005Metric | Vendor MPN unselected | 1 | 0 | In inventory: Samsung CL05A105KA5NQNC; recorded received pool 50 (shared by source row, do not sum per BOM row); count before assembly; qualify effective capacitance |
| D1 | 1 | PRTR5V0U2X | SOT-143 | Nexperia PRTR5V0U2X | 0 | 1 | No matched usable stock; purchase required |
| D2 | 1 | STATUS | LED_0603_1608Metric | 0603 status LED; vendor MPN unselected | 0 | 1 | No matched usable stock; purchase required |
| F1 | 1 | 500mA | Fuse_1206_3216Metric | 1206 resettable fuse, 0.5 A hold | 0 | 1 | No matched usable stock; purchase required |
| J1 | 1 | REAR_USB_DAUGHTERBOARD | JST-SR-4 | JST SM04B-SRSS-TB(LF)(SN), candidate | 0 | 1 | No matched usable stock; purchase required |
| J2 | 1 | PROTECTED_1S_4V2_NTC10K | JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal | JST S3B-PH-SM4-TB(LF)(SN) | 0 | 1 | No matched usable stock; purchase required |
| L1 | 1 | 1.5uH_74438336015 | L_Wuerth_MAPI-3015 | Wurth 74438336015 | 0 | 1 | No matched usable stock; purchase required |
| R3, R4, R5, R6, R7, R47, R53, R54 | 8 | 100 | R_0402_1005Metric | Vendor MPN unselected | 0 | 8 | No matched usable stock; purchase required |
| R8, R9, R10, R11, R12, R13, R14, R15, R16, R18, R19, R20, R21, R23, R24, R25, R42, R43, R44, R45, R46, R48, R49, R50 | 24 | 100k | R_0402_1005Metric | Vendor MPN unselected | 0 | 24 | No matched usable stock; purchase required |
| R17 | 1 | 1k | R_0402_1005Metric | Vendor MPN unselected | 1 | 0 | In inventory: Uniroyal 0402WGF1001TCE; recorded received pool 100 (shared by source row, do not sum per BOM row); count before assembly |
| R26 | 1 | 10k | R_0402_1005Metric | Vendor MPN unselected | 1 | 0 | In inventory: Uniroyal 0402WGF1002TCE; recorded received pool 100 (shared by source row, do not sum per BOM row); count before assembly |
| R30, R31 | 2 | 0 | R_0402_1005Metric | Vendor MPN unselected | 2 | 0 | In inventory: Uniroyal 0402WGF0000TCE; recorded received pool 100 (shared by source row, do not sum per BOM row); count before assembly |
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
| U5 | 1 | BQ24074RGT | VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm | TI BQ24074RGTR | 0 | 1 | No matched usable stock; purchase required |
| U6 | 1 | TPS63031DSK | WSON-10-1EP_2.5x2.5mm_P0.5mm_EP1.2x2mm | TI TPS63031DSKR | 0 | 1 | No matched usable stock; purchase required |
| U7, U8 | 2 | TPS22919DCK | SOT-363_SC-70-6 | TI TPS22919DCKR | 0 | 2 | No matched usable stock; purchase required |

JP1 quantity is **0**, DNP. J3 is six PCB SWD contact pads, with no fitted header. Mainboard totals: 43 resistors, 17 capacitors and 16 other components = 76.

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
| M02 | Bottom shell | 1 | Default P2 derived STEP with 1600 mAh recess; unchanged exterior |
| M03 | Plate | 1 | Audited HHKB DXF; 1.2 mm stainless steel, tapped M2 at 29 matched mounting centers; deburr and insulate |
| M04 | EC slider/housing sets | 60 | Matched independently mountable Topre-compatible sets; two wide openings need stabilized housings; supplier/plate fit not frozen |
| M05 | Rubber domes | 60 positions | Matched to housings, travel and PCB sensing geometry; a sheet may supply multiple positions |
| M06 | Conical EC springs | 60 | Matched to domes; these are electrical sensing elements, not MX switch springs |
| M07 | Stabilizers and spacebar hardware | 1 matched set | Return, left Shift and 6U HHKB spacebar; retain the donor clips/wires and confirm exact cap stem spacing |
| M08 | Keycaps | 60 | Topre-compatible HHKB set including 6U spacebar; generic MX caps require compatible sliders and a separate fit check |
| M09 | Adapter standoffs | 29 | YETI60-STANDOFF-46, brass Ø3.5, shoulder 4.50±0.03; top M2×0.4 stud 1.0; bottom M1.6×0.35 female depth 3.2 |
| M10 | Top insulating films | 29 | Polyimide, 0.10±0.02 mm, OD 4.5 / ID 1.8; isolate brass shoulder from PCB sensing copper |
| M11 | PCB screws | 29 | M1.6×5 pan head; head envelope and actual threads require first-article confirmation |
| M12 | PCB washers | 29 | PEEK, OD≤4.0, ID 2.2, thickness 0.8 mm; not conductive metal washers against PCB |
| M13 | Top-shell inserts | 4 | Cold-bonded knurled brass M3×0.5, OD 4.6, length 3.0; bores Ø4.85±0.05, depth 3.5 |
| M14 | Daughterboard inserts | 4 | Cold-bonded brass M2×0.4, OD 3.2, length 2.5; bores Ø3.35±0.05, depth 2.9 |
| M15 | Shell closure screws | 4 | M3×5 with 0.30 mm shim washer; proposed from CAD seat z=2.59 and insert entry z=4.79; nominal engagement 2.50 mm, verify head Ø≤5.6 in Ø5.8 recess |
| M16 | Daughterboard screws | 4 | M2×4 with 0.30 mm insulating washer; nominal thread engagement 4−1.6062−0.30=2.0938 mm in 2.5 mm insert; head clearance to connector requires check |
| M17 | Gasket stock | 1 set | 2 mm sheet cut to existing ledges; nominal 50% compression gives 1 mm each side of plate; do not fill USB/cable/service clearances |
| M18 | Case feet | 4 | [SKUF silicone feet](https://keeb.io/products/skuf-silicone-rubber-keyboard-feet), 41.8 x 5.8 x 2 mm, 45A, adhesive backed; four approximately 42.2 x 6.2 mm case pockets. One 8-pack leaves four spares |
| M19 | Insert adhesive | As needed | Resin-compatible structural epoxy; cold-bond only, cure per adhesive/resin supplier, keep thread bores clear |
| M20 | Battery retention and insulation | 1 set | Nonconductive removable retention and edge protection; include tape thickness in the pocket budget; do not clamp the pouch |

**The key mechanism is not frozen.** Sixty independently mountable housing/slider sets must suit this 1.2 mm plate. Do not assume an original HHKB's housings can be removed from its integrated plate. Domes, conical springs, stabilizers and caps must form a matched system; qualify normal, wide and 6U-spacebar local samples first.

### Additional retention parts and consumables

| Material | Quantity | Specification/inclusion |
|---|---:|---|
| Shell screw shims | 4 | 0.30 mm thick, M3 clearance, used with the four M3 x 5 screws above; OD must fit the screw seat |
| Daughterboard insulating washers | 4 | 0.30 mm thick, M2 clearance, for four M2 x 4 screws |
| Rear harness guide bases | 2 | One each of `mechanical/generated/interconnect-guides/rear-1-base` and `rear-2-base` STEP/STL; current width 5.4 and route-direction length 2 mm |
| Rear removable bridges | 2 | One each of `rear-1-bridge` and `rear-2-bridge`; three lower battery wires/four upper USB wires, groove radius 0.5 mm |
| Front USB guide | 1 | `front-base` STEP/STL, width 6 and route-direction length 1.8 mm; install in case coordinates without scaling |
| Polyimide insulation stock | 1 sheet | At least 100 x 100 x 0.10 mm; supplies the 29 insulating discs; do not double-count pre-cut parts. Upper harness retention uses the separately listed adhesive-backed film |
| Gasket stock | 1 sheet | Suggested purchase >=330 x 260 x 2 mm, cut separately for both sides of the plate; stock quantity replaces M17's one-set allowance; material/hardness unselected |
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
| Back-side stencil | 1 (self-reflow only) | Laser cut from current B.Paste Gerber; 0.10 mm stainless prototype proposal, final thickness/thermal-pad apertures require assembly-process acceptance |
| Plate tapping tools | 1 set (self-machined plate only) | M2 x 0.4 tap and matching pilot-hole tools; do not retap a supplied finished plate unnecessarily |
| Insert-bore finishing tools | 1 set (unless supplied finished) | Finish to diameter 4.85 +/-0.05 and 3.35 +/-0.05 mm and specified depths; unmeasured printed bores are not equivalent |
| Current-limited supply, battery simulator, current logger and temperature probes | 1 each (prototype qualification) | Bring-up, charging/termination/thermal/runtime acceptance; not fitted parts |

See [materials](docs/engineering/materials.md) and [power/charging calculations](docs/engineering/power-budget.md) for purchasing limits. Supplier pack approval, unselected parts, key mechanism and ordinary-process conversion acceptance remain required before treating this preparation list as a production purchase order.
