English | [Chinese](README.zh-CN.md)

# YETI60 single-nRF52840 PCB

One Raytac MDBT50Q-1MV2 handles the intended EC scan, native USB and BLE roles. OPA350, muxes, charger and regulator are peripherals, not additional controllers. STM32 and onboard USB1 are removed; a rear Type-C daughterboard connects to J1. Original EC60 sensing geometry, outline, mounting locations and four-layer structure are retained.

Strict CAD DRC has 0 errors and 0 opens with 270 physical pin pairs connected. Local power paths are shortened using the HDI process specified below; hardware measurements remain pending. See the [comprehensive review](../../docs/audit/yeti60-comprehensive-review.md).

## Electrical contract

Power retains BQ24074 charger/PowerPath and TPS63031 3.3 V buck-boost. Default P2 uses a custom 1600 mAh, 85×43×4.8 mm pack; J2 is positive/negative/NTC. R40=2.21k, R55=69.8k and R56=1.82k, all 1%, program 402.71 mA nominal / 445.63 mA maximum. Charging is enabled only after the host accepts the 500 mA USB configuration; preconfiguration remains USB100 and suspend disables charging. Independent pack thermal interruption and third-wire 10k NTC are mandatory; supplier approval is pending. See [power and charging](../../docs/engineering/power-budget.md).

Module VDD/VDDH connect to 3.3 V, VBUS to USB 5 V and DCCH is unconnected. R30/R31 are **0 Ω** links because the nRF PHY contains termination. An internal low-frequency RC clock is intended; target configuration must match. J3 is a custom six-contact SWD pinout, not a standard ARM connector.

U8 switches the analog front end and U7 switches the 1M:1M battery divider with 10 nF filtering. GPIOs must not back-power an unpowered AFE. Enable, settle and calibrate before scanning; battery sampling waits at least 50 ms. The [portable nRF control core](../../firmware/yeti60/README.md) is host-tested, and now integrated into buildable USB/BLE target applications.

Local I/O uses 0.127 mm tracks / 0.15 mm clearance / 0.50 mm via copper with 0.30 mm drill; ordinary routing is based on 0.2 mm tracks. Inductor-side straight tracks are 0.35 mm. SW60/SW62 ground guards were narrowed from 0.4 to 0.394 mm in the earlier clearance repair; sensing copper/locations remain retained. Finished PCB thickness is 1.59 mm, while native substrate-only STEP is 1.50 mm.

Nine back-side 0.40/0.20 mm filled microvias require the asymmetric HDI stack defined in the fabrication notes. U1.39/U1.51 require [filled, planarized and copper-capped vias-in-pad](fabrication-notes.md). Ordinary tenting is not equivalent.

## Source and rebuild

The current KiCad PCB, project and schematics are the editable design sources. `pinmap.json`, the partial redesigned-component contract `components.json`, exported `netlist.xml` and per-reference frozen footprints must stay consistent. Existing `YAECKB` library IDs remain for compatibility.

After schematic changes, export `netlist.xml` with KiCad CLI, update explicit contracts and regenerate `firmware/yeti60/board_pins.h` when needed. Run `python3 scripts/run_audit.py`. Fresh schematic parity, native DRC, PCB contracts and physical connectivity regression are checked separately. Historical builders and routing snapshots have been removed.

[Current PCB renders](../../renders/ec60-nrf52840/README.md) and [conditional assembly renders](../../renders/yeti60-assembly/README.md) are source-linked visualizations. Final power-loop layout, component ratings, special fabrication, resin inserts, switch/dome/fastener stack, daughterboard/plug/cables, actual firmware/calibration and later SI/RF remain unqualified.
