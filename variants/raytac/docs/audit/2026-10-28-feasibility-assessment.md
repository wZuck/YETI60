English | [Chinese](2026-10-28-feasibility-assessment.zh-CN.md)

# YETI60 P2 feasibility and component compatibility assessment

Assessment date: 2026-10-28. Scope: the current YETI60 P2 working tree, based on commit `39ae3cc59d0e98faf3aea6630d677b6c8c9ea990`. This is a design assessment, not production authorization.

## 1. Decision

**The architecture and static electrical connections support continuing with controlled engineering prototypes. The design is not ready for unrestricted procurement or production.** Core IC functions, voltage domains and interfaces broadly align. The main dependencies are the custom battery, complete EC key mechanism, special PCB process, final passive-component selection and physical qualification.

This combines EC60 capacitive electrodes, a 60-key HHKB mechanism, a single nRF52840 for USB/BLE and a derived FELK60 resin enclosure. Similar part names, matching mounting holes and passing scripts do not independently establish complete compatibility.

In one sentence: **a working engineering prototype is feasible; direct production from the current files is not.**

| Area | Assessment | Reason |
|---|---|---|
| Architecture | Feasible | One controller handles scanning and both transports; charger and buck-boost form a suitable power chain |
| Core electronics | Broadly compatible, conditional | Nominal 3.3 V interfaces and key pins align; waveforms and derating remain unqualified |
| PCB manufacturing | Conditional | Requires the specified asymmetric four-layer HDI stack, blind vias and capped via-in-pad |
| Mechanical/key mechanism | Partially compatible | Case/plate geometry has evidence; complete housings, domes, springs and stabilizers are not frozen |
| Battery and charging | Critical open dependency | Pack drawing, conflicting cell current data, independent thermal protection and complete charging need acceptance |
| Firmware | Target artifacts available; hardware unverified | Artifact checks and host simulation pass; enumeration, pairing and per-key physical calibration remain |
| Runtime | Model only | Idle scan, AFE gating and REG1 DC/DC implemented; deep sleep disabled because EC keys lack a reliable wake path; 106.64 hours remains a conservative planning point |
| Procurement/reproducibility | Not frozen | Several MPNs, connector details and mechanical suppliers remain unconfirmed |

A numerical overall score would obscure mandatory dependencies without hardware data or quotations.

### 1.1 Stage-release decision

| Stage | Decision | Basis | Next action |
|---|---|---|---|
| Architecture/concept | Pass | Complete single-MCU, EC front-end, USB/BLE, charger and buck-boost chain; schematic/PCB contracts pass | Keep the architecture |
| Controlled prototype (1–3 units) | Conditional pass | Static electrical, CAD and firmware-artifact evidence exists; battery, key mechanism and special PCB process remain open | Build the power board and local key sample first |
| Pilot batch (10–30 units) | Not passed | 62/76 fitted parts have no orderable MPN; battery, HDI and mechanism lack signed drawings | Close the priority-A risks in section 8 |
| Production | Not passed | No physical test, life, certification or supplier-capacity evidence | Outside this assessment |

This table matters more than a binary verdict. The design has crossed the “can be drawn, connected and built into firmware” threshold, but not the “can be purchased, assembled and measured” threshold.

## 2. Evidence and limits

The review examined current schematic/netlist data, PCB checks, BOM, target firmware, assembly specification, STEP geometry reports and power/battery calculations, and ran `python3 scripts/run_audit.py`. Section 9 records the result. ARM binaries and photographic renders were not rebuilt; the pipeline checks existing target artifacts and provenance and reruns host simulation and CAD/engineering checks.

Primary project evidence:

- [Schematic parity](schematic-current.json), [strict PCB audit](../../hardware/ec60-nrf52840/audit-current.json), [electrical paths](yeti60-electrical.json).
- [Mainboard BOM](../../hardware/bom/mainboard.csv), [materials](../engineering/materials.md), [assembly specification](../../../../mechanical/assembly-spec.json).
- [Assembly](yeti60-assembly.json), [battery recess](yeti60-battery-pocket.json), [target firmware](yeti60-target-check.json), [power model](yeti60-power-budget.json).

