English | [Chinese](raytac-review.zh-CN.md)

# Raytac review conclusions

**All 92 recorded software/CAD audit stages passed. Manufacturing and physical operation are not approved.** This review covers Raytac only, not the old dual-option report.

The table describes the current short-USB candidate; retained reference-board figures are labeled separately.

| Area | Result |
|---|---|
| PCB | 0 errors / 0 opens; 411 signal pairs |
| DRC | 102 disclosed noncomponent courtyard warnings |
| ERC | 0 errors; 183 inherited off-grid warnings |
| CAM | 846 drill/slot features; 813 via sites; 297 stencil apertures |
| USB / BLE | Current normal/calibrator ARM artifacts and USB500 descriptors checked; simultaneous charge/wired-priority policy host-tested |
| BOM | Current candidate: 75 parts; 8 planned from stock, 67 net purchases |
| Harness | Current candidate: 9 conductors |

**Use the [short-USB repair candidate package](../../hardware/usb-short-route/FIRST-ARTICLE.md) for the current first board.** The old long-route archive remains a held reference; its seven-wire illustrations do not describe the current nine-wire assembly. Pack confirmation, complete USB-link/analog stability and physical acceptance remain open. See the [battery-inclusive open-bench flow](../../OPEN-BENCH.md).

See [scanner fault handling](../testing/scan-control.md): unavailable initialization rejects commands, faults shut down and release tracked keys; fifteen scenarios and seventeen mutants, with a 128-entry queue checked against a 120-event burst. Physical host delivery remains open.

The [NVS recovery model](../testing/nvs-powercut.md) passes 14,795 selected write/GC/recovery interruptions and rejects two ordering/live-copy mutants. Actual NVMC, Bluetooth-bond and brownout acceptance remain first-board work. The NVS model itself does not change firmware identifiers.

Idle short-tap correction: the first pending active edge restores fast scanning while retaining two-frame debounce. A modeled 50 ms hold now produces one press/release and a later single-frame spike produces no extra event; see [evidence](../testing/scan-control.md). Upgrade with matched images and recalibrate; actual first-key latency and noise-related power remain unmeasured.

New [matrix/Fn/HID pipeline checks](../testing/key-pipeline.md) execute pinned ZMK functions in six scenarios and reject four mutants. Current reports hold six ordinary keys plus separate modifier bits; a seventh can be omitted. Sixty-key scanning is not full-key rollover. Physical host delivery and transport remain open. These tests leave images and calibration identifiers unchanged.

