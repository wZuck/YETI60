[English](gpio-mode-policy.md) | 简体中文

# 模拟 GPIO 配置与初始化失败清理

当前 Raytac 固件将模拟高阻与放电钳位释放映射为 **`GPIO_DISCONNECTED`**，关闭数字输入缓冲、输出驱动和内部上下拉，仍保留模拟焊盘／外设连接。普通版和校准版共用同一辅助函数。本次仅修固件，PCB、元件和制板文件不变。升级使用同包两版并重新校准：GPIO 辅助函数已纳入 v3 校准指纹。

## 发现的问题及修正行为

原来可移植核心的 `Y_HIZ` 和 `Y_OD_RELEASE` 都变成 `GPIO_INPUT`，虽然释放了输出驱动，却开启了数字输入缓冲。这些引脚不通过 GPIO IN 读取；模拟电压上没有必要启用数字接收器，也不符合预期的断开状态。本次不宣称节省了某个实测电流数值。

| 核心请求 | 实际目标标志 | 数字输入缓冲 | 输出／上下拉 |
|---|---|---|---|
| 高阻 | `GPIO_DISCONNECTED` | 断开 | 禁用／无 |
| 释放放电钳位 | `GPIO_DISCONNECTED` | 断开 | 禁用／无 |
| 驱动高电平 | `GPIO_OUTPUT_HIGH` | 断开 | 高／无 |
| 驱动低电平或钳位 | `GPIO_OUTPUT_LOW` | 断开 | 低／无 |

实际目标 GPIO 回调使用 [gpio_modes.h](../../firmware/target/src/gpio_modes.h)。ADC=P0.04、BAT_ADC=P0.05 不接数字 GPIO 驱动、输入缓冲或上下拉；共享感应／钳位 P0.26 在低电平驱动和断开释放之间切换。关闭 AFE 时，五根行线、三根地址线、两根使能、共享钳位及扫描 ADC 先断开，再拉低 AFE_EN。AFE_EN 和 BAT_MEAS_EN 禁用时仍为明确的低电平控制输出。

[固定版本 nrfx GPIO 驱动](https://github.com/zmkfirmware/zephyr/blob/10ba6d0cb38bc3d258775d27982f707599320085/drivers/gpio/gpio_nrfx.c)处理断开模式时不连接输入缓冲，其 GPIOTE 路径会取消引脚初始化。Nordic 将数字缓冲断开与模拟外设访问分别说明。此模式不是电气隔离：保护结构和模拟通路仍存在，不能证明零漏电、电源轨瞬间落零，或物理引脚卡死时仍然安全。

另一处问题是扫描器初始化出错后直接返回：若错误在 AFE 上电后才被发现，可能没有将它关掉。当前初始化函数在核心已初始化时调用实际关闭函数，再返回 `-EIO`。成功初始化仍正常扫描。ADC／GPIO 设备缺失会在 GPIO 设置前拒绝；USB 初始化失败或模型中的 GPIO 错误结束后，AFE 关闭、相关信号脚断开。

此清理针对 AFE，不代表电池隔离。充电／USB 由独立的 [USB 回调策略](usb-event-policy.zh-CN.md)控制；硬件关机自主充电、电池保护和真实电池测试仍沿用已有要求。

## 验证内容及边界

[测试脚本](../../scripts/test_yeti60_gpio_modes.py)逐字提取实际 GPIO 回调和初始化函数，与真实辅助函数、可移植核心一起在 ASan/UBSan 下编译，通过主机驱动模型检查引脚状态。主机 GPIO 标志数值会逐一与固定版本 Zephyr 头文件比较。记录 nrfx 驱动源码哈希，但没有在主机执行真实驱动或芯片寄存器。

| 正向场景 | 检查结果 |
|---|---|
| 正常启动、150 次扫描采样、空闲／恢复、关闭及电池测量 | ADC／释放钳位无数字缓冲、输出或上下拉；AFE 关闭时信号脚断开 |
| 设备缺失 | GPIO／USB 设置前拒绝初始化 |
| USB 初始化失败 | AFE 未上电，信号脚保持断开 |
| AFE 开启后的启动 GPIO 错误 | 拒绝初始化并执行关闭，结束时 AFE 关闭 |
| ADC 读取失败后执行运行时关闭动作 | 核心中止整帧，目标引脚配置结束于断开状态 |

四个错误变体必须失败：重新开启数字输入缓冲、浮空脚请求上拉、将钳位释放改为高电平驱动，以及省略启动失败关闭。这些验证电气／软件约束，不测试实际漏电、电流或损坏的芯片。

[机器证据](../audit/gpio-mode-policy.json)记录五个正向场景、四个被拒绝的错误变体、准确来源哈希和固定头文件／驱动版本。总审查已包含此阶段。另有 CMake 变更测试修改 GPIO 辅助函数，确认校准标识随之变化；同一板型包内普通版／校准版标识仍须一致。

在 Raytac 目录复现：

```sh
python3 scripts/test_yeti60_gpio_modes.py
python3 scripts/test_yeti60_recovery.py
```

第一条需要本机 Clang，以及 `~/.cache/yeti60-zmk-workspace/zephyr` 中的固定版本源码；恢复测试还使用固定构建容器。按[候选固件入口](../../hardware/usb-short-route/firmware/README.zh-CN.md)构建和检查 ARM 文件，扫描来源变化后以 `--refresh-guide` 执行总审查。

## 首板仍需检查

核实真实 GPIO 输入／驱动／上下拉配置和关轨状态；测量漏电、输入负载及电源轨下降过程，不能仅凭标志推断。按[模拟时序研究](analog-waveform.zh-CN.md)在正常／空闲门控，以及 USB／蓝牙／充电负载下重做按键校准和脉冲捕获。确认 SAADC 仍读取指定模拟焊盘，空闲恢复或启动故障后没有误键。主机测试、源码复核和 ARM 构建不能关闭这些实物验收项。

原始依据：[Nordic nRF52840 GPIO](https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/gpio.html)、[Zephyr GPIO API](https://docs.zephyrproject.org/latest/hardware/peripherals/gpio.html)及上面的固定版本驱动。器件／电源轨测量仍需首板。
