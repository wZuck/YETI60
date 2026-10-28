English | [Chinese](battery-study.zh-CN.md)

# Bottom-case recess and larger battery feasibility

**An interior recess can accommodate a 60×36×6.2 mm complete-pack design envelope without changing the FELK60 exterior envelope. It does not make a 1000 mAh pack electrically interchangeable with the current 200 mAh pack.** The current charger setting and safety timer require a separate large-pack electrical revision; see [power and charging calculation](power-budget.md).

![Optional recess, source coordinates and section](images/battery-pocket.png)

## Geometry and reproducible calculation

The source is the derived tough-resin bottom STEP with bonded inserts and switch access, in the original FELK60 coordinates (X right, Y negative toward the typist, Z upward). Current PCB bottom is z=−2.00. The exterior union remains **325.700×125.200×31.190 mm**. This is one checked candidate location, not a global proof of the largest possible pack.

| Quantity | Checked value |
|---|---|
| Pack maximum complete envelope | 60.0×36.0×6.2 mm |
| Pack bounds | X 240.0…300.0; Y −142.0…−106.0; Z −10.8…−4.6 mm |
| Recess bounds | X 239.25…300.75; Y −142.75…−105.25 mm |
| Recess floor / original inner floor | z=−11.00 / −5.91 mm; local depth 5.09 mm |
| Recess corner radius | 1.00 mm |
| Removed solid volume | 11734.443 mm³, approximately 11.734 cm³ |
| Minimum wall normal to sloping exterior bottom | 3.452489 mm |
| Wall after 0.30 mm manufacturing allowance | 3.152489 mm; exceeds the **chosen** 3.0 mm geometric design floor |
| Nominal gap to conservative PCB fastener envelope | 0.700 mm |
| Floor retention / gap budget | 0.200 mm; include actual tape and isolation thickness |
| Nominal and XY-expanded pack overlap with shells | 0 mm³; XY expansion ±0.40 mm includes ±0.25 pack placement and ±0.15 case allowance |
| Component-envelope and protected insert conflicts | None in the checked source |
| Resulting bottom solid | One valid BRep solid; original exterior bounding coordinates retained |

The original underside is a plane at the 7° typing angle: floor thickness decreases toward the front. Vertical ray checks showed approximately 11.98 mm at Y=−115, 8.91 mm at −140 and 4.00 mm at −180. This is why moving the pocket to the rear is preferable to uniformly thinning the front floor.

The validation uses the **exact minimum BRep distance** from a conservative rectangle covering the new floor to the original large sloping exterior underside face. This covers the full floor area and its corners, rather than relying only on grid samples. For that plane:

```text
z_outer(x,y) = z0 − [nx(x−x0)+ny(y−y0)]/nz
vertical wall = z_floor − z_outer
normal wall = vertical wall × cos(7°)
worst-case wall = minimum normal wall − 0.30 mm
```

The report records the actual plane normal/location and exact BRep distance. The rounded pocket also clears the full rectangular pack with XY manufacturing/placement allowances. The 0.70 mm fastener gap has an illustrative remaining vertical budget of `0.70−0.15(case floor)−0.05(retention)−0.15(PCB stack)−0.10(head)=0.25 mm`; these are imposed manufacturing requirements, not measured supplier tolerances. Final hardware must satisfy them. The unchanged near-module and daughterboard regions are not cut.

Run with the pinned CAD runtime: `python scripts/study_yeti60_battery_pocket.py`. The editable [study specification](../../mechanical/battery-pocket-study.json), [optional STEP](../../mechanical/generated/yeti60-bottom-battery-pocket.step) and [audit](../audit/yeti60-battery-pocket.json) are separate from the baseline bottom. Regenerate the baseline assembly report first if PCB geometry changes.

## Capacity evidence and pack construction

[Honcell HCP-503450, 2024 bare-cell sheet](https://www.honcell.com/Public/Uploads/uploadfile/files/20241220/DATASHEETHCP5034503.7V1000mAhCELL2024.pdf) specifies minimum 1000 mAh at 0.2C/23±2°C, nominal 3.7 V, body maximum 50×34 mm excluding tabs, thickness maximum 5.0 mm delivered / 5.4 mm after cycling, 4.2 V charge termination and 3.0 V discharge cutoff. The standard charge row is 200 mA over 0…45°C; the higher maximum-current row has a different temperature condition. These are cell specifications, not an assembled pack approval.

The proposed **60×36×6.2 mm** budget adds room for folded connections, PCM, independent charge-temperature protection, NTC and wrapping. That allocation is an engineering requirement, not a manufacturer drawing. The assembler must verify tab bend limits, weld insulation, protection/NTC thickness, after-cycle growth and capacity, and sign the final complete-pack drawing. A generic two-wire “503450” pack is not a substitute for the custom three-wire polarity/thermal contract.

Do not scale capacity from cavity volume or infer capacity from the six-digit size code. The existing 200 mAh/2.9 mm pack is itself a supplier-unqualified custom design target. The 1000 mAh value has a published cell minimum, but finished-pack qualification and electrical compatibility remain separate gates.

## Reference designs and decision

| Reference | Relevant idea | Not transferable |
|---|---|---|
| FELK60, pinned source `624e6a7` | Keep outside dimensions, plate and gasket registration; alter only the selected internal floor region | Original metal-thread pilots do not qualify resin inserts |
| DELTA OMEGA, inspected `64db818` | Separate battery, insulation, fasteners and keycap clearance in the BOM | Its split MX geometry and battery envelope do not fit this case by assumption |
| [PH60 Rev.3](https://github.com/ph-design/PH60) | Purpose-designed removable battery tray; README lists up to 100×50×5 mm | Different case/PCB; its allowance and runtime do not validate this recess |

Use the **baseline bottom + 200 mAh electrical configuration** for the currently frozen P1 design. Keep the larger recess as a manufactured-prototype option for the next electrical revision. Do not enlarge the external shell or silently replace the baseline pack. A compliant removable cradle or adhesive arrangement must respect the 0.2 mm floor budget, avoid pouch pressure and protect cable exits. Complete wire routing, actual resin strength/creep, vibration/drop behavior, insert pullout and physical pack acceptance are still required; the selected 3 mm wall criterion is a geometric engineering target, not a resin strength certification.
