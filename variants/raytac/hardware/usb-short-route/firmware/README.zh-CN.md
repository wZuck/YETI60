[English](README.md) | 简体中文

# USB 修补候选板固件

本固件必须与 SH 三针电池插座修订配套。校准版和普通版须成套使用；PCB 指纹变化后重新采集阈值。

静电容扫描已修正为先释放再升行、先钳位再降行；见[模拟时序研究](../../../docs/testing/analog-waveform.zh-CN.md)。校准版新增 `yeti_calibrate timing`，报告行 GPIO 调用至 ADC 返回的 RTC 粗略耗时及计时频率，含一格量化余量；实际为 32768 Hz，不能据此确定精确采样时刻。升级后用同包两版重新校准。

USB 充电控制已改为[状态回调及取消配置处理](../../../docs/testing/usb-event-policy.zh-CN.md)，不再等待扫描轮询。挂起禁充／输入高阻；恢复和 500 mA 授权按实际配置字节处理。两版共用此逻辑，从旧包升级需重新校准。

[恢复和校准兼容性](../../../docs/testing/firmware-recovery.zh-CN.md)：Fn＋双击 Backspace 仅清除当前蓝牙槽位。新的 v3 信号指纹会拒绝旧校准；需使用本固件包重新采集，并使用配套普通版。

这些文件只用于[本候选板及其两条必要线束](../README.zh-CN.md)。候选板仍属工程版本，尚未发布制板包。正常版和校准版已按本板重新使用锁定的 ZMK／Zephyr 依赖构建，核对 ARM 固件，并执行主机侧控制及校准测试。没有进行实物刷写或测试。

| 用途 | SWD HEX | 平坦二进制 |
|---|---|---|
| 通过 USB 采集真实按键校准数据 | [校准版](releases/calibrator/yeti60-raytac.hex) | [校准版 BIN](releases/calibrator/yeti60-raytac.bin) |
| 正常 USB／BLE 键盘 | [正常版](releases/normal/yeti60-raytac.hex) | [正常版 BIN](releases/normal/yeti60-raytac.bin) |

沿用原有 [SWD 刷写及目标固件说明](../../../firmware/target/README.zh-CN.md)。应用起始地址为 0x00000000，不假设存在 UF2 引导程序。从校准版切换到正常版时保留校准／设置区，采集完数据后不能再进行整片擦除。J3、GPIO 分配和静电容校准流程保持不变。仅 USB 供电前必须接好 J5 → J1 电源跳线。

[发布清单](manifest.json)记录候选 PCB 指纹、当前来源哈希和下载产物哈希。[构建证据](build.json)、[目标检查](target-check.json)、[主机模拟](simulation.json)、[校准测试](calibration.json)、[主机轨迹](trace.csv)保留本轮证据。两版已链接的 USB 配置均声明 500 mA，但描述符检查不能证明实物主机已经完成配置或授予该电流。

复制的构建／测试报告中的路径均相对于独立目录 `.assembly-work/usb-short-build`；发布清单另行给出相对于 Raytac 正式目录的文件路径。ELF 文件留在该忽略目录中并记录哈希，需要调试时可重新构建，避免在工程候选目录重复存储大型调试文件。

在仓库根目录执行，前提是本候选板的原生及 CAD 检查已通过：

```sh
python3 variants/raytac/scripts/prepare_yeti60_workspace.py
python3 variants/raytac/scripts/build_usb_short_firmware.py
python3 variants/raytac/scripts/check_usb_short_firmware.py
```

封装脚本将当前固件源码、候选 PCB／网表和引脚表复制到独立构建目录，在锁定的容器中构建两版固件，执行目标、主机及校准检查，最后只发布本候选板的 HEX／BIN 和证据，不覆盖正式目录中的固件。所需主机工具、准确初始化命令及自定义工作区见[新检出仓库的构建环境说明](../../../docs/build/firmware-environment.zh-CN.md)。USB／BLE 射频、真实按键、边充边输入、模拟信号建立时间及电池安全仍须按实物验收流程检查。

模拟 GPIO 和初始化失败清理见[说明](../../../docs/testing/gpio-mode-policy.zh-CN.md)及[本包独立主机证据](gpio-mode-policy.json)。两版均使用关闭数字缓冲的高阻模式；升级后重新校准。

扫描初始化失败时命令立即返回不可用；运行故障关闭模拟前端、释放已记录按键并拒绝继续采集／保存。两个固件均采用 128 项按键事件队列。见[扫描状态与故障回归](../../../docs/testing/scan-control.zh-CN.md)，包含实际工作循环、60 键采集和 120 事件突发测试；真实主机送达仍待首板验收。

校准记录现为带独立 CRC-32 的 308 字节，旧 304 字节记录必须重新采集；全局 NVS 设置格式及蓝牙绑定不变。见[校准存储校验与升级](../../../docs/testing/calibration-storage.zh-CN.md)。损坏注入已覆盖，真实闪存断电仍待首板验收。

新增[固定版本 NVS 中断恢复模型](../../../docs/testing/nvs-powercut.zh-CN.md)：实际 NVS／校准加载代码完成 14,795 次指定中断试验，覆盖垃圾回收和恢复期间再次中断；哨兵及恢复后再次保存均通过。它不是物理 NVMC／欠压／蓝牙验收。NVS 模型本身只增加测试；已有候选产物可用 `--host-tests-only` 重新验证并发布测试，来源变动则必须完整构建。

空闲后短按修补已包含在两个固件中：首个有效待确认边沿恢复 4 ms 扫描，保留两帧消抖。见[模型证据及边界](../../../docs/testing/scan-control.zh-CN.md)。扫描器指纹已变化，升级后重新采集 60 键，刷本目录配套普通版。

[本包独立键位／HID 证据](key-pipeline.json)与[完整说明](../../../docs/testing/key-pipeline.zh-CN.md)覆盖基础／Fn／松键顺序及六键上限。本轮仅增加测试，镜像与校准标识未改变；不因这项测试而重新采集。

[本包目标检查](target-check.json)新增实际 ELF 的 HID 报告映射、对象大小／编号、USB 端点和蓝牙 Report Reference 核对，详见[格式和运行时边界](../../../docs/testing/key-pipeline.zh-CN.md#已链接的-usb蓝牙报告格式)。仅更新检查与证据，固件镜像和校准标识未改变。

本次[封装及阻焊修补](../PACKAGE-MODELS.zh-CN.md)改变 PCB 指纹。使用本目录新构建的校准版／正常版配套文件；从旧版更新需重新校准。
