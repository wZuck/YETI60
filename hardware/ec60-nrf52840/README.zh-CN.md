[English](README.md) | 简体中文

# YETI60 单 nRF52840 PCB

单颗 Raytac MDBT50Q-1MV2 承担静电容扫描、原生 USB 和 BLE；OPA350、复用器、充电及稳压芯片为外围，不是第二主控。移除 STM32 和板载 USB1，后侧 Type-C 子板连接 J1；保留 EC60 感应几何、板框、安装位置及四层结构。

严格 CAD DRC 为 0 错误、0 断线，268 对引脚导通；这**不能批准剩余电源局部布局或整机硬件**。见[全面复查](../../docs/audit/yeti60-comprehensive-review.zh-CN.md)。最初 12 错误／35 断线快照仍保存在 `docs/audit/checkpoints/`。

## 电气契约

供电为 BQ24074 充电／电源路径和 TPS63031 3.3 V 升降压。J2 顺序 BAT／GND／NTC，要求受保护的单节 4.2 V 电池和兼容 103AT-2 的 10k NTC；充电约 100 mA，上电输入默认 USB100，固件须按枚举和挂起控制 EN1／EN2／CE。电池未选型。

模块 VDD／VDDH 接 3.3 V，VBUS 接 USB 5 V，DCCH 不接。nRF PHY 已内置终端，R30/R31 使用 **0 Ω**。采用内部低频 RC，目标固件须正确配置。J3 为自定义六点 SWD，不是标准 ARM 接口。

U8 控制模拟前端，U7 控制 1M:1M、电容 10 nF 的电池分压。关闭 AFE 时必须避免 GPIO 反向供电；开启后应等待稳定并校准，电池采样至少等待 50 ms。[nRF 控制核心](../../firmware/yeti60/README.zh-CN.md)通过主机测试，但不是可刷写 USB/BLE 目标应用；`firmware/ec60/` 是独立 STM32 参考。

局部 I/O 为 0.127 mm 线宽／0.15 mm 间距／0.50 mm 过孔铜径及 0.30 mm 钻孔，普通走线以 0.2 mm 为基准；电感侧直段 0.35 mm。此前 SW60/SW62 接地护线由 0.4 缩至 0.394 mm，感应铜和位置保留。成品 PCB 厚 1.59 mm，原生仅基材 STEP 为 1.50 mm。

U1.39/U1.51 须[填孔、磨平并盖铜](fabrication-notes.zh-CN.md)，仅盖油不能替代。

## 源文件与重建

`EC60-nRF52840.kicad_pcb` 是工作设计，`.unrouted.kicad_pcb` 只是布线输入快照。`pinmap.json`、`components.json`、原理图 XML 和审查哈希定义引脚／元数据契约；`YAECKB` 库名及原文件名为技术兼容保留。

先运行 `build_single_nrf.py` 重建原理图，再由 KiCad CLI 导出 XML，使用 KiCad Python 运行 `build_single_nrf_pcb.py`。布局生成器只写 `.unrouted`，避免覆盖布线板。网表、PCB 契约、严格审查和逐引脚回归由不同检查器分别验证。

[PCB 渲染](../../renders/ec60-nrf52840/README.zh-CN.md)和[条件装配图](../../renders/yeti60-assembly/README.zh-CN.md)关联源文件。电源回路、器件额定值、特殊制板、树脂嵌件、胶碗／螺钉结构、子板／线缆、真实固件／校准及后续信号／射频仍未定型。
