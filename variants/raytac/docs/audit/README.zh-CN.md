[英文](README.md) | 简体中文

# YETI60 当前审计

[P2 阶段记录](../design-checkpoint.zh-CN.md)说明当前设计和待供方／实物验收项目；完整复查记录当前证据和验收边界。检查通过不等于批准生产。

[可行性与元件匹配评估](2026-10-28-feasibility-assessment.zh-CN.md)

| 范围 | 当前证据 |
|---|---|
| 干扰与首件验收 | [当前阻塞项、模拟及测量流程](../../../../docs/testing/README.zh-CN.md)；CAD 通过不能代替射频验收 |
| 统一结果 | [各阶段结果](outcome.json)、[一致性](integration.json) |
| 原理图与 PCB | [重新导出的原理图一致性及 ERC](schematic-current.json)、[严格 CAD 检查](../../hardware/ec60-nrf52840/audit-current.json)、[电气复查](yeti60-electrical.json) |
| 固件核心 | [主机消毒器模拟](yeti60-firmware-simulation.json)、[轨迹](yeti60-firmware-trace.csv) |
| 逐图安装 | [28 步指南](../assembly/build-guide.zh-CN.md)、[图像及位号验证](yeti60-build-guide-check.json)、[定位板／铜箔／固件映射](yeti60-key-geometry.json) |
| 机械 | [只读定位板比较](plate.json)、[PCB 元数据](yeti60-pcb-mechanical-metadata.json)、[条件装配](yeti60-assembly.json) |
| 渲染来源 | [几何](yeti60-render-geometry.json)、[装配图](../../renders/yeti60-assembly/README.zh-CN.md)、[PCB 图与动画](../../renders/ec60-nrf52840/README.zh-CN.md) |
| 文档及文件 | [文档检查](documentation-check.json)、[源码清单](source-inventory.json) |

在根目录运行 `python3 scripts/run_audit.py`。需要 KiCad CLI／Python、clang 和 uv，CAD 依赖固定在 `requirements-audit.txt`。可用 `KICAD_PYTHON`、`YETI_CAD_PYTHON` 指定已安装运行环境，KiCad Python 默认采用 macOS 路径。`--baseline <commit>` 指定连通回归基线；`--refresh-renders` 重建 PCB 与装配图，Blender 依赖见 `requirements-render.txt`，PCB 动画需要 ffmpeg。

退出码 0 表示所有已实现的当前方案检查通过。阶段失败返回 1，并阻止依赖阶段执行。使用 `--require-production` 时，若检查通过但生产要求仍未完成则返回 2。每次运行均记录 `design-constraints.json` 中的未完成要求，目前不会授予生产批准。

一致性检查将原理图、连接器、PCB、固件引脚、轨迹、配合几何和每张渲染图绑定到当前源码与生成脚本。验证期间设计文件必须保持字节不变。文件清单不代表逐文件语义批准，不包含上游子模块内部文件及本地编辑器设置。

已移除过时生成器、布线快照、重复历史固件及历史审计输出，保留上游子模块、署名和许可证。当前只检查单 nRF 方案。目标固件构建、C5 选择、默认电池／凹槽及充电计算已完成；供方批准、完整线束／插头验收、器件额定值、制造及实物测试仍待完成。信号及射频检查已开始，最小天线铜区检查已通过，USB 信号完整性和关壳射频仍待验收。

故障注入测试确认反接的 USB 数据契约、过期轨迹、元件碰撞、单张旧图和图片字节变化均会被拒绝；仅在未修改数据的一致性检查通过后执行。

新检出仓库需运行 `git submodule update --init --recursive`，取得固定版本的 EC60 与 FELK60 源几何。

材料、默认 1600 mAh 凹槽／目录筛选、独立装配图和功耗计算已纳入同一审计流水线。[工程证据](yeti60-engineering.json)核对来源、产物和算术；五个负向用例检查图片变更、薄壁、未批准替换、充电电流过大及终止电流过大，目标固件负向用例拒绝只申请 100 mA 的链接描述符。这些不能替代实物验收。

[普通工艺检查](yeti60-ordinary-process.json) · [制板包](yeti60-fabrication.json) · [README 材料一致性](yeti60-materials.json) · [内部连接](yeti60-interconnects.json) · [评估回应](../engineering/assessment-response.zh-CN.md)

扫描源码、按键映射或目标固件 README 等指南来源变化后，用 `python3 scripts/run_audit.py --refresh-guide` 重新生成指南并检查，不能只覆盖哈希。新增 [USB 事件测试](usb-event-policy.json)编译固定 ZMK USB 回调，ARM 目标检查还解码初始化至包装函数及原栈的实际调用。上一轮 USB 事件审查的[重检记录](usb-event-followup.json)保留初次结果及真实重跑命令，属于历史快照，不能替代当前结果；未重跑的失败不能改成通过。

新增[静电容波形研究](../testing/analog-waveform.zh-CN.md)阶段需要 PATH 中的 ngspice 和本机 Clang，并使用 CAD 依赖中的 NumPy／Matplotlib。它从实际核心产生控制序列，以真实网表参数做无源 RC 敏感性模型；不是实测按键电容或运放动态模型。

总审查新增[GPIO 模式与启动清理](../testing/gpio-mode-policy.zh-CN.md)阶段，以实际回调／初始化源码和核心在主机模型上检查，物理漏电及电源轨仍待首板验收。

扫描初始化失败时命令立即返回不可用；运行故障关闭模拟前端、释放已记录按键并拒绝继续采集／保存。两个固件均采用 128 项按键事件队列。见[扫描状态与故障回归](../testing/scan-control.zh-CN.md)，包含实际工作循环、60 键采集和 120 事件突发测试；真实主机送达仍待首板验收。

校准记录现为带独立 CRC-32 的 308 字节，旧 304 字节记录必须重新采集；全局 NVS 设置格式及蓝牙绑定不变。见[校准存储校验与升级](../testing/calibration-storage.zh-CN.md)。损坏注入已覆盖，真实闪存断电仍待首板验收。

新增[固定版本 NVS 中断恢复模型](../testing/nvs-powercut.zh-CN.md)：实际 NVS／校准加载代码完成 14,795 次指定中断试验，覆盖垃圾回收和恢复期间再次中断；哨兵及恢复后再次保存均通过。它不是物理 NVMC／欠压／蓝牙验收。NVS 模型本身只增加测试；已有候选产物可用 `--host-tests-only` 重新验证并发布测试，来源变动则必须完整构建。

NVS 模型这一轮的[指南关联重检记录](nvs-guide-followup.json)保存初次指南哈希失败、跳过项及真实重跑结果。它是该次运行的历史快照；当前状态以总结果为准，未执行的检查不能变成通过。
