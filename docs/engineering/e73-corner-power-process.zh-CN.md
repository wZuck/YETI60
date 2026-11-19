[English](e73-corner-power-process.md) | 中文

# CORNER-05 电源和普通 PCB 工艺复核

CORNER-05 合入了低电阻 USB 供电走线，并将 C42、C48 接地孔移出锡膏和阻焊开窗。交付包中的原生 PCB、固件、材料表和制板文件对应此版。电脑完成 USB 配置后，固件允许同时走 USB HID 和充电。

| 主板供电段 | CORNER-04 铜线电阻 | CORNER-05 铜线电阻 |
|---|---:|---:|
| J4.1 到 J5.1 | 0.086 Ω | 0.015 Ω |
| J1.1 到 F1.2 | 0.057 Ω | 0.029 Ω |
| F1.1 到 U5 IN | 0.292 Ω | 0.089 Ω |

## 充电电压余量

按 `R = ρL/(线宽 × 铜厚)` 合计三段铜线。四根 AWG28 供电及回流导线总自由长度 1.083 m，标称铜截面 0.0804 mm²，对应 20 °C 线束回路电阻 0.232 Ω。将线束和铜线按 `R60 = R20 × (1 + 0.00393 × 40)` 折算得 **0.423 Ω**，CORNER-04 为 0.772 Ω。计算未计入主板地回路、孔铜、C5 走线、两颗保险丝、连接器、压接点和外部 USB 线。

| Type-C 插座带载电压 | 假设输入电流 | 所计路径压降 | 未计其他损失的 U5 IN |
|---|---:|---:|---:|
| 4.75 V | 100 mA | 0.042 V | 4.708 V |
| 4.75 V | 450 mA | 0.190 V | 4.560 V |
| 4.75 V | 500 mA | 0.211 V | 4.539 V |
| 5.00 V | 450 mA | 0.190 V | 4.810 V |
| 5.00 V | 500 mA | 0.211 V | 4.789 V |

BQ24074 在 4.35–4.63 V 输入阈值处可能降流。在弱供电情况下，阈值较高的充电器仍可能达不到假设电流。nRF52840 的 VBUS 工作下限为 4.35 V。U1 从 F1 后的独立支路取电，测量 U1 VBUS 时使用 U1 本地地线，U5 IN 则用充电器地线。上述计算未求解实际调节闭环。[TI BQ24074 电气参数](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [Nordic USB 供电条件](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/power.html)

10 条局部电源走线符合项目线宽和长度限制。R40 为 2.21 kΩ，充电电流设定的最小／典型／最大值为 357.06／402.71／445.63 mA。完整保护包须接受 4.16–4.23 V 调节范围。假设 U5 IN 为 5.25 V、BAT 为 3.10 V、OUT 为 4.50 V 且负载为 40 mA，按 `P = (VIN−VBAT)×IBAT + (VIN−VOUT)×IOUT`，在 445.63 mA 时损耗约为 **0.99 W**。标准测试板的热阻无法预测本键盘温度。[TI BQ24074 充电及热参数](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

## 普通钻孔和焊盘开窗

852 个过孔均为机械贯通孔。标称钻孔／焊环外径为 0.30／0.50 mm（203 个）、0.30／0.60 mm（63 个）、0.40／0.80 mm（586 个）。最小走线宽度为 0.127 mm。主板采用指定的普通四层叠层和盖油工艺。请用实际制造文件与工厂确认阻焊对位。[嘉立创制造能力](https://jlcpcb.com/capabilities/pcb-capabilities/)

| 位号 | 标称钻孔至开窗检查 |
|---|---|
| C42.2 | 地过孔位于 PCB 坐标 (122.120, 142.315) mm，距自身锡膏及阻焊开窗均为 0.130 mm |
| C48.2 | 地过孔位于 PCB 坐标 (107.1368, 147.6572) mm，距自身锡膏及阻焊开窗均为 0.237 mm |
| SW1.2、D2.1 | 标称间隙分别为 0.037 mm 和 0.142 mm。确认工厂钻孔与阻焊对位，重点核对 SW1 |
| U5.17、U6.11 | 保留阻焊岛，钻孔至阻焊开窗标称间隙均为 0.100 mm，距分割锡膏开窗分别为 0.150 和 0.167 mm |

原生检查量测过孔焊环与实装焊盘相交时的钻孔半径和开窗关系。检查两颗裸露散热焊盘的盖油及分割钢网。JST SH 端子适用 AWG32–28，线束采用此范围内的 AWG28，仍须满足绝缘外径及压接质量要求。[嘉立创过孔覆盖](https://jlcpcb.com/help/article/pcb-via-covering) · [JST SH 规格](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)

## 样机验收

先使用电池模拟器。在 USB 枚举、充电、键盘使用、挂起及恢复期间，测量插座、J4、J1、F1、U5 IN 和 U1 VBUS。弱供电下应验证充电降流时可以正常打字，拔线后进入蓝牙。按供应商规范确认电池包保护和独立 NTC 后再接合格的保护包。关壳样机须实测充电器、PCB 及电池温度。详见[电池包规格](battery-pack-specification.zh-CN.md)和[固件指南](../testing/e73-corner-firmware.zh-CN.md)。

重新生成线束报告后，用 KiCad 10 Python 运行 `scripts/check_e73_corner_power.py`。 [现板检查及计算](../../hardware/e73-hhkb-corner/audit/power-process.json) · [CORNER-04 对照与合并试验](https://github.com/wZuck/YETI60/tree/c3872db49bbff5188b7be3fab3fa73b81b2b9028/hardware/e73-hhkb-corner/audit)
