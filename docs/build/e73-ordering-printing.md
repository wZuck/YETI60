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
| Bare-board electrical test | Ask the factory to use the included [IPC-D-356A netlist](../../delivery/YETI60-E73/01-pcb/gerbers/EC60-nRF52840.d356) for CAM comparison and confirm open/short testing |
| Impedance | Preserve geometry and selected stack; USB signal integrity is not qualified by choosing an impedance option alone |
| Assembly service | This guide assumes self-soldering; placement CSV is a reference, not an approved turnkey JLC assembly order |
| Stencil | One front and one back stencil, both **0.12 mm** standard laser-cut stainless steel. See the selections below |

Use the [matching Gerber and drill ZIP](../../delivery/YETI60-E73/01-pcb/YETI60-E73-gerbers-REVIEW.zip) for the factory preview. Verify the outline, four copper layers, slots, non-plated holes, sensing geometry and mask openings before accepting the quotation. Stop if it imports as two layers or the factory proposes changing the specified geometry/process. The exported position file contains 75 fitted parts; sensing electrodes, mounting holes and pogo pads are not purchased components.

The [fabrication ZIP audit](../../delivery/YETI60-E73/06-validation/cam-ordinary.json) matches the 285.0 × 94.6 mm closed profile to all 40 source segments and arcs. It also matches 852 through-via drill hits and their land flashes on each copper layer, one plated round mounting hole, two plated 2.20 × 5.00 mm slots and 30 non-plated holes. The smallest routed via drill is 0.30 mm and the tightest nominal via-hole edge gap is 0.358 mm.

