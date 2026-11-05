English | [Chinese](calibration-storage.zh-CN.md)

# Calibration record integrity and upgrade

Both Raytac firmware images now save a **308-byte calibration record with its own CRC-32** under `yeti60/thresholds`. Upgrade with the matched calibrator/normal pair and recapture all sixty keys. The older 304-byte record is rejected. Preserve the settings partition; a full-chip erase is unnecessary and would remove Bluetooth bonds as well.

This update changes firmware and its evidence, not PCB, component quantities or fabrication files. The v3 signal fingerprint already includes the calibration source/header and scanner, so their changes produce a new identifier within each board bundle. The v3 fingerprint label is distinct from the record's byte layout.

## Finding and chosen correction

The resolved targets use NVS with **`CONFIG_NVS_DATA_CRC` disabled**. NVS protects its metadata with a checksum, but that does not checksum the payload. Previously a threshold bit flip could preserve the version, range and low-before-high checks and be accepted.

Zephyr documents that enabling its global data-CRC option over an existing store invalidates prior records. We keep that global option unchanged and protect only the keyboard's calibration payload, avoiding a change to Bluetooth and other settings formats. The builder checks the resolved option in both targets. See [Zephyr NVS documentation](https://docs.zephyrproject.org/latest/services/storage/nvs/nvs.html) and the [pinned NVS implementation](https://github.com/zmkfirmware/zephyr/blob/10ba6d0cb38bc3d258775d27982f707599320085/subsys/fs/nvs/nvs.c).

| Byte offset | Size | Field |
|---:|---:|---|
| 0 | 4 | Current board/signal fingerprint, `uint32_t` |
| 4 | 150 | Five rows × fifteen low thresholds, `uint16_t`, row-major |
| 154 | 150 | Five rows × fifteen high thresholds, same ordering |
| 304 | 4 | CRC-32/ISO-HDLC over the preceding fields |

The CRC feeds version, low and high fields explicitly in little-endian order, with polynomial `0xEDB88320`, initial value `0xFFFFFFFF` and final XOR `0xFFFFFFFF`. It excludes the CRC field itself. Production static assertions check the 308-byte layout and CRC offset. The [implementation](../../firmware/yeti60/calibration.c) is shared by normal and calibrator images. CRC detects accidental corruption; it is not authentication and cannot detect every possible multi-bit alteration.

## Loading and saving

The actual settings handler rejects unknown keys, wrong lengths, read errors/short reads, a different fingerprint, a CRC mismatch, reversed/equal thresholds, and thresholds above the 12-bit ADC range. It publishes a loaded record only after all checks pass. A rejected load does not overwrite a valid pending record. With no valid loaded calibration the scanner suppresses key reports; it does not silently fall back to the illustrative default thresholds.

The worker computes a candidate CRC after collecting the thresholds. Only a complete valid capture and a successful `settings_save_one` result enable the new thresholds. A failed save leaves the previous runtime `saved` record unchanged and does not mark the new capture valid. The actual [pinned settings dispatcher](https://github.com/zmkfirmware/zephyr/blob/10ba6d0cb38bc3d258775d27982f707599320085/subsys/settings/src/settings.c) logs and consumes an individual handler error, so a bad calibration entry does not abort subsequent ordinary settings handlers. We compile that dispatcher body in the regression test.

No change here erases settings, clears bonds, enables global NVS CRC, or changes the final 64 KiB settings partition. The new record uses four extra payload bytes. Complete flash allocation includes NVS metadata/alignment and the setting name, not only the payload. Hardware power-loss behavior, flash wear and voltage margins are not established by the host tests.

## Reproduce and evidence

From the repository root:

```sh
python3 variants/raytac/scripts/test_yeti60_calibration.py
python3 variants/raytac/scripts/test_yeti60_scan_control.py
```

The first command requires host Clang/Python; the second also reads the pinned ZMK/Zephyr workspace. Both run native C under ASan/UBSan.

| Evidence | Coverage |
|---|---|
| [Calibration report](../audit/calibration.json) | Independent Python zlib comparison for 512 encoded records, including correctly checksummed invalid thresholds; 2,464 single-bit flips; 308 whole-byte inversions; 2,433 sliding all-ones 32-bit bursts; all corruptions rejected |
| Calibration mutants | Omitted CRC validation, omitted ADC maximum and wrong CRC polynomial all fail |
| [Scanner report](../audit/scan-control.json) | Verbatim production load/save/worker bodies and pinned settings dispatcher; old 304-byte and other wrong lengths; read error/short read; CRC/version/range failures; valid threshold application; rejected load preserves pending valid record; failed save preserves previous runtime record |
| Scanner mutants | Fourteen scenarios, thirteen rejected mutants overall, including skipped record-length/validation/read-size/save-CRC checks and incorrectly propagated handler errors |
| [Candidate reports](../../hardware/usb-short-route/firmware/README.md) | Independent tests in the isolated candidate tree, matched ARM image identifiers, source/output hashes and settings-safe HEX address ranges |

This is not physical flash testing or a Zephyr/NVMC/NVS power-cut emulator. The modeled settings interfaces do not prove sector erase atomicity, garbage-collection recovery, brownout behavior, transport delivery or simultaneous runtime settings reload. Do not interpret corruption tests as power-loss acceptance.

## Upgrade and first-board acceptance

1. Use the [current candidate bundle](../../hardware/usb-short-route/firmware/README.md). Program only the image's application sectors, preserving `0xF0000–0xFFFFF`, following [SWD instructions](../build/flashing.md).
2. The old 304-byte calibration is rejected, leaving key reporting disabled until recapture. The USB calibrator shell remains the first-board input path. Compare `status` with the bundle's `calibration_contract_version`; do not reuse threshold values from a different bundle.
3. Capture released keys and all sixty pressed positions, save, and inspect confirmation/status. Flash the matched normal image without mass erase. Reboot and verify all keys plus existing Bluetooth profiles.
4. On the first board, measure supply voltage during save/erase, verify actual saved-data retention across ordinary resets, and qualify controlled interrupted writes with the battery/charger supply arrangement. Confirm complete valid prior data, a fully committed new record, or a clear uncalibrated state, never silently wrong thresholds. Record real flash/driver errors and recovery before accepting this behavior.

Battery supplier confirmation and all [open-bench electrical/functional checks](../../OPEN-BENCH.md) still apply. No board has been flashed or physically tested for this change.
