English | [Chinese](scan-control.zh-CN.md)

# Scanner availability, fault shutdown and calibration commands

The Raytac normal and calibrator images now share an atomic scanner lifecycle and a single-command mailbox. Initialization must finish before commands are accepted. An ADC or GPIO fault shuts the AFE down, releases tracked keys through the kscan callback, cancels capture and latches the scanner off until reset. USB charging control remains in its independent status callback. PCB, materials and fabrication files are unchanged.

## Findings and behavior

Previously the shell could acknowledge a command when scanner initialization had failed; the worker would never consume it, leaving subsequent requests busy. A command queued just before a runtime scan failure could also be processed after shutdown. GPIO errors were checked after calibration collection and key callbacks, so a faulty frame could contribute capture data. Fault shutdown cleared the core matrix but did not immediately release the worker's previously reported keys.

| Scanner state | `release`, `press row col`, `save` | `status`, `timing` |
|---|---|---|
| Initialization incomplete or failed | Reject with `-ENODEV` and unavailable message | Same rejection |
| Running | Queue one request; reject a second with `-EBUSY` | Same mailbox |
| Runtime fault latched | Reject with `-EIO`; diagnose and reset | Available for diagnosis, normally within the next 100 ms worker interval |

Only the scan owner changes capture data or powers down the core. The shell communicates through [scanner_control.c](../../firmware/target/src/scanner_control.c), using the pinned Zephyr sequentially consistent atomic operations. Initialization publishes the device pointer before publishing the running state. A second initialization is rejected. A latched fault cannot become running again through the ready operation.

The owner rechecks state when taking a queued request. A mutation accepted immediately before a fault is discarded with an explicit console message; read-only requests remain usable. After failure, `status` reports `scanner_fault=1` and calibration invalid for this runtime. Fault handling does not erase saved calibration or BLE bonds. Reset after diagnosing the fault; compatible saved calibration can load again at boot. Changing the firmware signal fingerprint still requires recapture.

Fault detection occurs before capture collection and frame callbacks. The shutdown path attempts core power-off, emits release callbacks for all tracked held positions exactly once, clears capture validity and stops further scanning. Disabled/idle AFE gating GPIO errors also latch the fault. This software cannot force a physically failed GPIO or load switch off; rail state must be measured.

## First tap after idle

The review reproduced a separate missed-tap case in the actual worker: after entering idle, a 50 ms modeled key hold overlapped just one scan. The old policy waited for a debounced matrix change before selecting active speed. That left another 30 ms idle sleep before confirmation; the key had already released and no press/release callback was generated.

The owner now also checks **nonzero pending debounce counters on active positions**. The first observed transition restores the 4 ms active interval and keeps the AFE enabled while normal confirmation continues. The existing two-frame debounce remains in force; neither threshold rules nor per-position waveform waits are shortened. The new scanner source changes the calibration fingerprint, so use the rebuilt matched bundle and recapture all sixty keys after upgrading.

| Native worker case | Press / release callbacks |
|---|---|
| Old idle policy, 50 ms modeled hold | 0 / 0; regression test fails |
| Corrected policy, same hold plus a later one-frame spike | 1 / 1; spike produces no extra event |
| Deliberately bypassed debounce, same input | 2 / 2; noise-rejection test fails |

The positive short-tap case runs 7,520 frames with all fifteen unused positions at 4095. It observes 564,000 reads, one idle sleep and 7,519 active sleeps. The modeled press/release delays are 29/7 ms relative to the modeled hold edges. These are host-clock results that exclude ADC/GPIO/settling/scheduler time, not hardware latency measurements. Initial detection still depends on idle polling; this correction does not guarantee detection of every short pulse or qualify USB/BLE delivery.

A one-frame threshold spike can restart the 30-second active timer without becoming a reported key. Noise may therefore increase active duty; the conservative continuous-AFE power model still applies, and actual power/first-key latency require bench measurement.

## Unused positions and idle/wake boundary

The production code already disables the fifteen unused positions correctly. The unused-position policy is unchanged; this bundle also corrects the separate idle short-tap issue described above and requires recalibration. The normal and calibrator device trees are checked against their build hashes and against the board-source transform order. Their sixty positions and the scanner's active bitmap must agree. The separate [plate/copper mapping check](../audit/yeti60-key-geometry.json) ties that board-source order to native geometry.

| Matrix row | Active bitmap | Used / unused positions |
|---:|---|---|
| 0 | `0x7FFF` | 15 / 0 |
| 1 | `0x3FFF` | 14 / 1 |
| 2 | `0x2FFF` | 13 / 2 |
| 3 | `0x6FFD` | 13 / 2 |
| 4 | `0x0646` | 5 / 10 |
| Total | | 60 / 15 |

The actual calibration save path sets unused low/high thresholds to **4094/4095**, clears the matrix and debounce counters, and uses strict `sample > high` to press a position. For every legal 12-bit ADC value, `sample <= 4095`, so a full-scale unused sample still cannot press it. Values above 4095 or ADC failures abort the frame through the existing fault path. This statement concerns calibrator-produced records and ordinary initialized state, not arbitrary hand-authored records or physical analog immunity.