Manufacturer references in section 10 were checked online. Stock, prices, lead times and supplier production capability were not verified. At the start, the EC60 submodule had local changes and `mechanical/interconnect-spec.json`, `docs/audit/yeti60-interconnect-connectors.json`, `scripts/check_yeti60_interconnects.py` and `scripts/interconnect_geometry.py` were untracked. These were left untouched. The first two files provide a useful J1/J2 land-pattern check, but that harness check is not wired into `run_audit.py`; the ordinary Python environment here also lacked OCP, so it was not rerun. It is therefore not counted in the section 9 pass result. Scripts and JSON `scope`/`limits` fields define automated coverage.

## 3. Architecture

The signal chain is GPIO row drive → EC electrodes/conical springs → two 74HC4051 devices → OPA350 → nRF52840 SAADC → ZMK USB/BLE HID. Power runs from the rear USB-C daughterboard through protection and BQ24074 to VSYS, then TPS63031 generates 3.3 V. The battery connects to the charger's power path. U8 controls the AFE and U7 switches the battery divider.

A single MCU avoids inter-controller communication and startup coordination. A radio module reduces bare-chip RF design work but does not remove antenna clearance or final enclosure testing. Retaining upstream electrodes reduces geometric redesign risk; it does not establish unchanged sensing behavior after changing the controller, ADC, stack and mechanics. Success depends on sensing margin, supply noise and mechanical preload. SI/RF analysis remains explicitly deferred.

## 4. Component compatibility

“Compatible” below means a reasonable nominal design choice, not completed physical or manufacturer-land-pattern qualification.

| Part/combination | Selection | Assessment and conditions |
|---|---|---|
| U1 controller | MDBT50Q-1MV2 | Strong functional fit for USB, BLE, GPIO and SAADC. Scan is module pin20/P0.04/AIN2; battery pin21/P0.05/AIN3. Confirm exact antenna variant and manufacturer keep-out |
| U2/U4 mux | 74HC4051PW, TSSOP16 | Appropriate HC logic family. Do not substitute HCT on name alone. Verify actual 3.3 V switching residue, capacitance and settling |
| U3 amplifier | OPA350UA, SOIC-8 | Suitable supply/ADC-drive function, substantial continuous current. Nominal gain 101; JP1 unpopulated. Verify amplitude, saturation, settling and noise; OPA2350/different packages are not direct replacements |
| U5 charger | BQ24074RGTR, VQFN16 | Suitable 1S 4.2 V power-path/USB100/500 function. Exposed-pad assembly, thermal regulation, timer, termination and cell limits need acceptance |
| U6/L1 regulator | TPS63031DSKR + 74438336015 1.5 µH | Buck-boost is suitable across a cell voltage above/below 3.3 V. Fixed-output variant and nominal passives align with the application concept. Loop, ripple and light-load behavior remain unverified |
| U7/U8 switches | TPS22919DCKR, SC70-6 | Reasonable switched-divider/AFE arrangement. Test settling, residual voltage and GPIO/ADC backfeed. Software off is not zero system current |
| USB chain | C5 JSH, J1, D1, 0-ohm R30/R31 | Pin contract: 1 VBUS, 2 D−, 3 D+, 4 GND. Keep existing zero-ohm links with nRF PHY termination. The daughterboard SH model Y offset was corrected from +2.425 mm to −1.45 mm, removing a 3.875 mm body displacement. That is a geometry correction, not insertion-force or SI acceptance |
| J1 header | Inherited 1.0T-4P; candidate SM04B-SRSS-TB | Land-pattern match, assembly open. A supplementary check shows the four signal and two mechanical pads match the standard JST footprint by a **0.0625 mm rigid translation**. Still verify body height, insertion direction, retention and trial mating. This check is not in the main audit |
| J2 battery header | S3B-PH-SM4-TB | Land-pattern match, custom pinout. The three signal and two mechanical pads match the standard JST footprint with zero translation. Pin 1 positive, 2 negative, 3 NTC; require a supplier pin-number drawing. Same housing does not establish polarity |
| Battery | Custom 1600 mAh, 85×43×4.8 mm | Conditional geometric fit; procurement unqualified. Full envelope must include PCM, NTC, folded tabs, insulation and growth; independent thermal protection required |
| Passives | Mainly 0402/0603; many MPNs open | Requirements are a starting point, not a frozen BOM. Use C0G for 220 pF and evaluate final capacitor effective capacitance under bias |
| F1/D2 | 0.5 A PTC / 0603 LED | Select final trip/hold behavior, resistance and temperature derating; LED forward voltage controls actual current and brightness |
| EC mechanism | 60 matching HHKB/Topre-compatible sets | Not frozen. Source matching housings, domes, conical springs, wide-key stabilizers and 6U spacebar. NIZ/Topre/MX-conversion parts are not assumed interchangeable |
| Plate/standoffs | 1.2 mm steel, 29 custom standoffs | CAD fit, specialized manufacturing. M2 upper/M1.6 lower threads require the specified machined part, insulation and thread checks |

