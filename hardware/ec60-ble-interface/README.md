English | [简体中文](README.zh-CN.md)

# Historical EC60 BLE interface BLE-IF-0.2

**Superseded.** YETI60 now uses one nRF52840. STM32 and the dual-controller SPI bridge are not part of the current design; see [current hardware](../ec60-nrf52840/README.md).

This prototype was derived from Cipulot EC60 commit `b9c04625bb9944f6fb806aa571da8592cdff8565`; `LICENSE.EC60` is retained. `EC60-BLE-Interface.kicad_pro` contains a USB-powered interface schematic with a J2 SPI2 header and local `YAECKB.kicad_sym` library. It has no routed PCB, final radio, battery power circuit or controller firmware. J2 has no selected production footprint and must not receive battery voltage.

J2: 1=SYS_3V3, 2=GND, 3=SCK, 4=MOSI, 5=MISO, 6=CS_N, 7=IRQ_N, 8=RESET_N. In this historical architecture STM32 was master and nRF SPIS was slave. SYS_3V3 is a regulated system rail, not BAT_CELL; supply capacity and sequencing require review.

```sh
python3 scripts/build_ble_interface.py
python3 scripts/check_ble_interface.py
```

The generator overwrites generated schematics, symbols and project files; edit its source first. `validation.json` checks retained connectivity and unused extension pins. ERC electrical errors were eliminated by adding NC markers, correcting VCAP1 electrical type and moving a redundant supply flag to real USB VBUS. Upstream library, net-name and grid warnings remain; zero ERC errors do not approve manufacturing.

The [historical plan](../../docs/felk60-bluetooth.md) records the research sources and limitations.
