English | [Chinese](README.zh-CN.md)

# Raytac review and first-article acceptance

EC scanning now releases before raising a row and reclamps before lowering it; see the [analog timing study](analog-waveform.md). The calibrator adds `yeti_calibrate timing` for coarse RTC elapsed estimates from the row GPIO call to ADC return, with the 32768 Hz clock reported and one tick of quantization guard; these are not physical sample timestamps. Recalibrate with the matching bundle after upgrading.

Return to the [handbook](../../BUILD.md). This page covers the current Raytac RF wing, USB protection repair and 75-part BOM. The old repository-root dual-option acceptance report is not this revision's result.

**The current [audit outcome](../audit/outcome.json) `checks_passed` field governs software/CAD consistency. It never automatically releases production or physical acceptance.** No unit exists; all physical steps below are unexecuted.

| Area | Evidence and boundary |
|---|---|
| Schematic/connectivity | [Fresh schematic](../audit/schematic-current.json), [native strict DRC](../../hardware/ec60-nrf52840/audit-current.json), [baseline regression](../../hardware/ec60-nrf52840/connectivity-changes.json): 267 signal pairs without new opens; mainboard D1 removal is reviewed explicitly |
| Ordinary process | [Process check](../audit/yeti60-ordinary-process.json): 816 mechanical through vias, hole/land >=0.30/0.50 mm, no blind/buried/module via-in-pad or fill/capping dependency |
| USB protection/path | [Actual C5 coverage](../audit/C5-protection.json), [contact-aware geometry](../audit/USB-signal-paths.json): protected pins 1/2/4/5, not internal-NC routing pads 6/7/9/10. Keep C5 U1/D1/F1, remove redundant mainboard D1 branches. No USB eye or board ESD qualification |
| Antenna copper | [Four native layers](../audit/interference-layout.json): zero GND/non-GND area in Raytac's minimum 10.5x3.8 mm projection; real copper-injection negatives per layer. This is not measured RF acceptance |
| Firmware | [Normal/calibrator targets](../audit/yeti60-target-check.json), [core/USB host regressions](../audit/yeti60-firmware-simulation.json): accepted configuration enables the USB500 input budget, charging and wired HID priority; actual pack current depends on settings/load sharing |
| Fit/harness | [Assembly](../audit/yeti60-assembly.json), [seven wires](../audit/yeti60-interconnects.json), [60 keys](../audit/yeti60-key-geometry.json): nominal collision-free fit, 29 native PCB holes and 28 installed mounts (H26 unused), subject to actual dimensions/tolerances |
| Deliverables/provenance | [Inventory](../audit/yeti60-inventory.json), [28 steps](../assembly/build-guide.md), [complete explosion](../engineering/exploded.md), [integration](../audit/integration.json); never manually restamp stale images |

PCB DRC retains 102 courtyard warnings for non-purchased electrodes/mount graphics/probe geometry. ERC retains 183 inherited off-grid endpoints; fresh nets and pin contracts independently verify connectivity. Shared analog/discharge labels are unified as `APLEX_OUT_PIN_0`, without shorting two MCU outputs. Upstream C5 default DRC still discloses footprint/courtyard/edge review items; these are not a zero-error C5 manufacturing claim. Prefer populated C5 for the first prototype.

## Physical sequence

1. Inspect incoming thickness/outline/29 holes, electrodes, orientations, joints and hidden lands. Verify rails, each connector pin and every harness conductor unpowered. Repair failures before connecting a battery.
2. Use current-limited USB and a battery simulator; inspect rails/current/hot spots, then SWD program/verify. Do not use a real pouch for reverse/short/overtemperature faults. See [wiring/flash commands](../build/flashing.md).
3. Qualify normal/wide/6U mechanism samples, independent housings, dome preload, sensing springs, travel/return and stabilizers. Inspect standoffs/insulation; do not force interference away with screws.
4. Capture released and individually held pressed samples for all 60 keys, inspect guard intervals/saturation/overlap, then confirm save. Quiet-condition recalibration cannot conceal charge/BLE interference.
5. Verify real enumeration/HID. After host configuration, record positive battery charge current and simultaneous wired key reports. Verify retained BLE preference cannot defeat USB priority; test unplug/replug/reset/suspend/resume/reconnect.
6. Verify no active-firmware charging before configuration or during suspend. USB500 is an input budget, not fixed pack current. Separately qualify SW100-off autonomous USB100 slow charge. A non-enumerating adapter is not a data host. Real charge/termination/thermal/runtime tests require a supplier-approved complete pack; qualified bench operators may substitute sensor signals, never heat a pouch to force faults.
7. Check PCB centring, RF recess, crimps/bends/serviceability/guides, screw engagement and no pack compression. Inspect tolerance compliance, close the shell and repeat all keys, transports, charging and thermal tests.
8. Measure enclosed range/orientation/loss/recovery and per-key released/pressed distributions during idle, typing, USB, charge and BLE transmission with final resin/pack/caps. Untested means untested. Use a capable laboratory for required USB/EMC/ESD compliance work.

Retain board IDs, PCB/firmware hashes, actual component/pack lots, instrument settings, logs/waveforms/temperatures/photos and individual pass/fail records. First-article results precede scaling; CAD consistency is not production approval.

For mechanical acceptance follow the [NiZ / plate-mount guide](../build/key-mechanism.md): 28 installed fastener sets, H26 empty, lower/upper gasket stock 2.0/1.2 mm. Check NiZ clips/skirts, three independent stabilizer pairs, the actual 6U wire/cap fit, released-key return and full stroke. Check neighboring EC keys while operating each big key.

The [analog GPIO / startup cleanup checks](gpio-mode-policy.md) cover the actual callback/init bodies, pinned Zephyr flag values and final rail-off pin state. Real leakage and rail decay still require measurement.

Commands reject unavailable startup; runtime scan faults power down the AFE, release tracked keys and reject further capture/save. Both images use a 128-entry key-event queue. See [scanner lifecycle/fault regression](scan-control.md), including the actual worker, 60-key capture and a 120-event burst. Real host delivery remains first-board acceptance work.

Calibration now uses a 308-byte record with its own CRC-32; older 304-byte records require recapture. Global NVS settings formats and Bluetooth bonds are unchanged. See [calibration storage and upgrade](calibration-storage.md). Corruption is host-tested; physical flash power-loss acceptance remains open.
