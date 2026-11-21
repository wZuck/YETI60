English | [Chinese](e73-m05-prototype.zh-CN.md)

# M05 access prototype for E73

M05 adds two removable covers to the CORNER-06 mechanical trial. It retains the M04 outer dimensions and the location of the footpads, upper shell, steel plate and C5 daughterboard. The original right rear foot recess is part of the J4 cover, so its footpad comes off with that cover. Use this M05 configuration for the CORNER-07 first article.

![M05 underside with the J2 and J4 covers removed](../../hardware/e73-hhkb-corner/audit/m05-access-exploded.png)

## Files and parts for one prototype

| Part | Quantity | File or specification |
|---|---:|---|
| FELK60-based top | 1 | [Print STL](../../delivery/YETI60-E73/02-mechanical/top.stl) · [STEP](../../mechanical/generated/yeti60-top.step) |
| M05 bottom | 1 | [Print STL](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/bottom-m05-REVIEW.stl) · [STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/bottom-m05-REVIEW.step) |
| J2 cover | 1 | [Print STL](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J2-REVIEW.stl) · [STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J2-REVIEW.step) |
| J4 cover | 1 | [Print STL](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J4-REVIEW.stl) · [STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J4-REVIEW.step) |
| Cover screws | 4 | M2 × 0.4, 4 mm under the head, low socket head with flat bearing face, head Ø ≤3.90 mm and height ≤1.50 mm. The SUNCO M2 low-head series gives a 3.8 × 1.3 mm nominal head. [Manufacturer dimensions](https://th.misumi-ec.com/en/vona2/detail/221005676582/?Tab=codeList) |
| Cover inserts | 4 | M2 × 0.4 knurled brass, Ø3.2 × 2.5 mm, same size as the C5 insert specification. Prepare four extra and use the cover bore depth in this guide. |
| Adhesive and footpads | As required | Use the case's cold-bond adhesive for the inserts. Use the four footpads from the keyboard materials list, one on the removable J4 cover. |
| Parallel-jaw tool | 1 per port | The [tool guide](e73-m05-service-tool.md) contains the print, blade-cutting pattern and fitting instructions. |
| Parking supports | 1 per port | The [support guide](e73-m05-parking-support.md) contains both carriers, shelves, fasteners and the parking sequence. |

Print one of each of the four shell parts at 100% in millimetres using tough engineering SLA resin. Choose either STEP or STL for each part. Both formats use the same case coordinates. Inspect the seating faces, foot recess and blind bores after the resin is fully post-cured. Keep supports off those faces.

## Resin printing tolerance and receiving inspection

JLC3DP lists ordinary SLA dimensional tolerances of **±0.20 mm through 100 mm**, **±0.30% above 100 mm** and **±0.30 mm for holes**. Its size figures assume no deformation, warping or added finish. The 325.70 mm shell length corresponds to about **±0.98 mm** under that rule. The finished project still needs **±0.15 mm per axis at functional surfaces**. Treat the published figures as a quotation screen and agree with the supplier on the critical features to measure after post-cure. [JLC3DP §10](https://jlc3dp.com/help/article/3d-printing-design-guideline) · [Four-part STEP readback](../../delivery/YETI60-E73/06-validation/m05-print-fit.json)

On the quotation, specify four parts at 1:1 in millimetres. Request support placement clear of the mating ledges, USB opening, cover seating faces and screw/insert bores. Keep coating and heavy sanding off functional surfaces. Ask whether the shop can finish the insert bores after curing. If the plan uses undersize pilots, agree on the pilot dimensions and finishing sequence before the parts are made. The delivered STEP files show the finished nominal bores.

| Check before bonding the inserts | Drawing target and parts to use |
|---|---|
| Upper/lower registration and four M3 fasteners | Hole pattern nominally **300 × 90 mm**, with **Ø3.40 mm** passages in the lower shell. Check both diagonals, seat the shells by hand, and hold the inserts in place for a dry alignment check with the actual screws. Upper insert bores finish to **Ø4.80–4.90 mm** and **3.50 mm** depth |
| C5 board and incoming USB plug | Confirm the **14 × 12.5 mm** pattern against the existing C5. With the board located at its seating height and unpowered, insert and withdraw the actual USB cable from outside. Check that the plug reaches full mating depth without rubbing or moving the board |
| C5 and both cover insert bores | Finish to **Ø3.30–3.40 mm** and **2.90 mm** depth from the local seating face. Check cured bore size before bonding. An undersized, correctly located bore can be finished with a depth stop. Set aside oversize or misplaced bores for supplier disposition |
| J2 and J4 covers | Hole center distances **25.35 mm** and **17.00 mm**, respectively. CAD clearance is **0.35 mm per side**, with a **0.45 mm** nominal screw-tip reserve. Check flush seating and straight withdrawal with the actual screws. When seated, the right rear foot belongs in the J4 recess and the case should rest on all four feet |

For a rigid M3 screw, the nominal radial clearance through the lower pilot is `(3.40 − 3.00) / 2 = 0.20 mm`. Taking ±0.15 mm on one part and ±0.05 mm on the opposing insert per axis yields a worst-case example of `√2 × (0.15 + 0.05) = 0.283 mm` center offset. Check the matched shell pair before committing to extra prints. Record the actual part dimensions, assembly alignment and cable used with the first-article record.

## Build the matched M05 harness

Use the [M05 free lengths](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/wire-lengths-m05.csv) for all nine conductors. These are lengths along the insulation, from housing exit to housing exit or to the pack strain-relief face. Add the termination and stripping allowances for the actual contacts when cutting the wire. The trial uses stranded AWG28 copper with a maximum finished insulation diameter of 0.65 mm.

### Wire and contacts to buy

The documented wire candidate is **CnC Tech 10064-28-1-0500-0XX-1-TS**, FEP-insulated tinned copper, 28 AWG, seven 0.12 mm strands, approximately 0.0792 mm² by nominal strand geometry, finished insulation OD **0.60 ±0.05 mm**, rated 30 V and 105 °C. Use the manufacturer drawing or verify equivalent wire from your stock. A listing marked only UL10064 or AWG28 can have a different insulation or strand diameter. [CnC Tech datasheet and colours](https://www.cnctech.us/pdfs/10064-XX-1-0500-0XX-1-TS.pdf) · [CnC Tech change notice](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/6791/Change%20Notice%20Hook-up-Wire%203-2025.pdf)

| Colour | CnC Tech part number | Combined free length installed | Purchase with allowance |
|---|---|---:|---:|
| Red | `10064-28-1-0500-004-1-TS` | 541.14 mm | 0.75 m |
| Black | `10064-28-1-0500-001-1-TS` | 554.13 mm | 0.75 m |
| White, D− | `10064-28-1-0500-002-1-TS` | 285.19 mm | 0.50 m |
| Green, D+ | `10064-28-1-0500-007-1-TS` | 285.19 mm | 0.50 m |

These quantities cover the USB cable and power bridge. Prepare **three SHR-04V-S housings, one SHR-02V-S housing and 12 SSH-003T-P0.2-H contacts**. For hand assembly, 20 contacts gives eight spares for setup and mistakes. The complete protected pack includes its own red, black and yellow leads, SHR-03V-S housing and three contacts. [JST SH tooling and dimensions](https://www.jst.com/wp-content/uploads/2025/06/eSH.pdf) · [Pack procurement](../engineering/battery-pack-specification.md)

Measure the received wire before cutting. JST's listed contact range is 0.032–0.081 mm² conductor area and 0.4–0.8 mm insulation OD. M05 sets its own 0.65 mm OD limit. The wire dimensions pass this paper screen. Confirm the actual crimp with a sample of each wire lot using the JST contact tooling or a harness shop that can qualify this combination. Inspect the conductor and insulation crimps, and check that each contact latches without side force. On a sample, measure from the cut conductor tip to the housing exit plane for each termination. The cut length equals the listed free length plus these two allowances. [Source-bound wire calculations](../../hardware/e73-hhkb-corner/audit/m05-wire-spec.json)

Twist the white and green wires together along the specified path. The FEP wire data does not give a finished-pair impedance. Use the [USB full-speed checks](../testing/e73-usb-signal.md) before accepting it as the M05 data pair.

![M05 installed cable paths and winding stations](../../hardware/e73-hhkb-corner/audit/m05-harness-plan.png)

| Set | Parts and placement |
|---|---|
| USB from J4 to C5 | Two SHR-04V-S housings and eight SSH-003T-P0.2-H contacts. Match pins 1–4 directly. The two data conductors use the same 285.189 mm free-length target. |
| PCB power bridge | One SHR-02V-S at J5, one SHR-04V-S at J1 and four contacts. J5.1 goes to J1.1, J5.2 goes to J1.4. Leave the center two positions empty at J1. Route both wires above the USB cable at the crossover. |
| Pack to J2 | One SHR-03V-S with three contacts on the PCB end. Pin order is PACK+, PACK−, NTC. Use the specified complete protected pack or an inert gauge during fitting. |
| Battery retainers | Two new prints, [BAT-R1](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R1-M05.stl) and [BAT-R2](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R2-M05.stl). Locate their centers at case X 186 and 189 mm respectively, both at Y −106.60 mm. The [BAT-R1 placement STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R1-M05.step) and [BAT-R2 placement STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R2-M05.step) retain the original case datums. |
| Other retainers and films | Reuse the 14 remaining rigid files and 17 film blank shapes from the [retainer set](../engineering/e73-retention.md). Place the two battery films on the new battery retainers. Use their [BAT-R1](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R1-film-M05.step) and [BAT-R2](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R2-film-M05.step) folded shapes as placement references. |

### Print checklist for the 16 retainers

Print one of each linked STL. Cut the 17 film pieces using the film templates.

| Group | Quantity | STL |
|---|---:|---|
| USB rear guides | 3 | [USB-R1](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-R1.stl), [USB-R2](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-R2.stl), [USB-R3](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-R3.stl) |
| USB front guides | 4 | [USB-F1-base](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-F1-base.stl), [USB-F1-lid](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-F1-lid.stl), [USB-F2-base](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-F2-base.stl), [USB-F2-lid](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-F2-lid.stl) |
| Power bridge guides | 7 | [PWR-R1](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-R1.stl), [PWR-R2](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-R2.stl), [PWR-R3](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-R3.stl), [PWR-R4](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-R4.stl), [PWR-R5](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-R5.stl), [PWR-F-upper](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-F-upper.stl), [PWR-F-lower](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-F-lower.stl) |
| Battery guides | 2 | [BAT-R1-M05](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R1-M05.stl), [BAT-R2-M05](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R2-M05.stl) |

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
