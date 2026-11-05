[English](usb-event-policy.md) | [Chinese](usb-event-policy.zh-CN.md)

# USB event and charger ownership review

This applies to the current Raytac [first-article package](../../hardware/usb-short-route/FIRST-ARTICLE.md). Both normal and calibrator firmware use the same policy. It preserves simultaneous configured USB HID and charging. Host tests and linked ARM checks pass; real USB timing, current and charge transitions remain first-board measurements.

## Problems found and correction

The previous adapter changed charger pins only when the EC scanner polled USB status. An idle scanner sleeps 30 ms between scans, in addition to ADC, AFE settling and other work. Console output and settings writes could delay the next poll further. That is unsuitable for a prompt suspend or deconfiguration response.

The pinned Zephyr stack reports both configuration 1 and `SET_CONFIGURATION(0)` as `USB_DC_CONFIGURED`, with the actual configuration byte in `params`. The pinned ZMK callback ignores this byte. Merely checking its HID-ready flag can therefore retain charging and wired readiness after configuration zero.

The target module now links with `--wrap=usb_enable`. Its wrapper registers a charger callback with the original Zephyr `usb_enable`, then forwards each notification to the original ZMK callback. It does not replace the controller's internal callback, add a USB interface, or modify dependency sources. A zero, missing or invalid configuration byte is forwarded to ZMK as RESET so ZMK also drops its accepted-configuration flag. The host tests compile the complete unmodified pinned ZMK USB source to verify that behavior.

Charger GPIO writes finish inside the USB status callback, before ZMK queues its notification and without waiting for the scanner/system workqueue. The pinned nRF driver itself dispatches these notifications on its USB workqueue: this removes the additional scan delay, not all driver/RTOS latency. The scanner continues to request USB transport preference on ZMK's system workqueue, where endpoint/report changes belong. A stale queued preference request rechecks readiness before switching hosts.

## State and pin table

Pins are physical active levels: CE is active low. All three are on GPIO0: EN1=P0.06, EN2=P0.07, CE=P0.08.

| Event/state | CE | EN1 | EN2 | Result |
|---|---:|---:|---:|---|
| Boot/connected, not configured | 1 | 0 | 0 | No charging; USB100 system input |
| Configuration byte 1 accepted | 0 | 1 | 0 | Charging allowed; USB500 budget shared with system; USB HID preferred |
| Suspend | 1 | 1 | 1 | No charging; input high impedance; system uses the battery |
| Resume after valid configuration | 0 | 1 | 0 | USB500/charging restored |
| Reset, detach, configuration zero/missing/invalid | 1 | 0 | 0 | Configuration revoked; no charging; USB100 if input exists |
| Resume following reset/deconfiguration | 1 | 0 | 0 | Resume alone cannot reauthorize charging |
| USB controller error | 1 | 1 | 1 | No charging; configuration revoked |
| GPIO write or USB-enable failure | 1 | 1 | 1 | Best-effort disable/high impedance; latched until restart |

SOF/interface/halt notifications do not independently grant configuration or lift suspend. Repeated events in an unchanged power mode do not rewrite GPIO. Initialization is idempotent. Charger pins have one runtime owner; the scanner no longer calls the portable core's `yeti_connections` charger/report demo. Actual HID remains ZMK-owned.

CE is disabled before changing modes. The mode writes pass through EN1 high before changing EN2, avoiding the unintended EN1=0/EN2=1 external-ILIM mode, including suspend-to-reset transitions. The short intermediate modes are USB100, USB500 or high impedance, with charging disabled. A GPIO error aborts normal sequencing and attempts disable/high impedance; software cannot guarantee safety against a physically stuck pin or failed charger. Independent pack protections remain required.

**A protected battery or suitable battery simulator is required for meaningful suspend/resume acceptance.** With no battery, selecting input high impedance can remove system power. USB-only power is useful for initial bring-up, but cannot prove battery-backed suspend, resume or BLE operation. An ordinary power-only charger does not enumerate and therefore does not authorize this design's USB500 charging.

## Evidence and limits

- [USB event host evidence](../audit/usb-event-policy.json): 11 isolated scenarios under ASan/UBSan, actual adapter plus unmodified pinned ZMK USB callback. Covers configuration zero/null/invalid, suspend/reset/resume without scanner polls, events while preference work is blocked, stale queued work, repeated events, intermediate GPIO states, unavailable GPIO, all three initialization writes and all five resume writes failing individually, and USB-enable failure.
- [Candidate ARM check](../../hardware/usb-short-route/firmware/target-check.json): both linked USB500 descriptors and decoded Thumb BL targets verify ZMK initialization calls the wrapper and the wrapper calls the original stack. Symbol presence alone is insufficient.
- [Core simulation](../../hardware/usb-short-route/firmware/simulation.json): the retained portable charger helper also avoids external-ILIM intermediate states. Its mock HID reports are not real target USB/BLE delivery.

Before accepting the first board, capture the USB suspend/reset/configuration events against CE/EN1/EN2 and USB input current, with the actual protected pack connected. Check host deconfiguration, suspend/resume, repeated reset/re-enumeration and typing while charging. Measure total callback/driver latency, input transients, suspend current and temperatures. No native test or ELF check certifies those physical results or full-stack concurrency.

Reproduce with `python3 scripts/test_yeti60_usb_events.py`, then build/check both firmware bundles as described in the [target guide](../../firmware/target/README.md). The host event test needs the pinned ZMK checkout at `~/.cache/yeti60-zmk-workspace/zmk` and host Clang. These source changes alter the v3 calibration identifier: use matching normal/calibrator files and recalibrate when upgrading from an older bundle.

## Primary sources

- [Pinned ZMK USB callback](https://github.com/wZuck/zmk/blob/0862fc0f8c864834007986efcaf52f292ea6d37d/app/src/usb.c): accepted-configuration flag, status callback and deferred notification.
- [Pinned Zephyr configuration handling](https://github.com/zmkfirmware/zephyr/blob/10ba6d0cb38bc3d258775d27982f707599320085/subsys/usb/device/usb_device.c): configuration zero and configuration-byte forwarding; [nRF USB driver](https://github.com/zmkfirmware/zephyr/blob/10ba6d0cb38bc3d258775d27982f707599320085/drivers/usb/device/usb_dc_nrfx.c): USB workqueue dispatch.
- [TI BQ24074 datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf): EN1/EN2 modes, CE and PowerPath; input high impedance retains the battery-to-system path.
- [USB-IF USB 2.0 specification](https://www.usb.org/document-library/usb-20-specification): governing configuration and suspend requirements; actual conformance remains unqualified.
