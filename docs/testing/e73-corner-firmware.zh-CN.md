[English](e73-corner-firmware.md) | [中文](e73-corner-firmware.zh-CN.md)

# E73 右下角 PCB 对应固件

使用 `hardware/e73-hhkb-corner/firmware/` 内的 CORNER-03 构建，包括 `manifest.json`、`releases/normal/yeti60-e73.hex` 正常版及 `releases/calibrator/yeti60-e73.hex` 校准版。根目录迁移前固件和 Raytac 固件不匹配本板的校准身份。[右下角审查](../engineering/e73-hhkb-corner.zh-CN.md)中的设计暂停放行条件仍有效。

当前原生布线、USB 参考地及有界装配检查完成后，重现方式为：

```sh
uv run --python 3.14.7 --with-requirements requirements-audit.txt python scripts/build_e73_corner_firmware.py
python3 scripts/check_e73_corner_firmware.py
```

构建需要锁定版本的 ZMK 工作区、固定摘要的 Docker 镜像，以及正在运行的 Docker 服务。脚本在忽略目录内隔离构建，检查两份 ARM 链接产物，运行核心、校准、USB、GPIO、扫描、按键事件、NVS、恢复及 RC 灵敏度测试，并执行链接目标和套件故障注入测试，通过后才复制固件。`--prepare-only` 仅准备引脚契约；`--development-build` 仅在忽略目录构建测试，不发布镜像。

**首次通过 SWD 写入时使用 HEX**，其中包含将 NFC 引脚释放为 GPIO 的 UICR 记录，BIN 不包含这项显式记录。应用从地址零开始，不假定存在 UF2 引导程序。连接探针前必须核对自定义 J3 针序。按[现有校准步骤](../../firmware/target/README.zh-CN.md)操作，但替换为本候选版 HEX：先刷校准版，完成全部 60 键并保存，再刷正常版，保留最后 64 KiB 设置分区。全片擦除会丢失校准和蓝牙配对；PCB 指纹变化必须重新校准。

两份固件均使用内部低频 RC 时钟和 REG1 LDO。主机完成配置后，可同时充电和使用 USB HID，并优先走 USB；挂起时关闭充电器输入，拔线后允许回退蓝牙。这些是链接产物及主机模型检查，尚无实物 USB、蓝牙、静电容、充电、温升或无线验收。电量上报仍待电池及测量集成完成后启用。被动 RC 模型采用假定寄生参数，并非 PCB／NiZ 提取电容。
