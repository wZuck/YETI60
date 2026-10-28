[英文](README.md) | 简体中文

# YETI60

以 Cipulot EC60 为基础、使用 FELK60 外壳的单 nRF52840 静电容键盘 PCB。保留感应几何、板框和安装孔位置；后侧 USB 子板连接 J1。

> **阶段性设计提交：** PCB、目标固件及树脂外壳派生设计已更新，PCB 图片和动画已同步清理后的板面；下方新增工程装配图及可选电池槽研究。旧摄影风格装配图与此前完整集成报告仍属历史结果。见[阶段记录](docs/design-checkpoint.zh-CN.md)。

## 当前复查

**CAD 导通检查通过，尚未批准生产或证明整机硬件运行。** [完整复查](docs/audit/yeti60-comprehensive-review.zh-CN.md)记录仍需处理的电源布局、目标固件、公差、开关操作、树脂嵌件及线缆／电池问题。

| 范围 | 结果 |
|---|---|
| PCB | 严格 DRC 0 错误／0 断线，268 对实际引脚连接通过；USB 电阻已改为 0 Ω，电源局部路径已缩短，使用七个背面填孔盲孔，需要 HDI 制板 |
| 固件 | 按原理图绑定的新控制核心通过主机 ASan/UBSan；已完成 GPIO/SAADC 与 USB/BLE 目标集成，普通版和校准版构建通过；实机验证待进行 |
| 机械 | 明确暂定 Z 结构下，源 PCB／定位板／壳体无实体相交；胶碗、螺钉和树脂公差未定型 |
| 电池 | 定制 200 mAh 电池包设计包络为 50×20×2.9 mm；供应商签图、独立温度保护及容量验收待完成 |
| 可视化 | PCB 图／动画及独立工程装配图已更新；旧摄影风格装配图待刷新 |

- [工程装配图及步骤](docs/engineering/assembly.zh-CN.md)
- [电池下挖可行性](docs/engineering/battery-study.zh-CN.md)
- [功耗、续航及充电计算](docs/engineering/power-budget.zh-CN.md)
- [材料与采购表](docs/engineering/materials.zh-CN.md)
- [PCB 标记清理](docs/engineering/board-markings.zh-CN.md)
- [完整复查](docs/audit/yeti60-comprehensive-review.zh-CN.md)
- [硬件及特殊制板要求](hardware/ec60-nrf52840/README.zh-CN.md)
- [控制核心、模拟和轨迹](firmware/yeti60/README.zh-CN.md)
- [装配渲染](renders/yeti60-assembly/README.zh-CN.md)
- [PCB 渲染及 360° 动画](renders/ec60-nrf52840/README.zh-CN.md)
- [当前审查索引](docs/audit/README.zh-CN.md)

外壳暂按树脂，信号／射频模拟继续暂缓。项目文档默认英文并提供 `.zh-CN.md`，机器数据字段保持稳定。

基于 [Cipulot/EC60](https://github.com/Cipulot/EC60) 和 [fredlb/felk60](https://github.com/fredlb/felk60)，保留上游作者、许可证和原名称。`EC60-nRF52840.*` 文件名及 `YAECKB` 库标识为技术兼容保留，公开项目名统一为 **YETI60**。
