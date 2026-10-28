[英文](README.md) | 简体中文

# YETI60 机械检查

`felk60_plate_hhkb.audited.dxf` 来自 fredlb/FELK60。只修复三处 DXF 字典所有者句柄；圆、折线、圆弧凸度和图层几何在记录的 1e-9 毫米比较精度内不变。

FELK60 要求 **1.2 毫米定位板，优先不锈钢**，以及约 2 毫米厚、压缩 50% 的垫片。这不是树脂定位板规格。原上盖 M3 底孔约 2.529 毫米；当前派生设计改为冷粘嵌件座，见装配规范。

当前[装配报告](../docs/audit/yeti60-assembly.json)使用明确暂定的 PCB 至定位板间距，检查当前 PCB 与原始壳体、定位板几何。原生 STEP 基材厚度与声明的含铜、阻焊成品厚度分别记录。见[全面复查](../docs/audit/yeti60-comprehensive-review.zh-CN.md)和[装配渲染](../renders/yeti60-assembly/README.zh-CN.md)。

尚无获准生产的树脂 STL、选定嵌件、树脂收缩余量、合格轴体与胶碗堆叠、最终电池或完整后侧 USB 线缆及插头装配。

运行 `python3 scripts/run_audit.py` 导出当前 PCB 元数据、只读核对定位板几何、检查条件装配及渲染几何。发现 PCB、定位板、元件包络或电池候选包络碰撞时验证失败。依赖固定在 `requirements-audit.txt`。

渲染保持 FELK60 原始壳体尺寸：原始 CAD 坐标系中，上下壳联合包围尺寸为 325.700 × 125.200 × 31.190 毫米。网格线性离散偏差为 0.015 毫米，包围坐标差值检查小于 0.02 毫米。7° 展示旋转为刚性变换，不改变外壳尺寸。见[渲染几何验证](../docs/audit/yeti60-render-geometry.json)。

当前[工程装配图及步骤](../docs/engineering/assembly.zh-CN.md)与[可选电池下挖研究](../docs/engineering/battery-study.zh-CN.md)分别保存。后者通过完整 60×36×6.2 mm 包络及壁厚检查，但大电池充电电路尚需独立改版，不能替换基准 200 mAh 配置。
