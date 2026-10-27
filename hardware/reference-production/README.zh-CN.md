[English](README.md) | 简体中文

# 上游 EC60 生产文件核查副本

`POS-EC60.corrected.csv` 对应未改版的上游 EC60 PCB，不对应新增蓝牙接口或最终蓝牙 PCB。

原坐标表把 OPA350 的位号误写为 U1，造成 U1 重复、U3 缺失。修正版按 PCB 中唯一匹配的位置、角度、封装、元件值和面别恢复为 U3，并与原 BOM 的全部位号核对。

此修正不代表已批准生产：原 PCB 的 DRC 错误、Gerber 与 PCB 的几何一致性、具体采购型号和最终蓝牙改版均尚待完成。不要将这个坐标表与未来版本的 BOM/Gerber 混用。

从仓库根目录运行 `python3 scripts/check_manufacturing_reference.py` 可重新生成；先用 KiCad 的 Python 运行 `scripts/extract_pcb_metadata.py` 更新源 PCB 元数据。审查结果在 `docs/audit/manufacturing-reference.json`。