The mainboard has **76 fitted parts; JP1 is DNP**. The PCB's 74 optional electrode sites, 75 firmware scan positions and 60 fitted keys are different counts. Count the finished daughterboard separately without also purchasing its loose BOM twice.

### 4.1 BOM compatibility coverage

Grade by whether an orderable manufacturer part number exists, not by whether the part is common:

| Grade | Meaning | Parts | Share | Includes |
|---|---|---:|---:|---|
| A | Manufacturer PN fixed; package/pin contract exists | 13 | 17.1% | D1, J2, L1, SW1, SW100, U1, U2/U4, U3, U5, U6, U7/U8 |
| B | Candidate PN; land pattern or assembly needs trial | 1 | 1.3% | J1 SM04B-SRSS-TB |
| C | Specification only; no MPN | 62 | 81.6% | 43 resistors, 17 capacitors, F1, D2 |
| Total | — | **76** | 100% | JP1 is DNP and excluded |

By BOM line: 11 of 36 are A, one is B and 24 are C (including one DNP line). **Low coverage does not make the design infeasible**: 60 of the 62 C-grade parts are commodity passives. The real selection risk is concentrated in F1 hold/trip current and USB drop, D2 forward voltage and brightness, and effective capacitance under bias, temperature and tolerance. Conversely, grade A is not acceptance: the U1 order suffix/antenna variant, U5 exposed-pad assembly and U6 loop compensation still need physical confirmation.

### 4.2 Quantity contract

| Item | Count | Meaning |
|---|---:|---|
| Schematic component records | 178 | Includes electrode and power symbols; not fitted parts |
| Mainboard fitted parts | 76 | JP1 DNP |
| PCB electrode pads | 74 | Retained optional EC60 layout sites |
| Firmware scan matrix | 5×15 = 75 | Every frame scans all 75 positions |
| Fitted keys | 60 | HHKB plate and keymap |
| PCB/plate mounting centres | 29 | Two geometries matched |
| Connected physical pin pairs | 270 | Connectivity regression |

**74, 75 and 60 are not interchangeable.** 74 is the available electrode-pad count, 75 is the firmware scan count and 60 is the fitted key count. Extra scan positions do not prove extra keys, nor reduce calibration scope. First-article acceptance still needs per-key calibration and confirmation that unpopulated positions cannot generate false presses.

## 5. Quantitative findings

### Power capacity versus thermal/analog behavior

The model uses 11.39 mA at 3.3 V for planning and 17.69 mA for stress. Nominal regulator output capacity is not the limiting concern; light-load efficiency, ripple coupling and capacitor derating deserve attention.

A thermal screening estimate at 5 V input, 3.0 V battery and 0.403 A charge current is `(5−3)×0.403≈0.81 W` in the linear charge path, before other effects. This is not a junction-temperature calculation. Measure charger temperature and actual thermally regulated current in the closed resin enclosure. Charger die protection does not replace cell temperature protection.

### Battery/charger dependency

With R40=2.21 kΩ, R55=69.8 kΩ and R56=1.82 kΩ, the project's coefficients and 1% resistor tolerances give:

| Quantity | Calculated value | Implication |
|---|---|---|
| Charge current min/typ/max | 357.06/402.71/445.63 mA | Only 4.37 mA below the project's 450 mA pack requirement, which is not yet a supplier guarantee |
| Minimum fast-charge timer | 6.9102 h | Exceeds ideal CC time of 4.48 h at minimum current, but does not prove complete CV termination |
| Maximum termination current | 31.51 mA | Only about 0.49 mA below 1600 mAh×0.02C=32 mA; confirm against corrected cell data |
| USB500 lower-limit budget | 450−40=410 mA | System reserve is an assumption; upper-tolerance charging can become input-limited |

The HCP404074 sheet lists minimum 1600 mAh but also 0.2C=270 mA and 1C=1350 mA. Those figures conflict. Obtain corrected supplier current/temperature/capacity/termination limits before accepting 445.63 mA or revising the setting. The pack must independently enforce the project's actual charging window of 15–43°C, targeting 18–40°C, even without MCU operation. An NTC wire or voltage/current-only PCM is insufficient. Require a signed full-pack drawing and thermal interruption/recovery evidence. [Manufacturer cell sheet](https://www.honcell.com/Public/Uploads/uploadfile/files/20240401/DATASHEETHCP4040743.7V1600mAhCELL2024.pdf)

### Runtime

At assumed 80% usable capacity and 12.003 mA battery current, planning runtime is **106.64 hours, about 4.44 days continuously**. The 57.73–153.01-hour scenarios are neither measurements nor guaranteed bounds.

OPA350's typical 5.2 mA is about **46%** of the planning 3.3 V current. Firmware now slows to a 30 ms idle scan, gates the AFE with U8, and enables REG1 DC/DC. The planning table still assumes the AFE is on continuously, so 106.64 hours is conservative and does not credit idle gating. `CONFIG_ZMK_SLEEP=n` remains because EC keys are not a System OFF GPIO wake source. For a multiweek target, measure idle duty cycle and first-key latency before evaluating a lower-power amplifier or a dedicated wake channel; an amplifier substitution requires renewed settling/noise/stability checks. [OPA350 datasheet](https://www.ti.com/lit/ds/symlink/opa350.pdf)

### Scan timing

The current budget is at least 8.32 ms/frame before GPIO, driver and scheduling overhead: an ideal upper rate around 120 Hz. Two-frame debounce and transport scheduling add latency; scan rate is not end-to-end latency.

SAADC internal reference, gain 1/6 and 40 µs acquisition, and the 1M:1M battery divider with 10 nF filtering and 50 ms settling, form a plausible nominal arrangement. Physical signal amplitude, source impedance, timing and per-key release/press distributions still require measurement. Firmware intentionally sends no key events without valid calibration, so calibration is a prerequisite for first-unit acceptance.

### 5.5 Key margins

| Item | Calculated | Threshold/assumption | Assessment |
|---|---:|---:|---|
| Maximum charge current | 445.63 mA | 450 mA pack requirement | 4.37 mA (about 0.97%) margin; nominal pass, supplier unconfirmed |
| Maximum termination current | 31.51 mA | 0.02C = 32 mA | 0.49 mA (about 1.5%) margin; window too narrow |
| USB500 worst-case input budget | 410 mA | 357.06 mA minimum charge | 52.94 mA margin, but the 40 mA system reserve is an assumption |
| Planned 3.3 V current | 11.39 mA | TPS63031 rating | Ample capacity; light-load efficiency, ripple and heat unproven |
| Planned runtime | 106.64 h | “several days” goal | About 4.44 days, model point only |
| Scan frame budget | 8.32 ms | about 120 Hz upper bound | Excludes GPIO, driver, scheduling and two-frame debounce |
| Minimum screw radial clearance | 0.0766 mm | 0 | Very tight; mandatory first-article check |
| Pack-to-component minimum clearance | 0.555 mm | 0.50 mm | 0.055 mm margin; no room for uncontrolled tolerance |
| Remaining floor wall | 3.6585 mm | 3.0 mm | 0.6585 mm geometric margin, not a strength qualification |

