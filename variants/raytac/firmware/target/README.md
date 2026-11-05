English | [Chinese](README.zh-CN.md)

# YETI60 target firmware

EC scanning now releases before raising a row and reclamps before lowering it; see the [analog timing study](../../docs/testing/analog-waveform.md). The calibrator adds `yeti_calibrate timing` for coarse RTC elapsed estimates from the row GPIO call to ADC return, with the 32768 Hz clock reported and one tick of quantization guard; these are not physical sample timestamps. Recalibrate with the matching bundle after upgrading.

USB charging now uses the [status callback and deconfiguration policy](../../docs/testing/usb-event-policy.md), independently of scan polling. Suspend disables charging/input; resume and 500 mA permission follow the actual configuration byte. Both variants share this logic; recalibrate when upgrading from an older bundle.

For the current repaired PCB, use the [candidate build/flash entry](../../hardware/usb-short-route/firmware/README.md). [Recovery and calibration contract v3](../../docs/testing/firmware-recovery.md) adds Fn + double-tap Backspace (less than 400 ms between presses) to clear only the selected BLE profile. The first v3 update requires recapturing thresholds; preserve settings when flashing the matching normal build.

This ZMK module binds the tested portable scan core to nRF52840 GPIO/SAADC and the current schematic pin header. ZMK provides USB HID, BLE HID, bonding, five host profiles and persistent settings. The HHKB transform follows the actual plate-to-electrode correspondence. The custom board uses its internal LF RC clock, no development-kit LEDs, and a direct SWD application at address zero.

## Reproducible build

Docker must be running. Initialize a west workspace at `~/.cache/yeti60-zmk-workspace` with `firmware/target/config/west.yml`, then run `west update` and `west zephyr-export` in the pinned build container. The manifest freezes every active ZMK, Zephyr and HAL dependency to a commit. ZMK is the project fork `https://github.com/wZuck/zmk` at `0862fc0f8c864834007986efcaf52f292ea6d37d`; its only divergence from upstream is the configurable connectable advertising interval (`ZMK_BLE_ADV_INT_MIN/MAX`). The builder rejects any workspace revision that differs from this lock. Run `python3 scripts/build_yeti60_firmware.py --workspace <workspace>` from this repository. The script rejects modified dependency sources, builds normal and calibrator variants, and records commits, source/configuration/device-tree hashes and output hashes in `docs/audit/yeti60-target-build.json`.

The build container is pinned by digest in the script. Generated build directories are ignored. Distributable HEX, BIN and ELF files are under `firmware/releases/`. J3 uses the project's custom SWD pinout: check the hardware contract before connecting a probe. Preserve the final 64 KiB settings partition when updating normal firmware after calibration. A full-chip erase removes calibration and Bluetooth bonds.

## Calibration and operation

Flash the calibrator HEX first. Run `yeti_calibrate release` with all keys released and wait for the 128-frame completion message. For each of the 60 installed keys, hold that key fully down BEFORE running `yeti_calibrate press <row> <col>`; keep it held until its 128-sample completion message, then release it. Use `yeti_calibrate status` to inspect sample counts, worst-case bounds and guards; save only after all keys pass with `yeti_calibrate save`. Bare `press` is intentionally rejected. The owner scan thread requires at least 64 labeled samples per state, rejects saturation/overlap, and places thresholds strictly between the worst observed bounds with a conservative six-standard-deviation guard. No key events are emitted during capture or without valid calibration. The new fingerprint includes pins, device tree, native PCB and calibration algorithm, so old optimistic calibration is rejected. Keep the exact same board and settings partition when flashing normal firmware.

The Fn layer supplies F-keys, navigation and five Bluetooth profile selections. USB/BLE HID and host switching use the pinned ZMK implementation. P2 requests 500 mA (legacy Zephyr `CONFIG_USB_MAX_POWER=250`). Firmware enables USB500 charging only after host configuration, keeps USB100 with charging disabled before configuration, disables charging/input during suspend and retains the accepted configuration on resume. Both linked ELF descriptors are checked. Battery reporting is disabled until the pack and measurement integration are completed. Scan faults latch the analog front end off; reset after diagnosing the fault.

## Wired charging and automatic USB priority

