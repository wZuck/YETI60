[English](README.md) | 简体中文

# USB 修补候选板固件

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
python3 variants/raytac/scripts/build_usb_short_firmware.py
python3 variants/raytac/scripts/check_usb_short_firmware.py
```

封装脚本将当前固件源码、候选 PCB／网表和引脚表复制到独立构建目录，在锁定的容器中构建两版固件，执行目标、主机及校准检查，最后只发布本候选板的 HEX／BIN 和证据，不覆盖正式目录中的固件。所需 Docker 和已锁定的 west 工作区见目标固件说明。USB／BLE 射频、真实按键、边充边输入、模拟信号建立时间及电池安全仍须按实物验收流程检查。
