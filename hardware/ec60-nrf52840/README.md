English | [简体中文](README.zh-CN.md)

# YETI60 single-nRF52840 PCB

One Raytac MDBT50Q-1MV2 handles the intended EC scan, native USB and BLE roles. OPA350, muxes, charger and regulator are peripherals, not additional controllers. STM32 and onboard USB1 are removed; a rear Type-C daughterboard connects to J1. Original EC60 sensing geometry, outline, mounting locations and four-layer structure are retained.

Strict CAD DRC has 0 errors and 0 opens with 268 physical pin pairs connected. This does **not** approve the remaining local power layout or complete hardware. See the [comprehensive review](../../docs/audit/yeti60-comprehensive-review.md). The original checkpoint with 12 errors/35 opens remains historical under `docs/audit/checkpoints/`.

## Electrical contract

Power is BQ24074 charger/PowerPath plus TPS63031 3.3 V buck-boost. J2 is BAT/GND/NTC and requires a protected 1S 4.2 V pack with a 10k 103AT-2-compatible NTC. Charge programming is approximately 100 mA; input defaults to USB100 and firmware controls EN1/EN2/CE according to enumeration and suspend. No final battery is selected.

Module VDD/VDDH connect to 3.3 V, VBUS to USB 5 V and DCCH is unconnected. R30/R31 are **0 Ω** links because the nRF PHY contains termination. An internal low-frequency RC clock is intended; target configuration must match. J3 is a custom six-contact SWD pinout, not a standard ARM connector.

U8 switches the analog front end and U7 switches the 1M:1M battery divider with 10 nF filtering. GPIOs must not back-power an unpowered AFE. Enable, settle and calibrate before scanning; battery sampling waits at least 50 ms. The [portable nRF control core](../../firmware/yeti60/README.md) is host-tested, but not a flashable USB/BLE target application. `firmware/ec60/` is the separate STM32 reference.

Local I/O uses 0.127 mm tracks / 0.15 mm clearance / 0.50 mm via copper with 0.30 mm drill; ordinary routing is based on 0.2 mm tracks. Inductor-side straight tracks are 0.35 mm. SW60/SW62 ground guards were narrowed from 0.4 to 0.394 mm in the earlier clearance repair; sensing copper/locations remain retained. Finished PCB thickness is 1.59 mm, while native substrate-only STEP is 1.50 mm.

U1.39/U1.51 require [filled, planarized and copper-capped vias-in-pad](fabrication-notes.md). Ordinary tenting is not equivalent.

## Source and rebuild

`EC60-nRF52840.kicad_pcb` is the working design. `.unrouted.kicad_pcb` is only a routing-input snapshot. `pinmap.json`, `components.json`, schematic XML and the audit hash inventory define the pin/metadata contract. Existing `YAECKB` library IDs and filenames are retained for compatibility, not public branding.

Regenerate schematic sources with `scripts/build_single_nrf.py`, export the XML using KiCad CLI, then run `scripts/build_single_nrf_pcb.py` using KiCad Python. The layout builder writes `.unrouted` to avoid overwriting the routed board. `check_single_nrf.py`, `check_single_nrf_pcb.py`, `audit_single_nrf.py` and the connectivity-regression checker cover different levels of validation.

[Current PCB renders](../../renders/ec60-nrf52840/README.md) and [conditional assembly renders](../../renders/yeti60-assembly/README.md) are source-linked visualizations. Final power-loop layout, component ratings, special fabrication, resin inserts, switch/dome/fastener stack, daughterboard/plug/cables, actual firmware/calibration and later SI/RF remain unqualified.