The native worker test injects 4095 into every unused position throughout the complete 128-frame release/sixty-key capture/save procedure. Those saturated unused populations do not invalidate the actual save, which qualifies only active keys. The saved and applied inactive thresholds must remain 4094/4095. The worker then runs continuously for **7,511 frames / 563,325 ADC reads**, reaching idle and requesting AFE gating, debouncing all sixty active presses, then releasing them. The test observes three idle sleeps, 7,508 active sleeps and exactly sixty press plus sixty release callbacks. An unmapped callback fails the fixture's assertion. The queue retains all 120 events without overflow.

The fixture uses resolved target scan options (4 ms active, 30 ms idle, 30,000 ms idle threshold), the reported clock and the actual bundle calibration identifier. Its 30,122 ms total is **modeled sleep time only**: GPIO/ADC work, busy waits, AFE settling, transport and scheduling do not advance that host clock. It is not measured scan rate, wake latency, power draw or HID delivery. Every frame still samples all 75 positions; this test does not shorten the waveform or skip unused electrodes.

Two additional mutants must fail: lowering the unused saved thresholds, or changing the high comparison to `>=`. Real idle-current, AFE rail switching, key wake and USB/BLE/charging interaction remain first-board tests.

## ZMK event queue

The pinned [physical-layout callback](https://github.com/wZuck/zmk/blob/0862fc0f8c864834007986efcaf52f292ea6d37d/app/src/physical_layouts.c) submits each event with `K_NO_WAIT` and does not retry a full queue. The old default was four entries. Both targets now set **`CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE=128`**. A deterministic test holds the consumer and submits all sixty presses followed by all sixty releases: all **120 events** retain their order without overflow. The two complete frames fit with eight entries spare.

The queue is finite. This bounded test does not guarantee delivery during an indefinitely stalled system workqueue, nor prove USB/BLE HID delivery. The target build checker verifies that both resolved configurations use 128 entries and builtin atomics. The host uses the same pinned atomic implementation, with the native host's word size; it does not execute Cortex-M4 atomics or the actual Zephyr scheduler.

## Reproduce and inspect evidence

From the repository root:

```sh
python3 variants/raytac/scripts/test_yeti60_scan_control.py
python3 variants/raytac/scripts/test_yeti60_gpio_modes.py
python3 variants/raytac/scripts/test_yeti60_recovery.py
```

Host Clang, the pinned ZMK/Zephyr workspace, built normal/calibrator configuration/device trees, and the pinned build container are required. The [scanner test recipe](../../scripts/test_yeti60_scan_control.py) extracts the production shell, worker and fault helper verbatim. It links the actual core, calibration and lifecycle module with modeled ADC/GPIO, settings, sleep and queue interfaces. It also compiles the pinned ZMK callback unchanged; the host maps its layout pointer name to avoid a collision with the scanner bitmap.

[Reference evidence](../audit/scan-control.json) and [candidate evidence](../../hardware/usb-short-route/firmware/scan-control.json) record exact source hashes, fifteen positive scenarios and seventeen rejected mutants. Cases cover unavailable startup; all 60 active and 15 inactive positions; mailbox busy behavior; the 120-event burst; accepted-before-fault commands; sixty releases and idempotent shutdown; actual worker ADC/GPIO faults; exclusion of a faulty calibration frame; disabled gating faults; and 128-frame release plus 60-key capture/save, including rejection before capture completion and settings-write failure.

Mutants must fail when they accept offline commands, accept mutations after fault, omit the consumer recheck, overwrite pending work, omit releases, omit power-off, publish faulty capture data, or reduce the event queue to four entries. ASan/UBSan check the native executions. These checks do not simulate the actual RTOS, flash, USB/BLE stack or electrical failure modes.

Use the matched [candidate firmware bundle](../../hardware/usb-short-route/firmware/README.md) and recalibrate after upgrading. The lifecycle source/header and scan configuration are in the calibration fingerprint; CMake mutation tests verify that a control-source change changes that identifier. Rebuild both board bundles before running the full audit with `--refresh-guide`.

## First-board checks

On an insulated, current-limited bench, verify startup diagnostics, USB enumeration, actual release/press/save/status/timing responses, and preservation of valid settings across the matched calibrator-to-normal flash. Exercise multi-key holds, releases, idle gating and USB/BLE host changes. Check that release callbacks arrive as real host key releases after a safe, instrumented scan-failure injection. Do not short powered pins to induce a fault. Record AFE rail shutdown, continued USB diagnostics/charger policy, and recovery after reset. These physical checks remain open.

Storage cases also cover legacy length, short reads, version/CRC/threshold rejection, valid loading and failed saves. The actual pinned settings dispatcher confirms that a rejected calibration does not block subsequent settings. Five additional mutants remove length checking, record validation, exact reads or save CRC, or incorrectly propagate the dispatcher error. See [calibration storage](calibration-storage.md).
