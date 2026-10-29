English | [Chinese](README.zh-CN.md)

# YETI60 firmware

The current [nRF52840 control core](yeti60/README.md) and [host simulation](../docs/audit/yeti60-firmware-simulation.json) use the schematic-derived GPIO, SAADC and mux contract. Run `python3 scripts/simulate_yeti60_firmware.py` from the repository root.

Only the current core and its tests are maintained here. Original EC60 QMK sources remain in the attributed `EC60` submodule; duplicate legacy firmware and tests have been removed. The GPL license is retained.

The target module supplies a flashable SWD application, GPIO/ADC driver, USB/BLE stacks and HHKB keymap. Physical calibration and on-device operation require a sample. Host sanitizer tests establish logic behavior with mocked hardware, not on-device operation.

[Buildable target firmware](target/README.md) now supplies a custom YETI60 board, the same portable core, ZMK USB/BLE HID, persistent calibration and normal/calibrator HEX files. On-device verification remains pending.

The [plate/copper/firmware check](../docs/audit/yeti60-key-geometry.json) matches all 60 opening centers to actual ROW/COL copper, including the alternate lands inside SW60/SW62. Right Shift is ROW3/COL13 and Fn is ROW3/COL14; the former ROW3/COL12 and ROW4/COL14 choices were corrected in both the target transform and calibration mask, and both target variants were rebuilt. Geometric coverage does not replace physical key calibration. Follow the [illustrated programming and installation guide](../docs/assembly/build-guide.md).
