English | [Chinese](README.zh-CN.md)

# YETI60 acceptance and test procedure

[Remediation plan and closing evidence](remediation-plan.md) · [Guarded per-key calibration](calibration.md) · [USB path review](USB-paths.md)

**Design acceptance remains on hold.** Antenna engineering projections are now clear of host copper and plate metal, but RF range/immunity and USB eyes remain unmeasured. See the [current E73 review](../audit/e73-review.md) for USB branches, PH withdrawal and the integrated NiZ plate. Raytac uses its [separate candidate entry](../../variants/raytac/BUILD.md). No physical item is recorded as passed.

Choose one complete alternative throughout assembly, programming and testing:

Both alternatives use the same wired policy: a configured computer connection charges the battery while carrying USB HID input, with USB preferred even over a saved BLE preference. Unplugging allows ZMK's BLE fallback. Confirm simultaneous charging and wired input with the USB analyzer, battery logger and host event log; host policy tests and ARM builds do not replace this measurement.

| Alternative | Illustrated soldering and assembly guide | Firmware |
|---|---|---|
| E73-2G4M08S1C, default | [28 steps, including bare-PCB soldering](../assembly/build-guide.md) | [HEX files and flash/calibration procedure](../../firmware/target/README.md) |
| Raytac MDBT50Q-1MV2 | [28 steps, including bare-PCB soldering](../../variants/raytac/docs/assembly/build-guide.md) | [Independent HEX files and procedure](../../variants/raytac/firmware/target/README.md) |

E73 needs reflow for its five connected bottom lands; exposed edge pads do not make the complete board iron-only. Both alternatives also contain hidden-pad power packages. Inspect the selected stencil, paste and process before assembly. Do not mix mainboard Gerbers, module, pin contract or firmware between alternatives. Retain the existing C5 JSH. Current case reliefs, plate and harness details differ between options; use the selected entry. Skip optional C5 bare-board steps when reusing the already-made board.

## Executed design checks

Current E73 evidence is the [complete review run](../audit/e73-review-run.json) and [readiness gates](../audit/e73-readiness.json). The [older combined acceptance record](../audit/acceptance.json) is a historical baseline, not release evidence for the current Raytac candidate or E73 revision. The [two-option check](../audit/variants.json) verifies the current designs separately and records maturity differences.

| Gate | Current evidence | Meaning |
|---|---|---|
| Connectivity / ordinary JLC process | Native strict DRC: 0 errors, 0 opens, 270 physical signal pairs per board | CAD pass; E73 has 102 expected virtual-courtyard warnings; use each native report for its scope |
| Firmware | Normal and calibrator ARM ELF/BIN/HEX for each option; host ASan/UBSan tests | Build and portable-core checks; GPIO/ADC/USB/BLE are mocked in host tests |
| Noise behavior | 2000 hysteresis-band frames plus 2000 correlated-ripple / isolated-burst frames per option | Expected debounce behavior passes; two sustained over-threshold frames still cause synthetic false keys |
| Analog front end | Pinned official TI OPA350 model; 28 sensitivity cases | AC/transient model checks pass; physical noise margin is unknown |
| RF / USB SI | Actual four-layer copper intersections, plate BRep projection and contact-aware USB main/stub paths | Antenna projections clear; E73 long TVS branches remain open; no RF field solution, antenna match, impedance extraction or USB eye acceptance |
| Assembly | 60 keys, 28 installed mounts; H26 unused, original case scale; current component/pack/harness envelopes | Conditional CAD fit only; real dome compression, supplier pack, resin and fasteners remain unqualified |

## Reproduce the checks

Run at the repository root. The CAD environment must satisfy [requirements-audit.txt](../../requirements-audit.txt); KiCad Python and `ngspice` are also required. `KICAD_PYTHON` and `YETI_CAD_PYTHON` may point at installed runtimes. TI's model is downloaded into ignored local storage and verified against a pinned SHA-256; it is not redistributed.

