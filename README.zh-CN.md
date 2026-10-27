[English](README.md) | 简体中文

# YETI60

以 Cipulot EC60 为基础、使用 FELK60 外壳的单 nRF52840 静电容键盘 PCB。保留感应几何、板框和安装孔位置；后侧 USB 子板连接 J1。

![名义装配研究](renders/yeti60-assembly/assembled.png)

## 当前复查

**CAD 导通检查通过，尚未批准生产或证明整机硬件运行。** [完整复查](docs/audit/yeti60-comprehensive-review.zh-CN.md)记录仍需处理的电源布局、目标固件、公差、开关操作、树脂嵌件及线缆／电池问题。

| 范围 | 结果 |
|---|---|
| PCB | 严格 DRC 0 错误／0 断线，268 对实际引脚连接通过；USB 电阻已改为 0 Ω，电源局部路径仍待改版 |
| 固件 | 按原理图绑定的新控制核心通过主机 ASan/UBSan；真实 ADC/GPIO/USB/BLE HAL 和目标二进制尚未完成 |
| 机械 | 明确暂定 Z 结构下，源 PCB／定位板／壳体无实体相交；胶碗、螺钉和树脂公差未定型 |
| 电池 | 未选型；暂定结构下有 50×20×2.9 mm 条件包络，不是采购推荐 |
| 可视化 | 当前 PCB 图／动画，以及装配、爆炸和电池空间研究，均声明示意模型限制 |

- [完整复查](docs/audit/yeti60-comprehensive-review.zh-CN.md)
- [硬件及特殊制板要求](hardware/ec60-nrf52840/README.zh-CN.md)
- [控制核心、模拟和轨迹](firmware/yeti60/README.zh-CN.md)
- [装配渲染](renders/yeti60-assembly/README.zh-CN.md)
- [PCB 渲染及 360° 动画](renders/ec60-nrf52840/README.zh-CN.md)
- [审查索引和历史证据](docs/audit/README.zh-CN.md)

外壳暂按树脂，信号／射频模拟继续暂缓。项目文档默认英文并提供 `.zh-CN.md`，机器数据字段保持稳定。中途进展已作为 `8f1b0fc` 推送。

基于 [Cipulot/EC60](https://github.com/Cipulot/EC60) 和 [fredlb/felk60](https://github.com/fredlb/felk60)，保留上游作者、许可证和原名称。`EC60-nRF52840.*` 文件名及 `YAECKB` 库标识为技术兼容保留，公开项目名统一为 **YETI60**。
