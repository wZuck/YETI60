English | [Chinese](README.zh-CN.md)

# Firmware for the USB repair candidate

EC scanning now releases before raising a row and reclamps before lowering it; see the [analog timing study](../../../docs/testing/analog-waveform.md). The calibrator adds `yeti_calibrate timing` for coarse RTC elapsed estimates from the row GPIO call to ADC return, with the 32768 Hz clock reported and one tick of quantization guard; these are not physical sample timestamps. Recalibrate with the matching bundle after upgrading.

USB charging now uses the [status callback and deconfiguration policy](../../../docs/testing/usb-event-policy.md), independently of scan polling. Suspend disables charging/input; resume and 500 mA permission follow the actual configuration byte. Both variants share this logic; recalibrate when upgrading from an older bundle.

[Recovery and calibration compatibility](../../../docs/testing/firmware-recovery.md): Fn + double-tap Backspace clears only the selected BLE profile. The new v3 signal fingerprint rejects older calibration; capture again with this bundle and use its matching normal image.

Use these files only with the [candidate board and its two required cables](../README.md). The candidate is still an engineering build, not a fabrication release. Normal and calibrator targets were rebuilt from the pinned ZMK/Zephyr dependencies against this PCB, checked as ARM firmware, and exercised through the host control/calibration tests. No board has been flashed or physically tested.

| Purpose | SWD HEX | Flat binary |
|---|---|---|
| Capture actual key calibration over USB | [Calibrator](releases/calibrator/yeti60-raytac.hex) | [Calibrator BIN](releases/calibrator/yeti60-raytac.bin) |
| Normal USB/BLE keyboard | [Normal](releases/normal/yeti60-raytac.hex) | [Normal BIN](releases/normal/yeti60-raytac.bin) |

Follow the retained [SWD and target instructions](../../../firmware/target/README.md). The application starts at 0x00000000; no UF2 bootloader is assumed. Preserve calibration/settings when transitioning from calibrator to normal; do not mass-erase after capture. J3, GPIO assignments and EC calibration procedure are unchanged. Install the mandatory J5-to-J1 power jumper before expecting USB-only enumeration.

[Publication manifest](manifest.json) records the candidate PCB fingerprint, current source hashes and downloadable artifact hashes. [Build evidence](build.json), [target checks](target-check.json), [host simulation](simulation.json), [calibration tests](calibration.json) and [host trace](trace.csv) preserve the build/test evidence. Both linked USB configurations request 500 mA; descriptor validation does not prove the host has configured the device or granted that current on hardware.

Paths inside copied build/test reports are relative to the isolated `.assembly-work/usb-short-build` tree. The publication manifest maps the published files to paths under the Raytac variant root. ELF files remain in that ignored build tree and are listed by hash; rebuild to obtain them for debugging. This avoids duplicating large debug files in the engineering candidate.

From the repository root, after the candidate native and CAD checks pass:

```sh
python3 variants/raytac/scripts/build_usb_short_firmware.py
python3 variants/raytac/scripts/check_usb_short_firmware.py
```

The wrapper copies current firmware sources, candidate PCB/netlist and pin map into an isolated build directory, rebuilds both targets in the pinned container, runs target/host/calibration checks and publishes only this candidate's HEX/BIN and evidence. Canonical firmware releases are left untouched. Docker and the existing locked west workspace are required, as described in the target instructions. USB/BLE radio, actual key signals, simultaneous charging/input, analog settling and battery safety still require the physical acceptance procedure.

See the [analog GPIO/startup cleanup review](../../../docs/testing/gpio-mode-policy.md) and [this bundle's independent host evidence](gpio-mode-policy.json). Both builds use high impedance with digital buffers disabled; recalibrate after upgrading.

Commands reject unavailable startup; runtime scan faults power down the AFE, release tracked keys and reject further capture/save. Both images use a 128-entry key-event queue. See [scanner lifecycle/fault regression](../../../docs/testing/scan-control.md), including the actual worker, 60-key capture and a 120-event burst. Real host delivery remains first-board acceptance work.

Calibration now uses a 308-byte record with its own CRC-32; older 304-byte records require recapture. Global NVS settings formats and Bluetooth bonds are unchanged. See [calibration storage and upgrade](../../../docs/testing/calibration-storage.md). Corruption is host-tested; physical flash power-loss acceptance remains open.

The [pinned NVS recovery model](../../../docs/testing/nvs-powercut.md) executes actual NVS/calibration-load code across 14,795 selected interruption trials, including GC and a second cut during recovery, with sentinel preservation and successful later saves. It is not physical NVMC/brownout/Bluetooth acceptance. The NVS model itself is test-only; `--host-tests-only` can recheck existing candidate artifacts and republish tests, while changed firmware inputs require a full build.

Both images include the idle short-tap correction: the first active pending edge restores 4 ms scanning while retaining two-frame debounce. See [model evidence and limits](../../../docs/testing/scan-control.md). The scanner fingerprint changes, so recapture all sixty keys and use the matching normal image in this directory.
