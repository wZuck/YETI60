English | [Chinese](e73-corner-power-process.zh-CN.md)

# CORNER-04 power and ordinary PCB process review

The current PCB passes the ten local power trace limits. Two exposed solder apertures still intersect mechanical via drills. The USB input path also has significant series loss at the planned charging current. These findings keep the present Gerbers on engineering review.

## Local power stage and charging

The native board connects U1 to the BQ24074's EN1, EN2 and active-low CE pins, with 100 kΩ pull-downs. SW100 controls the TPS63031 enable. The linked firmware checks cover host configuration, USB HID with charging enabled, suspend and BLE fallback. The switch-off pull-down state permits USB100 charging without firmware. See the [firmware guide](../testing/e73-corner-firmware.md) for the linked-binary evidence and the [pack specification](battery-pack-specification.md) for the minimum rating and independent thermal interruption.

The regulator-to-inductor routes are 3.29 and 3.63 mm measured between pad centres through actual copper contacts, with 0.30 mm traces and no layer changes. The regulator input and its closest output capacitor measure 3.45 and 1.52 mm. The charger IN, BAT and OUT capacitor paths are 3.88, 3.42 and 3.05 mm. These are PCB geometry checks. Actual ripple, converter startup, capacitor effective capacitance and settling during sensing still need validation. Buy to the effective-capacitance rows in the [BOM](../../hardware/e73-hhkb-corner/mainboard-purchase.csv). [TI TPS63031 layout guidance](https://www.ti.com/lit/ds/symlink/tps63031.pdf)

The charger’s 2.21 kΩ setting and the published ISET factors give 357.06 / 402.71 / 445.63 mA minimum / typical / maximum programmed charge current. The 4.16–4.23 V regulation limits still govern pack selection. The cell vendor must confirm the complete protected pack and the inconsistent bare-cell charge-current data. [TI BQ24074 characteristics](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

## Voltage drop and heat

The positive path runs from C5 through J4 and J5, then J1, F1 and U5 IN. The four AWG28 supply and return leads total **1.083 m** between housing exits. Their modeled loop resistance is 0.232 Ω at 20 °C using a nominal 0.0804 mm² copper cross-section. The selected PCB positive trace route contributes 0.435 Ω, of which 0.292 Ω is between F1 output and U5 IN. Copper resistance uses `R = ρL/(width × thickness)` and the selected stack. Applying `R60 = R20 × (1 + 0.00393 × 40)` gives **0.772 Ω**. This screen excludes the PCB ground return, via barrels, C5 traces, both fuses, mated connectors, crimp joints and external cable losses.

| Voltage measured at the Type-C jack under load | Assumed input current | Included voltage drop | Estimated U5 IN before omitted losses |
|---|---:|---:|---:|
| 4.75 V | 100 mA | 0.077 V | 4.673 V |
| 4.75 V | 450 mA | 0.347 V | 4.403 V |
| 4.75 V | 500 mA | 0.386 V | 4.364 V |
| 5.00 V | 450 mA | 0.347 V | 4.653 V |
| 5.00 V | 500 mA | 0.386 V | 4.614 V |

The charger can reduce input current at its 4.35–4.63 V input-voltage threshold. At 4.75 V, the table shows that the unabated 450–500 mA operating point has insufficient margin. The nRF52840 USB supply has a 4.35 V operating minimum. U1 uses its own branch after F1, so verify its voltage at U1 relative to local ground, separately from U5 IN. The calculation does not solve the charger feedback loop or predict disconnects. [TI charger input regulation](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [Nordic USB supply limits](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/power.html)

At an assumed U5 IN of 5.25 V, BAT of 3.10 V and OUT of 4.50 V with a 40 mA load, `P = (VIN−VBAT)×IBAT + (VIN−VOUT)×IOUT` gives **0.99 W** at 445.63 mA. TI's 44.5 °C/W figure is for a standardized test board. It does not determine junction or cell temperature in this case. Verify closed-case temperature at the charger, PCB and battery before qualifying the charging profile. [TI BQ24074 thermal data and equation 11](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

The combined trial below shortens the three PCB supply paths. Further harness improvement would require a shorter power round trip. A direct C5-to-power-stage branch needs a new harness geometry and separate verification of the USB data pair and its ground return. Keep the existing C5 board. An input-current reduction also requires a new timer and charge-termination check. For the prototype, record jack, J4, J1, F1, U5 IN and U1 VBUS voltages under load and during enumeration and suspend. Verify stable typing while charge current folds back on a weak USB source. First use a battery simulator and follow the pack supplier checks before attaching a qualified pack.

## Fabrication and paste

The 856 vias are mechanically drilled through all four layers. The nominal drill and land combinations are 0.30/0.50 mm (200), 0.30/0.60 mm (65) and 0.40/0.80 mm (591). The minimum via drill-edge spacing is 0.358 mm. The smallest track is 0.127 mm. The specified stack, widths and drilling are within published ordinary capability. Submit the actual CAM for a fabrication review after the solder-aperture issue is resolved. [JLCPCB capabilities](https://jlcpcb.com/capabilities/pcb-capabilities/)

| Contact | Drill-to-opening relationship in nominal PCB geometry | Disposition |
|---|---|---|
| C42.2 | The Ø0.40 mm drill centre is inside both back-side openings | Move the ground drill clear of the openings and reconnect C42.2. Check the competing COL2 copper on In2.Cu |
| C48.2 | The Ø0.40 mm drill reaches 0.170 mm into both openings by the centre-distance screen | Move the ground drill to the adjacent ground route outside the paste and mask |
| SW1.2 and D2.1 | Nominal drill clearance to both apertures is 0.037 mm and 0.142 mm respectively | Check drill registration and mask in factory CAM, especially the smaller SW1 margin |
| U5.17 and U6.11 | Both Ø0.30 mm drills have 0.100 mm to the nearest nominal mask opening. The paste gaps are 0.150 mm and 0.167 mm | Preserve mask islands and split stencil apertures, and inspect actual tenting and reflow |

The screen reads the copper, mask and paste geometry from the current footprint definitions. A negative radius-adjusted centre distance denotes intersection. For a centre inside the opening it is reported as minus the drill radius. Opening areas containing no stencil geometry, such as the unpopulated sensing electrodes, are listed separately in the raw output. Ordinary tenting needs a valid mask island. It cannot close a drill intentionally exposed by the surrounding pad opening. [JLCPCB via covering options](https://jlcpcb.com/help/article/pcb-via-covering)

[Source-bound audit, dimensions and calculations](../../hardware/e73-hhkb-corner/audit/power-process.json). Reproduce with KiCad 10's Python runtime using `python3 scripts/check_e73_corner_power.py`.

## Via relocation trial

The trial uses Ø0.30 mm mechanical through drills on Ø0.50 mm via lands. C42 moves to PCB (122.120, 142.315) mm with a 0.25 mm ground link. C48 lands on the existing ground bend at (107.1368, 147.6572) mm. The minimum nominal margins to the respective mask and paste openings are 0.130 and 0.237 mm. Refilled KiCad DRC found zero errors, zero opens and zero schematic parity findings. The trial PCB is generated in a scratch directory. The selected delivery still contains the current board. See the [trial record](../../hardware/e73-hhkb-corner/audit/paste-repair-trial.json).

## Combined trial results

The trial combines the C42/C48 via relocation and three rerouted USB supply spans on one PCB. It preserves the fitted parts, pad geometry, outline, sensing electrodes, USB data pair and harness endpoints from CORNER-04. Added vias are ordinary Ø0.30 mm mechanical through drills.

| Mainboard supply span | Current length and trace resistance | Combined trial length and trace resistance |
|---|---:|---:|
| J4.1 to J5.1 | 23.16 mm, 0.086 Ω | 13.55 mm, 0.015 Ω |
| J1.1 to F1.2 | 43.81 mm, 0.057 Ω | 36.30 mm, 0.029 Ω |
| F1.1 to U5 IN | 68.21 mm, 0.292 Ω | 52.78 mm, 0.089 Ω |

At the same assumed 60 °C, included series resistance falls from **0.772 Ω to 0.423 Ω**, a 45.2% reduction. At 4.75 V at the Type-C jack and an assumed 500 mA input, U5 IN rises from 4.364 V to **4.539 V** before fuse, contact and additional board losses. The result remains below the upper 4.63 V charger DPM threshold. First-article checks must cover USB data during charge-current foldback. [TI BQ24074](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

The combined trial passed strict refilled DRC, schematic parity and the connected USB reference test. The nominal drill gaps to each component's own mask and paste openings are 0.130 and 0.237 mm for C42 and C48. The report records 852 ordinary through vias and 100 courtyard warnings on non-purchased geometry. The trial PCB is generated in a work directory. The delivery Gerber still describes the current board while the revised package is awaiting regeneration and validation. [Combined trial evidence](../../hardware/e73-hhkb-corner/audit/charge-feed-trial.json)

The specified SSH-003T-P0.2-H terminal accepts AWG32–28. The current wire model already uses the largest listed conductor size. A larger conductor would require a different termination and new crimp and insulation-envelope checks. [JST SH specification](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)

Run `scripts/study_e73_corner_charge_feed.py` with KiCad 10's Python runtime to reproduce the trial and its checks.
