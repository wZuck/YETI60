[英文](README.md) | 简体中文

# YETI60 固件

当前 [nRF52840 控制核心](yeti60/README.zh-CN.md)和[主机模拟](../docs/audit/yeti60-firmware-simulation.json)使用从原理图推导的 GPIO、SAADC 和复用器契约。在仓库根目录运行 `python3 scripts/simulate_yeti60_firmware.py`。

此处只维护当前核心及其测试。原始 EC60 QMK 源码仍保留在具有上游署名的 `EC60` 子模块中，重复历史固件与测试已移除，GPL 许可证保留。

当前核心不是可刷写应用。目标 GPIO／ADC、USB／BLE 协议栈、完整 HHKB 键位映射和实物校准尚未完成。主机消毒器测试验证模拟硬件下的逻辑行为，不证明实机可运行。
