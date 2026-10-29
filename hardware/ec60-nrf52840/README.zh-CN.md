[英文](README.md) | 简体中文

# YETI60 单 nRF52840 PCB

单颗 Ebyte E73-2G4M08S1C 承担静电容扫描、原生 USB 和 BLE；OPA350、复用器、充电及稳压芯片为外围，不是第二主控。移除 STM32 和板载 USB1，后侧 Type-C 子板连接 J1；保留 EC60 感应几何、板框、安装位置及四层结构。

严格 CAD DRC 为 0 错误、0 断线，270 对引脚导通；这**不能批准整机硬件或替代电源实测**。见[全面复查](../../docs/audit/yeti60-comprehensive-review.zh-CN.md)。

## 电气契约

供电保留 BQ24074 充电／电源路径与 TPS63031 3.3 V 升降压。默认 P2 为定制 1600 mAh、85×43×4.8 mm 电池包，J2 为正极／负极／NTC。R40=2.21k、R55=69.8k、R56=1.69k，均为 1%；名义充电 402.71 mA，最大公差值 445.63 mA。USB 主机接受 500 mA 配置后才允许充电；未枚举保持 USB100，挂起禁充。电池须有独立温度断充和第三线 10k NTC，供方签图待完成。计算见[功耗与充电](../../docs/engineering/power-budget.zh-CN.md)。

模块 VDD／VDDH 接 3.3 V，VBUS 接 USB 5 V，DCCH 不接。nRF PHY 已内置终端，R30/R31 使用 **0 Ω**。采用内部低频 RC，目标固件须正确配置。J3 为自定义六点 SWD，不是标准 ARM 接口。

U8 控制模拟前端，U7 控制 1M:1M、电容 10 nF 的电池分压。关闭 AFE 时必须避免 GPIO 反向供电；开启后应等待稳定并校准，电池采样至少等待 50 ms。[nRF 控制核心](../../firmware/yeti60/README.zh-CN.md)通过主机测试，并已接入可构建的 USB／蓝牙目标应用。

局部 I/O 为 0.127 mm 线宽／0.15 mm 间距／0.50 mm 过孔铜径及 0.30 mm 钻孔，普通走线以 0.2 mm 为基准；电感侧直段 0.35 mm。此前 SW60/SW62 接地护线由 0.4 缩至 0.394 mm，感应铜和位置保留。普通下单标称 1.6 mm，含模型阻焊的 CAD 包络为 1.6062 mm。

当前使用 JLC 普通四层工艺：全部为最小 0.50／0.30 mm 机械通孔，无盲埋孔和模组盘中孔，不要求填孔盖铜。按[普通制板说明](fabrication-notes.zh-CN.md)选择标准叠层和 1.6 mm 标称板厚，CAD 包络为 1.6062 mm。

## 源文件与重建

当前 KiCad PCB、项目及原理图文件是可编辑设计源文件。`pinmap.json`、仅覆盖改版元件的 `components.json`、导出的 `netlist.xml` 和按元件引用固定的本地封装必须保持一致。`YAECKB` 库标识为兼容性保留。

原理图变更后，通过 KiCad CLI 导出 `netlist.xml`，更新显式契约，必要时重新生成 `firmware/yeti60/board_pins.h`，然后运行 `python3 scripts/run_audit.py`。审计分别检查重新导出的原理图一致性、原生 DRC、PCB 契约和物理连通回归。历史生成器和布线快照已移除。

[PCB 渲染](../../renders/ec60-nrf52840/README.zh-CN.md)和[条件装配图](../../renders/yeti60-assembly/README.zh-CN.md)关联源文件。电源回路、器件额定值、普通工艺验收、树脂嵌件、胶碗／螺钉结构、子板／线缆、真实固件／校准及后续信号／射频仍未定型。
