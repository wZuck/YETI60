English | [Chinese](README.zh-CN.md)

# YETI60 firmware review

The current [nRF52840 control core](yeti60/README.md) and [host simulation](../docs/audit/yeti60-firmware-simulation.json) use the schematic-derived GPIO/SAADC/mux contract. They do not provide a flashable nRF application or validated USB/BLE stacks.

`ec60/` preserves the GPL-2.0-or-later EC60 QMK reference from Cipulot commit `b9c04625bb9944f6fb806aa571da8592cdff8565`, with its license. Its previous repairs address five rows incorrectly accessing a sixth pin, fifteen columns accessing a sixteenth column, reversed hysteresis, incompletely initialized configuration, and invalid/equal threshold acceptance. Failed initialization avoids ADC reads and clears key state.

Run `python3 scripts/check_firmware.py` to compile the actual reference `ec_switch_matrix.c` and `matrix.c` under ASan/UBSan. It covers boundaries, mux channels, 75 positions, threshold edges, invalid configuration and reinitialization. `python3 scripts/check_firmware.py --source EC60/Firmware/ec60 --bounds-only` intentionally reproduces upstream bounds failures.

ADC, GPIO and critical sections in the reference tests are mocked. They do not certify timing, analog noise, power sequencing, thresholds, wake behavior, target QMK compilation or wireless operation. An upstream old `.bin` is not a build of these repaired sources.
