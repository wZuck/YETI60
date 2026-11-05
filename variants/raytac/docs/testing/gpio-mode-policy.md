English | [Chinese](gpio-mode-policy.zh-CN.md)

# Analog GPIO configuration and initialization cleanup

The current Raytac firmware maps analog high impedance and discharge-clamp release to **`GPIO_DISCONNECTED`**. This disables the digital input buffer, output driver and internal pulls; the analog pad/peripheral connection remains available. Both normal and calibrator builds use the same helper. This is a firmware correction: PCB, components and fabrication files are unchanged. Upgrade with a matched bundle and recalibrate because the GPIO helper is part of the v3 calibration fingerprint.

## Findings and corrected behavior

Previously the portable core's `Y_HIZ` and `Y_OD_RELEASE` both became `GPIO_INPUT`. That released the output driver but connected the digital input buffer. These pins are never read through GPIO IN. Keeping the buffer active on analog voltages was unnecessary and did not match the intended disconnected shutdown state. No measured power-saving number is claimed.

| Core request | Actual target flags | Digital input buffer | Output/pulls |
|---|---|---|---|
| High impedance | `GPIO_DISCONNECTED` | Disconnected | Disabled / none |
| Release discharge clamp | `GPIO_DISCONNECTED` | Disconnected | Disabled / none |
| Drive high | `GPIO_OUTPUT_HIGH` | Disconnected | High / none |
| Drive low or clamp | `GPIO_OUTPUT_LOW` | Disconnected | Low / none |

The helper in [gpio_modes.h](../../firmware/target/src/gpio_modes.h) is used by the actual target GPIO callback. ADC=P0.04 and BAT_ADC=P0.05 stay disconnected from digital GPIO drive/input/pulls. The shared sense/clamp pad P0.26 alternates between low drive and disconnected release. On AFE shutdown, all five rows, three mux address pins, two mux enables, the shared clamp and scan ADC are disconnected before AFE_EN is lowered. AFE_EN and BAT_MEAS_EN remain explicit low control outputs when disabled.

The [pinned nrfx GPIO driver](https://github.com/zmkfirmware/zephyr/blob/10ba6d0cb38bc3d258775d27982f707599320085/drivers/gpio/gpio_nrfx.c) handles disconnected GPIO without connecting the input buffer; its GPIOTE path uninitializes the pin. Nordic describes GPIO buffer disconnect separately from analog peripheral access. This is not galvanic isolation: pad protection and analog circuitry still exist. It does not prove zero physical leakage, an instantaneous rail fall, or safe behavior of a physically stuck pin.

A second finding was the scanner's initialization-error return: a failure detected after AFE power-up could return without powering it down. The current initialization function calls the actual core shutdown when initialized before returning `-EIO`. Successful initialization still enables normal scanning. Missing ADC/GPIO devices are rejected before GPIO setup; USB-init failure and a modeled GPIO error end with AFE off and its signal pins disconnected.

This cleanup concerns the AFE, not battery isolation. Charger/USB control has its own [USB callback policy](usb-event-policy.md). Hardware-off autonomous charging, pack protection and real battery tests retain their existing requirements.

## Verification and its scope

The [test recipe](../../scripts/test_yeti60_gpio_modes.py) extracts the production GPIO callback and initialization function verbatim, compiles them with the actual helper and portable core under ASan/UBSan, and checks pin-state invariants through a host driver model. It independently compares every relevant host GPIO flag value with the pinned Zephyr headers. The nrfx driver source hash is recorded, but that hardware driver and its registers are not executed on the host.

| Positive case | Checked result |
|---|---|
| Normal startup, 150 scan samples, idle/wake, shutdown, battery measurement | ADC/clamp inputs have no digital buffer, output drive or pull; AFE signal pins are disconnected when off |
| Device missing | Initialization rejects before any GPIO or USB setup |
| USB initialization failure | No AFE power-up; signal pins remain disconnected |
| GPIO error during startup after AFE enable | Initialization rejects and executes shutdown; AFE ends off |
| ADC read failure followed by the runtime shutdown action | Core aborts the frame and the target pin configuration ends disconnected |

Four mutated variants must fail: reconnecting digital input buffers, requesting a pull-up on floating pins, driving the clamp-release state high, and omitting startup shutdown. These are electrical/software invariants, not tests of real leakage/current or failed silicon.

[Machine evidence](../audit/gpio-mode-policy.json) records five positive cases, four rejected mutants, exact source hashes and the pinned header/driver revision. The full audit includes this stage. A separate CMake mutation case changes the GPIO helper and verifies that its calibration identifier changes; normal/calibrator identifiers must still match within each board bundle.

Reproduce from the Raytac directory:

```sh
python3 scripts/test_yeti60_gpio_modes.py
python3 scripts/test_yeti60_recovery.py
```

The first command requires host Clang and the pinned Zephyr checkout in `~/.cache/yeti60-zmk-workspace/zephyr`. The recovery test also uses the pinned build container. Build and check the current ARM images using the [candidate firmware entry](../../hardware/usb-short-route/firmware/README.md), then run the full audit with `--refresh-guide` after scanner provenance changes.

## First-board checks still required

Confirm actual GPIO input/drive/pull configuration and rail-off behavior. Measure analog leakage/loading and rail decay rather than inferring them from flags. Repeat actual key calibration and pulse capture with active/idle AFE switching and USB/BLE/charging loads, following the [analog timing study](analog-waveform.md). Verify that the SAADC still reads the intended analog pad, and that there are no false keys after idle recovery or startup faults. Host tests, source review and ARM builds do not close these physical acceptance items.

Primary sources: [Nordic nRF52840 GPIO](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/gpio.html), [Zephyr GPIO API](https://docs.zephyrproject.org/latest/hardware/peripherals/gpio.html), and the pinned driver linked above. Package/rail measurements remain first-board work.
