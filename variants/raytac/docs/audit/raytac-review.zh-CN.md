[English](raytac-review.md) | 简体中文

# Raytac 本轮审查结论

**89 个软件／CAD 审查阶段全部通过；尚未放行生产或证明实物工作。** 本轮只覆盖 Raytac，不把旧双方案报告当作本版验收。

| 范围 | 结果 |
|---|---|
| PCB | 0 错误／0 断线；267 对信号连接 |
| DRC | 保留 102 条非实装图形 courtyard 告警 |
| ERC | 0 错误；183 条继承离网格告警 |
| JLC | 816 个普通机械通孔，盘／孔不小于 0.50／0.30 mm |
| USB / BLE | 普通版／校准版 ARM 构建及 USB500 描述符通过；同时充电与 USB 优先策略已做主机回归 |
| RF | 厂商最小天线投影内四层铜均清空；实际射频待测 |
| BOM | 当前候选板 {'status': 'bounded-plate-switch-design-fit-passed', 'physical_verification': False, 'manufacturing_released': False, 'complete_keyboard_tolerance_qualified': False, 'acceptance_limits_are_measured_requirements': True, 'plate_and_switch_bounded_envelopes_passed': True, 'interfaces': [{'interface': 'plate-bottom-static', 'continuous_envelope_gap_mm': 0.44989992881670965, 'case_coordinate_error_L2_bound_mm': 0.25980762113533157, 'computation_guard_mm': 0.002, 'remaining_air_gap_mm': 0.18809230768137808}, {'interface': 'plate-top-static', 'continuous_envelope_gap_mm': 0.4498999999032992, 'case_coordinate_error_L2_bound_mm': 0.25980762113533157, 'computation_guard_mm': 0.002, 'remaining_air_gap_mm': 0.18809237876796764}, {'interface': 'plate-bottom-continuous-extraction', 'continuous_envelope_gap_mm': 0.44989992881670965, 'case_coordinate_error_L2_bound_mm': 0.25980762113533157, 'computation_guard_mm': 0.002, 'remaining_air_gap_mm': 0.18809230768137808}, {'interface': 'SW100-bottom', 'continuous_envelope_gap_mm': 0.6562000000000001, 'case_coordinate_error_L2_bound_mm': 0.25980762113533157, 'computation_guard_mm': 0.002, 'remaining_air_gap_mm': 0.39439237886466855}], 'switch_budget': {'downward_terms_mm': {'board_growth': 0.15379999999999994, 'shoulder': 0.03, 'film': 0.02, 'installed_plate_Z': 0.1, 'mounted_board_bow': 0.15, 'installed_height': 0.10000000000000009}, 'downward_sum_mm': 0.5538000000000001, 'XY_allowance_each_axis_mm': 0.35, 'bounds_case_mm': [106.625, -125.875, -6.0538, 117.375, -116.375, -1.9999999999999998]}, 'gasket_bearing_checks': [{'layer': 'lower', 'index': 1, 'nominal_area_mm2': 99.0, 'case_expanded_area_mm2': 120.96000000000075, 'case_supported_area_mm2': 120.96000000000075, 'plate_supported_after_XY_allowances': True}, {'layer': 'lower', 'index': 2, 'nominal_area_mm2': 99.0, 'case_expanded_area_mm2': 120.96000000000085, 'case_supported_area_mm2': 120.96000000000085, 'plate_supported_after_XY_allowances': True}, {'layer': 'lower', 'index': 3, 'nominal_area_mm2': 99.0, 'case_expanded_area_mm2': 120.95999999999984, 'case_supported_area_mm2': 120.95999999999984, 'plate_supported_after_XY_allowances': True}, {'layer': 'lower', 'index': 4, 'nominal_area_mm2': 99.0, 'case_expanded_area_mm2': 120.9599999999999, 'case_supported_area_mm2': 120.9599999999999, 'plate_supported_after_XY_allowances': True}, {'layer': 'upper', 'index': 1, 'nominal_area_mm2': 99.0, 'case_expanded_area_mm2': 120.96000000000075, 'case_supported_area_mm2': 120.96000000000075, 'plate_supported_after_XY_allowances': True}, {'layer': 'upper', 'index': 2, 'nominal_area_mm2': 99.0, 'case_expanded_area_mm2': 120.96000000000085, 'case_supported_area_mm2': 120.96000000000085, 'plate_supported_after_XY_allowances': True}, {'layer': 'upper', 'index': 3, 'nominal_area_mm2': 99.0, 'case_expanded_area_mm2': 120.95999999999984, 'case_supported_area_mm2': 120.95999999999984, 'plate_supported_after_XY_allowances': True}, {'layer': 'upper', 'index': 4, 'nominal_area_mm2': 99.0, 'case_expanded_area_mm2': 120.9599999999999, 'case_supported_area_mm2': 120.9599999999999, 'plate_supported_after_XY_allowances': True}], 'gasket_force_creep_and_adhesive_qualified': False, 'remaining': ['Incoming and installed dimensional measurement', 'Other components, caps, NiZ mechanisms, stabilizers and full flexible service motion', 'Foam compression force/creep and adhesive qualification', 'Physical electrical/thermal/RF acceptance'], 'source_sha256': {'scripts/check_usb_short_fit.py': '71968bdc410c1a081413839e34dca6606d1b3366c10dd9e7770ee300eb3075e1', 'scripts/build_usb_short_plate.py': 'ff509c0bca2fb7b8ca5a5005231ecc342f86a17c8b321b21978a0ed4ea80b684', 'hardware/usb-short-route/mechanical-fit-spec.json': 'c001d9d3482061dd4316f647b1a6ddfeecccda4273ab3f0dc088ff38b9c7815b', 'hardware/usb-short-route/audit/plate-build.json': '63e2a2527570ac9f21c8bad0498d4cc9a5764fe4e26a91c254e4164e00b09d84', 'hardware/usb-short-route/audit/assembly.json': '8c28ae26d9f6cd32864922d478e3dd4c3f33a80d1d5fc55837cde221d6d60c36', 'hardware/usb-short-route/audit/closed-assembly.json': 'd70449bc03f9721b7ed20cd5a40feb3649c5568b12d20fb450e269a2b8bad724', 'mechanical/assembly-spec.raytac.json': 'e7c14e76bbd0f26bb5c43ab8526bc897191050dc1127abab7db5acc24d4010c5', 'mechanical/pcb-fabrication-spec.json': '3275b155538b27e78c24cbb83a3d41bb787bbfdadb6c6ef0282db8295d2d3fed', 'mechanical/generated/yeti60-top.step': 'cbd59c41a843802d56e9e1a831e120d5d571e92bb03f21e071c8c2dd6db2947b', 'hardware/usb-short-route/mechanical/yeti60-bottom-short-usb.step': '40a0f23a7e93a365e9b7fe95efce1c276631771eec777c4701f9fcfd86bfecaa', 'scripts/cad_geometry.py': '4199d5ac7069ffe290e42e391eb175b504c140c5a75cbb2ace292846fd64c90b', 'scripts/check_yeti60_assembly.py': '049759707a29a2cb0370e2a11764a1c3856897d56be1f772cccfe5692c34bbce', 'scripts/check_usb_short_closed_assembly.py': '718d0b5748372434949942f5ecf28caa103a9f8c50350aa9a2d8c1500d0e25ee', 'hardware/usb-short-route/interconnect-spec.json': 'f17b44770a579595d699bcf128744ac3af68ad77895621e4dfe7f156bdf8b6d7'}} 件；计划用库存 8 件，净补购 67 件 |

