[English](power-process.md) | 中文

# CORNER-07 电源和普通 PCB 工艺复核

CORNER-07 调整 U5、U6、C42 和 SW1 的开窗，并移动 D2 接地过孔。USB 供电走线和 C42、C48、SW1 的接地过孔位置沿用前两版。交付包中的原生 PCB、固件、材料表和制板文件对应此版。电脑完成 USB 配置后，固件允许同时走 USB HID 和充电。

| 主板供电段 | CORNER-04 铜线电阻 | CORNER-07 铜线电阻 |
|---|---:|---:|
| J4.1 到 J5.1 | 0.086 Ω | 0.015 Ω |
| J1.1 到 F1.2 | 0.057 Ω | 0.029 Ω |
| F1.1 到 U5 IN | 0.292 Ω | 0.089 Ω |

## 充电电压余量

三段主板正向铜线按 `R = ρL/(线宽 × 铜厚)` 合计为 0.13335 Ω。M05 的四根 AWG28 供电和回流导线总自由长度为 1.09527 m，标称铜截面 0.0804 mm²，20 °C 线束回路为 0.23486 Ω。按 `R60 = (0.13335 + 0.23486) × (1 + 0.00393 × 40)` 折算，纳入模型的串联电阻为 **0.42608 Ω**，500 mA 时压降 **0.213 V**。M04 对照值为 0.423 Ω。模型未计主板地回路、孔铜、C5 走线、保险丝、连接器和压接；表中从插座带载电压算起。[测点及 M05 计算记录](bench-power-plan.json)

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

## 电脑端 USB 总电流

固件申报的 500 mA 适用于电脑 USB 端口。F1 后的 `USB_5V` 同时供 U5.13 和 U1.27，因此电脑侧测到充电器输入电流和 E73 的 USB 收发电路支路电流。BQ24074 的 USB500 输入限流为 450／475／500 mA。Nordic 给出的 nRF52840 USB 活动时 VBUS 电流典型值为 **2.4 mA**，该表未给最大值。若 U5 负载达到限流上限，加上这条支路的典型值便是 502.4 mA。这一组合说明现有公差计算无法保证整机上限，是否达到该组合取决于 U5 的实际负载。 [USB-IF 端口电流要求](https://compliance.usb.org/index.asp?Format=Standard&UpdateFile=Policies) · [TI 第 8.5 节](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [Nordic USB 电流表](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/_tmp/nrf52840/autodita/current/parameters.i_usbd.html?contentId=0~r9OOfQs0Fo3SLnXciN~A)

估算时给 U5 OUT 预留 40 mA、芯片内部耗电预留 2 mA，其余 USB 支路预留 10 mA。R40 为 2.21 kΩ 时，高公差端的规划电流为 `445.63 + 40 + 2 + 10 = 497.63 mA`。2.37 mA 的余量取决于这三项假设。USB100 的 100 mA 上限也只约束 U5 IN。主板上直接接 VBUS 的 C32（4.7 µF）和 C40（2.2 µF）合计理想充入电量为 `(4.7 + 2.2) × 5 = 34.5 µC`。首件需要测整机插入浪涌和稳态电流。 [绑定本版源文件的计算](usb-host-current.json) · [USB-IF 浪涌测试，第 B.4 节](https://www.usb.org/sites/default/files/USB-IFTestProc1_3.pdf)

若主机配置后的总电流超标，优先用 **2.49 kΩ ±1%、0402** 试换 R40。计算的充电设定上限为 395.52 mA，用相同负载假设得到 447.52 mA，规划余量 52.48 mA。此试改保留 USB500 模式及输入电压偏低时的降流保护。选用前须复测 USB 与充电，包括恒压收尾、终止、安全定时和完整充满时间。外部 ILIM 模式可以改输入限流值，TI 的 USB500 输入电压降流条件不适用于该模式。 [TI 第 8.5、9.3.4.1 节](https://www.ti.com/lit/ds/symlink/bq24074.pdf)

## 普通钻孔和焊盘开窗

852 个过孔均为机械贯通孔。标称钻孔／焊环外径为 0.30／0.50 mm（203 个）、0.30／0.60 mm（65 个）、0.40／0.80 mm（584 个）。最小走线宽度为 0.127 mm。主板采用指定的普通四层叠层和盖油工艺。请用实际制造文件与工厂确认阻焊对位。 [嘉立创制造能力](https://jlcpcb.com/capabilities/pcb-capabilities/)

| 位号 | 标称钻孔至开窗检查 |
|---|---|
| C42.2 | 地过孔位于 PCB 坐标 (122.120, 142.315) mm，距自身锡膏及阻焊开窗均为 0.230 mm |
| C48.2 | 地过孔位于 PCB 坐标 (107.1368, 147.6572) mm，距自身锡膏及阻焊开窗均为 0.237 mm |
| SW1.2 | 地过孔位于 PCB 坐标 (322.220, 122.370) mm，钻孔 0.30 mm，焊环外径 0.60 mm。两处间距均从 0.037 mm 增至 0.230 mm |
| D2.1 | 地过孔位于 PCB 坐标 (315.516, 122.070) mm，钻孔 0.30 mm，焊环外径 0.60 mm |
| U5.17、U6.11 | 更新阻焊岛及分割钢网开窗，钻孔至阻焊开窗的标称间距均为 0.230 mm。锡膏覆盖率见全板开窗复核 |

四张制造图层的最小钻孔余量为 `0.230 − √2 × 0.075 − 0.13 / 2 − 0.0002 ≈ 0.059 mm`，已扣除孔位、孔径和曲边近似。阻焊实际对位须向工厂确认，散热焊盘须检查过孔盖油和钢网锡膏转移。 [嘉立创钻孔公差](https://jlcpcb.com/capabilities/Capabilities) · [嘉立创盖油工艺](https://jlcpcb.com/help/article/pcb-via-covering) · [阻焊及钢网复核](aperture-review.zh-CN.md)

JST SH 端子适用 AWG32–28，线束采用此范围内的 AWG28，并须满足绝缘外径及压接质量要求。[JST SH 规格](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)

## 样机验收

按[台架供电与充电测试](bench-power.zh-CN.md)完成壳外测量，再按[电池包规格](../03-bom/battery-requirements.zh-CN.md)验证实物电池。

重新生成线束报告后，用 KiCad 10 Python 运行 `scripts/check_e73_corner_power.py`。 [现板检查及计算](power-process.json) · [CORNER-04 对照与合并试验](https://github.com/wZuck/YETI60/tree/c3872db49bbff5188b7be3fab3fa73b81b2b9028/hardware/e73-hhkb-corner/audit)
