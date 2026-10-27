[English](README.md) | 简体中文

# YETI60 单 nRF52840 改版

> **最新 CAD 验证通过：严格 DRC 0 错误、0 处未连接。** 见 [修复验证报告](../../docs/audit/pcb-review-2026-10-27.zh-CN.md) 和 `audit-current.json`。两个主控焊盘内过孔需要[填孔盖铜](fabrication-notes.zh-CN.md)，尚未实板验证。

当前方案只有一颗 nRF52840（Raytac MDBT50Q-1MV2 模块，贴装在主 PCB）。它负责静电容扫描、USB HID、蓝牙 HID 和电源状态控制。OPA350 运放、模拟复用器、充电 IC 和稳压 IC 属于外围电路，不是第二颗主控。

保留原 PCB 外形、安装孔和电极矩阵。移除 STM32、晶振和原偏左的 USB1。后侧中央 Type-C 使用独立 USB 子板，经 J1 接主 PCB；子板和线束仍需完成装配验证。FELK60 树脂外壳暂沿用原结构。

## 当前状态

- 已生成五页原理图、176 个元件的网表和已完成本轮布线和 CAD 验证的 PCB。
- 原理图 ERC 已检查到 0 错误；仍有继承的非网格端点和模拟前端共用放电网络命名警告。
- `connectivity-check.json` 检查单主控、供电及所有新电路引脚与设计契约一致。
- 2026-10-27 阶段快照：原理图 ERC 为 0 错误；当时 PCB 有 12 个 DRC 错误、35 处未连接。历史结果见 [阶段记录](../../docs/audit/checkpoints/12d9d58-checkpoint.json) 和 [归档 DRC](../../docs/audit/checkpoints/12d9d58-DRC-routed.json)，该历史快照尚不能生产。
- `EC60-nRF52840.kicad_pcb` 是当前工作板；`.unrouted.kicad_pcb` 是布线器输入快照，也不代表完成板。
- 主控 I/O 引出使用 0.127 mm 走线、0.15 mm 间距和 0.5/0.3 mm 过孔；普通网络仍以 0.2 mm 走线为基准。
- SW60/SW62 的接地护线从 0.4 mm 缩至 0.394 mm，感应电极形状、键位、板框和安装孔保持不变。
- 信号干扰模拟按用户要求留到 PCB 设计完成后，尚未运行。
- nRF52840 扫描固件及 ADC 采样／放电时序需要移植和实物验证。`firmware/ec60` 是 STM32 扫描参考，不是新板可刷写固件。

## 电路

`pinmap.json` 是模块引脚分配，`components.json` 记录新电路连接。模拟前端通过 U8 开关供电，电池测量分压通过 U7 开关控制。固件关闭模拟前端前，必须避免 GPIO 反向供电；开启后等待稳定并校准。电池采样开启后至少等待 50 ms。

电源为 BQ24074 充电及电源路径 + TPS63031 3.3 V 升降压。电池接口要求带保护板的单节 4.2 V 锂电池、兼容 103AT-2 的 10 kΩ NTC；J2 的顺序为 BAT、GND、NTC。充电设定约 100 mA。USB 输入限流上电默认 100 mA，固件须按枚举和挂起状态管理 EN1/EN2/CE。

模块 VDD/VDDH 均连接 3.3 V；VBUS 引脚接 USB 5 V；DCCH 不连接。采用内部低频 RC 时钟，固件配置必须一致。下载与调试使用 J3 自定义六点 SWD，针序见网表，不是标准 ARM 接口。

## 渲染

[正反面渲染、360° 动画和重建说明](../../renders/ec60-nrf52840/README.zh-CN.md)。渲染副本只修正模型引用，不修改本设计 PCB；J2、SW100、U5 的模型存在说明中列出的外形简化。

## 重建

先运行 `scripts/build_single_nrf.py`，使用 KiCad CLI 导出 XML 网表，再用 KiCad 自带 Python 执行 `scripts/build_single_nrf_pcb.py`。布局生成器仅写入 `.unrouted.kicad_pcb`，避免覆盖后续已布线板。运行 `python3 scripts/check_single_nrf.py` 检查网表连接。

重建完成不代表生产批准。当前板已完成本轮布线与严格 DRC；后续需要电源器件具体料号审核、特殊制板工艺确认、子板与电池装配、固件和实物验证。信号干扰分析暂不进行。

## 全面复查进行中

R30/R31 已按 nRF52840 内置 USB PHY 终端电阻要求改为 0 Ω。电源局部路径、装配及新渲染仍待继续，详见[阶段记录](../../docs/audit/yeti60-review-checkpoint.zh-CN.md)。旧 PCB 单板渲染不是当前装配验收结果。