Once a computer accepts the USB configuration, charging and USB HID operate concurrently. The target adapter explicitly selects ZMK's USB preference even if settings retained a BLE preference. An already selected USB preference is left alone, avoiding repeated settings writes. Detach leaves ZMK to fall back to the active BLE profile; no new pairing is required for an existing bond. A charge-only source does not enumerate and does not become a USB data host.

| Host state | Charging while firmware runs | HID route |
|---|---|---|
| Powered, not configured | Disabled; USB100 input mode | Ready BLE profile, if connected |
| Configured, 500 mA accepted | Enabled; USB500 input budget shared with system load | USB takes priority, including while BLE is connected |
| USB suspended | Disabled; input high impedance | ZMK suspend handling; USB reports resume with the host |
| USB detached | No USB charging | Active BLE profile when connected |

The 500 mA value is not a fixed cell charge current. Charger programming, PowerPath load sharing, temperature, cable loss and the battery's charge phase govern actual current. The host regressions compile the actual adapter with GPIO/workqueue interfaces under ASan/UBSan; the USB event suite also compiles the complete pinned ZMK USB source. The portable core is tested separately. It tests concurrent charging/USB preference, retained BLE override, suspend/resume/reset/detach, failed-update retry and absence of repeated settings/GPIO writes. It does not execute a real USB or BLE stack.

## Idle power policy

The scan thread keeps a 4 ms interval while a key is held or state changes. After 30 seconds without a pressed or changed key it switches to 30 ms, gates the AFE through U8/AFE_EN between idle frames, and restores it before the next scan. `YETI60_ACTIVE_SCAN_MS`, `YETI60_IDLE_SCAN_MS`, `YETI60_IDLE_AFTER_MS` and `YETI60_AFE_IDLE_GATING` control this behavior. The devicetree selects REG1 DC/DC; REG0 remains LDO because the board has no external DCCH inductor. BLE requests a 15–30 ms connection interval and 0 dBm; connectable advertising uses 200–300 ms through the ZMK fork's `ZMK_BLE_ADV_INT_MIN/MAX`. The host may still override connection parameters. `CONFIG_ZMK_SLEEP` remains disabled because EC keys are not a System OFF GPIO wake source; enabling it would leave no reliable key wake.

Successful compilation proves a target binary can be produced. First-article measurements are still required for thresholds, timing, USB enumeration, pairing, current consumption and wake behavior. The startup and calibration values are engineering parameters pending those measurements. This firmware does not make a physical acceptance claim.

This option publishes `yeti60-raytac.hex/.bin/.elf` under `firmware/releases/normal/` and `firmware/releases/calibrator/`. Build from this variant directory and do not flash E73 files.

[Per-key capture and rejection rules](../../../../docs/testing/calibration.md); [60-key command map](calibration-keys.csv).

Analog high impedance and clamp release now use `GPIO_DISCONNECTED`, with digital input/output and pulls disabled; initialization failure attempts AFE shutdown. See the [GPIO mode review](../../docs/testing/gpio-mode-policy.md) for actual-source tests and physical limits. The mode helper is part of the calibration fingerprint; recalibrate after upgrading.

Commands reject unavailable startup; runtime scan faults power down the AFE, release tracked keys and reject further capture/save. Both images use a 128-entry key-event queue. See [scanner lifecycle/fault regression](../../docs/testing/scan-control.md), including the actual worker, 60-key capture and a 120-event burst. Real host delivery remains first-board acceptance work.

Calibration now uses a 308-byte record with its own CRC-32; older 304-byte records require recapture. Global NVS settings formats and Bluetooth bonds are unchanged. See [calibration storage and upgrade](../../docs/testing/calibration-storage.md). Corruption is host-tested; physical flash power-loss acceptance remains open.

The [pinned NVS recovery model](../../docs/testing/nvs-powercut.md) executes actual NVS/calibration-load code across 14,795 selected interruption trials, including GC and a second cut during recovery, with sentinel preservation and successful later saves. It is not physical NVMC/brownout/Bluetooth acceptance. This test update leaves firmware and identifiers unchanged; `--host-tests-only` can recheck existing candidate artifacts and republish tests, while changed firmware inputs require a full build.
