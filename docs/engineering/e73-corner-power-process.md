English | [Chinese](e73-corner-power-process.zh-CN.md)

# CORNER-07 power and ordinary PCB process review

CORNER-07 revises the U5, U6, C42 and SW1 openings and relocates the D2 ground via. It carries forward the USB supply paths and the C42, C48 and SW1 ground via locations from CORNER-05 and CORNER-06. The native PCB, firmware, BOM and CAM in this delivery identify this revision. The current path preserves direct USB HID while charging after host configuration.

| Mainboard supply span | CORNER-04 trace resistance | CORNER-07 trace resistance |
|---|---:|---:|
| J4.1 to J5.1 | 0.086 Ω | 0.015 Ω |
| J1.1 to F1.2 | 0.057 Ω | 0.029 Ω |
| F1.1 to U5 IN | 0.292 Ω | 0.089 Ω |

## Charge headroom

The three positive PCB traces total 0.13335 Ω at 20 °C using `R = ρL/(width × thickness)`. The four M05 AWG28 supply and return leads span 1.09527 m with nominal copper area 0.0804 mm², for 0.23486 Ω at 20 °C. At 60 °C, `R60 = (0.13335 + 0.23486) × (1 + 0.00393 × 40)` gives **0.42608 Ω** and a **0.213 V** drop at 500 mA. The M04 reference is 0.423 Ω. The model excludes the PCB ground return, via barrels, C5 traces, fuses, contacts and crimps. The table starts at the loaded jack. [Probe map and M05 calculation data](../../hardware/e73-hhkb-corner/audit/bench-power-plan.json)

| Type-C jack under load | Assumed input current | Calculated drop on included paths | Estimated U5 IN before omitted losses |
|---|---:|---:|---:|
| 4.75 V | 100 mA | 0.043 V | 4.707 V |
| 4.75 V | 450 mA | 0.192 V | 4.558 V |
| 4.75 V | 500 mA | 0.213 V | 4.537 V |
| 5.00 V | 450 mA | 0.192 V | 4.808 V |
| 5.00 V | 500 mA | 0.213 V | 4.787 V |

