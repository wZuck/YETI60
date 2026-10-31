English | [Chinese](inventory-allocation.zh-CN.md)

# YETI60 inventory allocation and remaining purchases

Revision P2, 2026-10-29. For one keyboard with a loose-part mainboard build and a **populated C5 JSH** daughterboard, plan **10 mainboard parts from inventory and 66 to buy**. These are component counts, not distinct SKUs. No PCB, firmware, case or battery specification changes are needed for these stock selections.

The [mainboard purchase CSV](../../hardware/bom/mainboard-purchase.csv) gives every fitted reference, required quantity, planned stock use and net purchase. Use it with the [complete preparation list](../../README.md#complete-materials-for-one-keyboard) for the case, EC mechanisms, battery, cables, guides, consumables and tools. Those other items have no confirmed direct stock allocation and still need procurement or a physical compatibility check.

## Stock allocated to the mainboard

The README mainboard and optional C5 tables show stock use, remaining purchases and an inventory note on each component row. Received pool counts are shared by inventory source row: C9/C11/C12 and C31 draw from the same 100-part pool, not separate pools. The same-family C5 USB receptacle is marked as unconfirmed stock and receives no purchase credit. The allocation generator updates both language tables; the materials check rejects stale quantities or notes.

| Inventory row | Stock MPN and rating | Recorded received units | Recorded in transit, excluded | References | Use | Recorded balance after planned use |
|---|---|---:|---:|---|---:|---:|
| 48 | Samsung CL05B104KO5NNNC, 100 nF, 16 V, 10%, X7R, 0402 | 100 | 100 | C9, C11, C12, C31 | 4 | 96 |
| 57 | Samsung CL05A105KA5NQNC, 1 uF, 25 V, 10%, X5R, 0402 | 50 | 100 | C13, C48 | 2 | 48 |
| 50 | Uniroyal 0402WGF0000TCE, 0 ohm, 0402 | 100 | 100 | R30, R31 | 2 | 98 |
| 51 | Uniroyal 0402WGF1001TCE, 1 kohm, 1%, 62.5 mW, 0402 | 100 | 100 | R17 | 1 | 99 |
| 52 | Uniroyal 0402WGF1002TCE, 10 kohm, 1%, 62.5 mW, 0402 | 100 | 100 | R26 | 1 | 99 |

The capacitor family specifications and sizes match the nominal circuit requirements. This does not establish effective capacitance under DC bias or verify the identity/condition of an actual stored part. Preserve the existing capacitor qualification requirement, including the relevant 3.3 V operating bias. Check the reel labels and actual unused quantity before assembly. The zero-ohm parts are jumpers; their current rating, rather than a nominal resistor power rating or a claimed 1% tolerance at zero, governs that use.

The workbook is an order-derived inventory, not a current physical count. Column E is received **units**, column H is in-transit units; column D is purchase packs and is not the available-unit input. The figures above are planning balances, not stock ledger deductions. No stock has been marked consumed and the source workbook remains unchanged.

For each stock pool: `available = recorded received units`; allocate at most that quantity across all matching references. For each BOM group: `net purchase = required − planned stock allocation`. Summing the fitted references gives `76 − (4 + 2 + 2 + 1 + 1) = 66`. In-transit units contribute zero. JP1 remains DNP and J3 remains bare SWD pads.

## C5 JSH alternatives and uncertain stock

The default is one populated daughterboard. Its seven parts are included, so do not buy them again. For a separate **bare C5 PCB build**, inventory row 55 supplies two Uniroyal 0402WGF5101TCE 5.1 kohm/1%/0402 resistors for C5 R1/R2, from 100 recorded received units. That alternative uses 12 stocked electronics in total across both boards and still needs the other five C5 parts. It does not reduce the 66-part mainboard shortfall. The [pinned upstream C5 BOM](https://github.com/Unified-Daughterboard/UDB-C-JSH/blob/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/production/UDB-C-JSH_5.0_bom.csv) is authoritative for those five parts.

| Inventory rows | Candidate use | Decision and missing evidence |
|---|---|---|
| 43 | TYPE-C-31-M-12 receptacle for bare C5 J1 | Six recorded received. Family text matches, but the stock is listed as a domestic substitute, whereas upstream specifies Korean Hroparts. Confirm contact/anchor geometry, mating height and pinout before allocation. Already included with a populated C5. |
| 21 | M2 x 5, head diameter 4 mm, for daughterboard | 200 recorded received. Current design is M2 x 4 with 0.30 mm insulating washer. A 5 mm screw with that washer engages 3.0938 mm nominally, exceeding the 2.5 mm insert depth. A total 1.30 mm insulating spacer would restore 2.0938 mm engagement, but head height, connector clearance, screw/thread dimensions and retention must be checked before adoption. No credit in the default list. |
| 22 | M3 x 8, head diameter 5 mm, for shell closure | 100 recorded received. Current design is M3 x 5 with 0.30 mm shim. A total 3.30 mm spacer would restore the designed 2.50 mm thread engagement. The 5 mm head diameter fits the nominal 5.8 mm recess; actual head height, tool access, spacer seat and pitch remain unverified. No credit or new spacers in the default list. |
| 19 | Existing 133-key keycap set | Stem type, 6U spacebar and stabilizer spacing are not established. Qualify only after selecting the matched Topre-compatible slider/housing system; do not credit as 60 compatible caps. |
| 41–42 | Braided audio wire for internal harness | AWG, individual insulation OD, bend behavior and SH/PH crimp suitability are unspecified. The design requires AWG28 stranded copper with OD <=0.8 mm per conductor; keep the specified harness. |

Spacer alternatives above are dimensional screening calculations, not accepted CAD changes or an assembly instruction. Buy the canonical screws if the stock cannot pass the listed checks. The defaults and assembly drawings remain consistent.

## Stock that does not replace a current requirement

| Inventory rows | Stock | Reason / retained requirement |
|---|---|---|
| 49 | CL21A106KAYNNNE, 10 uF, 25 V, 0805 | C30/C41/C42/C43/C45/C46 require 0603. Same capacitance and higher voltage do not make a larger footprint compatible. Buy six qualified 0603 10 uF parts. |
| 48, 57 | 0402 100 nF and 1 uF capacitors | C44 and C40 are 0603. Stock allocation above deliberately excludes them. Do not shrink the charger input capacitor to reuse stock without a new electrical/layout review. |
| 44–45 | 15 pF 0402 and 20 pF 0603 | C10 requires 220 pF C0G 0402. Wrong value; the 20 pF part also has the wrong size. |
| 46, 53–54 | 10 ohm 0603, 27 ohm 0402, 4.7 kohm 0402 | No matching fitted values/packages. Do not replace USB zero-ohm links or charge/gain-setting resistors with approximate values. |
| 47, 56 | 100/600 ohm ferrite beads | Impedance at a stated frequency is not 1.5 uH inductance. L1 remains Wurth 74438336015 or a separately qualified equivalent. |
| 12 | MF-MSMF075-2, 1812, 0.75 A hold | Main F1 is 1206/0.5 A hold; C5 F1 is ASMD1206-150, 1206/1.5 A per upstream. The stock matches neither footprint/current requirement. |
| 9 | USBLC6-2SC6, SOT-23-6 | Main D1 is PRTR5V0U2X SOT-143; C5 U1 is TPD4E05U06DQAR uSON-10. Different packages/pinouts; no direct substitution. |
| 8, 39 | RP2040 and nice!nano nRF52840 board | U1 is the soldered Ebyte E73-2G4M08S1C module. Neither stock item matches its footprint. Keep the single-controller design. |
| 37 | 301230, 110 mAh cell | Does not establish the required protected 1600 mAh pack, independent thermal interruption or third-wire NTC. Programmed charging is about 403 mA typical, about 3.66C for 110 mAh, with no stock-cell rating supporting that use. Buy the specified pack; do not connect this cell to the current charger configuration. |
| 23 | M1.6 x 2 screws | Need 29 M1.6 x 5. Nominal reach is `2 − 0.8 − 1.6062 − 0.1 = −0.5062 mm`, so the stock screw cannot reach the adapter standoff. |
| 24–25 | M2 female/female 6/18 mm standoffs | Need 4.50 mm shoulder, upper M2 stud, lower M1.6 female adapter. Wrong height and thread arrangement. |
| 26–28, 30 | MSK miniature sliders; 6 x 6 mm PTS645 tactile | Do not match JS102011SAQN power-switch or EVQPUC02K reset-switch footprints/access envelopes. |
| 17–18 | 7U MX stabilizers; MX O-rings | Do not supply the matched Topre-compatible housings, domes, conical sensing springs or HHKB 6U spacebar hardware. |
| 14–15 | SK6812 RGB LEDs | Current D2 is a discrete 0603 status LED. No RGB footprint or firmware feature is specified. |
| 58 | K-704N RTV silicone | Not qualified as resin-compatible structural epoxy for inserts, nor as thin removable battery retention. Keep the specified adhesive/insulation process. |
| 6–7, 10–11, 13, 16, 20, 29, 31–36, 40 | Memory, touch/level-shifter chips, diodes, crystal, knobs/encoders, navigation switches, displays and audio plugs | No corresponding fitted requirement. These do not replace the EC analog front end or key mechanisms. |

Other non-component records are outside this allocation. No shopping/order identifiers, vendor contacts, unrelated purchase details or original workbook are published.

## Evidence and refresh

The private source is identified by SHA-256 `8a93ff0d1690e40ed8a3c9b1988946915bd4c6c8dc82e189426a1ef25d8a10de`; row locators above refer to its inventory-detail worksheet. Only relevant stock fields are transcribed to [the allocation input](../../hardware/bom/inventory-allocation.json). The file is a snapshot, not a synchronized inventory service. If stock is consumed elsewhere or a shipment arrives, update the sanitized quantities after counting and regenerate with `python3 scripts/plan_yeti60_inventory.py`.

Manufacturer checks: [Samsung MLCC catalog, January 2024](https://www.samsungsem.com/resources/file/kr/support/product_catalog/MLCC_2401.pdf), printed pages 50 and 63, lists CL05A105KA5NQN# and CL05B104KO5NNN# with the sizes/ratings above; `#` is the ordering suffix. This is family-level evidence, with exact supplied suffix/label confirmation still required. [Uniroyal catalog, June 2024](https://www.uni-royal.cn/images/upload/UniroyalCatalog2024.06.07.pdf), pages 10–12 and 175, specifies 0402 dimensions, 1/16 W normal rating, 1 A jumper rating and the WG/F power/tolerance coding. The [current mainboard BOM](../../hardware/bom/mainboard.csv), [materials](materials.md), [interconnects](interconnects.md) and [battery pack specification](battery-pack-specification.md) define the acceptance criteria. Published supplier tables do not verify actual inventory authenticity or a measured keyboard.
