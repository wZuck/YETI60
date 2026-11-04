English | [Chinese](PASSIVES.zh-CN.md)

# Passive purchasing specifications — revised Raytac candidate

Choose your own supplier and brand using the specifications below. Package names here are **imperial**: 0402 = metric 1005 (1.0 × 0.5 mm), 0603 = metric 1608 (1.6 × 0.8 mm), 0805 = metric 2012 (2.0 × 1.25 mm). Do not buy metric 0402 by mistake. Quantities are fitted quantities for **one mainboard**, excluding optional spares and the separately specified C5 daughterboard. The [complete purchase table](mainboard-purchase.csv) includes active parts and inventory allocation: 75 fitted, 8 planned from stock, 67 purchases.

This revision changes seven power capacitors and their native lands; it applies only to this [candidate PCB](EC60-nRF52840.kicad_pcb). The previous fabrication archive and soldering position sheets do not include these changes. No passive brand is mandatory. Keep the selected ICs, module, fuse, inductor and connector pinouts from the complete table; a similar package alone does not make those interchangeable.

**Power detour repaired:** the regulator stage and charger capacitors are relocated; conservative feedback and C46 paths are now 3.555 mm and 4.681 mm, with all ten local paths on B.Cu. Native DRC and per-layer ground connectivity pass. See [power layout](POWER-LAYOUT.md) for positions, ordinary thermal vias and limits; first-board stability remains unverified.

## Capacitors

Use nonpolar ceramic MLCCs. Voltage ratings below are minimum ratings. X5R or X7R is acceptable where both are shown; reject Y5V/Z5U. Effective capacitance requirements below still apply when buying a higher-voltage part.

| References | Fitted | Stock / buy | Value | Package | Voltage | Tolerance | Dielectric |
|---|---:|---:|---|---|---|---|---|
| C9, C11, C12 | 3 | 3 / 0 | 100 nF | 0402 | ≥16 V | ±10% | X7R |
| C10 | 1 | 0 / 1 | 220 pF | 0402 | ≥25 V | ±5% | C0G/NP0 |
| C13 | 1 | 1 / 0 | 1 µF | 0402 | ≥10 V | ±10% | X5R/X7R |
| C30 | 1 | 0 / 1 | 10 µF | 0603 | ≥10 V | ±10% | X5R/X7R |
| C31 | 1 | 1 / 0 | 100 nF | 0402 | ≥16 V | ±10% | X7R |
| C32 | 1 | 0 / 1 | 4.7 µF | **0805** | **≥16 V** | ±10% | X5R/X7R |
| C40 | 1 | 0 / 1 | 2.2 µF | **0805** | **≥25 V** | ±10% | X5R/X7R |
| C41, C42, C43, C45, C46 | 5 | 0 / 5 | 22 µF | **0805** | ≥10 V | ±20% | X5R/X7R |
| C44 | 1 | 0 / 1 | 100 nF | 0603 | ≥16 V | ±10% | X7R |
| C47 | 1 | 0 / 1 | 10 nF | 0402 | ≥16 V | ±10% | X7R |
| C48 | 1 | 1 / 0 | 1 µF | 0402 | ≥10 V | ±10% | X5R/X7R |

