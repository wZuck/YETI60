English | [Chinese](ordering-and-printing.zh-CN.md)

# E73 PCB and mechanical manufacturing instructions

**Engineering review only.** These are the intended ordinary-process parameters for the current corner PCB. Consult [start here](../START-HERE.md) and the snapshot manifest before ordering. A Gerber review archive exists; final manufacture acceptance remains open.

## PCB order

| Item | Selection / requirement |
|---|---|
| Mainboard count | Install 1 per keyboard; fabrication quantity is the factory minimum or your chosen spare count |
| Daughterboard count | **0 new boards for this build**; retain the already-made UDB C5 JSH |
| Mainboard source | [Current native PCB](source/EC60-nRF52840.kicad_pcb); the delivery folder contains the matching Gerber/drill ZIP |
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
| Stencil | Front **and** back paste layers: E73 is on front; the other fitted components are on back. Hidden module lands require an inspected reflow/stencil process |

Use the [matching Gerber and drill ZIP](YETI60-E73-gerbers-REVIEW.zip) for the factory preview. Verify the outline, four copper layers, slots, non-plated holes, sensing geometry and mask openings before accepting the quotation. Stop if it imports as two layers or the factory proposes changing the specified geometry/process. The exported position file contains 75 fitted parts; sensing electrodes, mounting holes and pogo pads are not purchased components.

The [fabrication ZIP audit](../06-validation/cam-ordinary.json) matches the 285.0 × 94.6 mm closed profile to all 40 source segments and arcs. It also matches 852 through-via drill hits and their land flashes on each copper layer, one plated round mounting hole, two plated 2.20 × 5.00 mm slots and 30 non-plated holes. The smallest routed via drill is 0.30 mm and the tightest nominal via-hole edge gap is 0.358 mm.

JLC ordinary-process references: [capabilities](https://jlcpcb.com/capabilities/pcb-capabilities/) and [stack-ups](https://jlcpcb.com/impedance). Availability/options must be checked against the actual quotation. Neither this document nor a clean DRC is a factory DFM approval.

CORNER-07 changes the U5, U6, C42 and SW1 apertures and relocates the D2 ground via. The complete ZIP has a 0.230 mm minimum nominal drill-to-opening gap. A conservative drill-position and finished-hole-size screen leaves at least 0.059 mm for other relative shifts. Ask the factory to confirm mask registration and the U5 and U6 mask islands for its ordinary process. [Artwork measurements](../06-validation/aperture-review.md) · [JLCPCB drill tolerances](https://jlcpcb.com/capabilities/Capabilities)

## Which mechanical files to send

| Item / net quantity | Delivery path | Manufacturing instructions |
|---|---|---|
| Top / 1 | `02-mechanical/top.step` or `top.stl` | Fully post-cured tough engineering SLA resin; millimetres; 100% scale |
| M05 lower shell and access covers / three parts, one each | [M05 print files and cover hardware](../02-mechanical/service-case-m05/print-guide.md) | Tough engineering SLA resin, millimetres, 100% scale. Use the matched M05 harness and retainers |
| Plate / 1 | `02-mechanical/steel-plate.dxf` | **304 stainless steel**, CAD nominal 1.60 mm, finished 1.55–1.60 mm; machine and deburr functional openings; not a PCB or resin print |
| Standoffs / 28 | `02-mechanical/standoff.step`, `assembly-spec.json` | Machined brass, OD3.5, 4.50 ±0.03 mm shoulder; top M2×0.4 stud 1.0 mm, bottom M1.6×0.35 internal thread depth 3.2 mm; model alone does not specify qualified threads |
| M05 cable guides / 16 rigid parts and 17 cut films | [Print checklist and placement](../02-mechanical/service-case-m05/print-guide.md) | Use 14 shared rigid parts plus two M05 battery guides and the M05 wire cut list |

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

Detailed mechanism and sample checks: [NiZ / plate stabilizer guide](../04-assembly/key-mechanism.md). Complete purchased materials: [materials and stock](../03-bom/materials.md). Battery: [pack requirements](../03-bom/battery-requirements.md). Soldering begins with the [blank-PCB inspection](../04-assembly/soldering.md).
