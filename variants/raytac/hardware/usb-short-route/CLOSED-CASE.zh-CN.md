[English](CLOSED-CASE.md) | 简体中文

# 关壳线束与理线件阶段性说明

当前[SH 三针电池接口](BATTERY-SERVICE.zh-CN.md)在改变高度前含 1→2 mm 扇出。采用下表修订电池线长；旧 PH 引线不能与新插头互插。

本轮已包含九根导线连续实体检查、底壳内部避让槽及 16 件可拆理线件。[分步插图与完整装配渲染](ASSEMBLY.zh-CN.md)已与此方案同步；下单包仍待收尾。尚未进行实物装配或电气验收。此版本仍是工程候选方案，原七线插图与制板包不适用于它。

## 底壳

[本版底壳 STEP](mechanical/yeti60-bottom-short-usb.step) · [本版底壳 STL](mechanical/yeti60-bottom-short-usb.stl)

保留 FELK60 外形、原螺孔及嵌件；翼板避空不侵入定位板承托保护区，并在后侧台阶下方增加线束内槽。切槽边界为 X = 190…354、Y = −106.3…−98、Z = −5.25…−1.9 mm，均为原壳体坐标。外包络不缩放。新切槽到所检查外表面的最小名义壁厚为 2.16 mm；扣除原壳体 0.15 mm 线性公差后为 2.01 mm。这个结果只针对新增切槽，不表示原壳体所有位置都具有 2 mm 壁厚。

新增翼板避空 X 357.25～365.25、Y −132.75～−113.75、Z −4.45～12.30 mm，圆角半径 0.5 mm。[连续标称取出检查及限制](SERVICE-PATH.zh-CN.md)单独记录；完整线束拆接尚未验收。后部 USB 路径改为 Y −100.80 mm，夹件前半宽 2.35 mm、后半宽 2.70 mm，须使用更新的 STEP／STL 及下表线长。

## 完整接线

| 线束 | 接法 |
|---|---|
| USB 四线 | C5 JSH 输出 1／2／3／4 → J4.1／2／3／4，依次为供电／D−／D+／地 |
| 电源两线 | J5.1 → J1.1；J5.2 → J1.4；J1.2／3 留空 |
| 电池三线 | J2.1 为保护包正极，J2.2 为负极，J2.3 为相对负极的 NTC |

关壳线束使用 AWG28 多股铜线，绝缘外径不大于 0.8 mm；按 SH 端子的适配范围确认绝缘外径。下表是两端出线口之间的成形自由长度，不是压接下料长度。公差为 ±0.5 mm，供应商须按 STEP 路径预成形并核对。裸板测试用的松放 250／300 mm 线束不是本表中的关壳线束。

| 线束／针号 | 自由长度 mm | 最小设计弯曲半径 mm |
|---|---:|---:|
| USB 1 | 286.55 | 4.00 |
| USB 2 | 296.37 | 5.10 |
| USB 3 | 296.69 | 5.10 |
| USB 4 | 305.40 | 5.50 |
| 电源 1 | 229.95 | 4.00 |
| 电源 2 | 232.20 | 4.00 |
| 电池 1 | 114.92 | 4.00 |
| 电池 2 | 111.61 | 7.00 |
| 电池 3 | 108.63 | 4.00 |

数据对线后段绞合 3 整圈，下行与回升段各翻转半圈，回到 C5 时针序不变。几何长度差约 0.314 mm；几何弯曲半径不低于 4 mm。绞合段用完整包络管检查净空；导线本身另有样条实体。该结果不证明差分阻抗或 USB 眼图合格。供方还需确认电气线材、压接与成形工艺。

## 打印件清单

共 16 件，每个文件打印 1 件。STEP 保留装配坐标；STL 已移到打印原点，部分零件已翻转，使贴合面朝打印底面。不要再次缩放。理线件要求后固化韧性树脂，尺寸验收 ±0.05 mm，清理槽内支撑与毛刺。

