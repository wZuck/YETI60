English | [Chinese](README.zh-CN.md)

# YETI60 mechanical studies

`felk60_plate_hhkb.audited.dxf` is derived from fredlb/FELK60. Only three DXF dictionary owner handles were repaired; circles, polylines, arc bulges and layer geometry remain unchanged to the recorded 1e-9 mm comparison precision.

FELK60 specifies a **1.2 mm, preferably stainless-steel plate** and approximately 2 mm gaskets at 50% compression. This is not a resin plate specification. Original top-case M3 pilots are approximately 2.529 mm; the derived resin case now uses specified cold-bonded insert seats.

The current [assembly report](../docs/audit/yeti60-assembly.json) evaluates the current PCB and source case/plate geometry using an explicit, provisional PCB-to-plate gap. Native STEP substrate thickness and declared finished copper/mask thickness are kept distinct. See the [comprehensive review](../docs/audit/yeti60-comprehensive-review.md) and [assembled renders](../renders/yeti60-assembly/README.md).

No production-ready resin STL, chosen insert, resin shrinkage allowance, qualified switch/dome stack, final battery or complete rear USB cable/plug assembly is approved.

Run `python3 scripts/run_audit.py` to export current PCB metadata, verify plate geometry without modifying the DXF, check conditional assembly fit and validate render geometry. Detected PCB, plate, component-envelope or battery-candidate collisions fail validation. Dependencies are pinned in `requirements-audit.txt`.

The render pipeline preserves the original FELK60 case solids at their source size: the combined case bounding box in the original CAD frame is 325.700 × 125.200 × 31.190 mm. Tessellation uses 0.015 mm linear deflection and checks bounding deviations below 0.02 mm. The 7° presentation transform is rigid; it does not resize the case. See [render geometry verification](../docs/audit/yeti60-render-geometry.json).

Current [engineering assembly sheets](../docs/engineering/assembly.md) and the [optional battery recess study](../docs/engineering/battery-study.md) are separate deliverables. The latter checks a complete 60×36×6.2 mm pack envelope and residual wall, but requires a separate larger-pack charging revision; it does not replace the baseline 200 mAh configuration.
