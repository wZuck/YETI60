English | [Chinese](README.zh-CN.md)

# YETI60 mechanical studies

`felk60_plate_hhkb.audited.dxf` is derived from fredlb/FELK60. Only three DXF dictionary owner handles were repaired; circles, polylines, arc bulges and layer geometry remain unchanged to the recorded 1e-9 mm comparison precision.

The upstream FELK60 baseline specified a 1.2 mm stainless plate. Both current YETI60 options select the **1.6 mm NiZ / plate-stabilizer plate**, with 28 mounting sets and H26 unused. Use lower 2.0 mm and upper 1.2 mm gasket stock; supplier compression and actual mechanism fit remain pending. See the [E73 specification](../docs/build/key-mechanism.md) and [Raytac specification](../variants/raytac/docs/build/key-mechanism.md). Original top-case M3 pilots are approximately 2.529 mm; the derived resin case now uses specified cold-bonded insert seats.

The current [assembly report](../docs/audit/yeti60-assembly.json) evaluates the current PCB and source case/plate geometry using an explicit, provisional PCB-to-plate gap. Native STEP substrate thickness and declared finished copper/mask thickness are kept distinct. See the [comprehensive review](../docs/audit/yeti60-comprehensive-review.md) and [assembled renders](../renders/yeti60-assembly/README.md).

No production-ready resin STL, chosen insert, resin shrinkage allowance, qualified switch/dome stack, final battery or complete rear USB cable/plug assembly is approved.

Run `python3 scripts/run_audit.py` to export current PCB metadata, verify plate geometry without modifying the DXF, check conditional assembly fit and validate render geometry. Detected PCB, plate, component-envelope or battery-candidate collisions fail validation. Dependencies are pinned in `requirements-audit.txt`.

The render pipeline preserves the original FELK60 case solids at their source size: the combined case bounding box in the original CAD frame is 325.700 × 125.200 × 31.190 mm. Tessellation uses 0.015 mm linear deflection and checks bounding deviations below 0.02 mm. The 7° presentation transform is rigid; it does not resize the case. See [render geometry verification](../docs/audit/yeti60-render-geometry.json).

Default P2 [engineering sheets](../docs/engineering/assembly.md) and [single-cell selection/recess design](../docs/engineering/battery-study.md) agree. E73 selects [`e73-fit/yeti60-e73-bottom-m01.step`](e73-fit/yeti60-e73-bottom-m01.step), derived from `generated/yeti60-bottom.step`, and adds the SW100 floor relief. Both include the 85×43×4.8 mm, 1600 mAh pack recess; the old optional bottom is removed. Independent pack thermal protection, supplier-signed drawings and physical acceptance remain procurement/production conditions.

E73 uses the [M01 inset plate and floor repair](../docs/engineering/e73-mechanical-fit-candidate.md); Raytac uses its independently checked C04 plate and short-USB shell. Do not mix the two assembly selections. The shared original NiZ DXF and generated base shells remain derivation inputs.
