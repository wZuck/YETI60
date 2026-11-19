English | [Chinese](e73-corner-power-process.zh-CN.md)

# CORNER-05 power and ordinary PCB process review

CORNER-05 integrates the lower-resistance USB supply route and moves the C42 and C48 ground drills outside their solder openings. The native PCB, firmware, BOM and CAM in this delivery identify this revision. The current path preserves direct USB HID while charging after host configuration.

| Mainboard supply span | CORNER-04 trace resistance | CORNER-05 trace resistance |
|---|---:|---:|
| J4.1 to J5.1 | 0.086 Ω | 0.015 Ω |
| J1.1 to F1.2 | 0.057 Ω | 0.029 Ω |
| F1.1 to U5 IN | 0.292 Ω | 0.089 Ω |

## Charge headroom

Sum the three copper paths using `R = ρL/(width × thickness)`. Add the four AWG28 supply and return leads, 1.083 m total at a nominal 0.0804 mm² copper area. The corresponding wire resistance is 0.232 Ω at 20 °C. Apply `R60 = R20 × (1 + 0.00393 × 40)` to the wires and traces to obtain **0.423 Ω**, down from 0.772 Ω for CORNER-04. The model excludes the PCB ground return, via barrels, C5 traces, both fuses, contacts, crimp joints and external USB cable.

| Type-C jack under load | Assumed input current | Calculated drop on included paths | Estimated U5 IN before omitted losses |
|---|---:|---:|---:|
| 4.75 V | 100 mA | 0.042 V | 4.708 V |
| 4.75 V | 450 mA | 0.190 V | 4.560 V |
| 4.75 V | 500 mA | 0.211 V | 4.539 V |
| 5.00 V | 450 mA | 0.190 V | 4.810 V |
| 5.00 V | 500 mA | 0.211 V | 4.789 V |

The BQ24074 can reduce current at its 4.35–4.63 V input threshold. At a weak source, the upper end of that threshold can still cause charge-current foldback at the requested load. The nRF52840 VBUS operating minimum is 4.35 V. U1 has its own branch after F1, so measure U1 VBUS relative to its local ground and U5 IN relative to the charger ground. This calculation does not solve the input-control loop. [TI BQ24074 electrical characteristics](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [Nordic USB supply limits](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/power.html)

The ten local power paths meet their project width and length limits. The programmed charge current remains 357.06 / 402.71 / 445.63 mA min / typ / max with R40 at 2.21 kΩ. The approved supply range of the complete pack must cover 4.16–4.23 V. At an assumed U5 IN of 5.25 V, BAT of 3.10 V and OUT of 4.50 V with a 40 mA load, `P = (VIN−VBAT)×IBAT + (VIN−VOUT)×IOUT` gives about **0.99 W** at 445.63 mA. The standardized thermal resistance cannot predict temperature inside this case. [TI BQ24074 charge and thermal data](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

## Ordinary drilling and solder apertures

All 852 vias are mechanical through holes. Nominal drill / land sizes are 0.30 / 0.50 mm (203), 0.30 / 0.60 mm (63) and 0.40 / 0.80 mm (586). The minimum trace width is 0.127 mm. The mainboard uses the specified ordinary four-layer stack and tenting. Review the actual CAM and mask alignment with the factory. [JLCPCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities/)

| Contact | Nominal drill-to-opening result |
|---|---|
| C42.2 | Ground via at PCB (122.120, 142.315) mm. Gap to the respective paste and mask openings is 0.130 mm |
| C48.2 | Ground via at PCB (107.1368, 147.6572) mm. Gap to the respective paste and mask openings is 0.237 mm |
| SW1.2, D2.1 | Nominal gaps are 0.037 mm and 0.142 mm. Verify factory drill and mask registration, especially SW1 |
| U5.17, U6.11 | Mask islands retain 0.100 mm nominal drill-to-mask gap. Split paste gaps are 0.150 and 0.167 mm respectively |

The native check covers the drill radius and openings around SMD lands whose copper intersects a via annulus. Inspect actual tenting and the split stencil for both exposed pads. The JST SH terminals accept AWG32–28. The harness uses AWG28 within that wire-size range and needs the specified crimp quality and insulation diameter. [JLCPCB via covering](https://jlcpcb.com/help/article/pcb-via-covering) · [JST SH specification](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)

## Prototype checks

First use a battery simulator. Record jack, J4, J1, F1, U5 IN and U1 VBUS voltages during enumeration, charging under USB load, suspend and resume. Check typing while current folds back, then BLE on detach. Verify pack protections and the separate NTC before physical charging. Measure charger, PCB and cell temperatures on the closed first article. See the [battery pack](battery-pack-specification.md) and [firmware](../testing/e73-corner-firmware.md) requirements.

Run `scripts/check_e73_corner_power.py` with KiCad 10 Python after regenerating the harness report. [Current audit and calculations](../../hardware/e73-hhkb-corner/audit/power-process.json) · [CORNER-04 comparison and combined trial](https://github.com/wZuck/YETI60/tree/c3872db49bbff5188b7be3fab3fa73b81b2b9028/hardware/e73-hhkb-corner/audit)
