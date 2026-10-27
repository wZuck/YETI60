English | [Chinese](README.zh-CN.md)

# YETI60 mechanical studies

`felk60_plate_hhkb.audited.dxf` is derived from fredlb/FELK60. Only three DXF dictionary owner handles were repaired; circles, polylines, arc bulges and layer geometry remain unchanged to the recorded 1e-9 mm comparison precision.

FELK60 specifies a **1.2 mm, preferably stainless-steel plate** and approximately 2 mm gaskets at 50% compression. This is not a resin plate specification. Original top-case M3 pilot holes are approximately 2.529 mm; they are not a completed resin-insert design.

The current [assembly report](../docs/audit/yeti60-assembly.json) evaluates the current PCB and source case/plate geometry using an explicit, provisional PCB-to-plate gap. Native STEP substrate thickness and declared finished copper/mask thickness are kept distinct. See the [comprehensive review](../docs/audit/yeti60-comprehensive-review.md) and [assembled renders](../renders/yeti60-assembly/README.md).

No production-ready resin STL, chosen insert, resin shrinkage allowance, qualified switch/dome stack, final battery or complete rear USB cable/plug assembly is approved.

Rebuild: run KiCad Python `scripts/export_yeti60_mechanical_metadata.py`, then a Python environment containing `requirements-audit.txt` to run `scripts/check_yeti60_assembly.py`. The older `check_plate.py`, `check_mechanical.py` and `check_case_assembly.py` preserve historical upstream checks.

The render pipeline preserves the original FELK60 case solids at their source size: the combined case bounding box in the original CAD frame is 325.700 × 125.200 × 31.190 mm. Tessellation uses 0.015 mm linear deflection and checks bounding deviations below 0.02 mm. The 7° presentation transform is rigid; it does not resize the case. See [render geometry verification](../docs/audit/yeti60-render-geometry.json).
