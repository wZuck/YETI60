[英文](README.md) | 简体中文

# YETI60 固件

当前 [nRF52840 控制核心](yeti60/README.zh-CN.md)和[主机模拟](../docs/audit/yeti60-firmware-simulation.json)使用从原理图推导的 GPIO、SAADC 和复用器契约。在仓库根目录运行 `python3 scripts/simulate_yeti60_firmware.py`。

此处只维护当前核心及其测试。原始 EC60 QMK 源码仍保留在具有上游署名的 `EC60` 子模块中，重复历史固件与测试已移除，GPL 许可证保留。

目标模块提供可通过 SWD 刷写的应用、GPIO／ADC 驱动、USB／蓝牙栈及 HHKB 键位映射；实物校准和实际运行仍待样机。主机消毒器测试验证模拟硬件下的逻辑行为，不证明实机可运行。

[可构建目标固件](target/README.zh-CN.md)现提供 YETI60 自定义板、同一可移植核心、ZMK USB／蓝牙 HID、持久校准和普通／校准版 HEX；实机验证仍待样机。
