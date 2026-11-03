English | [Chinese](CLOSED-CASE.zh-CN.md)

# Closed-case harness and guides checkpoint

This checkpoint contains continuous-solid checks for nine conductors, the internal bottom-shell relief and 16 removable guides. [Step illustrations and complete assembled renders](ASSEMBLY.md) now describe this design; the order package remains open. No physical assembly or electrical acceptance has been performed. This remains an engineering candidate; the previous seven-wire illustrations and fabrication archive do not describe it.

## Bottom shell

[Candidate bottom STEP](mechanical/yeti60-bottom-short-usb.step) · [Candidate bottom STL](mechanical/yeti60-bottom-short-usb.stl)

The FELK60 exterior and original holes/inserts are retained; the new wing relief avoids the guarded plate-bearing region. An underside relief is added beneath the rear ledge: X = 190…354, Y = −106.3…−98, Z = −5.25…−1.9 mm in the original case frame. No envelope scaling is applied. Minimum nominal distance from the new cut to the checked exterior skin is 2.16 mm; subtracting the existing 0.15 mm case tolerance leaves 2.01 mm. This applies to the added relief, not every unchanged wall of the original shell.

The additional wing relief spans X 357.25–365.25, Y −132.75–−113.75, Z −4.45–12.30 mm, with 0.5 mm corner radius. [Continuous nominal extraction and its limits](SERVICE-PATH.md) are recorded separately; complete harness disconnection is unqualified. Rear USB is now Y −100.80 mm, with clip front/rear half-widths 2.35/2.70 mm. Use the updated STEP/STL files and lengths below.

## Complete wiring

| Harness | Connection |
|---|---|
| USB, four wires | C5 JSH output 1/2/3/4 → J4.1/2/3/4: supply/D−/D+/ground |
| Power, two wires | J5.1 → J1.1; J5.2 → J1.4; J1.2/3 remain empty |
| Battery, three wires | J2.1 protected-pack positive; J2.2 negative; J2.3 NTC referenced to negative |

Use AWG28 stranded copper with insulation OD ≤0.8 mm, also within the selected SH/PH contact ranges. Values below are preformed free lengths between wire-exit datums, not crimp cut lengths. Tolerance is ±0.5 mm; the supplier must preform and verify against the STEP routes. Loose 250/300 mm open-bench leads are not these enclosed harnesses.

| Harness / pin | Free length mm | Minimum design bend radius mm |
|---|---:|---:|
| USB 1 | 286.55 | 4.00 |
| USB 2 | 296.37 | 5.10 |
| USB 3 | 296.69 | 5.10 |
| USB 4 | 305.40 | 5.50 |
| Power 1 | 229.95 | 4.00 |
| Power 2 | 232.20 | 4.00 |
| Battery 1 | 110.64 | 5.00 |
| Battery 2 | 107.50 | 7.00 |
| Battery 3 | 104.36 | 5.00 |

The data pair makes three full rear twists and a half-turn on each front leg, restoring pin order at C5. Geometric pair skew is approximately 0.314 mm; design bend radius is at least 4 mm. Complete pair tubes bound the twist sections for collision checks, with separate spline solids for the conductors. This does not certify impedance or a USB eye. The supplier must qualify electrical wire, crimps and forming.

## Printed parts

Print 16 pieces, one per file. STEP preserves assembly coordinates; STL is moved to the print origin and selected parts are flipped to put their bond face on the bed. Do not rescale. Use post-cured tough resin, qualify dimensions to ±0.05 mm and remove channel support scars/burrs.