**当前首板采用[短 USB 修补候选包](../../hardware/usb-short-route/FIRST-ARTICLE.zh-CN.md)。** 旧长布线压缩包保留为暂停的参考；不能把旧七线图用于当前九线装配。电池保护包仍待供方确认；完整 USB 链路、模拟稳定性及实物验收仍待首板。见[含电池的开台流程](../../OPEN-BENCH.zh-CN.md)。

扫描故障处理见[专项说明](../testing/scan-control.zh-CN.md)：初始化不可用明确拒绝命令，故障关闭并释放按键；14 个场景和 13 个错误版本验证，128 项事件队列覆盖 120 事件突发。实际主机送达仍待验收。

## 修补与图像复核

- C5 的真实保护通道和接地核对后，删除主板重复 D1 与长 USB 支线，保留 C5 必装的 D1／U1／F1。
- 共享模拟／放电总线标签统一；新导出网表与保存的引脚合同一致。
- 材料、库存、焊接步骤、实装坐标与编号图同步为 75 件。
- 保留的参考爆炸图展示七线；当前候选方案展示九线和 C04 垫片。制作时采用候选装配入口。
- 已改用 NiZ 普通轴座滑块及独立 Cherry 钢板卫星轴；新板 1.6 mm、28 个安装点，H26 不装；保留 60 个感应中心和外形，实际钢丝、卡扣及全行程须首件确认。
- 再次审查修正库存／验收页的旧 29 套五金及渲染说明中的旧 1.2 mm 板厚；中英文均增加错误注入检查，防止回退。
- 现行射频状态明确区分：最小天线铜区检查通过，USB 信号完整性及关壳射频仍待验收；历史审查保留为已标注的快照。
- 修复 Raytac 的 third_party/zmk 失效软链接，使其指向仓库固定版本子模块；新增全部受控软链接检查和缺失来源负向测试。

