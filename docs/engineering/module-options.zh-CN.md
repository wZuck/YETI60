中文 | [English](module-options.md)

# 主控模组备选方案

## 选择方案

每把键盘只使用一个 nRF52840 模组。两种模组的封装与引脚分配不同，不能在同一块 PCB 上直接互换。

| 方案 | 分支 | 当前阶段 | 库存分配 |
|---|---|---|---|
| Raytac MDBT50Q-1MV2 | [master](https://github.com/wZuck/YETI60/tree/master) | 已有布线 PCB、正常／校准两套 ARM 固件及 28 步装配指南；实物验收仍待完成 | 主板计划使用库存无源元件 10 只，补购 66 只 |
| Ebyte E73-2G4M08S1C | [codex/e73-variant](https://github.com/wZuck/YETI60/tree/codex/e73-variant) | 已实现原生原理图、封装、引脚契约和两套 ARM 固件；PCB 布线与完整集成尚在收尾 | 共用无源元件库存暂按基线分配；提供的库存快照没有 E73 模组 |

**本分支处于实现阶段，不能制板。** E73 正常／校准固件已构建，HEX 与 USB500 描述符检查通过，主控使用内部低频 RC 与 REG1 LDO。PCB 正在完成严格 DRC 闭环，制板包、装配图及完整报告尚需重新生成。现有 Raytac 图片和旧报告不能代替 E73 验证。参考封装见[厂商来源检查](../audit/yeti60-e73-reference.json)，当前模组契约见[E73 专用检查](../audit/yeti60-e73-variant.json)，固件见[构建记录](../audit/yeti60-target-build.json)。

## E73 来源与引脚阶段记录

[模组配置](../../hardware/module-options/e73.json) 记录全部 43 个厂商焊盘的尺寸、位置及拟分配逻辑网络。[导入的参考封装](../../hardware/module-options/Ebyte.pretty/E73-2G4M08S1C.kicad_mod) 保留厂商库原点和几何。标称本体为 18×13×3 mm，后续装配检查须计入所列尺寸公差。厂商来源为 [Ebyte 产品页](https://www.ebyte.com/product/444.html)、[手册](https://www.ebyte.com/downpdf/444.html) 与[原生封装下载](https://www.ebyte.com/pdf-down/2158.html)。配置文件保存来源与转换文件的 SHA-256。

提案保留 21 项 GPIO 功能，以及 USB、SWD、复位、电池测量和充电控制。43 个焊盘中有 28 个外围半孔和 15 个底部焊盘。拟连接 27 个外围焊盘和 **5 个底部焊盘：12、24、28、32、34**。因此 E73 仍需受控的底部焊接工艺和隐藏焊点检查，不能仅凭外围半孔宣称整板可只用烙铁焊接。

拟将 VDD／VCC 的 19 脚及 VDDH／VDH 的 23 脚接稳压 3.3 V，VBUS 的 27 脚接 USB 5 V，DCCH／DCH 的 25 脚不连接。当前使用 REG1 LDO，并关闭 REG0 DC/DC，不依赖未经核实的内部电感；功耗按 LDO 条件重新计算。P0.00／P0.01 用作 GPIO，须使用内部低频 RC 时钟；P0.09／P0.10 须配置为 GPIO 而非 NFC。扫描 ADC 改为 AIN4，电池 ADC 改为 AIN3，不能复用 Raytac 固件二进制或原校准值。

用 KiCad Python 执行 `scripts/check_e73_reference.py` 与 `scripts/check_e73_variant.py`，检查 43 焊盘参考数据、分配唯一性及 USB／SWD／电源专用引脚。该检查不代表 DRC、完整 PCB 仿真或 E73 固件构建。布线完成后，须重新生成并通过仓库完整审查、两套固件、引脚与 ADC 合约、结构间隙、分版本制板文件和图示指南。信号干扰及实物验收另列待完成事项。

## 引脚分配

| 逻辑网络 | 模组焊盘 | 芯片引脚 | 焊盘位置 |
|---|---:|---|---|
| ROW_DRV1 | 1 | P1.11 | 外围半孔 |
| CHG_N | 2 | P1.10 | 外围半孔 |
| CHG_EN1 | 3 | P0.03 | 外围半孔 |
| ADC | 4 | P0.28 | 外围半孔 |
| GND | 5 | GND | 外围半孔 |
| CHG_CE_N | 6 | P1.13 | 外围半孔 |
| CHG_EN2 | 7 | P0.02 | 外围半孔 |
| BAT_MEAS_EN | 8 | P0.29 | 外围半孔 |
| AFE_EN | 9 | P0.31 | 外围半孔 |
| STATUS_LED | 10 | P0.30 | 外围半孔 |
| ROW_DRV4 | 11 | P0.00 | 外围半孔 |
| APLEX_OUT_PIN_0 | 12 | P0.26 | 底部隐藏 |
| APLEX_EN_PIN_0 | 13 | P0.01 | 外围半孔 |
| BAT_ADC | 15 | P0.05 | 外围半孔 |
| ROW_DRV3 | 17 | P1.09 | 外围半孔 |
| +3.3V | 19 | VDD | 外围半孔 |
| GND | 21 | GND | 外围半孔 |
| +3.3V | 23 | VDDH | 外围半孔 |
| GND | 24 | GND | 底部隐藏 |
| RESET_N | 26 | P0.18 | 外围半孔 |
| USB_5V | 27 | VBUS | 外围半孔 |
| AMUX_SEL_2 | 28 | P0.15 | 底部隐藏 |
| USB_DM | 29 | D- | 外围半孔 |
| USB_DP | 31 | D+ | 外围半孔 |
| AMUX_SEL_0 | 32 | P0.20 | 底部隐藏 |
| ROW_DRV0 | 33 | P0.13 | 外围半孔 |
| AMUX_SEL_1 | 34 | P0.22 | 底部隐藏 |
| ROW_DRV2 | 35 | P0.24 | 外围半孔 |
| SWDIO | 37 | SWDIO | 外围半孔 |
| SWDCLK | 39 | SWDCLK | 外围半孔 |
| APLEX_EN_PIN_1 | 41 | P0.09 | 外围半孔 |
| PGOOD_N | 43 | P0.10 | 外围半孔 |
