# YETI60 nRF52840 control-core simulation

English | [Chinese](README.zh-CN.md)

`core.c` is a new portable control core bound to the current MDBT50Q-1MV2 pin assignment. `board_pins.h` is generated from the schematic XML and module pin contract. Scan ADC is P0.04/AIN2; battery ADC is P0.05/AIN3.

Run from the repository root:

```sh
python3 scripts/generate_yeti60_pin_contract.py --check
python3 scripts/simulate_yeti60_firmware.py
```

The host executable runs the actual core C source under AddressSanitizer and UndefinedBehaviorSanitizer. Coverage includes all 75 scan positions, mux bank/address and open-drain sequencing, one driven row at a time, explicit settling/discharge/acquisition waits, hysteresis and two-frame debounce, ADC failure with atomic frame abort, released keys on fault, AFE high-Z shutdown, USB100/USB500/suspend controls, held-key USB/BLE report handover, boot-protocol rollover, send retries, reentrancy exclusion and a 50 ms battery-divider settling delay. A deterministic 2,000-frame noise scenario checks logic behavior within the hysteresis band.

The core also checks aliased HAL/configuration reinitialization, invalid USB mode values and retrying a failed old-host release during transport changes. Successful scan frames are exported as a [CSV trace](../../docs/audit/yeti60-firmware-trace.csv), with a [trace-derived plot](../../renders/yeti60-firmware/README.md).

## Limits

This is native host simulation with mocked GPIO, ADC and HID transports, **not** an nRF52840 binary, peripheral-register/instruction emulator, USB enumeration test or BLE pairing/radio test. `usage[][]` is supplied by the caller; the test mapping is not a finished HHKB keymap. The application/HAL and actual USB/BLE stacks still need target integration.

The test timing and thresholds are illustrative configuration values, not physical calibration. The battery conversion assumes a 12-bit SAADC using a 0.6 V reference, gain 1/6 and the board's 1M:1M divider. Hardware must serialize access to the shared SAADC and configure that reference/gain. USB current limits must reflect host enumeration; the charger NTC protection remains a hardware function.

Results and source hashes: [yeti60-firmware-simulation.json](../../docs/audit/yeti60-firmware-simulation.json). Original GPL EC60 sources remain in the `EC60` submodule; duplicate legacy tests are outside this pipeline.

Use one owner for the core and queue other threads or interrupt requests. The busy flag rejects synchronous callback reentry; it is not an atomic thread lock. GPIO, wait and HID callbacks must return normally; initialize only a quiescent core. Tests cover reentry rejection during initialization, power, connection and scan callbacks, including fault reporting.
