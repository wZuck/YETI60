English | [Chinese](firmware-recovery.zh-CN.md)

# Raytac firmware recovery and calibration compatibility

Use the current candidate's [normal/calibrator files and first-board procedure](../../hardware/usb-short-route/FIRST-ARTICLE.md). Keep a normal/calibrator pair from the same candidate bundle: the retained reference-board releases use a different PCB fingerprint despite sharing a filename. This review changes firmware and tests; PCB wiring and the C04 mechanical parts are unchanged.

## Re-pair one Bluetooth host

1. Select the intended slot with **Fn + Q/W/E/R/T**, corresponding to slots 1–5 (internal indexes 0–4). Release the slot-selection key.
2. Keep Fn held and **double-tap Backspace**, with the two presses less than **400 ms** apart. Release Backspace and Fn. A single tap or one continuous hold does nothing; ordinary Backspace on the base layer is preserved.
3. Remove/forget the old YETI60 pairing on that host, then pair again using that slot. Check the intended host/slot before clearing.

The binding invokes `BT_CLR`, which clears the **selected** profile. It does not invoke `BT_CLR_ALL`, a flash erase, a settings reset, or the calibration capture command. Other host slots remain available. Re-pairing still requires the host to forget its old bond. See the [official Bluetooth behavior reference](https://zmk.dev/docs/keymaps/behaviors/bluetooth).

The gesture requires working, calibrated key input. For an uncalibrated first board, use the USB calibrator shell first. If key input is unavailable because of a hardware/scan fault, repair that fault and use SWD/USB recovery rather than relying on the key gesture.

## When calibration must be repeated

Calibration contract **v3** hashes the actual scanner, portable waveform core, calibration implementation and headers, pin header, board/device-tree/default configuration, dependency lock, and the calibration CMake contract. Effective active/idle scan intervals and AFE gating are included. Both variants must have the same identifier; the builder reads the actual scanner compiler invocation and resolved device tree to verify this.

Changing SAADC gain, pulse/discharge implementation, calibration rules or effective scan options now changes the identifier. Previously the fingerprint covered the PCB, pins, board DTS and calibration algorithm but omitted the scanner/core implementations. Old thresholds could therefore have survived incompatible changes.

The first v3 update rejects earlier calibration. Load the matching calibrator, capture all 60 keys, save, and then flash the matching normal image while preserving the final 64 KiB settings partition. The normal and calibrator images are at application address zero. A full-chip erase removes calibration and Bluetooth bonds; it is unnecessary for ordinary selected-profile clearing.

`yeti_calibrate status` prints `calibration contract=0x... valid=...` before the per-key table. Compare the identifier with [`calibration_contract_version` in the candidate target check](../../hardware/usb-short-route/firmware/target-check.json). Invalid versions or out-of-range/reversed thresholds are rejected before key reporting is enabled. The 304-byte NVS record format is unchanged. Keymap-only changes do not alter the signal fingerprint. Persisted settings ordinarily survive reflashing, as documented by [ZMK](https://zmk.dev/docs/config/settings).

## USB and held-key behavior

The configured USB link retains priority while charging is enabled; before accepted configuration charging is disabled and input remains USB100. Suspend selects charger/input high impedance. On detach the pinned ZMK endpoint implementation selects an available bonded BLE profile. These policies are unchanged by this recovery feature.

The actual target uses ZMK HID delivery. Its endpoint change handler clears the old endpoint's reports. **Release and press a held key again after changing hosts or profiles**; automatic replay of held keys to the new host is not promised. The portable core's report callback is acknowledged but unused by the target adapter, so its host-model handover alone is not evidence of ZMK HID behavior.

## Verification scope

| Evidence | What executes or is inspected |
|---|---|
| [Recovery tests](../audit/firmware-recovery.json) | Actual CMake fingerprint function in the pinned build container; source/timing mutation cases; unchanged keymap-only compatibility |
| Native gesture test in that report | Unmodified pinned ZMK tap-dance C under ASan/UBSan, with host timing and behavior-dispatch interfaces; single, held, slow and interrupted taps do not clear; fast double-tap dispatches selected-profile clear once |
| [Candidate target check](../../hardware/usb-short-route/firmware/target-check.json) | Both ARM builds, USB500 descriptors, identical calibration versions and the actual resolved Fn/Backspace/profile bindings |
| [Calibration test](../../hardware/usb-short-route/firmware/calibration.json) | Actual threshold generator and persisted-record validator, including stale version and malformed threshold rejection |
| [USB policy simulation](../../hardware/usb-short-route/firmware/simulation.json) | Actual adapter/core with simulated USB/ZMK interfaces; simultaneous charging/wired priority and suspend/reset/detach policies |

These tests do not execute real pairing/unpair persistence, USB traffic, radio timing or analog waveforms. RTOS/radio preemption, actual SAADC timing, threshold margin under USB/charge/BLE loads and physical key behavior require the first board. The scanner's deliberate fault latch requires a reset after diagnosing an error. Successful compilation or native simulation does not close physical acceptance.

Reproduce with `python3 scripts/test_yeti60_recovery.py` after initializing the pinned west workspace and starting Docker, followed by `python3 scripts/build_usb_short_firmware.py` for the current candidate. The test compiles the pinned upstream implementation; host interfaces do not replace the production ZMK source. Pinned dependency: `wZuck/zmk@0862fc0f8c864834007986efcaf52f292ea6d37d`.
