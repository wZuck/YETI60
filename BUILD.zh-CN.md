[English](BUILD.md) | 简体中文

# YETI60 E73：审查与制作入口

**当前开发方向：[将 E73 移到标准 HHKB 不使用的右下角](docs/engineering/e73-hhkb-corner.zh-CN.md)。** 新候选使用正面安装，尚未制作放行。需要完成重布线、线束和装配验证；下文右上角来源板的检查结果不能用于验收新位置。

**E73 仍未完成整板验收，不要按已通过方案投板。** 当前以[右下角迁移报告](docs/engineering/e73-hhkb-corner.zh-CN.md)及其原生工程为准；下方旧版审查、制造包、固件和装配指南仅为迁移前参考，不验收本版。Raytac 验收不能替代 E73。

继续使用已经做好的 **UDB-C-JSH C5 子板**。本轮工作不要求修改它的 PCB、连接器或安装孔。保留子板保险丝和 USB 保护器件，接主板前核对四针输出。

| 要做的事 | 对应入口 |
|---|---|
| 当前问题与未完成工作 | [E73 审查](docs/audit/e73-review.zh-CN.md)、[完整检查结果](docs/audit/outcome.json) |
| USB 修补阶段记录 | [E73 独立候选、原生检查及材料差异](docs/engineering/e73-usb-repair.zh-CN.md)；尚未放行，正式制造文件／固件未替换 |
| E73 模组、焊盘及 MCU 配置 | [厂商焊盘参考](hardware/module-options/e73.json)、[引脚约束](docs/audit/yeti60-e73-variant.json) |
| 当前开发 PCB | [右下角原生 PCB](hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pcb)、[本版检查及制造放行条件](docs/engineering/e73-hhkb-corner.zh-CN.md)；当前没有本版制造放行包 |
| 材料、封装规格、数量和库存 | [完整准备清单](README.zh-CN.md#一把键盘需要准备的完整材料)、[采购 CSV](hardware/e73-hhkb-corner/mainboard-purchase.zh-CN.csv)、[库存分配](docs/engineering/inventory-allocation.zh-CN.md) |
| 已做好的子板 | [C5 材料](hardware/bom/daughterboard.zh-CN.csv)；直接保留现有板 |
| 从裸板开始焊接 | [分步焊接及装配指南](docs/assembly/build-guide.zh-CN.md)；已同步 NiZ、1.6 mm 定位板及 28 套固定件 |
| 迁移前固件参考 | [构建／刷写说明](firmware/target/README.zh-CN.md)、[正常版 HEX](firmware/releases/normal/yeti60-e73.hex)、[校准版 HEX](firmware/releases/calibrator/yeti60-e73.hex) |
| USB 充电及有线优先 | [事件／故障测试](docs/audit/usb-event-policy.json)；接受 USB 配置后可同时充电和传输 USB HID |
| 电池供应商确认 | [电池包规格](docs/engineering/battery-pack-specification.zh-CN.md)；供应商需按该规格逐项确认 |
| 迁移前装配／信号参考 | [标称装配](docs/audit/yeti60-assembly.json)、[USB 路径](docs/audit/USB-signal-paths.json)、[PH 插拔路径](docs/audit/e73-service-motion.json) |
| 已选 NiZ 及钢板卫星轴 | [E73 机构规格](docs/build/key-mechanism.zh-CN.md)；60 个感应中心、三组卫星轴、28 套固定件，H26 不装；实物配合待确认 |
| 验证命令 | `YETI_CAD_PYTHON=/path/to/cad/python python3 scripts/run_audit.py --baseline HEAD --refresh-guide`；然后执行 `python3 scripts/review_e73_readiness.py --require-design` |

当前主板工艺为普通四层 FR-4，标称 1.6 mm，机械贯通孔，无需盲埋孔、树脂塞孔或铜盖帽。这些工艺参数不代表取消设计暂停放行。不要将 Raytac 的主板制造文件或固件用于 E73。

E73 的 USB／充电控制使用 GPIO0 的 EN1／EN2，以及 **GPIO1.13 的 CE_N**。正常版与校准版构建必须保留内部 RC 低频时钟、REG1 LDO，以及明确释放 NFC 引脚为 GPIO 的 UICR 设置。该模组有五个实际连接的底部焊盘，只焊边缘引脚不能完成电气连接，需按合适的锡膏／回流及检查流程装配。

旧 `scripts/run_e73_review.py` 流程仍对应迁移前工程，不能验收 CORNER-03。当前应按[右下角说明](docs/engineering/e73-hhkb-corner.zh-CN.md#重现及验收)依次运行原生布线、参考地、元件模型、装配边界及故障注入检查，再按本页末尾的独立固件说明构建。完整线束、功耗／电池和实物验收仍需同步完成。

[当前 E73 固件构建、回归证据和校准升级说明](docs/testing/e73-firmware-validation.zh-CN.md)。

[正式 M01 定位板／地板修补及 CAD](docs/engineering/e73-mechanical-fit-candidate.zh-CN.md)已接入装配、校准标识和渲染。[M01 前缺口回归](docs/engineering/e73-mechanical-tolerances.zh-CN.md)保留作对照；完整机械／检修验收仍未完成。

当前右下角 PCB 的固件、构建和刷写边界见[独立说明](docs/testing/e73-corner-firmware.zh-CN.md)。