```sh
python3 scripts/run_e73_review.py --require-design
python3 scripts/run_all_variants.py --check-existing
```

The first command reruns the complete E73 checks and returns 2 while design gates remain open. The second rechecks existing evidence and integration for both options, recording structural, harness, purchase and firmware maturity differences. It does not require identical source or BOMs, and successful execution is not product acceptance. Recheck the Raytac repair package through its handbook. The older `run_acceptance.py` covers the historical formal-board baseline and must not release the candidate.

## First-article sequence

Use a separate copy of the [measurement template](first-article-template.csv) for each board serial and firmware revision. Keep the original template unfilled. All limits below are project acceptance targets, not Bluetooth, USB or EMC certification limits. Store instrument settings, photographs, logs and raw traces with each measured row. Never mark a row passed from a drawing or build result.

| Order / guide step | Action and instrument | Project pass criterion |
|---|---|---|
| 1 / 01–03 | Identify board/module and BOM, microscope inspection, bare-board continuity; power disconnected | Correct alternative; no bridges, reversed parts or shorts; all required lands inspected. Use X-ray or an assembler's validated hidden-joint inspection for E73 bottom lands and power thermal pads |
| 2 / 04–11, 14–16 | Assemble by power domain, verify polarity and resistance before first power; current-limited bench supply, no battery | Begin at a 50mA bench limit and investigate current limiting; raise only after identifying legitimate load. 3.3V rail within imposed ±5%; no hot component, persistent current limit or unstable rail. Capture startup and load transients; a DC meter alone is insufficient |
| 3 / 12–17 | C5 CC1/CC2 resistances, numbered harness continuity and insulation, actual plug fit | Separate 5.1k CC resistors; correct D+/D−/VBUS/GND; no crossed wires or pouch loads. Confirm final routing and serviceability against drawings |
| 4 / 16, 25 | SWD flash correct calibrator HEX, readback/verify, USB descriptor capture, sample logs | Correct module pin map and E73 UICR NFC-as-GPIO when applicable; 60 actual key positions identified; no ADC saturation or missing channels |
| 5 / 17–24 | Dry-fit actual housings, domes, springs, spacers, film, fasteners and protected pack | 28 installed mounts align; H26 remains empty, no PCB bow/forced shell closure, service switch accessible, pouch not compressed, inserts secure. Record actual stack and donor parts; custom 1600mAh pack supplier approval remains mandatory |
| 6 / 25–26, 28 | Per-key calibration and interference matrix from the [test plan](interference.md#physical-interference-matrix) | Released/pressed distributions have positive guarded margin in every tested mode; zero false/missed/stuck keys in specified runs. Keep raw samples and threshold values |
| 7 / 26, 28 | USB analyzer, battery-side current logger, thermocouples, temperature-sensor substitution by a qualified bench operator | Before configuration use USB100 with charging disabled; configured host enables USB500 charging. Active-firmware suspend disables charging and selects EN1/EN2=1/1 standby input high impedance. SW100-off autonomous USB100 slow charging needs separate source qualification. Charge current, termination, rail limits and independent 15–43°C interruption meet the [power](../engineering/power-budget.md) and [pack](../engineering/battery-pack-specification.md) specifications. Do not heat/cool or short a pouch to force faults |
| 8 / 26, 28 | USB plug/unplug and suspend/resume 100 cycles; BLE connect/reconnect/profile switching 100 cycles; host HID event log | No stuck/lost key state, enumeration failure, unexpected reset or unhandled report loss. All five profiles retain intended bonds; verify on intended host systems |
| 9 / 28 | Normal firmware, debugger disconnected, battery analyzer; type/idle/advertise/reconnect/off and a complete usable discharge | Record measured currents and delivered capacity; reconcile runtime against the model. Do not use predicted hours as the measured acceptance value |

Close the antenna layout findings and repeat all affected tests before release. A qualified test house must perform any required radiated/conducted emissions, immunity and ESD certification; this repository supplies no certification claim.

[E73 firmware migration and expanded regression evidence](e73-firmware-validation.md).
