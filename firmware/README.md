English | [Chinese](README.zh-CN.md)

# YETI60 firmware

The current [nRF52840 control core](yeti60/README.md) and [host simulation](../docs/audit/yeti60-firmware-simulation.json) use the schematic-derived GPIO, SAADC and mux contract. Run `python3 scripts/simulate_yeti60_firmware.py` from the repository root.

Only the current core and its tests are maintained here. Original EC60 QMK sources remain in the attributed `EC60` submodule; duplicate legacy firmware and tests have been removed. The GPL license is retained.

The target module supplies a flashable SWD application, GPIO/ADC driver, USB/BLE stacks and HHKB keymap. Physical calibration and on-device operation require a sample. Host sanitizer tests establish logic behavior with mocked hardware, not on-device operation.

[Buildable target firmware](target/README.md) now supplies a custom YETI60 board, the same portable core, ZMK USB/BLE HID, persistent calibration and normal/calibrator HEX files. On-device verification remains pending.
