English | [Chinese](e73-ordering-printing.zh-CN.md)

# E73 PCB and mechanical manufacturing instructions

**Engineering review only.** These are the intended ordinary-process parameters for the current corner PCB. Consult [start here](e73-delivery-start.md) and the snapshot manifest before ordering. A Gerber review archive exists; final manufacture acceptance remains open.

## PCB order

| Item | Selection / requirement |
|---|---|
| Mainboard count | Install 1 per keyboard; fabrication quantity is the factory minimum or your chosen spare count |
| Daughterboard count | **0 new boards for this build**; retain the already-made UDB C5 JSH |
| Mainboard source | [Current native PCB](../../hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pcb); the delivery folder contains the matching Gerber/drill ZIP |
| Dimensions | 285.0 × 94.6 mm; use the supplied Edge.Cuts, holes and slots without scaling |
| Material / layer count | FR-4 / **4 copper layers** |
| Layer order | F.Cu, In1.Cu, In2.Cu, B.Cu; upload all four, not just the outer pair |
| Thickness | **1.6 mm nominal**; assembly accepts the specified 1.44–1.76 mm range subject to its tolerance checks |
| Stack-up | **JLC04161H-7628**; compare the manufacturer's offered ordinary stack with `01-pcb/process-spec.json` |
| Copper | Nominal outer 35 µm, inner 15.2 µm per the selected stack; have the manufacturer confirm the offered stack |
| Finish | ENIG, ordinary selectable finish |
| Vias | Mechanically drilled F.Cu–B.Cu through only; newly routed vias 0.50 mm diameter / 0.30 mm drill |
| Via treatment | Both-side tenting; no resin-fill/copper-cap requirement; no blind, buried or laser vias |
| Solder mask / legend | Retain the supplied mask and functional pin/hole/reference legends; normal offered colour |
| Drill files | Include separate plated and non-plated drills, plus the supplied board outline/slots |
| Impedance | Preserve geometry and selected stack; USB signal integrity is not qualified by choosing an impedance option alone |
| Assembly service | This guide assumes self-soldering; placement CSV is a reference, not an approved turnkey JLC assembly order |
| Stencil | One front and one back stencil, both **0.12 mm** standard laser-cut stainless steel. See the selections below |

Use the [matching Gerber and drill ZIP](../../delivery/YETI60-E73/01-pcb/YETI60-E73-gerbers-REVIEW.zip) for the factory preview. Verify the outline, four copper layers, slots, non-plated holes, sensing geometry and mask openings before accepting the quotation. Stop if it imports as two layers or the factory proposes changing the specified geometry/process. The exported position file contains 75 fitted parts; sensing electrodes, mounting holes and pogo pads are not purchased components.

The [fabrication ZIP audit](../../delivery/YETI60-E73/06-validation/cam-ordinary.json) matches the 285.0 × 94.6 mm closed profile to all 40 source segments and arcs. It also matches 852 through-via drill hits and their land flashes on each copper layer, one plated round mounting hole, two plated 2.20 × 5.00 mm slots and 30 non-plated holes. The smallest routed via drill is 0.30 mm and the tightest nominal via-hole edge gap is 0.358 mm.