The risk is not “insufficient headline rating” but **narrow windows, unverified assumptions and invisible tolerances**. Termination current and screw clearance are exactly the kind of items that calculate as a marginal pass and fail in hardware.

## 6. Mechanics and manufacturing

### Key stack

The modeled stack has a 1.2 mm plate, 4.50 mm shoulders plus 0.10 mm insulation, a 4.60 mm gap and 1.59 mm PCB. There are 29 mounting matches; minimum worst-case screw radial clearance is about **0.0766 mm**. Extra uncontrolled printing, drilling and assembly tolerances cannot be assumed harmless.

M2×0.4 tapped into 1.2 mm steel spans only about three nominal pitches; upper studs are 1.0 mm long. Validate thread quality, clamping and service life. Start with a local sample containing a normal key, wide key and standoff, confirming housing retention, dome preload, full travel and return before freezing the full plate.

Cold-bond inserts are suitable in concept for a thermoset resin shell. Final resin shrinkage, creep and pullout are unqualified. The nominal 50% gasket compression also needs a selected foam grade and hardness.

### Battery and harness

The modeled full pack with XY ±0.40 mm allowance has **0.555 mm** minimum component clearance, **0.700 mm** nominal fastener clearance and **3.6585 mm** minimum remaining floor after allowance. This supports the specified envelope, not arbitrary 1600 mAh packs. Tape, insulation, tab joints, wire exits and removal space must stay within allocated budgets.

C5 mounting/pin checks do not qualify full plugs, bend radius, extraction and service access. The 150 mm harness is a requirement rather than an accepted finished assembly.

### PCB process

Nine B.Cu–In2.Cu blind vias require 0.40/0.20 mm filled/planarized construction; two U1 signal via-in-pad locations require filling and copper capping. Preserve the 0.20 mm sensing dielectric, 0.15 mm lower laser dielectric and 1.59 mm finished envelope. Do not accept a default symmetric stack silently.

Obtain DFM against the [fabrication requirements](../../hardware/ec60-nrf52840/fabrication-notes.md), plus assembler acceptance of exposed pads, stencil and module soldering. If unavailable or uneconomic, rerouting is an engineering change; substituting ordinary through-vias is not equivalent.

## 7. Procurement and user experience

Core IC selections are relatively explicit. Passive MPNs, F1, D2, J1 and resin/foam/mechanism suppliers do not yet constitute a reproducible frozen BOM. HDI, custom battery, 29 custom mixed-thread standoffs, tapped plate and EC mechanism are the main cost/lead-time uncertainties. No cost estimate is supported without quotations.

Current behavior also needs explicit acceptance:

- With the board on, fast charging requires a host to accept the 500 mA configuration; a charging-only adapter cannot complete that enumeration, so firmware disables charging.
- Board-off hardware defaults to USB100 slow charging. SW100 does not isolate all battery circuitry; storage still has leakage/self-discharge.
- Battery reporting is disabled.
- Initial programming needs a custom SWD pogo fixture and per-key calibration; full-chip erase loses calibration and bindings.
- SW100 requires insulated-tool access through the underside service port.

These do not invalidate the architecture, but belong in prototype acceptance and user documentation.

## 8. Priorities and next steps

These are recommendations; no design changes were made for this report. A denotes a prerequisite before affected procurement/manufacture, B a required prototype qualification, C later optimization.

| Priority | Risk | Closure and evidence |
|---|---|---|
| A | Cell/pack specification | Correct current table; signed maximum envelope, approved charge current, pinout and independent thermal window/report |
| A | PCB/assembly process | Written DFM acceptance, stack drawing, blind-via/via-in-pad and exposed-pad process requirements |
| A | EC mechanism and stack | Matching mechanism source; local samples proving fit, travel, return, spring positioning and preload |
| A | BOM and harness | Final MPNs, J1 land-pattern overlay, full plug models and pin drawing; continuity/polarity and enclosure trial |
| B | Power and charge behavior | Controlled supply/battery simulator first; approved battery thereafter; voltage/ripple/temperature, CC/CV/termination/timer records |
| B | EC sensing margin | Per-key release/press/noise distributions and error counts across USB/BLE, charging, cell voltage and environment |
| B | USB/BLE | Enumeration, suspend/resume, cable changes, pairing/reconnection and distance tests; deferred SI/RF qualification separately |
| B | Mechanical durability | Insert pullout, thread service cycles, gasket compression, strain relief and pouch-edge protection results |
| C | Runtime/experience | Battery-side current and full runtime measurements before DC/DC, sleep, battery reporting or adapter-policy changes |

