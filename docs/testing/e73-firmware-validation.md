English | [Chinese](e73-firmware-validation.zh-CN.md)

# E73 firmware validation and migration

The E73 normal and calibrator ARM builds now include the scanner, calibration, storage, GPIO and key-reporting corrections previously checked on Raytac. They are built and tested against E73's own pin map and native PCB. This closes the software regression gap; it does not release the E73 PCB or qualify physical analog, USB, radio or charging operation. See the [remaining design gates](../audit/e73-review.md).

## Images and calibration

Use only [E73 normal files](../../firmware/releases/normal/) and [E73 calibrator files](../../firmware/releases/calibrator/), named `yeti60-e73.*`. Start with HEX over SWD: it includes UICR.NFCPINS = `0xfffffffe`; the BIN alone does not. Internal LF RC clock, REG1 LDO, scan AIN4, battery AIN3 and charger CE_N on P1.13 are retained. Neither Raytac image is interchangeable with E73. The [target build record](../audit/yeti60-target-build.json) and [linked-image checks](../audit/yeti60-target-check.json) bind both images to current inputs.

**Recapture calibration after this update.** The record is now 308 bytes with an application CRC32. A 304-byte legacy record, incorrect version, corrupt thresholds or CRC failure leaves the keyboard uncalibrated and suppresses key reports. The fingerprint includes the native PCB, pin mapping, scanner/core/control/GPIO sources, board configuration and effective scan options. Normal and calibrator builds must have the same identifier. Do not copy records between keyboards or erase the settings partition after capture. Follow the [60-key capture procedure](calibration.md). The CRC detects accidental corruption; it is not authentication or a battery safety mechanism.

Fn + **two Backspace taps within 400 ms** clears only the selected Bluetooth profile. A single tap or hold does not clear it. This gesture does not erase calibration. Use a second keyboard while commissioning and retain SWD access.

## Executed checks

| Area | Evidence and scope |
|---|---|
| Target builds | Normal + calibrator ARM ELF/HEX, E73 NFC GPIO UICR, LDO, linked USB 500 mA descriptor, USB callback wrapper, HID layouts and scan configuration |
| GPIO | [Five positive cases and four rejected changes](../audit/gpio-mode-policy.json); 150 sample conversions, disconnected analog GPIO modes and startup/fault shutdown |
| Scanner control | [15 positive cases and 17 rejected changes](../audit/scan-control.json); 60 active keys, 15 inactive positions, serialized captures, faults, wake/idle and 128-event queue handling of a 120-event burst |
| Key reporting | [Six scenarios and four rejected changes](../audit/key-pipeline.json); compiled transform/key bindings, layer release order, host reports, six-key rollover and all-key release |
| Calibration record | [Independent CRC verification](../audit/calibration.json); 512 reference records, 2,464 single-bit flips, 308 byte inversions and 2,433 sliding 32-bit bursts rejected |
| Interrupted storage | [14,795 bounded NVS cut trials](../audit/nvs-powercut.json); first save, rewrite, legacy replacement, garbage collection and interrupted recovery; unrelated sentinel preserved and resave checked |
| Recovery gesture | [Pinned upstream tap-dance execution and ten CMake mutation cases](../audit/firmware-recovery.json) |
| USB and charge permission | [11 callback cases](../audit/usb-event-policy.json), including deconfiguration, suspend, detach and GPIO faults; E73 GPIO1 device retained |
| Scan waveform | [36 passive RC sensitivities and two rejected transition orders](../audit/analog-waveform.json); clamp release precedes row rise, clamp assertion precedes row fall |
| Combined evidence | [Suite summary](../audit/firmware-suite.json) checks source/output hashes and compiled-build associations; corrupted/cross-version evidence is rejected by [12 regression cases](../../tests/audit/test_firmware_suite.py) |

The waveform is an illustrative passive RC study with assumed capacitances, switch resistances and GPIO latency. It does not model the complete opamp dynamics or establish NiZ signal margin. The diagnostic clock is 32,768 Hz, with a one-tick conservative allowance; its estimates are not SAADC sample timestamps. Host sanitizers and bounded NVS flash models do not reproduce real RTOS races, flash brownouts, USB electrical timing or battery behavior.

## Reproduction

Run the [builder](../../scripts/build_yeti60_firmware.py) with the pinned Docker workspace, then `python3 scripts/run_audit.py --baseline HEAD`. The audit executes the target, GPIO, scanner, pipeline, CRC, recovery, NVS and waveform checks before combined integration. `python3 scripts/check_yeti60_firmware_suite.py` only verifies existing evidence; it does not rebuild or rerun the tests. After the artifact audit, use `python3 scripts/run_e73_review.py --reuse-artifact-audit --require-design` for the separate design disposition. Nonzero design disposition remains expected while USB protection, battery plug service, NiZ integration or other design gates remain unresolved.

Hardware acceptance still requires first-board rails, SWD, per-key captures in the actual stack, 60-key press/release, USB enumeration and charging together, USB/BLE transitions, idle wake, flash interruption, thermal protection and RF/analog measurements. No physical test is marked passed here.