| 零件 | 数量 | 打印 STL | 装配 STEP |
|---|---:|---|---|
| USB-R1 | 1 | [USB-R1.stl](mechanical/guides/USB-R1.stl) | [USB-R1.step](mechanical/guides/USB-R1.step) |
| USB-R2 | 1 | [USB-R2.stl](mechanical/guides/USB-R2.stl) | [USB-R2.step](mechanical/guides/USB-R2.step) |
| USB-R3 | 1 | [USB-R3.stl](mechanical/guides/USB-R3.stl) | [USB-R3.step](mechanical/guides/USB-R3.step) |
| USB-F1-base | 1 | [USB-F1-base.stl](mechanical/guides/USB-F1-base.stl) | [USB-F1-base.step](mechanical/guides/USB-F1-base.step) |
| USB-F1-lid | 1 | [USB-F1-lid.stl](mechanical/guides/USB-F1-lid.stl) | [USB-F1-lid.step](mechanical/guides/USB-F1-lid.step) |
| USB-F2-base | 1 | [USB-F2-base.stl](mechanical/guides/USB-F2-base.stl) | [USB-F2-base.step](mechanical/guides/USB-F2-base.step) |
| USB-F2-lid | 1 | [USB-F2-lid.stl](mechanical/guides/USB-F2-lid.stl) | [USB-F2-lid.step](mechanical/guides/USB-F2-lid.step) |
| BAT-R1 | 1 | [BAT-R1.stl](mechanical/guides/BAT-R1.stl) | [BAT-R1.step](mechanical/guides/BAT-R1.step) |
| BAT-R2 | 1 | [BAT-R2.stl](mechanical/guides/BAT-R2.stl) | [BAT-R2.step](mechanical/guides/BAT-R2.step) |
| PWR-R1 | 1 | [PWR-R1.stl](mechanical/guides/PWR-R1.stl) | [PWR-R1.step](mechanical/guides/PWR-R1.step) |
| PWR-R2 | 1 | [PWR-R2.stl](mechanical/guides/PWR-R2.stl) | [PWR-R2.step](mechanical/guides/PWR-R2.step) |
| PWR-R3 | 1 | [PWR-R3.stl](mechanical/guides/PWR-R3.stl) | [PWR-R3.step](mechanical/guides/PWR-R3.step) |
| PWR-R4 | 1 | [PWR-R4.stl](mechanical/guides/PWR-R4.stl) | [PWR-R4.step](mechanical/guides/PWR-R4.step) |
| PWR-R5 | 1 | [PWR-R5.stl](mechanical/guides/PWR-R5.stl) | [PWR-R5.step](mechanical/guides/PWR-R5.step) |
| PWR-F-upper | 1 | [PWR-F-upper.stl](mechanical/guides/PWR-F-upper.stl) | [PWR-F-upper.step](mechanical/guides/PWR-F-upper.step) |
| PWR-F-lower | 1 | [PWR-F-lower.stl](mechanical/guides/PWR-F-lower.stl) | [PWR-F-lower.step](mechanical/guides/PWR-F-lower.step) |

USB-R1…R3 粘在后内槽顶部；USB-F1／F2 为前侧底座与可拆盖；BAT-R1／R2 固定电池三线；PWR-R1…R5 粘在主板背面；PWR-F-upper／lower 是 J1 附近的双层可拆分线架，先放红线，再装下层黑线架。

另需 0.1 mm 绝缘贴合胶用于 13 处底座／主板贴合面；0.05 mm 可拆绝缘胶用于两处 USB 盖及电源下层架的结合面；不超过 0.1 mm 的绝缘保持膜共 12 片。胶层厚度是装配基准，不是任意堆叠值。

## 装配与验收顺序

1. 打印并后固化本版底壳及 16 件理线件；确认新内槽与原嵌件孔，检查槽宽、毛刺和贴合面。
2. 先完成 C5 与主板的独立电源／USB 测试；主板仍为 75 件，使用本候选板材料表，R30／R31 不装。
3. 在主板背面安装电源理线件及 J5 → J1 跳线，按编号逐根量通断。红线走分线架上层，黑线走下层；不能按外观看左右来替代针号。
4. 将 USB 线束按三整圈及两次半圈的路线成形，先把线放入可拆理线件，再安装盖／保持膜；不要把已压接的胶壳硬穿封闭孔。
5. 安装 C5、绝缘垫及保护电池包，按原方案连接三线电池。电池参数仍须按供应商核对表确认。
6. 保持理线盖／固定膜可解除，在主板未完全落座时连接 USB 与电池插头，缓慢落座并整理导线；不能拉着线束强压主板。
7. 在合壳前复核导线与 CAD 路径的偏移不超过 0.25 mm，尤其检查电源跨线下沉段、J1 分线架和后内槽。检查未压到电池、焊点或螺钉头。
8. 先执行裸板电气流程，再合壳检查 USB 边充边输入、BLE、温升和反复开合。拆机时先解除理线固定，再抬起主板；实际插拔和保持力尚待首件验收。

当前通过的是连续实体尺寸检查，覆盖名义板厚和普通 1.6 mm 板的 1.44／1.76 mm 两端。0.25 mm 路径偏移是装配后必须量测满足的验收包络，不能把未经确认的打印、胶层及导线误差自动相加后当作已满足。

[关壳尺寸报告](audit/closed-assembly.json) · [理线件报告](audit/guides.json) · [电池供应商参数](../../docs/build/battery-vendor-checklist.zh-CN.md) · [候选板入口](README.zh-CN.md)
