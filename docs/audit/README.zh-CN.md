[English](README.md) | 简体中文

# YETI60 审查索引

优先阅读[电气／固件／装配全面复查](yeti60-comprehensive-review.zh-CN.md)。当前 CAD 导通通过，但电源回路、目标应用及最终机械／制造结构尚未批准生产。

| 范围 | 证据 | 边界 |
|---|---|---|
| 当前 PCB | [严格 CAD](../../hardware/ec60-nrf52840/audit-current.json)、[功能复查](yeti60-electrical.json) | DRC 0 错误／0 断线，268 对引脚通过；路径测量不证明稳定性或 SI |
| 当前 nRF 核心 | [模拟](yeti60-firmware-simulation.json)、[轨迹](yeti60-firmware-trace.csv) | 实际 C 核心运行 ASan/UBSan，外设／传输接口为模拟，不证明目标／无线运行 |
| 当前装配 | [装配](yeti60-assembly.json)、[元数据](yeti60-pcb-mechanical-metadata.json) | 暂定 Z 结构、源板／壳／定位板及电池空间，未批准制造公差 |
| 装配图片 | [渲染](../../renders/yeti60-assembly/README.zh-CN.md) | 壳／板来自源，其他外形含示意 |
| STM32 参考 | [修复测试](firmware.json)、[上游复现](firmware-upstream-reproduction.json) | 行列越界、滞回和配置修复，不是 nRF 固件 |
| 历史 SPI 接口 | [BLE-IF](../../hardware/ec60-ble-interface/validation.json) | 已停止采用的双主控原型 |
| 上游 BOM/CPL | [生产参考](manufacturing-reference.json) | OPA350 误标 U1 恢复为 U3，覆盖原 BOM 51 个位号，不对应新 PCB |
| 定位板／源 CAD | [板](plate.json)、[机械](mechanical.json)、[壳注册](case-assembly.json) | 3 处 owner 元数据修复、63 闭合轮廓、29 孔及源壳体有效性，不批准树脂打印 |
| 后侧 USB | [基准](typec-location.json)、[旧通路](case-assembly.json) | 后侧子板，旧 8×2 mm 芯体不批准真实插头／线缆／CC |
| 原生产包 | [Gerber](gerber-reference.json) | 38 外形图元、653 PTH、28 NPTH 在量化误差内一致；铜／阻焊／钢网仍待审查 |

旧上游 PCB 报告有 25 个 DRC 错误，两块原定位板各有 Edge.Cuts 文字错误；它们是参考源结果，不是当前 YETI60 的零错误 CAD，不要混用生产文件。

运行 `python3 scripts/run_audit.py`，需要 KiCad CLI/Python、clang、uv 和固定的 CAD 依赖。各阶段失败独立记录，依赖失败时跳过；局部通过不代表整体生产批准。总审查未完成时命令仍返回非零。`outcome.json`、`source-inventory.json` 是全范围记录，哈希清单不等于逐项功能审核。上游子模块的本地编辑器设置不作为设计提交。

继续暂缓信号／射频模拟；不宣称树脂嵌件、完整插头线缆、电池包、最终 EC 结构或实机固件／射频已经验证。
