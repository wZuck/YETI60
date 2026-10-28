[英文](README.md) | 简体中文

# YETI60 目标固件

此 ZMK 模块将已测试的可移植扫描核心接入 nRF52840 GPIO／SAADC，并使用当前原理图生成的引脚头文件。ZMK 提供 USB HID、蓝牙 HID、绑定、五组主机配置和持久设置。HHKB 映射依据实际定位板与感应焊盘对应关系，自定义板使用内部低频 RC 时钟，不占用开发板 LED 引脚，应用从地址零通过 SWD 刷写。

## 可复现构建

需要运行中的 Docker。使用 `firmware/target/config/west.yml` 在 `~/.cache/yeti60-zmk-workspace` 初始化 west 工作区，在固定构建容器中执行 `west update`、`west zephyr-export`。清单固定 ZMK 版本，导入的清单指定 Zephyr 与硬件库。随后在本仓库运行 `python3 scripts/build_yeti60_firmware.py --workspace <工作区>`。脚本拒绝修改过的依赖源码，构建普通版与校准版，并将提交号、源码／配置／设备树及产物哈希写入 `docs/audit/yeti60-target-build.json`。

构建容器按摘要固定，临时构建目录已忽略。可分发 HEX、BIN、ELF 位于 `firmware/releases/`。J3 使用本项目自定义 SWD 引脚，连接探针前核对硬件契约。校准后更新普通固件时，保留末尾 64 KiB 设置分区；整片擦除会丢失校准与蓝牙绑定。

## 校准与操作

先刷校准版 HEX，通过 USB CDC 控制台执行 `yeti_calibrate release`、`yeti_calibrate press`、`yeti_calibrate save`。先保持全部按键松开采集，再逐个将实际安装的按键完全按下至少一次，全部松开后保存。扫描持有者线程生成逐键滞回阈值，拒绝幅度不足及 ADC 饱和，并将有效数据保存到 NVS。没有有效校准数据时不发送按键事件。刷普通固件时保持板型及设置分区一致。

Fn 层提供功能键、方向键和五组蓝牙主机选择。USB／蓝牙 HID 与输出切换由固定版本 ZMK 实现。充电器保持 USB100 模式，固件按 USB 状态控制充电引脚。电池报告暂时关闭，待电池与测量接口完成后接入。扫描故障会将模拟前端锁定断电，排查后重启。

编译通过证明能够生成目标二进制。阈值、时序、USB 枚举、蓝牙配对、电流和唤醒仍需首件实测，启动及校准参数目前属于待测工程参数。此固件不声称已经通过实物验收。

所有启用的 ZMK、Zephyr 和 HAL 依赖均锁定到提交；构建器拒绝与清单不同的依赖版本。引脚头文件与设备树的指纹会使旧校准数据失效。
