English | [Chinese](e73-review.zh-CN.md)

# E73 complete-design review — November 12, 2026

**Disposition: design hold.** Passing DRC and ARM builds do not resolve the measured USB protection branches, PH connector service obstruction or deficient mechanical tolerance reserves; the NiZ/plate-stabilizer geometry is now integrated. Use the [build/review entry](../../BUILD.md) and [machine-readable gates](e73-readiness.json). The existing UDB-C-JSH C5 remains unchanged.

Executed results: the base artifact audit passed **63/63 stages**; the subsequent complete review executed **13/13 steps successfully**, including 28 analog-front-end SPICE sensitivity cases, RF/USB/withdrawal extraction and fault tests. See the [review execution record](e73-review-run.json). With `--require-design`, the command returned **2** because measured design defects and open gates remain. Successful execution is not design release.

## Checked successfully

- Native E73 pin mapping, all 43 vendor lands, the 21 GPIO functions, USB/SWD/power and five connected bottom lands match. Strict native checks have zero errors and zero opens. All 270 signal/power pairs and **142 additional ground pairs** connect. The 102 courtyard warnings concern retained noncomponent graphics; hidden solder joints still require physical inspection.
- The ordinary four-layer 1.6 mm board uses mechanically drilled through vias, with no blind/buried vias or module vias-in-pad. Native outline and mounting geometry checks pass; manufacturing DFM is separate.
- Normal and calibrator E73 ARM images were rebuilt. Internal RC LFCLK, REG1 LDO, NFC GPIO UICR and a linked 500 mA USB configuration are checked. The images preserve the settings partition. Actual USB/BLE operation has not been tested on hardware.
- The charger adapter now acts synchronously on USB configuration/reset/suspend/deconfiguration events. `SET_CONFIGURATION(0)` cannot retain charging permission; charging does not wait for scanner polling. Eleven tests use the complete pinned ZMK USB callback under ASan/UBSan, including initialization, enable and GPIO-write failures. The E73-specific **GPIO1.13 CE_N** is exercised through a separate GPIO1 test device. USB HID preference stays serialized on the system workqueue.
- Current-source antenna copper and metal-plate projections are clear in the declared engineering band. Ebyte supplies no numerical host keepout in the retained source, so the last-3-mm screen remains provisional and cannot qualify range or immunity.
- The reference seven-wire installed route, nominal PCB/case stack, mounting centers, bounded pack envelope and mechanical wall screens pass their existing checks. The revised NiZ plate preserves 60 sensing centers, installs 28 mounting sets and omits H26; supplier shapes, complete service motion and physical full travel remain unqualified.

- E73 scanner, GPIO, calibration CRC, NVS recovery and key-pipeline regressions now pass against the rebuilt normal/calibrator targets. The [current firmware evidence](../testing/e73-firmware-validation.md) documents the 308-byte record migration, guarded BLE recovery and model limits. Physical analog/timing margins remain open.

## Design failures and repair order

| Priority | Finding | Required repair / acceptance |
|---|---|---|
| P1 | Mainboard TVS branches are **29.7482 / 37.5611 mm**, exceeding the imposed 5 mm project target. J1-to-module path lengths are **254.5547 / 257.8642 mm**, with **4 / 6 vias**. | Rework E73 mainboard USB routing/protection topology and reference return. Preserve the already-made C5. Regenerate native/CAM/firmware/assembly artifacts. These geometric values are not a USB compliance test. |
| P1 | The existing PH battery housing's continuous nominal withdrawal overlaps **H8 by 6.0978 mm³** and the **bottom shell by 23.0639 mm³**. Its seated position alone is clear. | Resolve connector height, position and mating path on the E73 board; recompute battery lead exits, bend radii and guides. Raytac SH3 geometry cannot be transplanted without E73-specific routing and checks. |
| Nominal CAD only | NiZ, 1.6 mm plate, three stabilizer pairs and 28 installed mounting sets are integrated; H26 remains a native PCB hole without hardware. | [Plate contract](plate-mount.json) checks 60 sensing centers and actual DXF cutouts. The complete nominal case stack passes; NiZ N+ plastic, wire bends, retention and full travel require physical samples. |
| P1 | Plate-ear reserve is only 0.0980 mm and SW100 floor reserve is 0.0562 mm after known allowances, below the 0.15 mm target. | [E73 tolerance calculation](../engineering/e73-mechanical-tolerances.md): the [M01 repair candidate](../engineering/e73-mechanical-fit-candidate.md) passes enlarged plate/switch envelopes, gasket bearing and insert guards. Select and integrate it into the complete assembly/firmware pipeline; the current canonical geometry remains held. |
| P1 | Raytac's improved local power routing, component landing/mask/stencil checks and nine-wire service evidence have not all been ported. | Review U5/U6 power loops, complete package dimensions, capacitor derating, ordinary thermal-via paste/mask and battery connector clearances against E73. Existing net continuity does not qualify these. |

Measured source data: [USB path extraction](USB-signal-paths.json), [continuous PH withdrawal](e73-service-motion.json), [nominal assembly](yeti60-assembly.json), [USB event tests](usb-event-policy.json), [full artifact audit](outcome.json). The source hashes and individual gates are in [e73-readiness.json](e73-readiness.json).

## Supplier and physical qualification

The battery remains required: protected 1S 4.2 V, 1600 mAh planning capacity, complete pack envelope 85 × 43 × 4.8 mm, third-wire NTC. Supplier correction of cell limits, independent charging-temperature protection, voltage/cutoff/recovery guarantees and the completed-pack drawing remain open. The charge-current calculation is 402.71 mA nominal / 445.63 mA worst case; it does not certify temperature rise or protection operation. Use the [pack specification](../engineering/battery-pack-specification.md).

After design closure, obtain fabricator DFM and inspect the first board. Bench acceptance includes power rails and USB states, simultaneous charging plus USB HID, USB/BLE handover, per-key calibration, 60-key press/release, interrupted power/storage behavior, cell-temperature interruption and the applicable discharge limits. The full enclosure additionally needs flexible-wire service/tool access, actual NiZ/stabilizer travel, resin/insert tolerance and RF/EC testing. None of these physical tests is recorded as passed.

## Reproduce

Run `scripts/run_audit.py` with KiCad and the CAD Python runtime; `scripts/test_yeti60_usb_events.py` exercises the actual pinned upstream callback. Run the RF/USB extraction scripts, `scripts/study_e73_service.py`, then `scripts/review_e73_readiness.py`. The review writes an explicit HOLD with failed/open gates. `--require-design` returns a nonzero status while those gates remain unresolved; successful test execution must not be presented as design acceptance.
