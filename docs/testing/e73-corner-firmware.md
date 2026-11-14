[English](e73-corner-firmware.md) | [Chinese](e73-corner-firmware.zh-CN.md)

# Firmware for the E73 lower-right PCB

Use the CORNER-03 build under `hardware/e73-hhkb-corner/firmware/`, with `manifest.json` and both `releases/normal/yeti60-e73.hex` and `releases/calibrator/yeti60-e73.hex`. Root-level pre-migration images and Raytac images do not match this PCB calibration identity. The [corner review](../engineering/e73-hhkb-corner.md) controls the design hold.

Reproduce after the current native routing, USB-reference and bounded-fit checks:

```sh
uv run --python 3.14.7 --with-requirements requirements-audit.txt python scripts/build_e73_corner_firmware.py
python3 scripts/check_e73_corner_firmware.py
```

The builder requires the pinned ZMK workspace, its pinned Docker image and a running Docker daemon. It builds in an ignored isolated root, checks both linked ARM images, runs the core/calibration/USB/GPIO/scan/key-pipeline/NVS/recovery and RC sensitivity suite, and runs linked-target and suite mutation tests before copying images. `--prepare-only` prepares the pin contract without building. `--development-build` builds/tests in the ignored workspace and publishes no images.

Use **HEX for initial SWD programming**: it also releases NFC pins as GPIO through UICR. The BIN omits that explicit record. Application address is zero; no UF2 bootloader is assumed. Confirm the custom J3 pinout before connecting a probe. Follow the [existing calibration procedure](../../firmware/target/README.md#calibration-and-operation), substituting these candidate HEX files. Program calibrator first, complete all 60 keys, save, then program normal while preserving the final 64 KiB settings partition. Full erase loses calibration and BLE bonds. A changed PCB fingerprint requires fresh calibration.

Both images use internal RC low-frequency clock and REG1 LDO. After host configuration, charging and USB HID operate together with USB priority; suspend disables charger input, and detach permits BLE fallback. These are linked-binary and host-model checks. No unit has passed physical USB/BLE/EC, battery charging, thermal or RF tests. Battery reporting remains disabled pending pack/measurement integration. The passive RC model uses assumed parasitics, not extracted PCB/NiZ capacitance.

[Manifest](../../hardware/e73-hhkb-corner/firmware/manifest.json) · [Normal HEX](../../hardware/e73-hhkb-corner/firmware/releases/normal/yeti60-e73.hex) · [Calibrator HEX](../../hardware/e73-hhkb-corner/firmware/releases/calibrator/yeti60-e73.hex)
