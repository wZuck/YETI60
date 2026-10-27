# 机械审查副本

`felk60_plate_hhkb.audited.dxf` 来自 fredlb/FELK60 原定位板 DXF。仅修复三处 DXF 字典 owner handle 元数据；逐实体核对圆、折线、圆弧凸度及层名，几何数值在 1e-9 mm 比较精度内保持一致。

它是二维定位板加工参考，FELK60 原说明要求 **1.2 mm 定位板，优先不锈钢**，不等于树脂打印的定位板或已批准生产的壳体。螺纹、孔位公差、开口与轴体间隙、gasket 压缩量、外壳嵌件和整机干涉仍需验证。

本目录尚无已核准的树脂外壳 STL。不要将原 STEP 直接视为已经适配嵌件、收缩率和打印支撑的最终文件。

原上下壳的有效实体、四组固定孔注册、零实体交集及后侧中央 USB 通路已完成局部检查，结果在 `docs/audit/mechanical.json` 和 `case-assembly.json`。原上盖金属攻丝底孔直径约 2.529 mm，树脂嵌件孔仍需改版。后侧开口不能直接与 EC60 偏左的板载 USB1 对接，必须保留后侧 USB 子板路径。

重建检查：先更新 `docs/audit/pcb-metadata.json`，再运行 `uv run --with ezdxf python scripts/check_plate.py`。具体来源哈希、孔位匹配和检查范围见 `docs/audit/plate.json`。
