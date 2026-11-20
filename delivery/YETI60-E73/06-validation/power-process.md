English | [Chinese](power-process.zh-CN.md)

# CORNER-06 power and ordinary PCB process review

CORNER-06 relocates the SW1 ground via and retains the lower-resistance USB supply route and relocated C42 and C48 ground drills from CORNER-05. The native PCB, firmware, BOM and CAM in this delivery identify this revision. The current path preserves direct USB HID while charging after host configuration.

| Mainboard supply span | CORNER-04 trace resistance | CORNER-06 trace resistance |
|---|---:|---:|
| J4.1 to J5.1 | 0.086 Ω | 0.015 Ω |
| J1.1 to F1.2 | 0.057 Ω | 0.029 Ω |
| F1.1 to U5 IN | 0.292 Ω | 0.089 Ω |

## Charge headroom

The three positive PCB traces total 0.13335 Ω at 20 °C using `R = ρL/(width × thickness)`. The four M05 AWG28 supply and return leads span 1.09527 m with nominal copper area 0.0804 mm², for 0.23486 Ω at 20 °C. At 60 °C, `R60 = (0.13335 + 0.23486) × (1 + 0.00393 × 40)` gives **0.42608 Ω** and a **0.213 V** drop at 500 mA. The M04 reference is 0.423 Ω. The model excludes the PCB ground return, via barrels, C5 traces, fuses, contacts and crimps. The table starts at the loaded jack. [Probe map and M05 calculation data](bench-power-plan.json)

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

## Ordinary drilling and solder apertures

All 852 vias are mechanical through holes. Nominal drill / land sizes are 0.30 / 0.50 mm (203), 0.30 / 0.60 mm (64) and 0.40 / 0.80 mm (585). The minimum trace width is 0.127 mm. The mainboard uses the specified ordinary four-layer stack and tenting. Review the actual CAM and mask alignment with the factory. [JLCPCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities/)

| Contact | Nominal drill-to-opening result |
|---|---|
| C42.2 | Ground via at PCB (122.120, 142.315) mm. Gap to the respective paste and mask openings is 0.130 mm |
| C48.2 | Ground via at PCB (107.1368, 147.6572) mm. Gap to the respective paste and mask openings is 0.237 mm |
| SW1.2 | Ground via at PCB (322.220, 122.370) mm with a 0.30 mm drill and 0.60 mm land. Both gaps increase from 0.037 mm to 0.230 mm |
| D2.1 | The nominal drill-to-opening gap is 0.142 mm. Verify factory registration |
| U5.17, U6.11 | Mask islands retain 0.100 mm nominal drill-to-mask gap. Split paste gaps are 0.150 and 0.167 mm respectively |

The SW1 drill screen uses `0.230 − √2 × 0.075 − 0.13 / 2 = 0.059 mm` of residual gap after a conservative diagonal position error and maximum radial growth from the published finished-hole diameter tolerance. Mask registration remains a factory check. Inspect actual tenting and the split stencil for both exposed pads. [JLCPCB drill tolerances](https://jlcpcb.com/capabilities/Capabilities) · [JLCPCB via covering](https://jlcpcb.com/help/article/pcb-via-covering) · [Fabrication ZIP audit](cam-ordinary.json)

The JST SH terminals accept AWG32–28. The harness uses AWG28 within that wire-size range and needs the specified crimp quality and insulation diameter. [JST SH specification](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)

## Prototype checks

Follow the [bench power and charging procedure](bench-power.md) for open-bench measurements and the [pack specification](../03-bom/battery-requirements.md) for the physical pack.

Run `scripts/check_e73_corner_power.py` with KiCad 10 Python after regenerating the harness report. [Current audit and calculations](power-process.json) · [CORNER-04 comparison and combined trial](https://github.com/wZuck/YETI60/tree/c3872db49bbff5188b7be3fab3fa73b81b2b9028/hardware/e73-hhkb-corner/audit)
