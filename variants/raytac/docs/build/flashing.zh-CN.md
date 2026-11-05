[English](flashing.md) | 简体中文

# 刷写、串口与逐键校准

本页命令已指向当前候选板固件目录，普通版和校准版必须配套；旧 `firmware/releases` 为参考板构建。USB 接线使用[候选 J4／J5／J1 表](../../hardware/usb-short-route/README.zh-CN.md#必须采用的连接方式)，不是旧四线直连 J1。

返回[总入口](../../BUILD.zh-CN.md)。以下为首样待实测的操作程序，不是已经完成的实机刷写记录。准备支持 nRF52840 的 CMSIS-DAP SWD 调试器、OpenOCD，以及本版六针探针治具；不要购买另一个键盘控制板作为替代。

## 连接 J3

先断开 USB 与电池，按[第 16 步图](../assembly/images/16-step.zh-CN.png)和实际焊盘编号接线。J3 不是标准 ARM 插座针序，禁止直接插未核对的成品排线。

| J3 编号 | 接调试器 |
|---|---|
| 1，+3.3V | VTref／目标电压参考；不作为第二路 3.3 V 供电 |
| 2，SWDIO | SWDIO |
| 3，GND | GND |
| 4，SWDCLK | SWCLK |
| 5，RESET_N | nRESET |
| 6，GND | GND |

确认没有电源反灌后，通过已检查的 C5 USB 通路给板子供电，电池先不接；测量 3.3 V。OpenOCD 需包含 `interface/cmsis-dap.cfg` 和 `target/nrf52.cfg`。若改用 J-Link，使用对应 `interface/jlink.cfg`，仍须确认工具确实支持目标，不混用探针接口文件。

## 写入校准版

从仓库根目录进入 Raytac 目录：

```sh
cd variants/raytac
openocd -f interface/cmsis-dap.cfg -c "transport select swd" -f target/nrf52.cfg \
  -c "adapter speed 1000; program hardware/usb-short-route/firmware/releases/calibrator/yeti60-raytac.hex verify reset exit"
```

这里只是候选的 1 MHz 调试起始速度，不是已实测速度。必须看到编程和校验成功再继续；失败时先检查供电、地、针脚接触和目标识别，不能直接执行 recover 或整片擦除。已有设置会被 recover／mass erase 清除。参考 [OpenOCD 官方 program 文档](https://openocd.org/doc/html/Flash-Programming.html)。

## 打开校准串口

校准固件配置 USB CDC ACM shell。电脑上找到新出现的实际串口，macOS 通常为 `/dev/cu.usbmodem…`、Linux 为 `/dev/ttyACM…`、Windows 为新的 COM 口。用串口终端打开该口，可先设置 115200、8N1、无硬件流控；CDC 线路参数不等于模拟扫描频率。不要猜测固定设备号；本项目还没有实机枚举证据。

装好真实轴座、胶碗和锥形弹簧后，全部松键，发送：

```text
yeti_calibrate release
```

等待 128 帧采样完成提示。然后打开[60 键命令表](../../firmware/target/calibration-keys.csv)，每次只操作一个键：**先完全按住目标键，再发送表中对应命令**，保持到该键 128 个采样完成再松开，例如：

```text
yeti_calibrate press 0 0
yeti_calibrate status
```

示例 `0 0` 只演示语法，不能代替 60 键映射表；不能同时按下所有键代替逐键采样。状态必须显示所有实装键有效，无饱和、分布重叠或保护区间失败，然后发送：

```text
yeti_calibrate save
```

确认保存成功；失败不能当成已完成。分布不合格时排查接触、结构、供电和噪声，不能取消保护条件来通过。

## 写入普通版并复测

```sh
openocd -f interface/cmsis-dap.cfg -c "transport select swd" -f target/nrf52.cfg \
  -c "adapter speed 1000; program hardware/usb-short-route/firmware/releases/normal/yeti60-raytac.hex verify reset exit"
```

只写入 HEX 涉及的应用区域，保留 `0xF0000–0xFFFFF` 的末尾 64 KiB 设置区；不加整片擦除命令。固件检查器会检查分发文件的地址范围和描述符，但实际调试器写擦行为仍须首件确认。PCB、引脚、设备树或校准算法指纹变化后必须重新校准，不能复用旧数据。

最后验证 60 键、USB 配置后边充边输入、USB 挂起恢复和拔线后蓝牙回退，并在最终外壳内重复测试。更详细的功能边界见[目标固件说明](../../firmware/target/README.zh-CN.md)与[验收流程](../testing/README.zh-CN.md)。
