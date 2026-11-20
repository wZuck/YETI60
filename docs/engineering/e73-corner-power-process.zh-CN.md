[English](e73-corner-power-process.md) | 中文

# CORNER-06 电源和普通 PCB 工艺复核

CORNER-06 移动了 SW1 接地过孔，并沿用 CORNER-05 的低电阻 USB 供电走线及已移出开窗的 C42、C48 接地孔。交付包中的原生 PCB、固件、材料表和制板文件对应此版。电脑完成 USB 配置后，固件允许同时走 USB HID 和充电。

| 主板供电段 | CORNER-04 铜线电阻 | CORNER-06 铜线电阻 |
|---|---:|---:|
| J4.1 到 J5.1 | 0.086 Ω | 0.015 Ω |
| J1.1 到 F1.2 | 0.057 Ω | 0.029 Ω |
| F1.1 到 U5 IN | 0.292 Ω | 0.089 Ω |

## 充电电压余量

三段主板正向铜线按 `R = ρL/(线宽 × 铜厚)` 合计为 0.13335 Ω。M05 的四根 AWG28 供电和回流导线总自由长度为 1.09527 m，标称铜截面 0.0804 mm²，20 °C 线束回路为 0.23486 Ω。按 `R60 = (0.13335 + 0.23486) × (1 + 0.00393 × 40)` 折算，纳入模型的串联电阻为 **0.42608 Ω**，500 mA 时压降 **0.213 V**。M04 对照值为 0.423 Ω。模型未计主板地回路、孔铜、C5 走线、保险丝、连接器和压接；表中从插座带载电压算起。[测点及 M05 计算记录](../../hardware/e73-hhkb-corner/audit/bench-power-plan.json)

| Type-C 插座带载电压 | 假设输入电流 | 所计路径压降 | 未计其他损失的 U5 IN |
|---|---:|---:|---:|
| 4.75 V | 100 mA | 0.043 V | 4.707 V |
| 4.75 V | 450 mA | 0.192 V | 4.558 V |
| 4.75 V | 500 mA | 0.213 V | 4.537 V |
| 5.00 V | 450 mA | 0.192 V | 4.808 V |
| 5.00 V | 500 mA | 0.213 V | 4.787 V |

BQ24074 在 4.35–4.63 V 输入阈值处可能降流。在弱供电情况下，阈值较高的充电器仍可能达不到假设电流。nRF52840 的 VBUS 工作下限为 4.35 V。U1 从 F1 后的独立支路取电，测量 U1 VBUS 时使用 U1 本地地线，U5 IN 则用充电器地线。上述计算未求解实际调节闭环。[TI BQ24074 电气参数](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [Nordic USB 供电条件](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/power.html)

在 4.75 V 带载输入和 4.63 V 阈值下，按简化模型到达降流阈值时电流约为 `(4.75 − 4.63) / 0.42608 = 0.282 A`。这是未扣除其余路径损失的总输入电流估算，需实测充电电流和 U1 VBUS。

10 条局部电源走线符合项目线宽和长度限制。R40 为 2.21 kΩ，充电电流设定的最小／典型／最大值为 357.06／402.71／445.63 mA。完整保护包须接受 4.16–4.23 V 调节范围。假设 U5 IN 为 5.25 V、BAT 为 3.10 V、OUT 为 4.50 V 且负载为 40 mA，按 `P = (VIN−VBAT)×IBAT + (VIN−VOUT)×IOUT`，在 445.63 mA 时损耗约为 **0.99 W**。标准测试板的热阻无法预测本键盘温度。[TI BQ24074 充电及热参数](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

## 普通钻孔和焊盘开窗

852 个过孔均为机械贯通孔。标称钻孔／焊环外径为 0.30／0.50 mm（203 个）、0.30／0.60 mm（64 个）、0.40／0.80 mm（585 个）。最小走线宽度为 0.127 mm。主板采用指定的普通四层叠层和盖油工艺。请用实际制造文件与工厂确认阻焊对位。[嘉立创制造能力](https://jlcpcb.com/capabilities/pcb-capabilities/)

| 位号 | 标称钻孔至开窗检查 |
|---|---|
| C42.2 | 地过孔位于 PCB 坐标 (122.120, 142.315) mm，距自身锡膏及阻焊开窗均为 0.130 mm |
| C48.2 | 地过孔位于 PCB 坐标 (107.1368, 147.6572) mm，距自身锡膏及阻焊开窗均为 0.237 mm |
| SW1.2 | 地过孔位于 PCB 坐标 (322.220, 122.370) mm，钻孔 0.30 mm，焊环外径 0.60 mm。两处间距均从 0.037 mm 增至 0.230 mm |
| D2.1 | 钻孔到开窗标称距离为 0.142 mm，核对工厂对位 |
| U5.17、U6.11 | 保留阻焊岛，钻孔至阻焊开窗标称间隙均为 0.100 mm，距分割锡膏开窗分别为 0.150 和 0.167 mm |

按公布的孔位公差保守计算对角偏移，再扣除成品孔径最大增量的一半，SW1 的间距余量为 `0.230 − √2 × 0.075 − 0.13 / 2 = 0.059 mm`。阻焊对位仍须工厂确认。实物检查两颗裸露散热焊盘的盖油及分割钢网。[嘉立创钻孔公差](https://jlcpcb.com/capabilities/Capabilities) · [嘉立创过孔覆盖](https://jlcpcb.com/help/article/pcb-via-covering) · [制板压缩包核对报告](../../delivery/YETI60-E73/06-validation/cam-ordinary.json)

JST SH 端子适用 AWG32–28，线束采用此范围内的 AWG28，并须满足绝缘外径及压接质量要求。[JST SH 规格](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)

## 样机验收

按[台架供电与充电测试](../testing/e73-bench-power.zh-CN.md)完成壳外测量，再按[电池包规格](battery-pack-specification.zh-CN.md)验证实物电池。

重新生成线束报告后，用 KiCad 10 Python 运行 `scripts/check_e73_corner_power.py`。 [现板检查及计算](../../hardware/e73-hhkb-corner/audit/power-process.json) · [CORNER-04 对照与合并试验](https://github.com/wZuck/YETI60/tree/c3872db49bbff5188b7be3fab3fa73b81b2b9028/hardware/e73-hhkb-corner/audit)
