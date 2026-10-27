English | [简体中文](README.zh-CN.md)

# YETI60 host-simulation trace

![Debounce trace](debounce.png)

[Vector SVG](debounce.svg) plots the first four single-key scan frames from the [actual core CSV trace](../../docs/audit/yeti60-firmware-trace.csv). It shows the configured two-frame press/release debounce. Time is the sum of modeled waits and ADC acquisition, not CPU profiling or physical keyboard latency. ADC values and thresholds are illustrative; no analog noise or BLE performance is certified.

Run `python3 scripts/simulate_yeti60_firmware.py`, then `python scripts/plot_yeti60_simulation.py` in a Matplotlib environment. See [firmware documentation](../../firmware/yeti60/README.md).