The eight planned stock components include six capacitors: four Samsung CL05B104KO5NNNC and two CL05A105KA5NQNC. The latter stock part is actually rated **25 V**, which exceeds the 10 V minimum above ([Samsung](https://product.samsungsem.com/mlcc/CL05A105KA5NQN.do)). Count and inspect inventory before assembly. C30 remains supplementary local 3.3 V bulk; it is not credited toward the regulator's C45/C46 effective-capacitance target.

For the seven revised 0805 positions, maximum ceramic body dimensions including tolerance are **2.2 × 1.45 × 1.45 mm**. The frozen lands are 0.9 × 1.2 mm with centres at ±0.95 mm; keep the prescribed orientation. No additional PCB, filled vias or special JLC process is required.

## Effective capacitance and input-capacitance budget

The following are **project selection targets**, not guaranteed characteristics of every generic MLCC or a claim of measured regulator stability. Obtain the selected part's DC-bias curve; a catalogue nominal value alone is insufficient for these power positions. Account for initial tolerance, operating temperature and aging. For screening, use `C_screen = C_nom × retention_at_bias × tolerance_factor × 0.85 × 0.90`; 0.85 reserves the X5R/X7R temperature range and 0.90 is a project aging reserve, not a universal manufacturer lifetime guarantee. If a part's specified aging exceeds that reserve, use its worse factor. Curves specified only as typical remain a selection screen; confirm rail ripple and startup on the first board.

| Positions | Bias used | Required screening result | Purpose |
|---|---:|---|---|
| C32 | 5.25 V | ≥2.2 µF | USB supply local bypass; project margin |
| C40 | 5.25 V | ≥1.0 µF | Charger input bypass |
| C41 | 4.23 V | ≥4.7 µF | Battery bypass |
| C42 and C43 | 4.50 V | Each ≥4.7 µF; combined ≥9.4 µF | System output and local buck-boost input |
| C45 and C46 | 3.60 V | Each ≥5.0 µF; combined ≥10 µF | Local 3.3 V regulator output |

TI recommends nominal 4.7–47 µF at BQ24074 BAT/OUT and 1–10 µF at IN ([BQ24074 pin descriptions](https://www.ti.com/lit/ds/symlink/bq24074.pdf)). C41 = 22 µF and C42 + C43 = 44 µF remain within those nominal ranges. The TPS63031 selection section recommends nominal input ≥4.7 µF and output ≥10 µF, permits larger output capacitance, and recommends 0.1 µF at VINA with a 0.22 µF maximum; C44 stays 100 nF ([TPS63031 §9.2.2.3](https://www.ti.com/lit/ds/symlink/tps63031.pdf)). The effective targets above are our additional design margins.

The 3.60 V capacitor screen is a conservative project voltage, not the nominal 3.3 V rail or a claimed ±2% regulator limit. In power-save mode the TPS63031 electrical-characteristics table permits up to +6% relative to 3.3 V; do not screen this mode at only 3.366 V.

Reference examples, **not mandatory purchases**: TDK [C2012X5R1A226M125AB](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C2012X5R1A226M125AB), [C2012X5R1C475K125AC](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C2012X5R1C475K125AC) and [C2012X5R1E225K125AC](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C2012X5R1E225K125AC). Their manufacturer reference curves illustrate that different voltage ratings and constructions produce different capacitance loss. A 10 µF/10 V 0603 can lose most of its nominal capacitance near 4 V; replacing the number on the shopping list without checking the curve does not solve that.

C32 + C40 directly on USB_5V are **6.9 µF nominal, 7.59 µF at +10% initial tolerance**. This is a board-level subtotal before bias, **not total capacitance seen by the USB host**. Add C5 protection, module/internal bypass and other directly attached capacitance when assessing attachment/inrush; charger soft-start does not hide parallel C32/C40. USB attachment current and signal quality remain physical acceptance items. These capacitor changes do not increase the USB100/USB500 input-current policy.

## Resistors and status LED

All fitted resistors are **0402**, ≥0.0625 W (1/16 W), ≥50 V, ±1%, temperature coefficient ≤100 ppm/K. Values are resistance, not marking codes; 0402 bodies are often unmarked. Higher power ratings are acceptable only if the body still fits 0402. The precision charge/limit/timer resistors must remain ±1%; do not substitute a nearby E24 value.

| References | Fitted | Stock / buy | Resistance |
|---|---:|---:|---|
| R3, R4, R5, R6, R7, R47, R53, R54 | 8 | 0 / 8 | 100 Ω |
| R8–R16, R18–R21, R23–R25, R42–R46, R48–R50 | 24 | 0 / 24 | 100 kΩ |
| R17 | 1 | 1 / 0 | 1 kΩ |
| R26 | 1 | 1 / 0 | 10 kΩ |
| R32 | 1 | 0 / 1 | 2.2 kΩ |
| R40 | 1 | 0 / 1 | 2.21 kΩ |
| R41 | 1 | 0 / 1 | 7.50 kΩ |
| R51, R52 | 2 | 0 / 2 | 1 MΩ |
| R55 | 1 | 0 / 1 | 69.8 kΩ |
| R56 | 1 | 0 / 1 | 1.69 kΩ |

For a self-soldered C5, add **two 5.1 kΩ ±1% 0402 resistors**, ≥1/16 W and ≥50 V, for its independent CC1/CC2 pull-downs. Those two are already allocated from stock in the separate [C5 table](../bom/daughterboard.csv); they are additional to the 75 mainboard parts. Keep C5 protection devices, USB-C connector, SH connector and fuse specified there.

R17/R26 use the inventoried Uniroyal 0402WGF1001TCE / 0402WGF1002TCE. **R30/R31 are absent: buy and fit zero of them.** JP1 is left open.

D2: one non-addressable **0603 green LED**, body ≤1.8 × 1.0 × 1.0 mm, with useful visible output at approximately 0.4–0.7 mA and forward voltage ≤2.4 V at 0.5 mA. R32 is the external current-limiting resistor. Native D2 pad 1 = cathode/GND, pad 2 = anode/LED_A; confirm the supplier's polarity drawing rather than the apparent package mark. No exact LED brand is required.

## Soldering and verification changes

C32 remains at native (346.4, 118.0) mm / 90°. C40/C41/C42/C43/C45/C46 move with the power stage; use the [complete power position table](POWER-LAYOUT.md#component-positions). All are on B.Cu; previous placement images are superseded.

Follow the [candidate assembly sequence](ASSEMBLY.md). Populate the power-stage passives with U5/U6 before the module/AFE stages, inspect the enlarged lands and measure unpowered shorts, then verify current-limited startup, 3.3 V ripple and load steps on USB and battery. Recheck USB enumeration while charging and after disconnect/reconnect. Ordinary DRC/connectivity, host firmware tests and geometric checks cannot measure analog stability, charge temperature or real MLCC behavior.

The machine-readable [power-passive contract](power-passives.json) binds values, positions, lands and conservative body sizes. The native check also compares all 75 purchase values against the exported netlist and checks capacitor/resistor package consistency in both languages.
