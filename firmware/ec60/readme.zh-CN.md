# EC60 上游 QMK 说明

[English](readme.md) | 简体中文

60% 静电容 PCB，兼容 GH60 安装孔，支持多种布局。维护者：[Cipulot](https://github.com/cipulot)。硬件：EC60；原硬件可获取状态为 TBD。

在配置 QMK 构建环境后，原键盘定义的示例命令为：

```sh
make ec60:default
make ec60:via
make ec60:default:flash
make ec60:via:flash
```

这些是上游 STM32 键盘定义的命令，不是 YETI60 nRF52840 的编译／刷写命令。参见 [QMK 构建环境](https://docs.qmk.fm/#/getting_started_build_tools)、[make 指南](https://docs.qmk.fm/#/getting_started_make_guide)及[入门指南](https://docs.qmk.fm/#/newbs)。
