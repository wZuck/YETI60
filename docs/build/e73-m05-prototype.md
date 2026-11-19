English | [Chinese](e73-m05-prototype.zh-CN.md)

# M05 access prototype for E73

M05 adds two removable covers to the CORNER-05 mechanical trial. It retains the M04 outer dimensions and the location of the footpads, upper shell, steel plate and C5 daughterboard. The original right rear foot recess is part of the J4 cover, so its footpad comes off with that cover. The current M04 files remain the baseline in the main ordering table.

![M05 underside with the J2 and J4 covers removed](../../hardware/e73-hhkb-corner/audit/m05-access-exploded.png)

## Files and parts for one prototype

| Part | Quantity | File or specification |
|---|---:|---|
| M05 bottom | 1 | [Print STL](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/bottom-m05-REVIEW.stl) · [STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/bottom-m05-REVIEW.step) |
| J2 cover | 1 | [Print STL](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J2-REVIEW.stl) · [STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J2-REVIEW.step) |
| J4 cover | 1 | [Print STL](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J4-REVIEW.stl) · [STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J4-REVIEW.step) |
| Cover screws | 4 | M2 × 0.4, 4 mm under the head, low socket head with flat bearing face, head Ø ≤3.90 mm and height ≤1.50 mm. The SUNCO M2 low-head series gives a 3.8 × 1.3 mm nominal head. [Manufacturer dimensions](https://th.misumi-ec.com/en/vona2/detail/221005676582/?Tab=codeList) |
| Cover inserts | 4 | M2 × 0.4 knurled brass, Ø3.2 × 2.5 mm, same size as the C5 insert specification. Prepare four extra and use the cover bore depth in this guide. |
| Adhesive and footpads | As required | Use the case's cold-bond adhesive for the inserts. Use the four footpads from the keyboard materials list, one on the removable J4 cover. |
| Parallel-jaw tool | 1 trial assembly | The [tool guide](e73-m05-service-tool.md) contains the print, blade-cutting pattern and fitting instructions. |

Print at 100% in millimetres using tough engineering SLA resin. Make one of each of the three parts and choose either STEP or STL for each part. Both formats use the same case coordinates. Inspect the seating faces, foot recess and blind bores after the resin is fully post-cured. Choose supports and drainage before printing and keep support damage off those faces.

## Build the matched M05 harness

Use the [M05 free lengths](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/wire-lengths-m05.csv) for all nine conductors. These are lengths along the insulation, from housing exit to housing exit or to the pack strain-relief face. Add the termination and stripping allowances for the actual contacts when cutting the wire. The trial uses stranded AWG28 copper with a maximum finished insulation diameter of 0.65 mm.

![M05 installed cable paths and winding stations](../../hardware/e73-hhkb-corner/audit/m05-harness-plan.png)

| Set | Parts and placement |
|---|---|
| USB from J4 to C5 | Two SHR-04V-S housings and eight SSH-003T-P0.2-H contacts. Match pins 1–4 directly. The two data conductors use the same 285.189 mm free-length target. |
| PCB power bridge | One SHR-02V-S at J5, one SHR-04V-S at J1 and four contacts. J5.1 goes to J1.1, J5.2 goes to J1.4. Leave the center two positions empty at J1. Route both wires above the USB cable at the crossover. |
| Pack to J2 | One SHR-03V-S with three contacts on the PCB end. Pin order is PACK+, PACK−, NTC. Use the specified complete protected pack or an inert gauge during fitting. |
| Battery retainers | Two new prints, [BAT-R1](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R1-M05.stl) and [BAT-R2](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R2-M05.stl). Locate their centers at case X 186 and 189 mm respectively, both at Y −106.60 mm. The [BAT-R1 placement STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R1-M05.step) and [BAT-R2 placement STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R2-M05.step) retain the original case datums. |
| Other retainers and films | Reuse the 14 remaining rigid files and 17 film blank shapes from the [retainer set](../engineering/e73-retention.md). Place the two battery films on the new battery retainers. Use their [BAT-R1](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R1-film-M05.step) and [BAT-R2](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R2-film-M05.step) folded shapes as placement references. |

Print the two battery retainers at the same scale and finish as the other guides. Match their case surfaces and inspect the 0.10 mm nominal bonding gap. Leave the slots free of adhesive and retain the wires without clamping their axial movement.

Follow the USB winding stations from **J4 toward C5**. The turns describe the CAD centerline geometry. The [seated lead assembly STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/seated-wires-REFERENCE.step) shows the full wire paths for comparison with a fabricated harness.

| Station | Section | Centerline span | Turns |
|---|---|---:|---:|
| T1 | Rear straight at X 312.190 → 230.000 mm, Y −102.000 mm | 82.190 mm | 3.060 |
| T2 | Forward straight at X 193.000 mm, Y −126.674 → −164.500 mm | 37.826 mm | 0.613 |
| T3 | Return straight at X 214.313 mm, Y −164.500 → −142.000 mm | 22.500 mm | 0.327 |

With the new routed lengths, the four current-carrying wires total 1.095 m. Using the [existing charging model](../engineering/e73-corner-power-process.md), the included hot-path resistance is 0.426 Ω at 60 °C, with about 1.55 mV extra drop at 500 mA relative to M04. The [M05 wire and fit report](../../hardware/e73-hhkb-corner/audit/m05-harness.json) retains the assumptions and excluded losses. It also records the seven checked connector poses at each PCB thickness with the actual M05 parts modeled in place.

## Fit the covers before installing electronics

1. Dry-fit each cover to its matching pocket and confirm that it comes off straight down. The nominal perimeter clearance is 0.35 mm per side and the exterior surfaces are flush in CAD. Keep the cover and the right rear foot recess flush when finishing the parts.
2. Finish the four blind insert bores to **Ø3.35 ±0.05 mm**. Set the depth stop to **2.90 mm from the seating shelf at the bore axis**. Cold-bond the inserts with the outward face recessed **0.30 mm** at that axis. Bond and cure the empty shell before installing the battery or PCB.
3. Confirm the screws clamp each cover and clear the blind bottom. CAD gives **2.15 mm** nominal thread overlap and **0.45 mm** at the screw tip. Inspect the actual head envelope and tip clearance. Check for cover flex, stripped resin, loose inserts and rocking with the feet fitted.
4. Attach the right rear footpad wholly within the J4 cover recess. Keep both screw heads exposed. Remove the two covers to gain access to J2 and J4. Open-shell trials use an inert gauge in place of the battery and unpowered harnesses.
5. Dry-fit the C5, temporary guides, mainboard and unpowered harness using the plan above. Verify continuity and J1’s two empty positions before any powered test. Confirm the battery bow forms before its two guides, the USB loop can move forward and the power bridge stays above it. The intended removal order is J2, J4, then a straight PCB and plate lift. Check actual release tool access and cable feed with the covers removed before fixing the guides in place.

The [CAD report](../../hardware/e73-hhkb-corner/audit/service-case-m05.json) checks envelope dimensions, the four new insert supports, the eight existing screw regions, full cover withdrawal and the open paths around J2 and J4. [Case service checks](../engineering/e73-corner-service.md) document the paired wire routing trial. M05 is for mechanical fit testing. It still needs a qualified release tool, a complete wired service demonstration, load and repeated removal tests before production use.

With the shell and covers open and the two plugs parked, the [continuous lift study](../../hardware/e73-hhkb-corner/audit/m05-lift.json) checks 25 mm of straight motion at all three PCB thicknesses. It maintains at least 0.15 mm clearance between the modeled moving power wires and checked stationary objects. It also checks the moving PCB and rigid envelopes against all seven stationary conductors. Actual plug removal, flexible wire feed and tool force require a sample.
