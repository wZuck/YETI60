[English](README.md) | 简体中文

> **历史方案，已停止采用。** 当前按用户要求改为单颗 nRF52840，移除 STM32 和双主控 SPI 桥接。见 [当前设计](../../hardware/ec60-nrf52840/README.zh-CN.md)。

# EC60 BLE 接口原型 BLE-IF-0.2

从 EC60 `b9c04625bb9944f6fb806aa571da8592cdff8565` 派生，原作者 Cipulot，附 `LICENSE.EC60`。打开 `EC60-BLE-Interface.kicad_pro`，主图内有 J2 的 SPI2 接口。配套本地符号库为 `YAECKB.kicad_sym`。

本项目目前只包含 **USB 供电下的接口原理图**，用于设计审阅和后续控制器调试。没有对应 PCB 布线、蓝牙模块电路、锂电池电源电路或控制器固件；J2 的生产封装尚未选定。不能据此直接打样或连接锂电池。

J2：1=SYS_3V3，2=GND，3=SCK，4=MOSI，5=MISO，6=CS_N，7=IRQ_N，8=RESET_N。STM32 作 SPI 主机，nRF52840 作从机。SYS_3V3 是系统稳压电源，不是电池端；外接模块之前需确认供电余量与上电顺序。

在仓库根目录重建与检查：

```sh
python3 scripts/build_ble_interface.py
python3 scripts/check_ble_interface.py
```

重建脚本会覆盖本目录生成的原理图、本地库和项目文件，修改接口时先修改脚本。检查结果见 `validation.json`。本轮已核对原有电气连通性保留、扩展引脚未占用；派生图的 ERC 电气错误已清零；补齐原本未标注的 NC 引脚、纠正 VCAP1 的引脚电气类型，并将冗余 3.3V 电源标志移到真实 USB VBUS 输入。上游库、网名和网格等警告仍待处理，详见 validation.json；零 ERC 错误不代表已通过制造审查。

详见[改版方案](../../docs/felk60-bluetooth.zh-CN.md)，其中记录了 HHKB 参考来源、电源改版、低功耗和装配方面尚待完成的工作。
