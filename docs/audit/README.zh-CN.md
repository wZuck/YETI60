[英文](README.md) | 简体中文

# YETI60 当前审计

[P2 阶段记录](../design-checkpoint.zh-CN.md)说明当前设计和待供方／实物验收项目；完整复查记录当前证据和验收边界。检查通过不等于批准生产。

[可行性与元件匹配评估](2026-10-28-feasibility-assessment.zh-CN.md)

| 范围 | 当前证据 |
|---|---|
| 统一结果 | [各阶段结果](outcome.json)、[一致性](integration.json) |
| 原理图与 PCB | [重新导出的原理图一致性及 ERC](schematic-current.json)、[严格 CAD 检查](../../hardware/ec60-nrf52840/audit-current.json)、[电气复查](yeti60-electrical.json) |
| 固件核心 | [主机消毒器模拟](yeti60-firmware-simulation.json)、[轨迹](yeti60-firmware-trace.csv) |
| 机械 | [只读定位板比较](plate.json)、[PCB 元数据](yeti60-pcb-mechanical-metadata.json)、[条件装配](yeti60-assembly.json) |
| 渲染来源 | [几何](yeti60-render-geometry.json)、[装配图](../../renders/yeti60-assembly/README.zh-CN.md)、[PCB 图与动画](../../renders/ec60-nrf52840/README.zh-CN.md) |
| 文档及文件 | [文档检查](documentation-check.json)、[源码清单](source-inventory.json) |

在根目录运行 `python3 scripts/run_audit.py`。需要 KiCad CLI／Python、clang 和 uv，CAD 依赖固定在 `requirements-audit.txt`。可用 `KICAD_PYTHON`、`YETI_CAD_PYTHON` 指定已安装运行环境，KiCad Python 默认采用 macOS 路径。`--baseline <commit>` 指定连通回归基线；`--refresh-renders` 重建 PCB 与装配图，Blender 依赖见 `requirements-render.txt`，PCB 动画需要 ffmpeg。

退出码 0 表示所有已实现的当前方案检查通过。阶段失败返回 1，并阻止依赖阶段执行。使用 `--require-production` 时，若检查通过但生产要求仍未完成则返回 2。每次运行均记录 `design-constraints.json` 中的未完成要求，目前不会授予生产批准。

一致性检查将原理图、连接器、PCB、固件引脚、轨迹、配合几何和每张渲染图绑定到当前源码与生成脚本。验证期间设计文件必须保持字节不变。文件清单不代表逐文件语义批准，不包含上游子模块内部文件及本地编辑器设置。

已移除过时生成器、布线快照、重复历史固件及历史审计输出，保留上游子模块、署名和许可证。当前只检查单 nRF 方案。目标固件构建、C5 选择、默认电池／凹槽及充电计算已完成；供方批准、完整线束／插头验收、器件额定值、制造及实物测试仍待完成。信号及射频分析暂缓。

故障注入测试确认反接的 USB 数据契约、过期轨迹、元件碰撞、单张旧图和图片字节变化均会被拒绝；仅在未修改数据的一致性检查通过后执行。

新检出仓库需运行 `git submodule update --init --recursive`，取得固定版本的 EC60 与 FELK60 源几何。

材料、默认 1600 mAh 凹槽／目录筛选、独立装配图和功耗计算已纳入同一审计流水线。[工程证据](yeti60-engineering.json)核对来源、产物和算术；五个负向用例检查图片变更、薄壁、未批准替换、充电电流过大及终止电流过大，目标固件负向用例拒绝只申请 100 mA 的链接描述符。这些不能替代实物验收。

[普通工艺检查](yeti60-ordinary-process.json) · [制板包](yeti60-fabrication.json) · [README 材料一致性](yeti60-materials.json) · [内部连接](yeti60-interconnects.json) · [评估回应](../engineering/assessment-response.zh-CN.md)