Obtain battery/fabricator acceptance and local key samples first, then freeze the BOM. Build a small engineering batch and qualify power, sensing, transport and final assembly in that order. Optimize runtime/cost after functionality is proven, before considering production release.

### 8.1 Recommended prototype ladder

| Stage | Articles | Main verification | Exit criterion |
|---|---|---|---|
| S0 power/scan bench | One mainboard plus fixture | 3.3 V sequencing, USB enumeration, CC/CV charging, scan waveform, AFE switching | No over-temperature or saturation; per-key signals separable; calibrator saves thresholds |
| S1 local mechanism | Local plate plus normal, wide and 6U keys | Housing retention, dome preload, conical-spring alignment, full travel/return, representative standoffs | No binding or uneven wear; repeatable travel and return |
| S2 full engineering build | Three complete units | 60-key calibration, USB/BLE switching, battery runtime, closure and harness | All keys pass; no wire pinching; measured charging and runtime records |
| S3 pre-pilot | 10–30 units | HDI microsection, insert pullout, thread life, drop, temperature rise, supplier consistency | Priority-A items closed; priority-B sampling passed |

Do not skip S0/S1 and go straight to a full build. The cheapest failure is a power board and a local key sample; the most expensive is scrapping HDI boards, battery packs and resin cases together.

## 9. Verification in this assessment

`python3 scripts/run_audit.py` exited **0** with `checks-passed-production-incomplete`: **all 29 stage/input-protection records passed**, `production_approved=false`. Coverage includes schematic/PCB checks, 270 connected physical pin pairs, target artifacts, host ASan/UBSan simulation, mechanical geometry, BOM/battery/power arithmetic, provenance and negative fault injection. Protected design inputs stayed unchanged; see [stage outcomes](outcome.json). This is not a new target build or a hardware test.

Passing automation means the implemented checks found no violations. It does not certify all ratings, analog performance or physical connectors. DRC has **0 errors, 0 unconnected items and 111 warnings** (102 noncomponent courtyard notices and nine track endpoints not centred on vias); review them with engineering/the fabricator rather than describing the result as “zero warnings.” ERC has **184 warnings** (183 off-grid endpoints and one multiple-net-name warning); these are not counted as electrical errors but should be cleaned or formally accepted before release. SI/RF, hardware life and regulatory certification are outside this passing result.

## 10. Manufacturer references

Checked during this assessment; conclusions combine these with project data and do not guarantee ordering availability.

- [Raytac MDBT50Q-1MV2, Version L](https://www.raytac.com/download/index.php?index_id=43): module variant, pins, pads and antenna guidance.
- [Nexperia 74HC/HCT4051, Rev.12](https://assets.nexperia.com/documents/data-sheet/74HC_HCT4051.pdf): logic-family and switching specifications.
- [TI OPA350, SBOS099D](https://www.ti.com/lit/ds/symlink/opa350.pdf): supply, speed and current.
- [TI TPS63031, SLVS696D](https://www.ti.com/lit/ds/symlink/tps63031.pdf): input range, output, application and efficiency.
- [TI BQ24074, SLUS810N](https://www.ti.com/lit/ds/symlink/bq24074.pdf): power path, input limits, thermal behavior, timing and termination.
- [JST SH](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf): connector and land-pattern drawings.
- [Honcell HCP404074](https://www.honcell.com/Public/Uploads/uploadfile/files/20240401/DATASHEETHCP4040743.7V1600mAhCELL2024.pdf): capacity, dimensions and conflicting current entries.
- [Comprehensive review](yeti60-comprehensive-review.md), [power/charging calculations](../engineering/power-budget.md), [assembly requirements](../engineering/assembly.md).
