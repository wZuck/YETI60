English | [Chinese](POWER-LAYOUT.zh-CN.md)

# Power-stage relocation and verification

J2 is now the SH3 header at PCB [155.5, 129.0] mm, 0°, B.Cu. Its [native repair and cable fanout](BATTERY-SERVICE.md) supersede the old PH position/interface.

The [package and ordinary-process revision](PACKAGE-MODELS.md) governs current U5 lands/stencil and U5/U6 mask islands. Both via faces request tenting; previous back-open instructions are superseded.

This page applies to the USB repair candidate in this directory. The former U6 output/feedback and C46 routes detoured around a sensing-ground guard, with conservative contacted-track lengths of 29.183 mm and 28.504 mm. This revision relocates the regulator stage and charger capacitors. Feedback is now 3.555 mm and C46 is 4.681 mm; all ten local paths below remain on the component-side B.Cu layer.

**Design layout checks pass; physical stability is unverified.** Strict native checks report 0 errors, 0 opens and 0 schematic mismatches, with 411 pad-pair checks. The 102 missing-courtyard warnings belong to non-purchased sensing/mechanical geometry; there are no copper-sliver, fitted-courtyard-overlap or dangling-track warnings. The [geometry report](audit/geometry-check.json) separately records per-layer ground connectivity and relocated component clearances. These results do not establish loop stability, ripple, a USB eye, thermal performance or measured battery behavior.

## Component positions

Coordinates are native KiCad millimetres and degrees, all on the back; they are not a mirrored solder-side image. Values and pin assignments are unchanged. The seven power capacitors retain the [0805 purchasing specifications](PASSIVES.md). C32 is outside this relocation and remains at (346.4, 118.0) mm, 90°. Previous placement images do not locate the relocated parts below.

| Reference | X (mm) | Y (mm) | Angle (°) |
|---|---:|---:|---:|
| C40 | 122.0 | 146.9 | -90 |
| C41 | 113.0 | 143.7 | 180 |
| C42 | 121.9 | 142.7 | 0 |
| C43 | 132.0 | 136.5 | 0 |
| C44 | 137.0 | 139.8 | 0 |
| C45 | 132.5 | 143.3 | 0 |
| C46 | 136.0 | 144.0 | 0 |
| L1 | 128.5 | 141.5 | -90 |
| R45 | 124.5 | 136.0 | 0 |
| R46 | 137.0 | 135.0 | 0 |
| R47 | 136.6 | 136.5 | 0 |
| U6 | 133.0 | 140.8 | 0 |

## Local copper-path limits

Lengths sum complete contacted track primitives: conservative geometry, not propagation delay or loop inductance. Contact with a via object does not imply a layer transition; the C46 path touches one same-layer via junction but all its tracks remain on B.Cu. Maximum lengths and minimum widths are project screening limits, not TI stability guarantees.

| From → to | Length / limit (mm) | Minimum width / requirement (mm) |
|---|---:|---:|
| U6.4 → L1.1 | 2.829 / 4.0 | 0.300 / 0.300 |
| U6.2 → L1.2 | 1.759 / 4.0 | 0.300 / 0.300 |
| U6.5 → C43.1 | 3.454 / 4.0 | 0.250 / 0.250 |
| U6.8 → C44.1 | 2.334 / 3.0 | 0.200 / 0.200 |
| U6.1 → C45.1 | 1.519 / 3.0 | 0.250 / 0.250 |
| U6.1 → C46.1 | 4.681 / 8.5 | 0.200 / 0.200 |
| U6.1 → U6.10 | 3.555 / 5.0 | 0.200 / 0.200 |
| U5.13 → C40.1 | 3.276 / 4.5 | 0.300 / 0.300 |
| U5.2 → C41.1 | 3.384 / 4.0 | 0.250 / 0.250 |
| U5.10 → C42.1 | 2.242 / 4.0 | 0.300 / 0.300 |

Thirty-nine relocated-component checks cover nominal and accepted PCB thicknesses. Conservative envelopes have minimum gaps of approximately 0.756 mm to the original case, 0.245 mm to mounting hardware and 31.875 mm to the pack. This varies PCB thickness, not all combined XY placement, hole-position and resin tolerances; the 0.245 mm gap is not final tolerance acceptance.

## Ordinary vias and soldering

Continue using ordinary JLC four-layer FR4, 1.6 mm finished thickness. Relative to the preceding capacitor revision, nine ordinary through vias are added, four unused vias removed and three vias moved; the power checkpoint has 813 vias; the current [SH3 battery revision](BATTERY-SERVICE.md) adds two more, giving 815. Exact positions, diameters and nets are in the [machine contract](power-layout.json). Added vias use 0.50 mm lands / 0.30 mm drills; no blind/buried vias, resin filling, plated filling or capping is required.

C43 ground, U6 PGND and GND connect to local exposed ground; C45 uses the adjacent ground via. A U5.8-to-exposed-ground connection repairs the previously separate ground copper. Independent checking unions actual filled copper separately per layer and joins layers only through ground vias/PTH pads; a shared zone identity alone does not count as connectivity.

A B.Cu keepout between the L1 lands spans approximately X=126.8–130.2, Y=141.1–141.9 mm and prohibits tracks, vias and pours. This is the project central-land-gap constraint. Buy Würth 74438336015, WE-MAPI 3020, 1.5 µH, maximum body 3.2 × 3.2 × 2.0 mm. The retained native footprint name containing `3015` is a legacy technical identifier, not the purchasing dimensions. See the [manufacturer drawing](https://www.we-online.com/components/products/datasheet/74438336015.pdf).

## Sensing and first-article boundaries

Sensing electrodes, mounting holes, outline and pin assignments retain their positions. Local F.Cu ROW_DRV3/CHG_EN1 and In1.Cu ROW1 detour around the new U6 via; the CHG_N inner connection is also rerouted and its acute corner removed. Preserved electrodes do not imply unchanged front-side routing. Actual parasitics, scan noise and per-key calibration require the first board.

This closes the former long-detour design finding, not production acceptance. The canonical fabrication archive still describes the old routing and is not released by this page. Complete enclosed service, actual wire selection, pack supplier confirmation and physical measurements remain in the [candidate entry](README.md). The [open-bench sequence](README.md#solder-and-open-bench-sequence) needs no case but still requires the protected battery, plate, NiZ housings/sliders, domes and springs.