## 功能核对与测试边界

| 功能 | 本轮证据与尚未证明的部分 |
|---|---|
| 60 键扫描 | [几何及映射](yeti60-key-geometry.json)覆盖 60 键；主机核心覆盖 75 个矩阵位置、迟滞、消抖及 ADC 故障整帧撤销。真实静电容波形未测。 |
| 校准 | [保护区间测试](calibration.json)及目标代码核对覆盖松键／持按／保存、128 帧采样、饱和／重叠拒绝和阈值持久化；真实采样与刷写保留设置仍待验收。 |
| USB 优先 | [实际适配层主机回归](yeti60-firmware-simulation.json)覆盖配置后充电并优先 USB、历史 BLE 偏好、挂起／恢复／复位／拔线和失败重试；USB／BLE 接口为模拟。 |
| 供电 | [电流和定时计算](yeti60-power-budget.json)、控制网络与适配层符合 BQ24074 输入模式；关机自主 USB100 慢充与固件运行时策略不同。实际温度／电流仍待验收。 |
| 固件 | [已有普通版／校准版 ARM 产物](yeti60-target-check.json)再次核对当前来源哈希、刷写范围和已链接 USB500 描述符；固件修改后重建普通版与校准版；这些检查不代表执行过目标固件。 |
| 装配 | [原生装配](yeti60-assembly.json)、[新钢板](plate-mount.json)、28 套五金／H26 留空、1.6 mm 板厚、七根线及图像来源已核对；NiZ 下裙边／卡扣、6U 弯形、预压和局部刚度待实物验收. |
通用阻容与状态灯已改为[按规格采购](../../hardware/usb-short-route/PASSIVES.zh-CN.md)，七处电源电容同步改成 0805 焊盘，并保留库存备注。完整电源区域已重布，反馈／C46 保守路径缩短为 3.555／4.681 mm；[位置与普通散热通孔说明](../../hardware/usb-short-route/POWER-LAYOUT.zh-CN.md)记录设计检查与实测边界。

## 独立的 USB 修补候选板

