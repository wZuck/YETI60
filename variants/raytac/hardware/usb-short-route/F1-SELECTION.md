English | [Chinese](F1-SELECTION.zh-CN.md)

# Mainboard F1: selected fuse and revised lands

For this repair candidate, buy **one Littelfuse 0466001.NRHF**, a 1206/3216 **1 A, 63 V, one-time fast-acting** fuse. [Manufacturer datasheet](https://www.littelfuse.com/assetdocs/fuse-466-datasheet?assetguid=dbe9bcd7-6072-4adf-bf5b-d33e52a6b90f) · [LCSC C151135](https://www.lcsc.com/product-detail/Fuses_Littelfuse-0466001-NRHF_C151135.html). Two additional spares are optional. There is no allocated stock credit. This replaces the earlier unspecified 0.5 A PPTC selection **for the repair candidate only**; do not use the old mainboard materials table for F1.

F1 provides secondary fault protection. The BQ24074 and firmware USB100/USB500 policy still govern input current. A 1 A fuse does not authorize 1 A USB consumption. An opened fuse requires fault diagnosis and replacement; unplugging will not reset it. Do not substitute a wire link. C5 retains its separate upstream fuse and protection components.

## Why this rating

The June 2023 manufacturer sheet provides a continuous-operation example at 70°C:

```text
continuous allowance = rated current × 0.75 × 0.80
1.00 A part: 0.600 A allowance > 0.500 A configured USB limit
0.75 A part: 0.450 A allowance < 0.500 A
0.50 A part: 0.300 A allowance < 0.500 A
```

These are the manufacturer's nominal fast-fuse derating factors, not a measured board limit or a PPTC curve. Require measured local F1 ambient at or below 70°C for this design screen. The old unspecified PPTC had no qualified temperature/resistance contract. The selected fuse has nominal cold resistance **0.075 Ω**, not a published maximum; at 500 mA this corresponds to approximately 37.5 mV and 18.75 mW before resistance rise. Use the [updated feed budget](POWER-FEED.md) for the additional cable/contact losses.

The 25°C opening-time table specifies maximum 5 s at twice rated current and 0.2 s at three times rated current. It does not establish selective coordination with C5, a host port or a battery protector, and it does not mean the fuse opens at exactly 1 A. Inrush, hot operation and faults still need fixture testing. The input fuse does not replace the protected pack or its independent temperature interruption.

## Native PCB changes

F1 stays on B.Cu at PCB **(88.609827, 114.198524) mm, 90°**. Pin 1 remains USB_5V and pin 2 VBUS. The schematic uses the one-time `Fuse` symbol. Both the native board and frozen library use `Fuse_Littelfuse_0466_1206__F1`.

The manufacturer reflow drawing gives an outside land span of 0.150 inch, gap 0.060 inch and width 0.080 inch. Deriving the lands from those dimensions avoids accumulating rounded metric labels:

```text
pad length = (0.150 − 0.060) / 2 × 25.4 = 1.143 mm
pad width = 0.080 × 25.4 = 2.032 mm
pad centres = ±(0.150 + 0.060) / 4 × 25.4 = ±1.3335 mm
```

The old 1.25 × 1.75 mm rounded pads are replaced by these rectangular lands. Copper zones are refilled and strict DRC/connectivity is rerun. The original hole/sensing locations and every other retained footprint geometry stay fixed. Maximum fuse body dimensions are 3.302 × 1.651 × 0.660 mm; with the documented position/solder allowances they fit inside the larger previous F1 clearance envelope. The supplied [nominal STEP envelope](models/Littelfuse_0466001_NRHF_nominal.step) has the correct nominal dimensions; termination detail and finish remain illustrative.

## Assemble and verify

1. Follow the staged [solder/open-bench procedure](README.md#solder-and-open-bench-sequence), using this candidate's revised F1 lands and one-time fuse. Keep the pack and USB disconnected while inspecting solder and resistance.
2. Confirm the supplier MPN, top code H and actual package. If checking resistance, use a four-wire method on an isolated part; the cold incoming target is ≤0.10 Ω at 25°C. A normal two-wire meter's lead resistance cannot qualify this small value.
3. In a current-limited fixture, qualify the loaded hot-resistance target ≤0.15 Ω, local temperature, USB configuration, simultaneous charging/typing and inrush. The resistance targets are imposed incoming/test limits, not manufacturer maximum specifications.
4. Diagnose faults before replacing an opened part. Source/C5/fuse/harness coordination and actual USB/BLE/charge behavior remain physical acceptance items.

[Parts contract](parts-qualification.json) · [Updated purchase CSV](mainboard-purchase.csv) · [Assembly guide](ASSEMBLY.md) · [Candidate entry](README.md)
