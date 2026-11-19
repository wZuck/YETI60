[English](project-files.md) | 中文

# 打开正确的 E73 PCB 工程

当前右下角、正面安装 E73 的版本是 **CORNER-04**。受控来源为[右下角工程](source/EC60-nRF52840.kicad_pro)，[PCB 文件](source/EC60-nRF52840.kicad_pcb)在同一目录。用 KiCad 打开该工程，再进入 PCB 编辑器。交付快照的 `01-pcb/source/` 包含工程、全部原理图子页、本地符号／封装库和本地模型。

不能只凭 `EC60-nRF52840` 这个共同文件名判断版本：几个历史候选都使用该名称。`hardware/ec60-nrf52840` 是旧基线，`hardware/e73-usb-repair` 是中间来源，`variants/raytac` 是另一模组方案；这些都不是当前右下角板。

| 原生 PCB 核对项 | 当前版本应有的内容 |
|---|---|
| U1 模组 | 正面，原点 X332／Y195 mm、0°；本体位于 PCB X332–350／Y182–195 mm |
| J5 电源桥接口 | 背面，X335.5／Y117.5 mm、180° |
| J4 USB 接口 | 背面，X346.1／Y110.7 mm、90° |
| 板框 | 285.0 ×94.6 mm，已去掉原右上凸出部分 |
| 按键排列 | 60 个有效 HHKB 感应位置；去掉未用 SW72／SW73 电极 |
| 制造 | 普通四层 FR-4、标称 1.6 mm、机械贯通过孔 |

2026 年 11 月 14 日的 `b523e60` 新增右下角 PCB；`7d8b826` 完成布线／参考地修补，`91aa2f1` 清理残余铜线，11 月 17 日的 `d8c1bf0` 提交 J5 反向及局部走线修补。之后的理线件／胶膜工作修改机械产物，没有改动铜线。

`.kicad_pro` 保存工程配置，它的修改时间不会跟随每一次封装或走线编辑变化；实际 PCB 几何保存在 `.kicad_pcb`。请通过 Git 内容／历史及交付 `manifest.json` 内的 SHA-256 判断版本，不以 Finder 时间为准。交付 PCB 与固件清单中的板文件摘要必须一致。

PCB 历史轴体三维链接不是当前 NiZ 机构，部分还依赖旧版 KiCad 本机模型路径。原生三维预览不等于完整装配证据。请配套使用当前[机构](../04-assembly/key-mechanism.zh-CN.md)、[线束](../04-assembly/harness-routing.zh-CN.md)及[理线件](../04-assembly/retainers.zh-CN.md)文档；整机叠层见[当前装配图](../04-assembly/assembly-views.zh-CN.md)。拆修仍待验收。
