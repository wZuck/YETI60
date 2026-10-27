[英文](README.md) | 简体中文

# YETI60 主机模拟轨迹

![去抖轨迹](debounce.png)

[矢量 SVG](debounce.svg)绘制[实际核心 CSV 轨迹](../../docs/audit/yeti60-firmware-trace.csv)中首个按键的前四帧，显示配置的两帧按下／释放去抖。时间只累计模拟等待和 ADC 采集，不是 CPU 性能或实际键盘延迟；ADC 数值和阈值均为示例，不验证模拟噪声或 BLE 表现。

先运行 `python3 scripts/simulate_yeti60_firmware.py`，再在 Matplotlib 环境运行 `python scripts/plot_yeti60_simulation.py`。参见[固件说明](../../firmware/yeti60/README.zh-CN.md)。
