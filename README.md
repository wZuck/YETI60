# YAECKB

使用 FELK60 外壳、以 EC60 为基础的静电容蓝牙键盘改版。当前方案为**单颗 nRF52840**，同时负责静电容扫描、USB 和蓝牙；移除原 STM32。允许修改 PCB，尽量保持外壳、安装孔和键位不变。

Type-C 位于后侧（数字键／Esc 一侧），经后侧子板连接主板 J1。外壳暂按树脂考虑。

- [当前单主控设计与状态](hardware/ec60-nrf52840/README.zh-CN.md)
- [KiCad 项目](hardware/ec60-nrf52840/EC60-nRF52840.kicad_pro)
- [设计约束](design-constraints.json)
- [原板、机械与固件审查记录](docs/audit/README.zh-CN.md)
- [历史双主控方案](docs/felk60-bluetooth.zh-CN.md)

先完成 PCB 电路、布局、布线和基本电气／制造规则检查，再进行信号干扰模拟。当前仍在 PCB 设计阶段，尚未批准生产；nRF52840 扫描固件、实物装配和射频测试尚未完成。

`EC60/` 和 `felk60/` 保留为上游子模块。派生硬件放在 `hardware/`，EC60 派生设计的许可证见同目录 `LICENSE.EC60`。