上述原目录的 PCB、库存与七根线装配图仍对应原布线。新[修补候选板](../../hardware/usb-short-route/README.zh-CN.md)另行通过严格原生检查及 411 组实际连接检查；两路接触路径均为 5.286396 mm，无数据过孔，相邻层地铜中心线投影覆盖率均为 100%。新插座／胶壳局部公差检查及两版固件重建、主机模拟、校准测试通过。候选板仍装 75 件，计划用库存 8 件、补购 67 件，共九根导线。[九线关壳、16 件理线件及完整装配插图](../../hardware/usb-short-route/ASSEMBLY.zh-CN.md)已通过联合几何与来源一致性检查；检修插接路径及实物验收仍待完成，不能据此放行原制板压缩包。下节长线路数值继续用于说明原目录的限制。
当前候选板的[首板制造包及无外壳流程](../../hardware/usb-short-route/FIRST-ARTICLE.zh-CN.md)已经提供；独立回读覆盖 846 处孔槽、289 个实装铜焊盘、75 件贴装、297 个钢网开口及全部 1,444 条 IPC 记录。已排除 JP1 锡膏并统一电测原点。板厂 DFM 在生产前，实物验收在首板制造后；不放行原布线压缩包。
候选板 F1 已选为 [Littelfuse 0466001.NRHF 一次性快断及修订焊盘](../../hardware/usb-short-route/F1-SELECTION.zh-CN.md)。新增[连续垂直扫掠](../../hardware/usb-short-route/SERVICE-PATH.zh-CN.md)确认内部避空已消除标称刚体运动中的翼板阻挡，并修订后部理线夹公差通道；USB／电池插头退出、线束变形和完整公差仍未验收，不能据此批准关壳装配。
原定位耳及开关底部问题已通过 [C04 定位板、底壳凹槽和八条垫片](../../hardware/usb-short-route/MECHANICAL-FIT.zh-CN.md)修补。在规定的成品尺寸与安装误差内，定位板静态／连续取出和开关底部包络通过；定位板至少约剩 0.188 mm 空气余量。原诊断保留为修补前基线。整键盘公差、泡棉性能、带线检修和实物验收仍待完成。
模拟引脚已改为[断开数字缓冲的高阻模式，并清理初始化失败](../testing/gpio-mode-policy.zh-CN.md)。实际回调及初始化函数的五个正向场景通过，四个错误变体被拒绝；候选包独立重复测试。实际寄存器、漏电、瞬态及供电故障仍需首板测量。
静电容扫描修补[释放／充电和钳位／下降沿顺序](../testing/analog-waveform.zh-CN.md)。两个反向变体被实际核心回归拒绝；36 组无源 RC 敏感性计算不替代真实 NiZ 电容、运放动态或采样时刻验收。校准版新增 32768 Hz RTC 粗略耗时诊断，显示频率并计入一格量化余量，不当作精确采样时刻。
固件审查补齐[当前蓝牙槽位恢复与 v3 校准失效规则](../testing/firmware-recovery.zh-CN.md)。两版 ARM 构建的解析设备树已核对 Fn＋双击 Backspace，仅清除当前槽位；实际 CMake 指纹变动和固定版本 ZMK 手势实现经过主机测试。真实配对、模拟时序和充电切换仍需首板验证。
USB 审查修补[回调式禁充与主机取消配置](../testing/usb-event-policy.zh-CN.md)：固定版本 ZMK 原始 USB 回调经过 11 个主机场景测试，两版 ARM 的实际调用目标已核对。实测回调延迟、挂起电流和电池支撑仍未验收。

## USB 布线的具体限制

主板 D+／D− 实际线段中心线分别约 **253.541／249.122 mm**，经过 **4／6 个过孔**。含焊盘接入等桥接的几何接触路径差为 **2.165 mm**；它不是传播延迟差。这里未包含 C5、线束、连接器内部和模组内部。保护导通及 DRC 通过不能证明差分阻抗、回流连续性、共模或 USB 眼图通过；发布制造前需审查完整链路，并在最终线束下实测。

[充电器原厂资料](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [稳压器原厂资料](https://www.ti.com/lit/ds/symlink/tps63031.pdf)。数据手册复核不能代替本板波形和温升实测。

## 仍需实物或供应商证据

- 通用阻容／LED 按采购规格选购，不要求逐颗指定品牌；关键电容偏压下的有效容量及保险丝实际温度降额仍须符合要求。布局修补已通过设计检查，稳定性、纹波和瞬态仍需首板实测。
- 定制电池完整包络、供方签图、允许充电电压／电流及独立温度断充。
- 真实轴座、胶碗、弹簧、稳定机构、树脂公差与线束装配样件。
- 实际 USB 枚举／眼图、边充边输入、BLE、逐键校准、温升／续航及关壳后的干扰测试。
- C5 上游默认 DRC 仍有制造审查项；本轮保护通道通过不等于 C5 已取得制造或 ESD 认证。

[制作总入口](../../BUILD.zh-CN.md) · [完整爆炸图与元件对照](../engineering/exploded.zh-CN.md) · [首件验收流程](../testing/README.zh-CN.md) · [机器审查与来源哈希](raytac-review.json)
