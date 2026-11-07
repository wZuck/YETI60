[English](BUILD.md) | 简体中文

# YETI60 Raytac 当前下单与制作总入口

先打开[当前首板文件与下单参数](hardware/usb-short-route/FIRST-ARTICLE.zh-CN.md)。本版使用 Raytac MDBT50Q-1MV2、修补后的 USB／电源布线、C04 定位板及修订底壳。早期长 USB 制板包、七线装配和参考固件保留作工程参考；本次制作采用本页链接的当前文件。

首板可不制作外壳。生产前取得板厂 DFM 确认，连接真实电池前取得保护包确认，USB／蓝牙、充电、逐键校准及机械实测安排在制板之后。当前软件／CAD 证据不能证明实物工作正常或批准量产。

## 找到需要的文件

| 要做什么 | 当前文档／文件 |
|---|---|
| 封装模型、散热焊盘与普通阻焊工艺 | [模型、铜盘、钢网及阻焊岛](hardware/usb-short-route/PACKAGE-MODELS.zh-CN.md) |
| 下单主板及钢网，选择 JLC 参数 | [首板下单表与下载](hardware/usb-short-route/FIRST-ARTICLE.zh-CN.md) |
| 买主板元件、抵扣库存 | [75 件补购 CSV](hardware/usb-short-route/mainboard-purchase.zh-CN.csv)、[通用阻容／灯规格](hardware/usb-short-route/PASSIVES.zh-CN.md)、[已选 F1](hardware/usb-short-route/F1-SELECTION.zh-CN.md) |
| 购买或自行焊接 C5 JSH | [七件 C5 材料及库存](hardware/bom/daughterboard.zh-CN.csv)、[固定版本 C5 制板包](https://raw.githubusercontent.com/Unified-Daughterboard/UDB-C-JSH/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/production/UDB-C-JSH_5.0_gerbers.zip) |
| 买 NiZ 轴座、胶碗、弹簧、钢板卫星轴、钢丝及键帽 | [K01—K07 机构清单](docs/build/key-mechanism.zh-CN.md)；定位板采用下行的 C04 文件 |
| 加工钢板、打印外壳与理线件、装垫片 | [C04 尺寸、公差和八条垫片](hardware/usb-short-route/MECHANICAL-FIT.zh-CN.md)、[关壳线束及 16 件理线件](hardware/usb-short-route/CLOSED-CASE.zh-CN.md) |
| 从裸板开始焊接 | [焊接停检点](docs/build/soldering.zh-CN.md)、[28 步参考配图](docs/assembly/build-guide.zh-CN.md)；变化位置以当前[电源位置](hardware/usb-short-route/POWER-LAYOUT.zh-CN.md)、[F1](hardware/usb-short-route/F1-SELECTION.zh-CN.md)及[板面／装配图](hardware/usb-short-route/ASSEMBLY.zh-CN.md)为准 |
| 连接 C5 与电源跳线 | [J4／J5／J1 线序与连接器数量](hardware/usb-short-route/README.zh-CN.md#必须采用的连接方式)、[供电压降目标](hardware/usb-short-route/POWER-FEED.zh-CN.md) |
| 从源码构建固件 | [主机工具、工作区初始化及故障处理](docs/build/firmware-environment.zh-CN.md) |
| 刷写及校准 | [当前配套固件下载](hardware/usb-short-route/firmware/README.zh-CN.md)、[J3／SWD 命令及 60 键步骤](docs/build/flashing.zh-CN.md) |
| 不做外壳，包含电池验收 | [B0～B7 开台检查](OPEN-BENCH.zh-CN.md) |
| 检查基础／Fn 键位、松键顺序及同时按键上限 | [矩阵至 HID 链路、六键限制及实测边界](docs/testing/key-pipeline.zh-CN.md) |
| 检查校准保存、损坏拒绝及升级 | [308 字节 CRC 记录、旧格式重采集和实测边界](docs/testing/calibration-storage.zh-CN.md) |
| 检查写入中断及垃圾回收恢复 | [14,795 次 NVS 模型试验与验收边界](docs/testing/nvs-powercut.zh-CN.md) |
| 检查扫描故障、未使用位置、空闲及校准 | [不可用／故障处理、按键释放与事件队列测试](docs/testing/scan-control.zh-CN.md) |
| 检查模拟 GPIO 和初始化故障清理 | [数字输入缓冲断开、AFE 关闭及测试](docs/testing/gpio-mode-policy.zh-CN.md) |
| 检查静电容脉冲和采样时序 | [边沿修补、RC 模型及首板 timing 命令](docs/testing/analog-waveform.zh-CN.md) |
| 检查关机、主控复位与电池漏电 | [默认充电状态、关机电流计算及故障捕获](docs/engineering/power-states.zh-CN.md) |
| 理解 USB 边充边用、挂起和取消配置 | [实际 USB 事件策略与测试证据](docs/testing/usb-event-policy.zh-CN.md) |
| 清除蓝牙槽位、理解校准变化 | [保护手势及版本兼容](docs/testing/firmware-recovery.zh-CN.md) |
| 看当前整机、爆炸图及分步安装 | [候选方案装配指南](hardware/usb-short-route/ASSEMBLY.zh-CN.md) |
| 核实电池及耗电计算 | [供方参数清单](docs/build/battery-vendor-checklist.zh-CN.md)、[电池包规格](docs/engineering/battery-pack-specification.zh-CN.md)、[耗电计算及假设](docs/engineering/power-budget.zh-CN.md) |
| 查看检查证据及未验收项目 | [当前审查](docs/audit/raytac-review.zh-CN.md)、[机器结果](docs/audit/outcome.json)、[实物验收](docs/testing/README.zh-CN.md) |

## 每把键盘准备什么

- 主板 1 块，背面钢网可选 1 张：普通四层 FR-4、1.6 mm、289.387 × 94.600 mm、JLC04161H-7628、普通贯通孔。使用首板入口的候选压缩包，取得板厂 DFM；不能裁掉天线翼板。
- **主板实装 75 件，计划用库存 8 件，净补购 67 件**，不含备件。采购前清点实际库存。R30／R31 已移除，JP1 留空。普通阻容按当前规格买，不限定品牌；芯片、模组、电感、保险丝及连接器仍使用受控型号。
- C5 JSH 成品 1 块；或者 C5 裸板 1 块加七只元件，其中两只电阻计划用库存、五只补购。C5 的保护器件和保险丝保留。它是单独的一块 PCB 订单。
- C5→J4 四线 USB 线束 1 条、J5→J1 两线电源跳线 1 条；J1.2／J1.3 不接。准备 SHR-04V-S 胶壳 3 个、SHR-02V-S 胶壳 1 个、SSH-003T-P0.2-H 实装端子 12 个；买 20 个可留 8 个备件。另备外部 USB 数据线。开台时每根 USB 线自由长度 250 mm、每根跳线 300 mm；关壳长度／半径按关壳指南。
- 1S／1600 mAh 保护包 1 包，三线 PHR-3 接口，匹配 NTC，以及独立电压／电流／温度保护。准确成品包仍须供方确认。六根连接线加三根电池引线，完整当前装配共 **九根线**。电池极性为 J2.1 正极、J2.2 负极、J2.3 相对负极的 NTC。
- C04 定位板 1 张：304 不锈钢，名义 1.6 mm，成品厚 1.55～1.60 mm，**28 处 M2×0.4 攻丝轴线**，H26 不用。订单包含切割与攻丝，不能只激光切底孔。另按 K01—K07 准备 60 套 NiZ 轴座／滑块／原配圈、60 个锥簧、45g 胶碗整张、三组钢板卫星轴、两根短丝、居中 6U 钢丝及匹配键帽。
- 定制黄铜支柱、聚酰亚胺隔离环、PEEK 垫片、M1.6×5 螺钉各 28 件；准确尺寸见[机构与五金规格](docs/build/key-mechanism.zh-CN.md)。攻丝、清洗和去毛刺完成后再靠近电子件。
- 后续关壳再准备：当前上壳、修订底壳各 1 件，理线件 16 件，33×3 mm 垫片 8 条（下层 4 条名义 2.0 mm、上层 4 条名义 1.2 mm），指定 M3 合壳和 M2 子板嵌件／螺钉／垫片、脚垫、绝缘及固定材料。按[共用五金清单](README.zh-CN.md#一把键盘需要准备的完整材料)并采用上述 C04／关壳修订。泡棉性能、安装位置保持力、完整插接检修和组合公差仍需验收。
- 共用工具：ESD 条件、放大镜／显微镜、镊子、焊接／回流设备及匹配耗材、万用表、限流 5 V 电源、可吸收并输出电流的电池模拟器、USB 数据主机及另一把键盘、SWD 探针／自定义 J3 治具、卡尺、电流／温度记录和示波器。自压线另备适合所选 SH／PH 端子的工具。

## 实际制作顺序

1. 核对当前 PCB／制造文件／材料／固件属于同一套。取得板厂 DFM，确认通用元件规格。先装一块，通过后再考虑数量制作。
2. 检查裸板，先焊电源元件／F1；断电检查后才限流上电。变化元件采用当前电源位置和板面图，28 步指南提供保留的焊接顺序。
3. 安装 C5→J4、J5→J1，逐针确认线序及极性。通过 J3 刷当前校准版；不能并联主机 VBUS 与独立 5 V 电源，也不能通过探针反灌。
4. 先用仪器／模拟器完成 B0～B3；供方确认后再接真实保护包，完成 B4～B5。挂起时系统改由电池供电。
5. 在绝缘治具上装完整 C04／NiZ／胶碗／弹簧／卫星轴结构。完成 B6 逐键采集、保存及核查，再刷同包普通版，保留末尾 64 KiB 设置分区。校准标识变化后须重新采集。
6. 完成 B7 及真实边充边 USB 输入、取消配置、挂起／恢复、拔线转蓝牙和重复插拔。记录实物结果；编译与模拟属于另外的证据。
7. 开台验收后再做外壳。使用当前壳体／理线件／定位板和公差限值，测量来料及固定效果。合壳后重新检查全部按键、充电、USB／蓝牙和干扰，不能强行关壳掩盖干涉。
