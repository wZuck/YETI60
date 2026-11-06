English | [Chinese](key-pipeline.zh-CN.md)

# Matrix, keymap and HID pipeline review

The current normal and calibrator builds use **six ordinary HID key slots, with modifier bits separate**. Scanning sixty physical keys and retaining 120 queued transitions does not imply sixty-key rollover. If six ordinary keys are already held, a seventh is omitted by the pinned ZMK HKRO implementation. Releasing an earlier key does not automatically insert that held seventh key: release and press it again. This is an observed software behavior; actual host acceptance still requires the first board.

This review changes tests and documentation only. It does not change the board, firmware bytes, calibration identifier, six-key report format or USB/BLE policy. Existing matching images remain the firmware to use. These tests alone do not require recapturing calibration.

## Executed code and modeled boundaries

The runner loads both resolved ARM `zephyr.dts` and `.config` files, checks their hashes against the build manifest, and requires identical normal/calibrator transforms and two-layer bindings. It reads all sixty base labels and physical row/column coordinates from the calibration CSV. The independent Fn expectations cover grave, F1–F12, Delete and Left/Down/Up/Right at J/K/L/semicolon.

Pinned ZMK revision `0862fc0f8c864834007986efcaf52f292ea6d37d` supplies these actual function bodies:

- Physical-layout kscan callback and queue consumer, plus the matrix lookup function.
- Keymap layer-state changes, press-time layer snapshot, binding lookup and position dispatch.
- Key-press, momentary-layer and Bluetooth-command handlers, and encoded keycode-event conversion.
- HID listener press/release functions and the complete `hid.c` implementation. Keyboard/consumer report structs and key/usage/modifier constants come from the same pinned headers.

The fixture models queue operations, identity stock-position mapping, event dispatch, device lookup, endpoint report submission and time. The transform lookup initializer and binding tables are generated from the resolved target device trees. Assertions observe actual HID report state and the report body copied at the modeled endpoint. ADC scanning is covered by the separate [scanner worker tests](scan-control.md); this runner injects edges at the kscan callback boundary. It does not run the whole firmware, RTOS, USB stack, BLE stack or a computer HID driver.

The actual Bluetooth behavior decoder calls modeled BLE interfaces for five profile selections; the behavior router records one tap-dance boundary press. It does not implement Bluetooth profiles/bonds or tap-dance timing. Those bindings and the actual pinned tap-dance code are checked in [recovery tests](firmware-recovery.md); real pairing remains open. Transport switching and report clearing require the separate [USB policy checks](usb-event-policy.md) and physical host tests.

## Results

| Scenario | Checked behavior |
|---|---|
| Base | All 60 physical positions press/release; 59 HID-producing positions, one Fn position; 118 modeled HID report submissions |
| Fn | All 59 other positions with Fn held; expected Fn usages and transparent fall-through; five profile selections and one dance-boundary press; no remaining report/layer state after release |
| Release order | Base key pressed before Fn releases as its base usage; Fn key released after Fn releases as its Fn usage; neither leaves a stuck usage |
| Rollover | Six ordinary keys retained; seventh omitted; release/repress permits insertion; final report empty |
| Unused matrix cells | Fifteen absent positions produce no position events or HID reports |
| Full release | Sixty downs followed by sixty reverse-order ups; final report, layer state and all eight modifier counters empty; this does not assert sixty simultaneous HID keys |

Four intentionally wrong variants are rejected: shifted transform, missing press-time layer snapshot, release routed using current layers, and omitted HID key release. Clang AddressSanitizer and UndefinedBehaviorSanitizer instrument the host executable. No physical delivery, input latency, rollover behavior of a real host or electrical behavior is inferred.

## Reproduce and inspect

From the repository root:

```sh
python3 variants/raytac/scripts/test_yeti60_key_pipeline.py
python3 variants/raytac/scripts/build_usb_short_firmware.py --host-tests-only
python3 variants/raytac/scripts/check_usb_short_firmware.py
```

The first command needs the existing locked west workspace and resolved local ARM builds. Host-only publication first rejects stale firmware sources/images, then independently repeats the tests against the candidate build. It does not rebuild changed firmware.

[Reference evidence](../audit/key-pipeline.json) · [Current candidate evidence](../../hardware/usb-short-route/firmware/key-pipeline.json) · [Actual runner](../../scripts/test_yeti60_key_pipeline.py) · [Host fixture](../../tests/yeti60/key_pipeline.c) · [First-board acceptance](README.md)

On the first board, test every base/Fn position, both Fn release orders, modifier chords, six ordinary keys plus modifiers, the seventh-key limit and a clean final release on USB and BLE. Repeat after suspend/resume, disconnect/reconnect and host changes. Record actual reports with the selected host/OS; simulated report submissions are not evidence that a host received a packet.