| Part | Qty | Print STL | Assembly STEP |
|---|---:|---|---|
| USB-R1 | 1 | [USB-R1.stl](mechanical/guides/USB-R1.stl) | [USB-R1.step](mechanical/guides/USB-R1.step) |
| USB-R2 | 1 | [USB-R2.stl](mechanical/guides/USB-R2.stl) | [USB-R2.step](mechanical/guides/USB-R2.step) |
| USB-R3 | 1 | [USB-R3.stl](mechanical/guides/USB-R3.stl) | [USB-R3.step](mechanical/guides/USB-R3.step) |
| USB-F1-base | 1 | [USB-F1-base.stl](mechanical/guides/USB-F1-base.stl) | [USB-F1-base.step](mechanical/guides/USB-F1-base.step) |
| USB-F1-lid | 1 | [USB-F1-lid.stl](mechanical/guides/USB-F1-lid.stl) | [USB-F1-lid.step](mechanical/guides/USB-F1-lid.step) |
| USB-F2-base | 1 | [USB-F2-base.stl](mechanical/guides/USB-F2-base.stl) | [USB-F2-base.step](mechanical/guides/USB-F2-base.step) |
| USB-F2-lid | 1 | [USB-F2-lid.stl](mechanical/guides/USB-F2-lid.stl) | [USB-F2-lid.step](mechanical/guides/USB-F2-lid.step) |
| BAT-R1 | 1 | [BAT-R1.stl](mechanical/guides/BAT-R1.stl) | [BAT-R1.step](mechanical/guides/BAT-R1.step) |
| BAT-R2 | 1 | [BAT-R2.stl](mechanical/guides/BAT-R2.stl) | [BAT-R2.step](mechanical/guides/BAT-R2.step) |
| PWR-R1 | 1 | [PWR-R1.stl](mechanical/guides/PWR-R1.stl) | [PWR-R1.step](mechanical/guides/PWR-R1.step) |
| PWR-R2 | 1 | [PWR-R2.stl](mechanical/guides/PWR-R2.stl) | [PWR-R2.step](mechanical/guides/PWR-R2.step) |
| PWR-R3 | 1 | [PWR-R3.stl](mechanical/guides/PWR-R3.stl) | [PWR-R3.step](mechanical/guides/PWR-R3.step) |
| PWR-R4 | 1 | [PWR-R4.stl](mechanical/guides/PWR-R4.stl) | [PWR-R4.step](mechanical/guides/PWR-R4.step) |
| PWR-R5 | 1 | [PWR-R5.stl](mechanical/guides/PWR-R5.stl) | [PWR-R5.step](mechanical/guides/PWR-R5.step) |
| PWR-F-upper | 1 | [PWR-F-upper.stl](mechanical/guides/PWR-F-upper.stl) | [PWR-F-upper.step](mechanical/guides/PWR-F-upper.step) |
| PWR-F-lower | 1 | [PWR-F-lower.stl](mechanical/guides/PWR-F-lower.stl) | [PWR-F-lower.step](mechanical/guides/PWR-F-lower.step) |

USB-R1…R3 bond to the rear relief roof. USB-F1/F2 are front bases and removable lids. BAT-R1/R2 retain the three battery leads. PWR-R1…R5 bond to the PCB underside. PWR-F-upper/lower form the removable two-level fan-out near J1; install the red wire before the lower black-wire guide.

Also prepare 0.1 mm insulating bond tape for 13 case/PCB mounting faces, 0.05 mm removable insulating tape for the two USB lids and lower power bridge, and 12 retention-film strips with total thickness ≤0.1 mm. These thicknesses are assembly datums, not arbitrary tape stacks.

## Assembly and acceptance sequence

1. Print and post-cure the candidate bottom and all 16 guides; inspect reliefs, original insert bores, channels, burrs and bond datums.
2. Complete separate C5/mainboard power and USB tests first. The board still fits 75 components; use its candidate purchase table and omit R30/R31.
3. Install the PCB-side power guides and J5 → J1 jumper. Meter every pin. Route red through the upper fan-out and black through the lower one; apparent housing left/right is not a pin definition.
4. Preform the USB harness with three full rear twists and two half-turns. Lay completed wires into open guide halves before fitting lids/film; do not force crimped housings through closed holes.
5. Install C5, insulation and the protected pack. Retain the three-wire battery connection and obtain the required supplier parameter confirmation.
6. Keep guide lids/retention releasable. Connect USB and battery before fully seating the main stack; lower it gradually while arranging wires, without pulling on leads or compressing the stack.
7. Before closure, inspect conductor position within 0.25 mm of the controlled route, especially the power crossover dips, J1 fan-out and rear relief. Exclude contact with the pack, solder points and screw heads.
8. Run the open-bench electrical procedure, then check enclosed concurrent USB input/charging, BLE, temperature and repeated opening. Release harness retention before lifting the mainboard. Actual mating/removal and retention forces await first-article acceptance.

Current passing evidence covers continuous-solid dimensions at nominal thickness and both 1.44/1.76 mm extremes of ordinary 1.6 mm boards. The 0.25 mm route allowance is an as-assembled inspection requirement; unverified print, tape and wire errors must not be assumed to satisfy it.

[Closed-case report](audit/closed-assembly.json) · [Guide report](audit/guides.json) · [Battery supplier parameters](../../docs/build/battery-vendor-checklist.md) · [Candidate entry](README.md)