Actual ELF [HID format checks](../testing/key-pipeline.md#linked-usb-and-ble-report-formats) reconcile both maps, report objects and BLE References. USB 9/13-byte reports fit the 16-byte endpoint; BLE bodies are 8/12 bytes. Runtime descriptor patching, enumeration and host delivery remain untested.

The [targeted HID followup](hid-format-followup.json) is a historical snapshot; current linked layout evidence comes from the target checks.

New [off/reset power review](../engineering/power-states.md): SW100 controls regulator enable; undriven charger pins can permit hardware USB100 charging, unlike the initialized firmware inhibit. Datasheet shutdown subtotals are not board bounds; loss of battery support during suspend remains unqualified.

This power-state update uses targeted checks; the full audit matrix above is retained from the preceding run, without rerunning all CAD stages.

## Repairs and image inspection

- USB mainboard D1 and long branches removed after actual C5 protected-channel/ground verification; C5 D1/U1/F1 retained
- Shared analog/discharge net labels unified without changing exported pin connectivity
- 75-part purchase, stock allocation, placement and illustrated guide contracts reconciled
- Retained reference explosion includes seven wires; current candidate assembly supplies nine wires and C04 gasket strips. Use the candidate assembly entry for the current build
- NiZ ordinary housings/sliders and separate Cherry plate-mounted stabilizers selected; 1.6 mm plate, 28 mounts and H26 unused; 60 sensing centers and exterior preserved; actual wire/clip/stroke fit awaits a first article
- Second review corrected stale 29-fastener inventory/acceptance prose and 1.2 mm render descriptions in both languages; negative tests now reject their return
- Current RF status distinguishes passing minimum antenna-copper clearance from unqualified USB signal integrity and enclosed RF; historical reviews remain labeled snapshots
- Broken tracked Raytac third_party/zmk link repaired to the pinned repository submodule; all tracked shared links now checked and missing-source fault injected

## Functional coverage and test boundaries

| Function | Evidence and remaining boundary |
|---|---|
| 60-key scan | [Geometry/map](yeti60-key-geometry.json); host core tests all 75 matrix positions, hysteresis, debounce and ADC frame abort. Real EC waveforms remain unmeasured. |
| Calibration | [Guard tests](calibration.json); inspect the target release/press/save flow, 128-frame capture, saturation/overlap rejection and persistent thresholds. First-article capture and flash retention remain open. |
| USB priority | [Actual adapter host regression](yeti60-firmware-simulation.json) covers configured charging plus USB preference, retained BLE preference, suspend/resume/reset/detach and failure retries. USB/BLE interfaces are mocks. |
| Power | [Current/timer arithmetic](yeti60-power-budget.json), enable-net and adapter review agree with BQ24074 input modes. Off-state USB100 charging differs from firmware-controlled charging. Actual thermal/current behavior remains open. |
| Firmware | [Existing normal/calibrator ARM artifacts](yeti60-target-check.json) rechecked against current source hashes, flash ranges and linked USB500 descriptors. Normal and calibrator images are rebuilt after firmware changes; these checks do not execute the targets. |
| Assembly | [Current candidate assembly](../../hardware/usb-short-route/ASSEMBLY.md) checks nine conductors, C04 plate, 28 mounts / H26 omission, 1.6 mm plate and image provenance. Actual NiZ skirts/clips, 6U bends, preload and local stiffness remain open. |

Generic passives and the LED now use [purchasing specifications](../../hardware/usb-short-route/PASSIVES.md); seven power capacitors have matching 0805 lands and stock credits remain. The complete power stage is relocated; feedback/C46 conservative paths are 3.555/4.681 mm. [Positions and ordinary thermal vias](../../hardware/usb-short-route/POWER-LAYOUT.md) document the design checks and physical boundaries.

## Isolated USB repair candidate

The canonical PCB, inventory and seven-wire assembly images above still describe the previous routing. The separate [repair candidate](../../hardware/usb-short-route/README.md) passed strict native checks and 411 physical pin-pair checks. Both contact paths are 5.286396 mm, with zero data vias and 100% adjacent-ground centerline coverage. Local header/housing tolerance checks, both rebuilt targets, host simulation and calibration tests passed. The candidate fits 75 parts, credits 8 stock parts and requires 67 purchases, with nine conductors total. [Nine-wire enclosure routes, 16 guides and complete assembly illustrations](../../hardware/usb-short-route/ASSEMBLY.md) passed combined installed-geometry and provenance checks; service/mating access and physical acceptance remain open. This does not release the canonical fabrication archive. The long-route values below continue to document the canonical routing limitation.
The candidate [first-article fabrication package and case-free procedure](../../hardware/usb-short-route/FIRST-ARTICLE.md) are available. Independent readback covers 846 drill/slot features, 289 fitted copper lands, 75 placements, 297 stencil apertures and all 1,444 IPC records. JP1 paste is omitted and the test-netlist origin is normalized. Supplier DFM precedes fabrication; physical acceptance follows the first board. The previous routing archive remains held.
Candidate F1 is now the [Littelfuse 0466001.NRHF one-time fuse with revised lands](../../hardware/usb-short-route/F1-SELECTION.md). A new [continuous vertical sweep](../../hardware/usb-short-route/SERVICE-PATH.md) confirms that an internal relief removes the nominal rigid-body wing obstruction and revised rear clips provide a screened PCB corridor. USB/battery unmating, wire deformation and combined tolerances remain unqualified; enclosed service is not approved.
The previous locating-ear and switch-floor issues are repaired by the [C04 plate, lower-shell pocket and eight gasket strips](../../hardware/usb-short-route/MECHANICAL-FIT.md). Static/continuous plate and switch-floor envelopes pass under the stated finished-part and installation limits; the plate retains approximately 0.188 mm air reserve. The previous diagnostic remains a pre-repair baseline. Full-keyboard tolerances, foam behavior, connected service and physical acceptance remain open.
Analog pins now use [high impedance with digital buffers disconnected, plus startup-error cleanup](../testing/gpio-mode-policy.md). Five positive cases execute actual callback/init sources and reject four mutants; the candidate bundle repeats the tests independently. Actual registers, leakage, transients and physical power faults require the first board.
EC scanning repairs [release/charge and clamp/falling-edge order](../testing/analog-waveform.md). Actual-core regressions reject both reversed variants. Thirty-six passive RC sensitivity cases do not qualify real NiZ capacitance, op-amp dynamics or sample timing. The calibrator adds coarse 32768 Hz RTC timing estimates with the clock and one-tick guard reported, not precise sample timestamps.
Firmware review adds [selected-profile recovery and calibration v3 invalidation](../testing/firmware-recovery.md). Resolved device trees in both ARM builds verify Fn + double-tap Backspace clears only the selected slot. Actual CMake fingerprint mutations and pinned ZMK gesture code are host-tested. Real pairing, analog timing and charging transitions still require the first board.
USB review repairs [callback-driven charger disable and host deconfiguration](../testing/usb-event-policy.md). Eleven host scenarios compile the unmodified pinned ZMK USB callback; both ARM call targets are checked. Physical callback latency, suspend current and battery-backed transitions remain open.

## USB routing limitation of the retained reference board

Retained reference-board D+ / D− actual trace centerlines are approximately **253.541 / 249.122 mm**, through **4 / 6 vias**. The pad-access/contact-bridge geometric path difference is **2.165 mm**, not propagation-delay skew. C5, harness, connector and module internals are excluded. Protected connectivity and DRC do not establish differential impedance, continuous return, common-mode behavior or a passing USB eye. Review the complete link and measure it with the final harness before manufacturing release.

[Charger primary datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [Regulator primary datasheet](https://www.ti.com/lit/ds/symlink/tps63031.pdf). Datasheet review does not replace board waveform or thermal measurements.

## Supplier and physical work still open

- Generic passives/LEDs are purchased by specification without mandatory individual brands. Effective capacitance under bias and actual fuse thermal derating still require compliance; layout rework passes design checks; stability, ripple and transients still require first-board measurements.
- Supplier-signed complete pack envelope, charge limits and independent thermal interruption.
- Actual housings/domes/springs/stabilizers, resin tolerances and harness/mechanical samples.
- Physical USB enumeration/eye, concurrent charge/input, BLE, per-key calibration, thermal/runtime and enclosed interference tests.
- Upstream C5 default DRC review items remain; protected-channel verification is not C5 manufacturing or ESD certification.

[Build entry](../../BUILD.md) · [complete explosion and part index](../engineering/exploded.md) · [first-article acceptance](../testing/README.md) · [machine evidence/hashes](raytac-review.json)
