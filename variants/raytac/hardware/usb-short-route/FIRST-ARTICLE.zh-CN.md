[English](FIRST-ARTICLE.md) | 简体中文

# Raytac 首板：文件、下单参数与无外壳装配

下一次工程首样使用本修补主板。下列文件已经包含短 USB 输入、修订保险丝、七颗 0805 电源电容和重布后的电源区域。原 `yeti60-raytac-p2-dfm-review.zip` 对应其他布线，不是这块板。

**初步电气验证不需要外壳。** PCB 生产前完成板厂 DFM 确认；接入真实电池前完成电池供方核实；实际 USB／BLE、充电、逐键校准和温升验收在制板后进行。不能要求先有工作正常的实物才能制作首板，也不能把制造文件一致当作实物工作正常或生产验收通过。

## 应该发送哪些文件

候选装配使用 [C04 钢板、修订底壳和八条垫片](MECHANICAL-FIT.zh-CN.md)。原定位耳和开关底部的余量不足，已在文档尺寸限值内完成修补。整键盘适配、泡棉／胶粘性能和带线检修仍未验收；下文的无外壳首板流程可以继续使用。

| 用途 | 文件 | 每把键盘数量 |
|---|---|---:|
| 主板 PCB，上传板厂 | [候选板 Gerber 与独立镀铜／非镀铜钻孔](fabrication/yeti60-raytac-candidate-gerbers.zip) | 1 块 |
| 主板背面钢网，单独下单 | [背面锡膏与板框](fabrication/yeti60-raytac-candidate-bottom-stencil.zip) | 可选 1 张 |
| 裸板电测参考 | [IPC-D-356 网表](fabrication/mainboard.ipc) | 随主板文件提供 |
| 贴装审查 | [75 件元件位置 CSV](fabrication/positions.csv) | 随主板文件提供 |
| 采购及库存分配 | [完整主板补购表](mainboard-purchase.zh-CN.csv)、[通用阻容规格](PASSIVES.zh-CN.md) | 装 75 件；计划用库存 8 件；净补购 67 件 |
| 原生工程 | [PCB](EC60-nRF52840.kicad_pcb)、[原理图](EC60-nRF52840.kicad_sch)、[工程](EC60-nRF52840.kicad_pro) | 同一候选版 |
| 版本识别与检查 | [导出哈希](audit/fabrication-export.json)、[独立制造文件回读](audit/fabrication-check.json)、[钻孔报告](fabrication/drill-report.txt) | 与订单一起保存 |

主板压缩包只有九层 Gerber、两份钻孔及 Gerber 工作描述，不含 C5，也没有混入旧主板图层。钢网包只有 B.Paste 与 Edge.Cuts。钢网通过独立的锡膏层副本排除了 JP1 的两个开口；PCB 铜层仍保留，JP1 留空。不要合并两个压缩包，也不要手工镜像坐标。

