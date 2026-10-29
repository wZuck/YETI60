中文 | [English](module-options.md)

# 主控模组备选方案

## 选择方案

每把键盘只使用一个 nRF52840 模组。两种模组的封装与引脚分配不同，不能在同一块 PCB 上直接互换。

| 方案 | 分支 | 当前阶段 | 库存分配 |
|---|---|---|---|
| Raytac MDBT50Q-1MV2 | [master](https://github.com/wZuck/YETI60/tree/master) | 已有布线 PCB、正常／校准两套 ARM 固件及 28 步装配指南；实物验收仍待完成 | 主板计划使用库存无源元件 10 只，补购 66 只 |
| Ebyte E73-2G4M08S1C | [codex/e73-variant](https://github.com/wZuck/YETI60/tree/codex/e73-variant) | 已导入厂商封装并检查引脚分配提案；E73 PCB 布线、固件及装配验证尚未完成 | 共用无源元件库存暂按基线分配；提供的库存快照没有 E73 模组 |

**不能把本分支暂时保留的 Raytac PCB、制板压缩包或固件当作 E73 版本下单或刷写。** 本开发分支中原有完整审查报告和示意图对应 Raytac 基线，须在 E73 硬件完成后重新生成。[E73 提案专用检查记录](../audit/e73-pin-proposal.json) 明确标注 `PCB_routed: false` 与 `E73_firmware_built: false`。

## E73 来源与引脚阶段记录

[模组配置](../../hardware/module-options/e73.json) 记录全部 43 个厂商焊盘的尺寸、位置及拟分配逻辑网络。[导入的参考封装](../../hardware/module-options/Ebyte.pretty/E73-2G4M08S1C.kicad_mod) 保留厂商库原点和几何。标称本体为 18×13×3 mm，后续装配检查须计入所列尺寸公差。厂商来源为 [Ebyte 产品页](https://www.ebyte.com/product/444.html)、[手册](https://www.ebyte.com/downpdf/444.html) 与[原生封装下载](https://www.ebyte.com/pdf-down/2158.html)。配置文件保存来源与转换文件的 SHA-256。

提案保留 21 项 GPIO 功能，以及 USB、SWD、复位、电池测量和充电控制。43 个焊盘中有 28 个外围半孔和 15 个底部焊盘。拟连接 27 个外围焊盘和 **5 个底部焊盘：12、24、28、32、34**。因此 E73 仍需受控的底部焊接工艺和隐藏焊点检查，不能仅凭外围半孔宣称整板可只用烙铁焊接。

拟将 VDD／VCC 的 19 脚及 VDDH／VDH 的 23 脚接稳压 3.3 V，VBUS 的 27 脚接 USB 5 V，DCCH／DCH 的 25 脚不连接。REG1 DC/DC 的模组内元件配置仍待核实，之后才能冻结固件及功耗估算。P0.00／P0.01 用作 GPIO，须使用内部低频 RC 时钟；P0.09／P0.10 须配置为 GPIO 而非 NFC。扫描 ADC 改为 AIN4，电池 ADC 改为 AIN3，不能复用 Raytac 固件二进制或原校准值。

用 KiCad Python 执行 `scripts/check_e73_proposal.py`，检查 43 焊盘参考数据、分配唯一性及 USB／SWD／电源专用引脚。该检查不代表 DRC、完整 PCB 仿真或 E73 固件构建。布线完成后，须重新生成并通过仓库完整审查、两套固件、引脚与 ADC 合约、结构间隙、分版本制板文件和图示指南。信号干扰及实物验收另列待完成事项。
