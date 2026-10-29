English | [Chinese](calibration.zh-CN.md)

# Guarded per-key calibration

The former calibration used the smallest released sample and largest pressed sample. Those optimistic extrema could accept a noisy population whose normal states overlap. It has been replaced by labeled per-key captures and conservative bounds. This is a firmware correction; physical EC acceptance is still required.

1. Install the final mechanical stack, power source and protected pack. Use the calibrator for the selected module. Open its USB CDC console using a second input device.
2. Release every key and send `yeti_calibrate release`. Keep all keys released until the message confirms 128 complete frames. Starting release again clears all previous pressed captures.
3. Look up a key in the selected target's `firmware/target/calibration-keys.csv`. Hold that key fully down **before** sending `yeti_calibrate press ROW COL` with its decimal row/column. Keep it held until the completion message reports 128 samples. Release it and repeat for every one of the 60 installed keys. The other 15 raw positions are intentionally inactive.
4. Run `yeti_calibrate status`. It prints per-key counts, released/pressed minima and maxima, candidate thresholds, guard and validity. Save the console log with the board serial and firmware HEX hash. A repeated press command recaptures that key; do not release it partway through capture.
5. Run `yeti_calibrate save` only after every key is valid. A rejected key, busy capture or failed NVS write must not be reported as saved. Bare `press` is rejected because unlabeled whole-board peak collection does not establish a pressed distribution.
6. Flash normal firmware for the exact same board without erasing the settings partition. The calibration version binds pin mapping, device tree, native PCB bytes and calibration algorithm. Changes to these inputs invalidate stored thresholds and require recalibration. Do not copy thresholds between keyboards.

Each state needs at least 64 labeled samples; the target captures 128. Saturated samples at or above code 4090, missing data, a span below 32 codes or overlapping guarded ranges are rejected. The portable algorithm uses integer arithmetic with bounded counts and 64-bit variance accumulation:

```text
sigma = ceil(sqrt(ceil(sample_variance)))
G = max(6*sigma_released, 6*sigma_pressed, 1 code)
bottom = released_max + G + 1
top = pressed_min - G - 1
require top - bottom >= 4 and pressed_min - released_max >= 32
low = bottom + floor(0.35*(top-bottom))
high = bottom + floor(0.65*(top-bottom))
```

This ensures `released_max + G < low < high < pressed_min - G` for accepted observations. The guard is an imposed screening criterion, not a Gaussian error-rate guarantee. Variance, extrema and correlation remain dependent on operating conditions. Repeat the [physical interference matrix](interference.md#physical-interference-matrix) and reject a keyboard if its distributions overlap under charging, radio activity or final enclosure conditions.

[Portable implementation](../../firmware/yeti60/calibration.c) · [sanitizer tests](../../tests/yeti60/calibration.c) · [executed evidence](../audit/calibration.json) · [E73 command map](../../firmware/target/calibration-keys.csv) · [Raytac command map](../../variants/raytac/firmware/target/calibration-keys.csv).