The BQ24074 can reduce current at its 4.35–4.63 V input threshold. At a weak source, the upper end of that threshold can still cause charge-current foldback at the requested load. The nRF52840 VBUS operating minimum is 4.35 V. U1 has its own branch after F1, so measure U1 VBUS relative to its local ground and U5 IN relative to the charger ground. This calculation does not solve the input-control loop. [TI BQ24074 electrical characteristics](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [Nordic USB supply limits](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/power.html)

At a 4.75 V loaded jack and the 4.63 V threshold corner, the included path reaches the threshold at about `(4.75 − 4.63) / 0.42608 = 0.282 A` of total input current. This estimate excludes the other losses. Measure charging current and U1 VBUS under load.

The ten local power paths meet their project width and length limits. The programmed charge current remains 357.06 / 402.71 / 445.63 mA min / typ / max with R40 at 2.21 kΩ. The approved supply range of the complete pack must cover 4.16–4.23 V. At an assumed U5 IN of 5.25 V, BAT of 3.10 V and OUT of 4.50 V with a 40 mA load, `P = (VIN−VBAT)×IBAT + (VIN−VOUT)×IOUT` gives about **0.99 W** at 445.63 mA. The standardized thermal resistance cannot predict temperature inside this case. [TI BQ24074 charge and thermal data](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

## Current drawn from the USB host

The 500 mA descriptor applies at the host port. After F1, U5.13 and U1.27 both connect to `USB_5V`, so upstream current includes the charger's input and the E73 USB PHY branch. In USB500 mode the BQ24074 input limit is 450 / 475 / 500 mA. Nordic specifies **2.4 mA typical** for the active nRF52840 VBUS branch and supplies no maximum in that table. Combining the charger's upper limit with just that typical value gives 502.4 mA. This identifies a gap in the tolerance analysis. The board reaches that combined current only if the charger is loaded to its upper limit. [USB-IF host-port policy](https://compliance.usb.org/index.asp?Format=Standard&UpdateFile=Policies) · [TI §8.5](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [Nordic USBD current table](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/_tmp/nrf52840/autodita/current/parameters.i_usbd.html?contentId=0~r9OOfQs0Fo3SLnXciN~A)

For a planning point, allocate 40 mA at U5 OUT, 2 mA for U5 housekeeping and 10 mA for the rest of the port current. With R40 at 2.21 kΩ, the upper programmed charge current gives `445.63 + 40 + 2 + 10 = 497.63 mA`. The 2.37 mA remainder depends on the three assumed loads. In USB100 the 100 mA maximum likewise applies at U5 IN. During hot plug the directly connected mainboard capacitances C32 (4.7 µF) and C40 (2.2 µF) alone give the nominal estimate `(4.7 + 2.2) × 5 = 34.5 µC`. Test the whole device against the attach and steady-current criteria. [Source-bound calculations](../../hardware/e73-hhkb-corner/audit/usb-host-current.json) · [USB-IF inrush test, §B.4](https://www.usb.org/sites/default/files/USB-IFTestProc1_3.pdf)

If the configured host current fails, a trial 2.49 kΩ ±1% 0402 at R40 is the first component-value change to evaluate. It reduces the programmed maximum to 395.52 mA. The same allocations give 447.52 mA and 52.48 mA of modeled margin. This leaves the BQ24074 in USB500 with its input-voltage foldback. Before adopting the value, repeat USB and charge tests, including constant-voltage taper, termination, the safety timer and full-charge time. External ILIM mode has a programmable cap and does not have the USB500 input-voltage foldback specified by TI. [TI §§8.5, 9.3.4.1](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

## Ordinary drilling and solder apertures

All 852 vias are mechanical through holes. Nominal drill / land sizes are 0.30 / 0.50 mm (203), 0.30 / 0.60 mm (65) and 0.40 / 0.80 mm (584). The minimum trace width is 0.127 mm. The mainboard uses the specified ordinary four-layer stack and tenting. Review the actual CAM and mask alignment with the factory. [JLCPCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities/)

| Contact | Nominal drill-to-opening result |
|---|---|
| C42.2 | Ground via at PCB (122.120, 142.315) mm. Gap to the respective paste and mask openings is 0.230 mm |
| C48.2 | Ground via at PCB (107.1368, 147.6572) mm. Gap to the respective paste and mask openings is 0.237 mm |
| SW1.2 | Ground via at PCB (322.220, 122.370) mm with a 0.30 mm drill and 0.60 mm land. Both gaps increase from 0.037 mm to 0.230 mm |
| D2.1 | Ground via at PCB (315.516, 122.070) mm with a 0.30 mm drill and 0.60 mm land |
| U5.17, U6.11 | Revised mask islands and split paste windows. Drill-to-mask gap is 0.230 mm on both pads. See the full artwork audit for paste and stencil coverage |

The smallest drill budget across the four layers is `0.230 − √2 × 0.075 − 0.13 / 2 − 0.0002 ≈ 0.059 mm` after position, diameter and polygon allowances. Mask registration remains a factory check. Inspect actual tenting and the split stencil for both exposed pads. [JLCPCB drill tolerances](https://jlcpcb.com/capabilities/Capabilities) · [JLCPCB via covering](https://jlcpcb.com/help/article/pcb-via-covering) · [Mask and stencil audit](e73-aperture-review.md)

The JST SH terminals accept AWG32–28. The harness uses AWG28 within that wire-size range and needs the specified crimp quality and insulation diameter. [JST SH specification](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)

## Prototype checks

Follow the [bench power and charging procedure](../testing/e73-bench-power.md) for open-bench measurements and the [pack specification](battery-pack-specification.md) for the physical pack.

Run `scripts/check_e73_corner_power.py` with KiCad 10 Python after regenerating the harness report. [Current audit and calculations](../../hardware/e73-hhkb-corner/audit/power-process.json) · [CORNER-04 comparison and combined trial](https://github.com/wZuck/YETI60/tree/c3872db49bbff5188b7be3fab3fa73b81b2b9028/hardware/e73-hhkb-corner/audit)
