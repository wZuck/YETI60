English | [Chinese](flashing.zh-CN.md)

# Flash, serial shell and per-key calibration

Return to the [handbook](../../BUILD.md). This is an unexecuted first-prototype procedure, not a hardware success record. Prepare an nRF52840-compatible CMSIS-DAP SWD probe, OpenOCD and the custom six-pad J3 fixture.

With USB and battery disconnected, connect according to [step 16](../assembly/images/16-step.png) and actual pad numbers. This is not standard ARM connector order.

| J3 | Probe |
|---|---|
| 1, +3.3V | VTref, target-voltage reference; not another power supply |
| 2, SWDIO | SWDIO |
| 3, GND | GND |
| 4, SWDCLK | SWCLK |
| 5, RESET_N | nRESET |
| 6, GND | GND |

Power through the checked C5 USB path without a battery and verify 3.3 V; avoid probe back-power. OpenOCD must supply `interface/cmsis-dap.cfg` and `target/nrf52.cfg`. A J-Link instead needs its matching `interface/jlink.cfg` and verified target support.

From the repository root:

```sh
cd variants/raytac
openocd -f interface/cmsis-dap.cfg -c "transport select swd" -f target/nrf52.cfg \
  -c "adapter speed 1000; program firmware/releases/calibrator/yeti60-raytac.hex verify reset exit"
```

1 MHz is an initial probe-speed proposal, not a measured limit. Require successful programming and verification. Investigate power, grounds, contacts and target identification on failure; do not automatically recover or mass erase, which removes stored settings. See [OpenOCD program documentation](https://openocd.org/doc/html/Flash-Programming.html).

The calibrator enables a USB CDC ACM shell. Identify the actual new serial port (`/dev/cu.usbmodem…` on macOS, `/dev/ttyACM…` on Linux or a new Windows COM port). Open a terminal, initially 115200/8N1/no hardware flow control. CDC line settings are not the sensing scan rate. Enumeration has not been physically tested.

After installing actual matched housings, domes and springs, release every key and enter:

```text
yeti_calibrate release
```

Wait for 128 frames. Use the [60-key command table](../../firmware/target/calibration-keys.csv). Fully hold one target key **before** issuing its matching command and retain the press until that key's 128 samples complete:

```text
yeti_calibrate press 0 0
yeti_calibrate status
```

`0 0` demonstrates syntax only; follow the real mapping for every key. Do not press all keys as a substitute. Require every installed key valid, without saturation, overlapping distributions or guard failures, then:

```text
yeti_calibrate save
```

Require confirmed save success. Investigate structure, contacts, power and noise on rejection; never weaken guards to force acceptance.

Flash normal firmware:

```sh
openocd -f interface/cmsis-dap.cfg -c "transport select swd" -f target/nrf52.cfg \
  -c "adapter speed 1000; program firmware/releases/normal/yeti60-raytac.hex verify reset exit"
```

Write only image-touched application sectors, preserving settings at `0xF0000–0xFFFFF`; add no mass erase. Artifact checks verify distributed address ranges/descriptors; real probe erase behavior still requires first-article confirmation. PCB/pin/devicetree/calibration-algorithm fingerprint changes require new calibration.

Test all 60 keys, configured-host concurrent charging/USB input, suspend/resume and unplug-to-BLE, then repeat in the final case. See [target details](../../firmware/target/README.md) and [acceptance](../testing/README.md).
