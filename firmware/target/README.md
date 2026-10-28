English | [Chinese](README.zh-CN.md)

# YETI60 target firmware

This ZMK module binds the tested portable scan core to nRF52840 GPIO/SAADC and the current schematic pin header. ZMK provides USB HID, BLE HID, bonding, five host profiles and persistent settings. The HHKB transform follows the actual plate-to-electrode correspondence. The custom board uses its internal LF RC clock, no development-kit LEDs, and a direct SWD application at address zero.

## Reproducible build

Docker must be running. Initialize a west workspace at `~/.cache/yeti60-zmk-workspace` with `firmware/target/config/west.yml`, then run `west update` and `west zephyr-export` in the pinned build container. The manifest freezes every active ZMK, Zephyr and HAL dependency to a commit. The builder rejects any workspace revision that differs from this lock. Run `python3 scripts/build_yeti60_firmware.py --workspace <workspace>` from this repository. The script rejects modified dependency sources, builds normal and calibrator variants, and records commits, source/configuration/device-tree hashes and output hashes in `docs/audit/yeti60-target-build.json`.

The build container is pinned by digest in the script. Generated build directories are ignored. Distributable HEX, BIN and ELF files are under `firmware/releases/`. J3 uses the project's custom SWD pinout: check the hardware contract before connecting a probe. Preserve the final 64 KiB settings partition when updating normal firmware after calibration. A full-chip erase removes calibration and Bluetooth bonds.

## Calibration and operation

Flash the calibrator HEX first. Its USB CDC console exposes `yeti_calibrate release`, `yeti_calibrate press` and `yeti_calibrate save`. With every key released, collect release samples; then press every installed key fully at least once, release all keys and save. The owner scan thread derives per-key hysteresis thresholds, rejects insufficient ranges and ADC saturation, and saves valid data in NVS. No key events are emitted without valid calibration. Keep the same board/settings layout when flashing normal firmware. A fingerprint of the pin header and board device tree rejects stale calibration after either contract changes.

The Fn layer supplies F-keys, navigation and five Bluetooth profile selections. USB/BLE HID and host switching use the pinned ZMK implementation. Charging stays at USB100; firmware drives the charger controls from USB state. Battery reporting is disabled until the pack and measurement integration are completed. Scan faults latch the analog front end off; reset after diagnosing the fault.

Successful compilation proves a target binary can be produced. First-article measurements are still required for thresholds, timing, USB enumeration, pairing, current consumption and wake behavior. The startup and calibration values are engineering parameters pending those measurements. This firmware does not make a physical acceptance claim.
