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