JLC ordinary-process references: [capabilities](https://jlcpcb.com/capabilities/pcb-capabilities/) and [stack-ups](https://jlcpcb.com/impedance). Availability/options must be checked against the actual quotation. Neither this document nor a clean DRC is a factory DFM approval.

CORNER-07 changes the U5, U6, C42 and SW1 apertures and relocates the D2 ground via. The complete ZIP has a 0.230 mm minimum nominal drill-to-opening gap. A conservative drill-position and finished-hole-size screen leaves at least 0.059 mm for other relative shifts. Ask the factory to confirm mask registration and the U5 and U6 mask islands for its ordinary process. [Artwork measurements](../engineering/e73-aperture-review.md) · [JLCPCB drill tolerances](https://jlcpcb.com/capabilities/Capabilities)

## Stencil order

Use the [same CORNER-07 Gerber ZIP](../../delivery/YETI60-E73/01-pcb/YETI60-E73-gerbers-REVIEW.zip). It contains the [front paste layer](../../delivery/YETI60-E73/01-pcb/gerbers/EC60-nRF52840-F_Paste.gtp) for U1 and the [back paste layer](../../delivery/YETI60-E73/01-pcb/gerbers/EC60-nRF52840-B_Paste.gbp) for the back-side components. Order with the PCB and select a single PCB. For a separate stencil order, upload the same ZIP under SMT Stencil. [JLCPCB stencil ordering](https://jlcpcb.com/help/article/how-to-order-a-stencil)

| Setting | Selection |
|---|---|
| Type and quantity | 304 stainless paste stencil, frameless. Select Top + Bottom on Separate Stencils, one sheet per side. If the form has separate items, select Top Only and Bottom Only once each |
| Sheet size | Standard 380 × 280 mm, custom size off. Verify at least 285.0 × 94.6 mm usable area on each sheet. JLCPCB lists 290 × 190 mm for this model |
| Thickness | Select by customer, **0.12 mm** on each sheet |
| Fiducials and finish | No fiducials, standard finish and no nano-coating |
| Orientation | One board per sheet, long edge parallel to the sheet's long edge. Review side and orientation in the cutting preview |

Copy into the stencil remarks.

> YETI60 E73 CORNER-07. Use the supplied paste layer for each side. Preserve all aperture shapes and split windows. Keep mask openings out of the cutting data. Please send the cutting preview with both sides identified for review before cutting.

The area ratio is opening area ÷ (opening perimeter × foil thickness). The table uses the union of the actual Gerber shapes, so each physical cut is counted once. TI's QFN/SON guidance provides the 0.66 engineering screen. [Gerber geometry report](../../delivery/YETI60-E73/06-validation/cam-apertures.json) · [TI assembly note, §4.3](https://www.ti.com/lit/an/slua271c/slua271c.pdf) · [JLCPCB stencil capabilities](https://jlcpcb.com/capabilities/pcb-stencil-manufacturing)

| Side | Cuts | Min. ratio at 0.12 mm | Cuts below 0.66 at 0.12 / 0.15 mm |
|---|---:|---:|---:|
| Front, U1 only | 43 | 2.000 | 0 / 0 |
| Back, limiting opening at U5 | 236 | 0.742 | 0 / 16 |

Dry-align before printing. Match the front openings to U1 at the right-hand corner as viewed from the key side. For the back, turn the real PCB over and match J4, U5 and SW1 at three separated locations. Upload both paste layers in their original coordinates. Keep JP1 open by clearing paste from its two pads before reflow. J3's pogo pads have no stencil openings. Print the back for the first power stage. When printing U1 later, support the board so the populated back stays clear of the fixture. Check stencil transfer and hidden joints on the first article. [Staged soldering guide](../assembly/e73-corner/soldering.md)

## Which mechanical files to send

| Item / net quantity | Delivery path | Manufacturing instructions |
|---|---|---|
| Top / 1 | `02-mechanical/top.step` or `top.stl` | Fully post-cured tough engineering SLA resin; millimetres; 100% scale |
| M05 lower shell and access covers / three parts, one each | [M05 print files and cover hardware](e73-m05-prototype.md) | Tough engineering SLA resin, millimetres, 100% scale. Use the matched M05 harness and retainers |
| Plate / 1 | `02-mechanical/steel-plate.dxf` | **304 stainless steel**, CAD nominal 1.60 mm, finished 1.55–1.60 mm; machine and deburr functional openings; not a PCB or resin print |
| Plate trial-fit coupon / 1 before the full plate | [Coupon DXF](../../delivery/YETI60-E73/02-mechanical/plate-fit-coupon.dxf) | 120 × 64 mm, same 304 stock, finished thickness and machining as the full plate. [Fit checks](key-mechanism.md#trial-fit-coupon) |
| Standoffs / 28 | `02-mechanical/standoff.step`, `assembly-spec.json` | Machined brass, OD3.5, 4.50 ±0.03 mm shoulder; top M2×0.4 stud 1.0 mm, bottom M1.6×0.35 internal thread depth 3.2 mm; model alone does not specify qualified threads |
| M05 cable guides / 16 rigid parts and 17 cut films | [Print checklist and placement](e73-m05-prototype.md) | Use 14 shared rigid parts plus two M05 battery guides and the M05 wire cut list |

Use STEP as the dimension reference; STL is a mesh export in the same millimetre coordinates. Do not rescale the FELK60 shell or add an arbitrary shrinkage percentage. Agree on the supplier's process compensation and verify the finished dimensions. Orient/support the resin parts so mating ledges, insert bores and cable channels remain dimensionally controlled; clean and post-cure before finishing bores. Printed threads are not substitutes for the specified brass inserts or machined standoff threads.

The project case coordinate tolerance is ±0.15 mm per axis; a print supplier must demonstrate it at the functional datums, not only at the outer bounding box. Plate opening corners, finished thickness and actual NiZ/stabilizer retention require a local sample. Fit without force.

## Finish and inspect before electronics

- Shell closure: four cold-bonded M3×0.5 knurled inserts, OD4.6 × length3.0 mm; finished bore Ø4.85 ±0.05 mm, depth3.5 mm. Use four M3×5 screws with 0.30 mm shim washers and confirm actual head clearance/engagement.
- Daughterboard: four cold-bonded M2×0.4 inserts, OD3.2 × length2.5 mm; finished bore Ø3.35 ±0.05 mm, depth2.9 mm. Use four M2×4 screws with 0.30 mm insulating washers. Preserve the existing C5 mounting rectangle 14 ×12.5 mm.
- Do not heat-insert into thermoset resin. Follow the insert adhesive's cure requirements and keep adhesive out of the threads and electronics.
- Plate: preserve all 60 sensing centres and 28 mounting axes. The mount circles are **M2×0.4 machining/tapping datums**, not generic clearance holes. H26 is unused and receives no standoff, film, washer or screw.
- Stack: 4.50 mm shoulders plus 0.10 mm polyimide top insulation give nominal 4.60 mm plate-to-PCB gap. Use 28 PEEK washers, OD≤4.0 / ID2.2 / thickness0.8 mm, and 28 M1.6×5 PCB screws.
- Gaskets: lower stock **2.0 mm**, upper stock **1.2 mm**. Do not reuse the historical 2 mm upper gasket. Inspect actual compression and mechanism preload.
- Inspect shell ledges/registration, every bore/axis, USB opening, switch access, battery pocket and cable exits. Resin surface finish or a plausible render does not establish fit.

Detailed mechanism and sample checks: [NiZ / plate stabilizer guide](key-mechanism.md). Complete purchased materials: [materials and stock](../../README.md). Battery: [pack requirements](../engineering/battery-pack-specification.md). Soldering begins with the [blank-PCB inspection](../assembly/e73-corner/soldering.md).
