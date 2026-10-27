# YETI60 nRF52840 控制核心模拟

[英文](README.md) | 简体中文

`core.c` 是按当前 MDBT50Q-1MV2 引脚设计的新可移植控制核心。`board_pins.h` 从原理图 XML 和模块引脚契约生成；扫描使用 P0.04/AIN2，电池测量使用 P0.05/AIN3。

在项目根目录运行：

```sh
python3 scripts/generate_yeti60_pin_contract.py --check
python3 scripts/simulate_yeti60_firmware.py
```

测试将实际核心 C 源码编入主机程序，并启用 ASan/UBSan。覆盖全部 75 个扫描位置、多路选择器地址及分组、开漏充放电顺序、单行驱动、等待时序、滞回与两帧去抖、ADC 故障中止整帧及释放按键、模拟前端断电高阻、USB100/USB500/挂起控制、按住按键时 USB/BLE 报告切换、启动协议溢出、发送失败重试、重入排除和电池分压开启后 50 ms 等待。固定种子的 2000 帧噪声场景检查滞回带内的逻辑行为。

核心还检查 HAL／配置自引用重新初始化、无效 USB 模式值，以及切换输出时旧主机清键失败后的重试。成功扫描帧导出为 [CSV 轨迹](../../docs/audit/yeti60-firmware-trace.csv)，并提供[根据轨迹绘制的图表](../../renders/yeti60-firmware/README.zh-CN.md)。

## 限制

这是模拟 GPIO、ADC、HID 传输接口的主机执行，**不是** nRF52840 目标固件、寄存器／指令模拟、USB 枚举或蓝牙配对／无线测试。`usage[][]` 由调用者传入，测试键码不是完整 HHKB 键位。应用层、硬件 HAL 和真正 USB/BLE 栈仍需接入。

阈值和等待时间均为示例配置，不能作为实物校准结果。电池换算假定 12 位 SAADC、0.6 V 参考、1/6 增益及 1M:1M 分压；硬件必须正确配置并串行使用共享 ADC。USB 电流限制须遵循枚举授权，NTC 保护由充电芯片硬件承担。

结果与源码哈希见 [模拟报告](../../docs/audit/yeti60-firmware-simulation.json)。原 GPL EC60 扫描参考保留在 `firmware/ec60/`，其测试不能证明 nRF 支持。
