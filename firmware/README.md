# EC60 扫描固件审查副本

`ec60/` 来自 Cipulot EC60 `b9c04625bb9944f6fb806aa571da8592cdff8565` 的 QMK 键盘定义。保留源码的 GPL-2.0-or-later 许可声明，附 `LICENSE.GPL-2.0`。它仍是待适配构建的扫描固件，不是已经完成 nRF52840 蓝牙支持的可刷写版本。

已修复：

- 清行函数访问第 6 个引脚，而配置只有 5 行。
- 两组 8 通道扫描访问第 16 列，而矩阵只有 15 列。现在仅扫描有效的 75 个位置。
- 原按下阈值低于释放阈值，可能使稳定的中间值在按下/释放之间来回切换。交换两组数组的用途，恢复正确的滞回方向；实际数值仍需逐键采样校准。
- 配置结构未全部初始化；无效或相等阈值没有被拒绝。现在初始化为零并拒绝无效配置，扫描层在初始化失败时不读取 ADC、清空按键状态。

运行 `python3 scripts/check_firmware.py`，会将实际 `ec_switch_matrix.c` 和 `matrix.c` 编译进测试程序，并开启 AddressSanitizer / UndefinedBehaviorSanitizer。测试覆盖数组边界、复用器通道、75 个位置、滞回阈值边界、无效配置与重新初始化。原源码的两项越界可由 `python3 scripts/check_firmware.py --source EC60/Firmware/ec60 --bounds-only` 复现，该命令预期失败。

测试中的 ADC、GPIO 和临界区是主机模拟，不证明硬件的模拟时序、噪声、供电、阈值校准或唤醒行为。目标 MCU 的 QMK 构建、USB 枚举及 nRF52840 的 SPI/BLE 固件、上电/断连/重连测试仍未完成。不要将上游旧 `.bin` 与本目录修复源码视为同一构建结果。
