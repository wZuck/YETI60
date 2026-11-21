[English](e73-m05-prototype.md) | 中文

# E73 的 M05 维修口试制件

M05 为 CORNER-06 的装拆试验增加两个可拆盖。它保留 M04 的外形尺寸、脚垫位置及上壳、钢定位板和 C5 子板的安装基准。右后脚垫槽完整位于 J4 封盖上，拆盖时脚垫一起取下。CORNER-07 的首件装配使用这套 M05 配置。

![拆开 J2 与 J4 封盖后的 M05 底面](../../hardware/e73-hhkb-corner/audit/m05-access-exploded.png)

## 一套试制件需要的文件和材料

| 零件 | 数量 | 文件或规格 |
|---|---:|---|
| FELK60 尺寸上壳 | 1 | [打印 STL](../../delivery/YETI60-E73/02-mechanical/top.stl) · [STEP](../../mechanical/generated/yeti60-top.step) |
| M05 底壳 | 1 | [打印 STL](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/bottom-m05-REVIEW.stl) · [STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/bottom-m05-REVIEW.step) |
| J2 封盖 | 1 | [打印 STL](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J2-REVIEW.stl) · [STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J2-REVIEW.step) |
| J4 封盖 | 1 | [打印 STL](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J4-REVIEW.stl) · [STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/cover-J4-REVIEW.step) |
| 封盖螺钉 | 4 | M2 × 0.4，头下长度 4 mm，带平底承压面的低头内六角。头部直径 ≤3.90 mm，高度 ≤1.50 mm。SUNCO M2 低头系列的标称头部尺寸为 Ø3.8 × 1.3 mm。[厂商尺寸表](https://th.misumi-ec.com/en/vona2/detail/221005676582/?Tab=codeList) |
| 封盖螺纹嵌件 | 4 | M2 × 0.4，滚花黄铜，Ø3.2 × 2.5 mm，与 C5 规格相同。另备四枚，孔深按本页施工。 |
| 胶和脚垫 | 按需 | 用外壳规定的冷粘胶固定嵌件。使用整机清单中的四个脚垫，其中一个装在 J4 封盖上。 |
| 平行夹头工具 | 每个端口 1 套 | [工具说明](e73-m05-service-tool.zh-CN.md)提供握块打印文件、夹片下料图和试配步骤。 |
| 停放支撑 | 每个端口 1 套 | [支撑说明](e73-m05-parking-support.zh-CN.md)提供两套底座、托架、紧固件和停放顺序。 |

使用韧性工程 SLA 树脂，按毫米、100% 比例打印四件外壳零件，每种各一件。每件从 STEP 和 STL 中选一个文件，两种格式使用同一壳体坐标。树脂完全后固化后复查承压面、脚垫槽和盲孔。避免在这些面上留打印支撑。

## 树脂打印公差与到货检查

嘉立创公布的常规 SLA 尺寸公差为 **100 mm 以内 ±0.20 mm**、**超过 100 mm 为 ±0.30%**，孔径公差为 **±0.30 mm**。尺寸值以无变形、无翘曲且未喷涂为前提。**325.70 mm** 长的外壳按该规则约为 **±0.98 mm**。本项目的功能表面要求各轴 **±0.15 mm**。报价时和工厂确认哪些关键位置可在后固化后量测，按成品复核。[嘉立创打印设计指南第 10 节](https://jlc3dp.com/help/article/3d-printing-design-guideline) · [四件 STEP 回读报告](../../delivery/YETI60-E73/06-validation/m05-print-fit.json)

询价时注明四件按毫米、1:1 打印，避免在合壳台阶、USB 开口、检修盖承压面和螺钉／嵌件孔内布置支撑。功能面避免喷涂和重度打磨。确认后固化之后能否精加工嵌件孔。若采用预留小孔后加工，应在制件前确认小孔尺寸和工序。交付的 STEP 使用成品标称孔径。

| 粘嵌件前检查 | 尺寸与试装方法 |
|---|---|
| 上下壳定位与四颗 M3 螺钉 | 标称孔距 **300 × 90 mm**，下壳通过孔 **Ø3.40 mm**。核对两条对角线，上下壳手动落位，暂时扶住未粘接的嵌件，用四颗实物螺钉试对位。上壳嵌件孔成品 **Ø4.80–4.90 mm**、深 **3.50 mm** |
| C5 子板及外部 USB 插头 | 用已经制作的 C5 核对 **14 × 12.5 mm** 安装孔距。子板按安装高度定位并断电，从外部插拔实际使用的 USB 线，确认可插到底，外壳不刮插头且子板不被顶动 |
| C5 和检修盖的嵌件孔 | 成品 **Ø3.30–3.40 mm**，从各孔的局部承压面量深 **2.90 mm**。固化后先量孔再粘。孔偏小且孔位正确可用限深工具精加工。偏大或偏位的孔标记后交供应商处理 |
| J2 与 J4 检修盖 | 两颗螺钉孔距分别为 **25.35 mm** 和 **17.00 mm**。CAD 单边留缝 **0.35 mm**，螺钉末端标称余量 **0.45 mm**。用实物螺钉检查封盖齐平并能直向取出。J4 盖装好后，右后脚垫完整落在盖内，四个脚垫都能着地 |

M3 螺钉穿过下壳的标称单边余量为 `(3.40 − 3.00) / 2 = 0.20 mm`。两件单轴分别按 ±0.15 mm 和 ±0.05 mm 向相反方向偏移时，平面孔心偏差可达 `√2 × (0.15 + 0.05) = 0.283 mm`。追加打印之前先试配同一套上下壳，并在首件记录中写下成品尺寸、对位结果和实测使用的 USB 线。

### M3 螺钉卡住时的可选后加工

如果后固化的上下壳能自然合拢，但螺钉卡在下壳通孔或头部沉孔，可让加工方用夹具沿四处现有通孔轴线加工。原 Ø5.80 mm 沉孔对 Ø5.60 mm 螺钉头仅留 **0.10 mm** 单边余量，方案同时扩大两级孔径。加工前核对原通孔不大于 Ø3.70 mm，原沉孔半径加它相对通孔的偏心量不大于 **3.30 mm**。用尚未装电子件的下壳加工。

| 位置 | 成品要求 |
|---|---|
| 下壳 M3 通孔 | **Ø3.90 ±0.05 mm**，与头部沉孔同轴 |
| 下壳头部沉孔 | **Ø6.80 ±0.05 mm**，保留承压面标称 Z = 2.59 mm。刀具相对原通孔每轴对中误差不超过 ±0.05 mm，承压面深度变化不超过 0.05 mm |
| 螺钉和垫片 | M3×5，头部 Ø ≤5.60 mm。平垫片厚 0.30 mm，内孔可穿过 M3，外径 **5.50–5.80 mm**，相对螺钉的偏心量不超过 **0.10 mm**。确认螺钉头和垫片能坐平 |

按此处的尺寸和偏差取不利组合，螺钉杆单边余量为 **0.071 mm**，垫片到沉孔壁余量为 **0.021 mm**，垫片最窄承压宽度为 **0.321 mm**。四处 STEP 截面均保留连续 **0.50 mm** 的模拟外壁环和至少 **2.15 mm** 的模拟承压厚度。加工后检查树脂有无裂纹，量实际螺纹啮合，并重新试装螺钉和脚垫。[M3 余量计算和截面回读](../../delivery/YETI60-E73/06-validation/m05-print-fit.json)

## 制作 M05 配套线束

九根导线均按 [M05 自由长度表](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/wire-lengths-m05.zh-CN.csv)制作。自由长度沿绝缘层测量，从一端胶壳出口量到另一端出口或保护包的应力释放面。裁线时按实际端子另计剥皮和压接的余量。试装使用 AWG28 多股铜线，成品绝缘外径最大 0.65 mm。

### 线材和端子采购

可按 **CnC Tech 10064-28-1-0500-0XX-1-TS** 采购短料。规格为 FEP 绝缘、镀锡铜 28 AWG、7 股每股 0.12 mm，按标称股径计算导体截面积约 0.0792 mm²，成品绝缘外径 **0.60 ±0.05 mm**，额定 30 V、105 °C。有库存时按图纸验证同规格即可使用。只标 UL10064 或 AWG28 的线材可能有不同的绝缘外径或股径。 [CnC Tech 规格和颜色表](https://www.cnctech.us/pdfs/10064-XX-1-0500-0XX-1-TS.pdf) · [CnC Tech 变更公告](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/6791/Change%20Notice%20Hook-up-Wire%203-2025.pdf)

| 颜色 | CnC Tech 料号 | 装机自由长度合计 | 含预留采购长度 |
|---|---|---:|---:|
| 红 | `10064-28-1-0500-004-1-TS` | 541.14 mm | 0.75 m |
| 黑 | `10064-28-1-0500-001-1-TS` | 554.13 mm | 0.75 m |
| 白，D− | `10064-28-1-0500-002-1-TS` | 285.19 mm | 0.50 m |
| 绿，D+ | `10064-28-1-0500-007-1-TS` | 285.19 mm | 0.50 m |

上表只计 USB 线束和主板电源桥。另备 **SHR-04V-S 胶壳 3 只、SHR-02V-S 胶壳 1 只、SSH-003T-P0.2-H 端子实装 12 只**。自行压接可买 20 只，留 8 只试压和备用。红、黑、黄电池引线、SHR-03V-S 和 3 只端子计入完整保护包。 [JST SH 尺寸和压接工具](https://www.jst.com/wp-content/uploads/2025/06/eSH.pdf) · [保护包采购规格](../engineering/battery-pack-specification.zh-CN.md)

裁线前先量到货绝缘外径。JST 端子适用 0.032–0.081 mm² 导体和 0.4–0.8 mm 绝缘外径，M05 自身上限为 0.65 mm。本候选线材的图纸尺寸符合两处限制。用 JST 端子对应工装或能核对该搭配的线束商，先试压到货样件。检查导体和绝缘两段压接，确认端子能在胶壳内卡牢。每端在试压件上量线芯端头到胶壳出口平面的距离。实际裁线长度等于表中自由长度加两端的这个预留量。 [绑定本版的线材计算](../../hardware/e73-hhkb-corner/audit/m05-wire-spec.json)

白、绿两根按指定路线绞成一对。FEP 单线的规格没有给出绞成后的阻抗。作为 M05 数据对前，按 [USB 全速验收](../testing/e73-usb-signal.zh-CN.md)验证。

![M05 坐合状态的线束走向与绞线位置](../../hardware/e73-hhkb-corner/audit/m05-harness-plan.zh-CN.png)

| 项目 | 材料与安装位置 |
|---|---|
| J4 到 C5 的 USB 线束 | 两只 SHR-04V-S 胶壳、八只 SSH-003T-P0.2-H 端子。1–4 号逐针直连，两根数据线的自由长度目标均为 285.189 mm。 |
| 主板电源桥 | J5 用一只 SHR-02V-S，J1 用一只 SHR-04V-S，共四只端子。J5.1 接 J1.1，J5.2 接 J1.4，J1 中间两孔留空。交叉处两根电源桥导线都走 USB 线束上方。 |
| 保护包到 J2 | 主板端用一只 SHR-03V-S 和三只端子，针序为 PACK+、PACK−、NTC。实物须为符合规格的完整保护包，试配可用无电量块。 |
| 电池理线件 | 两件新打印件 [BAT-R1](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R1-M05.stl) 和 [BAT-R2](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R2-M05.stl)。中心分别位于外壳 X 186 mm 和 189 mm，两件的 Y 均为 −106.60 mm。[BAT-R1 定位 STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R1-M05.step)与 [BAT-R2 定位 STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R2-M05.step)保留装配坐标。 |
| 其他理线件及胶膜 | 其余 14 件刚性件和 17 片胶膜的下料形状沿用[现有理线件套件](../engineering/e73-retention.zh-CN.md)。两片电池胶膜装到新支架，可对照 [BAT-R1](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R1-film-M05.step) 和 [BAT-R2](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R2-film-M05.step) 的折后模型。 |

### 16 件理线件打印清单

每个链接打印 1 件。胶膜按模板裁切，共 17 片。

| 分组 | 数量 | STL |
|---|---:|---|
| USB 后侧导槽 | 3 | [USB-R1](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-R1.stl), [USB-R2](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-R2.stl), [USB-R3](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-R3.stl) |
| USB 前侧导槽 | 4 | [USB-F1-base](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-F1-base.stl), [USB-F1-lid](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-F1-lid.stl), [USB-F2-base](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-F2-base.stl), [USB-F2-lid](../../hardware/e73-hhkb-corner/mechanical/retention/print/USB-F2-lid.stl) |
| 电源桥导槽 | 7 | [PWR-R1](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-R1.stl), [PWR-R2](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-R2.stl), [PWR-R3](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-R3.stl), [PWR-R4](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-R4.stl), [PWR-R5](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-R5.stl), [PWR-F-upper](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-F-upper.stl), [PWR-F-lower](../../hardware/e73-hhkb-corner/mechanical/retention/print/PWR-F-lower.stl) |
| 电池导槽 | 2 | [BAT-R1-M05](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R1-M05.stl), [BAT-R2-M05](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/BAT-R2-M05.stl) |

两件电池支架按其他理线件的比例和工艺打印。试配壳底时核查标称 0.10 mm 的胶层。线槽内避免溢胶，固定后导线仍需能沿槽轴向滑动。

从 **J4 向 C5** 按下表布置数据对的绞合段。圈数对应 CAD 中心线几何。制作后可用[坐合线束 STEP](../../hardware/e73-hhkb-corner/mechanical/service-case-m05/harness/seated-wires-REFERENCE.step)核对完整走线形状。

| 标记 | 位置 | 中心线段长 | 圈数 |
|---|---|---:|---:|
| T1 | 后侧直段，X 从 312.190 到 230.000 mm，Y 为 −102.000 mm | 82.190 mm | 3.060 |
| T2 | 向前直段，X 为 193.000 mm，Y 从 −126.674 到 −164.500 mm | 37.826 mm | 0.613 |
| T3 | 回程直段，X 为 214.313 mm，Y 从 −164.500 到 −142.000 mm | 22.500 mm | 0.327 |

按新线长，四根供电和回流导线合计 1.095 m。沿用[原充电模型](../engineering/e73-corner-power-process.zh-CN.md)，60 °C 下纳入计算的串联电阻为 0.426 Ω，500 mA 时比 M04 多约 1.55 mV 压降。[M05 线束与试装报告](../../hardware/e73-hhkb-corner/audit/m05-harness.json)记录了计算前提、未计入的损耗，以及按 M05 实际壳体模型检查的三种板厚各七个插头姿态。

## 装电子件前试配封盖

1. 先把两只盖分别放进对应的凹槽，确认可垂直向下取出。每侧标称留缝 0.35 mm，CAD 外表面齐平。修整时保持封盖与底壳齐平，也保留右后脚垫槽原有高度。
2. 四个嵌件盲孔按 **Ø3.35 ±0.05 mm** 修孔。从孔轴中心所在的承压台阶计算，盲孔深度为 **2.90 mm**。冷粘嵌件，外端面比该处台阶内缩 **0.30 mm**。待空壳上的胶固化后再装电池和 PCB。
3. 确认螺钉能压住封盖，末端与盲孔底留有间隙。CAD 中标称螺纹重叠 **2.15 mm**，螺钉末端距孔底 **0.45 mm**。实测头部尺寸和孔底余量，并检查封盖受力、树脂裂纹、嵌件松动及装脚垫后是否摇晃。
4. 将右后脚垫完整贴在 J4 封盖槽内，留出两只螺钉的位置。取下两只盖后可接近 J2 和 J4。试装用无电池尺寸量块代替电池，并保持线束断电。
5. 按上图试放 C5、临时定位的理线件、主板和断电线束。上电前测通断，并核对 J1 中间两孔留空。确认电池侧弯在两只理线件之前形成，USB 前侧回环能向前移动，电源桥留在其上方。拆卸顺序为先 J2、再 J4，最后垂直抬起主板和定位板。在永久固定理线件前，取下封盖验证实际工具空间和导线滑动。

[CAD 报告](../../hardware/e73-hhkb-corner/audit/service-case-m05.json)检查了外形尺寸、四处新增嵌件的支撑、八处原有螺孔保护区、封盖拆出行程，以及打开后 J2、J4 的通道。[关壳装拆检查](../engineering/e73-corner-service.zh-CN.md)记录了配套的线束试验。M05 用于机械试配，仍需验证实际拔插工具、带线完整拆装、承载和反复拆装，之后才能用于正式装配。

上壳和封盖已拆下且两个插头已停放时，[连续抬升报告](../../hardware/e73-hhkb-corner/audit/m05-lift.json)检查了三种板厚下 25 mm 的直线行程。模型中的电源桥与所检静止物体始终至少保有 0.15 mm 间隙。报告也核对了移动的 PCB 和刚体包络与全部七根静止导线之间的空间。实际插头拔出、导线随动和工具受力仍需用样件验证。