另外需要一块 **C5 JSH**：购买已焊好的成品，或另行打印[固定上游版本 C5](https://raw.githubusercontent.com/Unified-Daughterboard/UDB-C-JSH/2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea/production/UDB-C-JSH_5.0_gerbers.zip)，并准备其[七只元件](../bom/daughterboard.zh-CN.csv)。C5 为 18.0 × 16.5 mm、四层、1.6 mm，钢网用 **F.Paste 正面**。自制时仍要处理上游 DFM 审查项；首样用已焊好 C5 更省事。C5 的 USB 保护器件和保险丝必须保留。无需额外 SWD 小板，J3 已在主板上。1.6 mm 金属定位板属于独立的[机械加工件](../../docs/build/key-mechanism.zh-CN.md)，不是 PCB。

## 主板下单选择

| 项目 | 参数 |
|---|---|
| 板材／层数 | 普通刚性 FR-4，**四层** |
| 层序 | F.Cu → In1.Cu → In2.Cu → B.Cu |
| 成品厚度 | **1.6 mm**；1.6062 mm 是 CAD 包络，不是下单厚度 |
| 叠层 | **JLC04161H-7628**，在板厂回传生产图中确认库存叠层 |
| 铜厚 | 外层 1 oz／库存内层约 0.5 oz |
| 尺寸 | **289.387 × 94.600 mm**，包含射频翼板，不能裁掉翼板 |
| 表面／阻焊 | 沉金，绿油，保留功能标识的白色丝印 |
| 过孔 | 普通机械贯通孔，最小孔径／焊盘 **0.30／0.50 mm** |
| 长圆孔 | 原设计保留的两个 **5.0 × 2.2 mm 镀铜贯通槽**，包含在镀铜钻孔文件内 |
| 特殊工艺 | 不选盲埋孔、激光孔、背钻、树脂塞孔或铜盖帽 |
| 过孔阻焊 | 按 Gerber；U5／U6 散热孔正面盖油、背面开放，不以填孔工艺代替 |
| 工厂编号 | 避开感应铜、天线、孔位及元件接触区；要求确认生产文件 |
| 电测 | 按提供的 IPC／原生网络，确认坐标对齐 |
| 贴片服务 | 自焊则关闭；位置 CSV 仅供审查，不是已验证可直接提交的 JLC 自动贴片清单 |
| 钢网 | 背面；0.10 mm 不锈钢为工艺审查起点，复核 U5／U6 开放孔吸锡 |
| 数量 | 每把键盘实际装 1 块，另计平台起订数量及备板 |

叠层及普通制造选择已对照 [JLC 叠层信息](https://jlcpcb.com/impedance)和[制造能力](https://jlcpcb.com/capabilities/pcb-capabilities)核对；这些是设计要求，不是报价或板厂 DFM 验收。回传生产图必须保留完整板框、孔位、阻焊和层序。若平台过孔处理选项与 Gerber 冲突，生产前让板厂确认两个散热孔的例外；[JLC 对盖油与填孔工艺有区分](https://jlcpcb.com/help/article/pcb-via-covering)。

钻孔文件共 **846 处孔／槽：816 处镀铜、30 处非镀铜**，其中有 813 个过孔和两个镀铜槽。29 个安装中心包含装配时不用的 H26；另有四个非镀铜开关定位孔。不能根据装配时的 28 套五金反推制板钻孔数量，应以文件及钻孔报告为准。

## 坐标与钢网检查

Gerber、钻孔与贴装数据使用相同绝对原点，背面 X 不取负。Gerber／钻孔／贴装文件用毫米。IPC-D-356 保留其声明的英寸编码，但导出副本中的辅助原点已归零，回读时先换算单位再比较；原生 PCB 没有因此修改。

独立回读核对 289 个实装器件铜焊盘及网络、全部 75 件元件位置与封装、全部孔槽、板框、两个散热孔的阻焊以及全部 1,444 条 IPC 记录。板框只允许端点在 0.001 mm 内找到唯一相邻点后闭合，实际原始最大端点差约 0.000060 mm。这是公开记录的数值拼接处理，不表示所有 Gerber 端点完全相同。详见[机器检查证据](audit/fabrication-check.json)。

U5 散热孔原生 PCB 坐标为（117.65，145.00）mm；U6 为（133.00，140.80）mm。两者均为普通 0.30 mm 孔，正面阻焊覆盖，背面在散热焊盘内开放。首件回流时检查吸锡与润湿，不购买填孔／盖帽工艺来替代本方案。使用提供的背面钢网文件，不要使用仍包含 JP1 的默认未过滤锡膏导出。

## 没有外壳时需要准备什么

使用[共用机械件与工具清单](../../README.zh-CN.md#一把键盘需要准备的完整材料)，其中主板部分以本候选板的 [75 件补购表](mainboard-purchase.zh-CN.csv)、[F1](F1-SELECTION.zh-CN.md)、[电源元件位置](POWER-LAYOUT.zh-CN.md)、J4／J5 和接线为准。普通阻容可以按规格采购；芯片、模组和连接器仍按受控型号选购。

开台线束准备[指定 SH 胶壳和端子](README.zh-CN.md#增加及变化的材料)：USB 用四根 AWG28 多股铜线，**每根自由长度 250 mm**；电源跳线两根，**每根 300 mm**。这是胶壳出线面到出线面的长度，压接供方另算裁线长度。D−／D+ 绞合，端头散开段尽量短，完成后两根数据线长度差不超过 1 mm。统一用于 SH／PH 时，绝缘外径按 **0.5～0.8 mm**，电阻按[供电压降页中的采购指标](POWER-FEED.zh-CN.md)。开台的独立导线和端头散开段按**至少 10 mm 弯曲半径**布线。数据对轻柔贴合绞合，**绞距至少 20 mm、线对中心线弯曲半径至少 25 mm**；线束外观看着平缓，不代表过紧的绞合没有把单根导线弯得过急。所购线材的厂商最小半径应不大于 10 mm，实际每根线都要满足厂商要求；若厂商要求更大，就增大线圈和绞距。这不代表更紧的关壳 4 mm 路线或 USB 阻抗已经合格，也不强制某个线材品牌。

**1S／4.2 V、1600 mAh 保护电池包仍然需要。** 先取得[供方确认](../../docs/build/battery-vendor-checklist.zh-CN.md)，包括独立温度断充、允许电压／电流、截止／恢复和线序。开台时可以绝缘放在主板旁，但不能用裸电芯替代。J2.1 为 PACK+，J2.2 为 PACK−，J2.3 为相对 PACK− 的 NTC，不能只凭线色判断。初步电气测试无需外壳、嵌件粘接或关壳理线件；有意义的 60 键测试仍需完整指定的 NiZ／定位板／胶碗／弹簧／钢板卫星轴结构。

## 板子到手后从哪里开始

1. 对照本候选板板框、钻孔报告和原生位号检查来料，检查孔位、阻焊、裸焊盘与短路。USB、电池均先断开，JP1 留空。
2. 无变化器件按[图解焊接顺序](../../docs/assembly/build-guide.zh-CN.md)，电源区域改按 [POWER-LAYOUT](POWER-LAYOUT.zh-CN.md)，R30／R31 不装。先焊并检查 U5／U6 与电源阻容，再装模组／模拟前端；F1 使用[当前焊盘](F1-SELECTION.zh-CN.md)。
3. 安装 J4／J5 后按[候选板连接表](README.zh-CN.md#必须采用的连接方式)逐线测通断。电源跳线必须连接：**J5.1 → J1.1；J5.2 → J1.4**，J1.2／3 留空。C5 JSH 的 1／2／3／4 接 J4.1／2／3／4。
4. 主板和 C5 放在绝缘支撑上，背面所有元件离开桌面，松散线束避开感应弹簧、裸焊点和天线。按 [B0～B3 限值](../../OPEN-BENCH.zh-CN.md)测试，但 USB 接线由本页覆盖原 J1 数据线方案。OFF 不隔离充电芯片；测电阻前应拔掉 USB 和电池。
5. 按[候选校准固件与 SWD 说明](firmware/README.zh-CN.md)刷写，再检查 USB 枚举。这些构建与当前候选 PCB 绑定，不能使用 E73 或旧 Raytac 发布目录中的二进制文件。
6. 确认电池身份、极性及供方参数后，先断 USB，再接保护包，执行 B4～B5 电池／充电测试，测量电流、电源轨及温度。重新插 USB，检查校准控制台在充电时仍保持有线连接。
7. 执行 B6 真实逐键校准，刷入候选普通固件，完成 B7 边充边走 USB 输入、拔线转蓝牙和重插测试。记录结果后再制作外壳。只完成电子部分上电不能代替完整按键机构验收。

[关壳装配](ASSEMBLY.zh-CN.md)属于后续阶段：插头检修路径、组合公差、线材回弹、固定及供方机械件仍待验收。原制板包继续暂停，生产验收仍为未通过。经板厂审查的首板用于取得这些后续资格确认所需要的实测数据。

## 重现制造文件检查

在带 Git 历史和已初始化子模块的仓库根目录运行。第一条命令刷新原生检查，后续导出与独立回读要求来源一致；`requirements-cam.txt` 固定回读器版本。以下为本项目使用的 macOS KiCad Python 路径；其他系统应换成包含 `pcbnew` 的 KiCad Python。修改 PCB 或固件后还必须重建相应固件并运行总审查，不能只用这些制造检查放行整个项目。

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 variants/raytac/scripts/check_usb_short_route.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 variants/raytac/scripts/export_usb_short_fabrication.py
uv run --python 3.11 --with-requirements variants/raytac/requirements-cam.txt python variants/raytac/scripts/check_usb_short_fabrication.py
uv run --python 3.11 --with-requirements variants/raytac/requirements-cam.txt python variants/raytac/tests/audit/test_usb_short_fabrication.py
```
