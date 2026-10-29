[英文](README.md) | 简体中文

# YETI60 目标固件

此 ZMK 模块将已测试的可移植扫描核心接入 nRF52840 GPIO／SAADC，并使用当前原理图生成的引脚头文件。ZMK 提供 USB HID、蓝牙 HID、绑定、五组主机配置和持久设置。HHKB 映射依据实际定位板与感应焊盘对应关系，自定义板使用内部低频 RC 时钟，不占用开发板 LED 引脚，应用从地址零通过 SWD 刷写。

## 可复现构建

需要运行中的 Docker。使用 `firmware/target/config/west.yml` 在 `~/.cache/yeti60-zmk-workspace` 初始化 west 工作区，在固定构建容器中执行 `west update`、`west zephyr-export`。清单固定 ZMK 版本，导入的清单指定 Zephyr 与硬件库。当前 ZMK 使用项目 fork `https://github.com/wZuck/zmk` 的 `0862fc0f8c864834007986efcaf52f292ea6d37d`；相对上游只增加了可配置的可连接广播间隔（`ZMK_BLE_ADV_INT_MIN/MAX`）。随后在本仓库运行 `python3 scripts/build_yeti60_firmware.py --workspace <工作区>`。脚本拒绝修改过的依赖源码，构建普通版与校准版，并将提交号、源码／配置／设备树及产物哈希写入 `docs/audit/yeti60-target-build.json`。

构建容器按摘要固定，临时构建目录已忽略。可分发 HEX、BIN、ELF 位于 `firmware/releases/`。J3 使用本项目自定义 SWD 引脚，连接探针前核对硬件契约。校准后更新普通固件时，保留末尾 64 KiB 设置分区；整片擦除会丢失校准与蓝牙绑定。

## 校准与操作

先刷校准版 HEX。全部松键执行 `yeti_calibrate release`，等待 128 帧完成提示。对 60 个实际按键分别操作：先将目标键完全按住，再执行 `yeti_calibrate press <row> <col>`，保持按住直到该键 128 个采样完成提示后再松开。用 `yeti_calibrate status` 检查样本数、最坏边界及保护裕量，全部有效后执行 `yeti_calibrate save`。不带行列的旧 `press` 命令会被拒绝。扫描持有者线程要求每状态至少 64 个有标签样本，拒绝饱和／重叠分布，以保守的六倍标准差保护值，在最坏边界之间选择严格分离的阈值。采样期间或没有有效校准时不发送按键。新指纹包含引脚、设备树、原生 PCB 和校准算法，旧的乐观校准会失效。写普通固件时须保持同一板型和设置分区。

Fn 层提供功能键、方向键和五组蓝牙主机选择。USB／蓝牙 HID 与输出切换由固定版本 ZMK 实现。P2 申请 500 mA（旧版 Zephyr `CONFIG_USB_MAX_POWER=250`）。仅主机接受配置后启用 USB500 充电；此前保持 USB100 且不充电，挂起时禁充并关闭输入，恢复后保留已接受配置。两个链接 ELF 的描述符均已检查。电池报告暂时关闭，待电池与测量接口完成后接入。扫描故障会将模拟前端锁定断电，排查后重启。

## 空闲功耗策略

扫描线程在有按键或状态变化时保持 4 ms 间隔；连续 30 s 无按键后改为 30 ms，并在空闲帧之间通过 U8/AFE_EN 关断 AFE，下一次扫描前重新稳定。参数由 `YETI60_ACTIVE_SCAN_MS`、`YETI60_IDLE_SCAN_MS`、`YETI60_IDLE_AFTER_MS` 和 `YETI60_AFE_IDLE_GATING` 控制。E73 版本把 REG1 设为 LDO，并关闭 REG0 DC/DC，避免依赖未经核实的模组内部电感。VDD 与 VDDH 同接稳压 3.3 V，DCCH 不连接。BLE 连接优先请求 15–30 ms 间隔并使用 0 dBm；未连接时的可连接广播使用 200–300 ms 间隔（ZMK fork 的 `ZMK_BLE_ADV_INT_MIN/MAX`），主机仍可覆盖连接参数。`CONFIG_ZMK_SLEEP` 仍关闭：EC 键不是 System OFF 的 GPIO 唤醒源，直接启用会导致无法用按键唤醒。

编译通过证明能够生成目标二进制。阈值、时序、USB 枚举、蓝牙配对、电流和唤醒仍需首件实测，启动及校准参数目前属于待测工程参数。此固件不声称已经通过实物验收。

所有启用的 ZMK、Zephyr 和 HAL 依赖均锁定到提交；构建器拒绝不同依赖版本。引脚、设备树、原生 PCB 或校准算法的变化都会使旧校准失效。

E73 发布文件位于 `firmware/releases/{normal,calibrator}/yeti60-e73.*`。HEX 额外将 0x1000120C 的 UICR.NFCPINS 写为 0xFFFFFFFE，释放 P0.09／P0.10 为 GPIO；首次刷写使用 HEX，单独的 BIN 不包含这条显式 UICR 记录。GPIO／ADC 分配专用于 E73，包括扫描 AIN4、电池 AIN3，不能刷写 Raytac 二进制。

[逐键校准操作与拒绝条件](../../docs/testing/calibration.zh-CN.md)；[60 键行列命令表](calibration-keys.csv)。