The same ZIP includes the IPC-D-356A reference. The audit matches all **1,457 records** to the native PCB, including 852 vias, 572 surface pad records, three plated component records and 30 non-plated holes. The legacy inch coordinates use the same origin and orientation as the Gerbers and drills. Maximum coordinate readback error is 0.001261 mm per axis. The factory chooses probe points based on actual accessibility and confirms test coverage, including how it handles tented vias and EC electrodes. [JLCPCB guidance on netlists and fabrication files](https://jlcpcb.com/blog/prepare-perfect-gerber-files)

The copper readback also matches **4,722 trace segments and arcs** by layer, width, position and net, plus **584 flashed lands** by layer, position, reference and net. Each of the 852 via lands on each layer matches its native net. Confirm filled copper, pad contours and resulting connectivity in the factory CAM review.

JLC ordinary-process references: [capabilities](https://jlcpcb.com/capabilities/pcb-capabilities/) and [stack-ups](https://jlcpcb.com/impedance). Availability/options must be checked against the actual quotation. Neither this document nor a clean DRC is a factory DFM approval.

CORNER-07 changes the U5, U6, C42 and SW1 apertures and relocates the D2 ground via. The complete ZIP has a 0.230 mm minimum nominal drill-to-opening gap. A conservative drill-position and finished-hole-size screen leaves at least 0.0587 mm for other relative shifts. Ask the factory to confirm mask registration and the U5 and U6 mask islands for its ordinary process. [Artwork measurements](../engineering/e73-aperture-review.md) · [JLCPCB drill tolerances](https://jlcpcb.com/capabilities/Capabilities)

## Stencil order

Upload the [CORNER-07 stencil ZIP](../../delivery/YETI60-E73/01-pcb/YETI60-E73-stencils-REVIEW.zip) as a separate **SMT Stencil** order. Leave the PCB form’s bundled stencil option off and use the Gerber and drill ZIP from the PCB section for the board order. The stencil ZIP contains the front paste for U1, the back paste for fitted parts and the outline for alignment. It omits the two paste openings at JP1 so the jumper stays open. Select a single board pattern per sheet. [JLCPCB stencil ordering](https://jlcpcb.com/help/article/how-to-order-a-stencil)

| Setting | Selection |
|---|---|
| Type and quantity | 304 stainless paste stencil, frameless. Select Top + Bottom on Separate Stencils, one sheet per side. If the form has separate items, select Top Only and Bottom Only once each |
| Sheet size | Standard 380 × 280 mm, custom size off. Verify at least 285.0 × 94.6 mm usable area on each sheet. JLCPCB lists 290 × 190 mm for this model |
| Thickness | Select by customer, **0.12 mm** on each sheet |
| Fiducials and finish | No fiducials, standard finish and no nano-coating |
| Orientation | One board per sheet, long edge parallel to the sheet's long edge. Review side and orientation in the cutting preview |

Copy into the stencil remarks.

> YETI60 E73 CORNER-07. Cut the supplied paste layers 1:1 and preserve the aperture shapes and split windows. Use Edge.Cuts for alignment only. Keep JP1 and J3 uncut. Please send a cutting preview identifying the two sides before cutting.

The area ratio is opening area ÷ (opening perimeter × foil thickness). The table uses the union of the actual Gerber shapes, so each physical cut is counted once. TI's QFN/SON guidance provides the 0.66 engineering screen. [Gerber geometry report](../../delivery/YETI60-E73/06-validation/cam-apertures.json) · [TI assembly note, §4.3](https://www.ti.com/lit/an/slua271c/slua271c.pdf) · [JLCPCB stencil capabilities](https://jlcpcb.com/capabilities/pcb-stencil-manufacturing)

| Side | Cuts | Min. ratio at 0.12 mm | Cuts below 0.66 at 0.12 / 0.15 mm |
|---|---:|---:|---:|
| Front, U1 only | 43 | 2.000 | 0 / 0 |
| Back, limiting opening at U5 | 234 | 0.742 | 0 / 16 |

Dry-align before printing. Match the front openings to U1 at the right-hand corner as viewed from the key side. For the back, turn the real PCB over and match J4, U5 and SW1 at three separated locations. Confirm the stencil leaves JP1 and the J3 pogo pads clear. Print the back for the first power stage. When printing U1 later, support the board so the populated back stays clear of the fixture. Check stencil transfer and hidden joints on the first article. [Staged soldering guide](../assembly/e73-corner/soldering.md)

## Steel plate and brass standoffs

| Item / net quantity | Delivery path | Manufacturing instructions |
|---|---|---|
| Plate / 1 | [`02-mechanical/steel-plate.dxf`](../../delivery/YETI60-E73/02-mechanical/steel-plate.dxf) | **304 stainless steel**, CAD nominal 1.60 mm, finished 1.55–1.60 mm; machine and deburr functional openings; not a PCB or resin print |
| Plate trial-fit coupon / 1 before the full plate | [Coupon DXF](../../delivery/YETI60-E73/02-mechanical/plate-fit-coupon.dxf) | 120 × 64 mm, same 304 stock, finished thickness and machining as the full plate. [Fit checks](key-mechanism.md#trial-fit-coupon) |
| Standoffs / 28 | [`02-mechanical/standoff.step`](../../delivery/YETI60-E73/02-mechanical/standoff.step), [`assembly-spec.json`](../../delivery/YETI60-E73/02-mechanical/assembly-spec.json) | Machined brass, OD3.5, 4.50 ±0.03 mm shoulder; top M2×0.4 stud 1.0 mm, bottom M1.6×0.35 internal thread depth 3.2 mm; model alone does not specify qualified threads |

Use STEP as the dimension reference; STL is a mesh export in the same millimetre coordinates. Do not rescale the FELK60 shell or add an arbitrary shrinkage percentage. Agree on the supplier's process compensation and verify the finished dimensions. Orient/support the resin parts so mating ledges, insert bores and cable channels remain dimensionally controlled; clean and post-cure before finishing bores. Printed threads are not substitutes for the specified brass inserts or machined standoff threads.

The project case coordinate tolerance is ±0.15 mm per axis at the functional datums. Use the [SLA quotation and receiving checks](e73-m05-prototype.md#resin-printing-tolerance-and-receiving-inspection) for all four shell pieces and the installed C5. Plate opening corners, finished thickness and NiZ/stabilizer retention require a local sample. Fit without force.

## M05 relieved trial STL upload list

For the M05 relieved trial, quote one copy of each of the seven mandatory STL files below as separate items in tough engineering SLA resin at **100% scale in millimetres**. For the first article, print the front guide carrier and separate floor coupon first. Confirm the fit before ordering the full bottom. Keep the relieved bottom, enlarged front guides and relieved wire lengths together as one set. The standard M05 uses its own bottom, retainers and wire lengths. [Standard M05 setup and relieved trial sequence](e73-m05-prototype.md)

| Category | Direct STL upload link | Quantity per STL | Units / scale | Mode / yield |
|---|---|---:|---|---|
| Shell model (1 of 4) | [`02-mechanical/top.stl`](../../delivery/YETI60-E73/02-mechanical/top.stl) | 1 | `mm` / 100% | Separate file; top shell |
| Shell model (2 of 4) | [`02-mechanical/service-case-m05/relieved-trial/bottom-m05-relieved-REVIEW.stl`](../../delivery/YETI60-E73/02-mechanical/service-case-m05/relieved-trial/bottom-m05-relieved-REVIEW.stl) | 1 | `mm` / 100% | Separate file; M05 relieved-trial lower shell |
| Shell model (3 of 4) | [`02-mechanical/service-case-m05/cover-J2-REVIEW.stl`](../../delivery/YETI60-E73/02-mechanical/service-case-m05/cover-J2-REVIEW.stl) | 1 | `mm` / 100% | Separate file; J2 access cover |
| Shell model (4 of 4) | [`02-mechanical/service-case-m05/cover-J4-REVIEW.stl`](../../delivery/YETI60-E73/02-mechanical/service-case-m05/cover-J4-REVIEW.stl) | 1 | `mm` / 100% | Separate file; J4 access cover |
| Guide carrier (1 of 3) | [`02-mechanical/front-retainer-coupon/M05-front-guides-SLA-COUPON.stl`](../../delivery/YETI60-E73/02-mechanical/front-retainer-coupon/M05-front-guides-SLA-COUPON.stl) | 1 | `mm` / 100% | Separate file; yields **4** guides |
| Guide carrier (2 of 3) | [`02-mechanical/retained-guide-blanks/M05-case-guides-SLA-BLANKS.stl`](../../delivery/YETI60-E73/02-mechanical/retained-guide-blanks/M05-case-guides-SLA-BLANKS.stl) | 1 | `mm` / 100% | Separate file; yields **5** guides |
| Guide carrier (3 of 3) | [`02-mechanical/retained-guide-blanks/M05-power-guides-SLA-BLANKS.stl`](../../delivery/YETI60-E73/02-mechanical/retained-guide-blanks/M05-power-guides-SLA-BLANKS.stl) | 1 | `mm` / 100% | Separate file; yields **7** guides |
| Separate pilot floor coupon | [`02-mechanical/front-retainer-coupon/M05-front-floor-SLA-COUPON.stl`](../../delivery/YETI60-E73/02-mechanical/front-retainer-coupon/M05-front-floor-SLA-COUPON.stl) | 1 for pilot | `mm` / 100% | First-article guide-seat fit check |

- Use the relieved-trial wire lengths to make the nine conductors. [`02-mechanical/service-case-m05/relieved-trial/wire-lengths-relieved.csv`](../../delivery/YETI60-E73/02-mechanical/service-case-m05/relieved-trial/wire-lengths-relieved.csv)
- Fully post-cure before finishing the bores. Finish all three carriers and test fit the isolated harness before installing electronics. Standard SLA tolerances do not guarantee the project’s ±0.15 mm functional datum tolerance. Confirm post-cure measurements and any finishing work with the supplier. [Carrier cut maps and finishing](../engineering/e73-retention.md#sla-coupons-for-the-enlarged-usb-front-guides)

For the dry fit, also prepare the inert 85.00 × 43.00 × 4.80 mm pack gauge, extraction tools and parking supports. These fixtures are for measuring fit and the 25 mm deck lift. [Gauge model](e73-m05-prototype.md#inert-battery-fit-gauge) · [Service tools](e73-m05-service-tool.md) · [Parking supports](e73-m05-parking-support.md)

## Finish and inspect before electronics

- Shell closure: four cold-bonded M3×0.5 knurled inserts, OD4.6 × length3.0 mm; finished bore Ø4.85 ±0.05 mm, depth3.5 mm. Use four M3×5 screws with 0.30 mm shim washers and confirm actual head clearance/engagement.
- Daughterboard: four cold-bonded M2×0.4 inserts, OD3.2 × length2.5 mm; finished bore Ø3.35 ±0.05 mm, depth2.9 mm. Use four M2×4 screws with 0.30 mm insulating washers. Preserve the existing C5 mounting rectangle 14 ×12.5 mm.
- Do not heat-insert into thermoset resin. Follow the insert adhesive's cure requirements and keep adhesive out of the threads and electronics.
- Plate: preserve all 60 sensing centres and 28 mounting axes. The mount circles are **M2×0.4 machining/tapping datums**, not generic clearance holes. H26 is unused and receives no standoff, film, washer or screw.
- Stack: 4.50 mm shoulders plus 0.10 mm polyimide top insulation give nominal 4.60 mm plate-to-PCB gap. Use 28 PEEK washers, OD≤4.0 / ID2.2 / thickness0.8 mm, and 28 M1.6×5 PCB screws.
- Gaskets: lower stock **2.0 mm**, upper stock **1.2 mm**. Do not reuse the historical 2 mm upper gasket. Inspect actual compression and mechanism preload.
- Inspect shell ledges/registration, every bore/axis, USB opening, switch access, battery pocket and cable exits. Resin surface finish or a plausible render does not establish fit.

Detailed mechanism and sample checks: [NiZ / plate stabilizer guide](key-mechanism.md). Complete purchased materials: [materials and stock](../../README.md). Battery: [pack requirements](../engineering/battery-pack-specification.md). Soldering begins with the [blank-PCB inspection](../assembly/e73-corner/soldering.md).
