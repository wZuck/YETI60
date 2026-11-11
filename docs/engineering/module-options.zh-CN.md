[English](module-options.md) | 简体中文

# 控制模组两套方案

两套方案保留在同一分支，每套仅使用一个 nRF52840。主板、模组和固件必须匹配；当前机械、线束与电源修订不同，不能互相继承验收。

| 方案 | 受控入口 | 当前状态 |
|---|---|---|
| 亿佰特 E73-2G4M08S1C | [E73 制作与审查入口](../../BUILD.zh-CN.md)、[当前门禁](../audit/e73-readiness.json) | 原生 270 组信号／电源及 142 组地连通性通过，普通／校准固件可构建。USB 支路、旧定位板和 PH 插头拔出干涉使设计继续暂停。 |
| Raytac MDBT50Q-1MV2 | [Raytac 手册](../../variants/raytac/BUILD.zh-CN.md)、[USB 修补候选板](../../variants/raytac/hardware/usb-short-route/README.zh-CN.md) | 独立候选板、九线线束和 SH3 电池接口；供方、制板审查及实物验收仍待完成。 |

保留已经制作的 UDB-C-JSH C5 子板。主板只有满足对应放行条件后才制作所选的一套。使用各入口中的当前物料表和库存抵扣；旧元件总数及历史两方案合并检查不代表当前候选包。继续限定 JLC 普通四层工艺。

## E73 来源与引脚阶段记录

[模组配置](../../hardware/module-options/e73.json) 记录全部 43 个厂商焊盘的尺寸、位置及拟分配逻辑网络。[导入的参考封装](../../hardware/module-options/Ebyte.pretty/E73-2G4M08S1C.kicad_mod) 保留厂商库原点和几何。标称本体为 18×13×3 mm，后续装配检查须计入所列尺寸公差。厂商来源为 [Ebyte 产品页](https://www.ebyte.com/product/444.html)、[手册](https://www.ebyte.com/downpdf/444.html) 与[原生封装下载](https://www.ebyte.com/pdf-down/2158.html)。配置文件保存来源与转换文件的 SHA-256。

本方案保留 21 项 GPIO 功能，以及 USB、SWD、复位、电池测量和充电控制。43 个焊盘中有 28 个外围半孔和 15 个底部焊盘。拟连接 27 个外围焊盘和 **5 个底部焊盘：12、24、28、32、34**。因此 E73 仍需受控的底部焊接工艺和隐藏焊点检查，不能仅凭外围半孔宣称整板可只用烙铁焊接。

将 VDD／VCC 的 19 脚及 VDDH／VDH 的 23 脚接稳压 3.3 V，VBUS 的 27 脚接 USB 5 V，DCCH／DCH 的 25 脚不连接。当前使用 REG1 LDO，并关闭 REG0 DC/DC，不依赖未经核实的内部电感；功耗按 LDO 条件重新计算。P0.00／P0.01 用作 GPIO，须使用内部低频 RC 时钟；P0.09／P0.10 须配置为 GPIO 而非 NFC。扫描 ADC 改为 AIN4，电池 ADC 改为 AIN3，不能复用 Raytac 固件二进制或原校准值。

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

## 制板包与条件功耗

| 方案 | 制板包 | 固件电源模式 | 1600 mAh 条件规划续航 |
|---|---|---|---|
| E73 | [E73 制板审查包](../../hardware/fabrication/yeti60-e73-p2-dfm-review.zip) | REG1 LDO | 90.77 小时 |
| Raytac | [Raytac 当前首板文件](../../variants/raytac/hardware/usb-short-route/FIRST-ARTICLE.zh-CN.md) | REG1 DC/DC | 106.64 小时 |

表中续航是条件模型值，不是实测或保证。当前 Raytac 修补候选板装 75 件器件，使用 813 个普通过孔，原生检查为 0 错误、0 断线，仅保留 102 条非实装图形的封装外框警告。以上链接提供其当前 Gerber、钢网、接线及无外壳流程；C5 单独处理。E73 的具体文件与审查状态以它的制作入口为准，不能套用 Raytac 的数量或结论。

[验收与干扰流程](../testing/README.zh-CN.md)：几何与文件检查不能替代实际射频、静电容扫描或 USB 验收。按各自方案制作入口选择对应的焊接、安装和首件测试资料。
