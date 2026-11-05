English | [Chinese](TOLERANCES.zh-CN.md)

# Shell tolerance findings and repair requirements

**Pre-C04 baseline diagnostic.** The table below records why the previous plate and switch-floor geometry needed repair. The [current C04 plate, floor pocket and bounded fit results](MECHANICAL-FIT.md) supersede these three baseline deficits. Full keyboard/physical qualification remains open; the [open-bench first-board sequence](FIRST-ARTICLE.md) is available.

[Measured evidence](audit/tolerance-diagnostic.json) · [Reproduce the CAD diagnostic](../../scripts/study_usb_short_tolerances.py) · [Service path](SERVICE-PATH.md)

## Measured limiting interfaces

The diagnostic rebuilds the plate's outer side surface from the actual plate DXF at the installed 4.2062–5.8062 mm Z range, then measures its distance to each shell STEP independently. It checks the lower-shell result against the complete nominal extraction evidence. This perimeter measurement excludes internal key and fastener openings; it does not replace the complete plate check. SW100's floor distance and nearest points come from the complete extraction report.

| Interface | Nominal gap | Quantified allowance subtotal | Optimistic residual | Additional clearance needed for 0.15 mm reserve, **before unknown terms** |
|---|---:|---:|---:|---:|
| Plate locating ears / upper shell | 0.2500 mm | 0.1500 mm wall + 0.0020 mm chord | 0.0980 mm | ≥0.0520 mm |
| Plate locating ears / lower shell | 0.2500 mm | 0.1500 mm wall + 0.0020 mm chord | 0.0980 mm | ≥0.0520 mm |
| SW100 / lower-shell floor | 0.4100 mm | 0.3538 mm | 0.0562 mm | ≥0.0938 mm |

These residuals are **optimistic directional subtotals**, not completed worst-case stacks. The 0.15 mm reserve is a project design target, not a manufacturer or IPC guarantee. Even with a 0.10 mm reserve, SW100's subtotal is insufficient. A reserve deficit does not by itself prove that parts will physically collide.

The limiting plate-ear walls occur in **both shells**. Representative nearest pairs are near X 307.2877/307.5377, Y −200.8097, Z 4.79 mm. Editing only the lower-shell RF-wing relief cannot resolve the upper-shell limit.

## Calculation and remaining terms

Use a directional arithmetic sum for each particular interface; do not use statistical RSS to guarantee that independently allowed worst cases fit. Values below come from the [assembly specification](../../mechanical/assembly-spec.raytac.json) and [ordinary PCB fabrication profile](../../mechanical/pcb-fabrication-spec.json).

The CAD perimeter uses a 0.002 mm chord-error bound, also present in the assembly report; this consumes clearance as well as manufacturing errors. For the locating ears, `0.25 − 0.15 − 0.002 = 0.098 mm` before adding plate outer-cut size/position error, installed plate XY translation/rotation, and gasket compliance. The exact plate tolerance and installed position limits have not been qualified. They cannot be silently set to zero. The 0.15 mm case deviation is applied toward the local limiting wall; it is not asserted to be a bound for arbitrary three-dimensional shrinkage.

For SW100, keep the plate nominally fixed while increasing the finished PCB thickness: the board's underside moves down. The CAD finished envelope is **1.6062 mm**, while the ordinary upper acceptance limit is **1.76 mm**. Therefore:

```text
PCB downward growth = 1.76 − 1.6062 = 0.1538 mm
known allowance subtotal = 0.1538 + 0.03 shoulder + 0.02 film + 0.15 floor
                         = 0.3538 mm
optimistic remaining gap = 0.4100 − 0.3538 = 0.0562 mm
```

Do not replace 1.6062 with rounded 1.6 in this calculation. The 0.03 mm shoulder and 0.02 mm insulating-film tolerances must be added even though nominal installed gap is 4.6 mm; do not add the separate 0.05 mm stack allowance again for the same two terms.

Unquantified SW100 terms include installed plate Z/gasket variation, board warpage, switch installed height and solder standoff. The existing 3.5 mm switch envelope is provisional. The [C&K JS102011SAQN manufacturer drawing, page 4](https://www.littelfuse.com/assetdocs/littelfuse-c-k-slide-js-series-datasheet?assetguid=aba42b08-0d2c-423b-813d-a2faa5a3bb14#page=4) gives nominal dimensions; it does not establish a qualified maximum installed height for this assembly. Do not shrink the envelope or declare the height allowance zero based on a nominal drawing.

## Required repair and acceptance sequence

1. Agree measurable plate outer-profile and installed XY/Z limits with the plate/case suppliers. Include rotation at the furthest locating ear, board warpage, solder standoff and gasket compression; inspect these after assembly.
2. Revise **both shells** at the locating-ear side walls, or revise the plate registration features while preserving key and fastener centers. Required extra side clearance is at least `0.052 mm + plate/profile/installed-position terms`. Preserve the gasket bearing surfaces, insert support and original FELK60 exterior. A 0.052 mm cut alone is not a complete repair.
3. Relieve the SW100 floor or alter the stack using a fully recalculated design. A smaller switch envelope is an alternative only when guaranteed maximum part dimensions and bounded installed solder/actuator geometry justify it; recalculate the whole budget. Required extra floor clearance with the current envelope is at least `0.0938 mm + downward plate-position/installed-height/warpage terms`. Verify local exterior skin, the existing access port and screw supports. This retained baseline diagnostic does not contain the repaired floor STEP; use the current MECHANICAL-FIT entry.
4. Rebuild case/plate outputs, continuous extraction, all component/hardware/harness checks, and drawings/renders from the repaired geometry. Repeat full tolerance analysis at the approved limits, including the purchased NiZ/stabilizer/keycap parts and connected plug service paths.
5. Measure a first article. CAD clearance does not demonstrate resin strength, adhesive retention, wire springback or full key travel.

Until those steps pass, use the current PCB and battery only in the documented insulated open fixture. Supplier pack confirmation is still required before connecting the real battery. The PCB/USB/firmware design and generated Gerbers are unchanged by this diagnostic.
