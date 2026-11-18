[English](BUILD.md) | 简体中文

# YETI60 E73：当前制作与审查入口

当前选择 **E73 CORNER-04**，模组正面安装在标准 HHKB 未用的右下角。请打开[当前 KiCad 工程](hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pro)和 [PCB](hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pcb)。[版本及工程文件核对](docs/build/e73-project-files.zh-CN.md)说明了如何区分历史候选。

**工程审查版，尚未放行下单。** 原生布线／参考地检查及配套固件构建通过；九根导线、16 件刚性理线件和 17 片胶膜通过静态公差检查。理线件制造工艺／拆修、完整关壳图纸、最终电源／电池／制造复核及实物验收仍待完成。原生规则检查或文件清单校验通过，不能关闭这些未完成项。

已经制作的 **UDB-C-JSH C5 子板保持不变**，不需要重做子板 PCB。

| 要做的事 | 当前受控入口 |
|---|---|
| 在一个目录找到全部交付产物 | [从这里开始](delivery/YETI60-E73/START-HERE.zh-CN.md)、[离线网页](delivery/YETI60-E73/index.zh-CN.html) |
| PCB 下单选项、文件及打印要求 | [PCB 与机械件制造说明](docs/build/e73-ordering-printing.zh-CN.md) |
| 当前电气与机械检查证据 | [右下角审查及复现命令](docs/engineering/e73-hhkb-corner.zh-CN.md) |
| 全部材料、封装、数量和库存 | [准备清单](README.zh-CN.md#一把键盘需要准备的完整材料)、[主板 75 件采购表](hardware/e73-hhkb-corner/mainboard-purchase.zh-CN.csv) |
| 从空 PCB 开始制作 | [12 步焊接与台架教程](docs/assembly/e73-corner/soldering.zh-CN.md)、[图文网页](docs/assembly/e73-corner/soldering.zh-CN.html) |
| 线束、准确针序和自由长度 | [九根导线线束](docs/engineering/e73-corner-harness.zh-CN.md) |
| 理线件文件、位置和裁膜模板 | [16 件刚性件及 17 片胶膜](docs/engineering/e73-retention.zh-CN.md) |
| NiZ 轴座／滑块及钢板卫星轴 | [机构与装配](docs/build/key-mechanism.zh-CN.md)；60 键、三组卫星轴、28 套固定件，H26 不装 |
| 请电池供应商核实参数 | [单节保护电池包规格](docs/engineering/battery-pack-specification.zh-CN.md) |
| 构建、刷写并校准配套固件 | [当前右下角固件](docs/testing/e73-corner-firmware.zh-CN.md) |
| 文件完整性与来源一致性 | `python3 scripts/check_e73_delivery.py`；未完成项存在时，`--require-release` 应继续报未放行 |

主板采用普通四层 FR-4、标称 1.6 mm、机械贯通过孔及过孔双面盖油，不要求高密度互连、填孔／盖帽或修改子板。当前审查用制造压缩包已在交付目录索引，尚不是放行订单。

E73 有五个实际连接的底部焊盘，只焊模块边缘不够；需要两面锡膏文件、分阶段检查和合适的回流工艺。无需外壳即可开始限流上电、USB 枚举、SWD、原始感应及蓝牙台架检查；有意义的 60 键校准需要装好的 NiZ／定位板机构。实际充电温升、USB 数据、蓝牙距离、静电容干扰和树脂／胶粘配合仍需样机验证。

旧 `hardware/ec60-nrf52840`、中间 `hardware/e73-usb-repair`、旧整机渲染及历史 `scripts/run_e73_review.py`／`scripts/run_audit.py` 对应其他版本，仅供追溯，不能验收当前右下角板。Raytac 资料位于其[独立入口](variants/raytac/BUILD.zh-CN.md)。
