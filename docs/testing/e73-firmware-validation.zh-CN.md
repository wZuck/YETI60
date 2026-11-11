[English](e73-firmware-validation.md) | 中文

# E73 固件验证与升级

E73 的正常版、校准版 ARM 构建已加入此前在 Raytac 上检查过的扫描、校准、存储、GPIO 和按键上报修补，并针对 E73 自身引脚分配及原生 PCB 重新构建和测试。这关闭了相应软件回归缺口；E73 主板设计、实物模拟信号、USB、射频及充电仍需分别验收。参见[剩余设计门槛](../audit/e73-review.zh-CN.md)。

## 固件与校准

只使用文件名为 `yeti60-e73.*` 的 [E73 正常版](../../firmware/releases/normal/)和 [E73 校准版](../../firmware/releases/calibrator/)。首次通过 SWD 刷入 HEX，其中含有 UICR.NFCPINS = `0xfffffffe`；单独的 BIN 没有该记录。保留内部低频 RC 时钟、REG1 LDO、扫描 AIN4、电池 AIN3 和 P1.13 充电使能。不能与 Raytac 固件互换。[构建记录](../audit/yeti60-target-build.json)及[链接后镜像检查](../audit/yeti60-target-check.json)将两个固件与当前输入绑定。

**升级后重新采集校准。** 当前记录为带应用层 CRC32 的 308 字节格式。304 字节旧记录、版本不符、阈值损坏或 CRC 错误会使键盘保持未校准状态，并禁止上报按键。指纹覆盖原生 PCB、引脚、扫描／核心／控制／GPIO 源码、板级配置及实际扫描选项；正常版与校准版必须使用同一标识。不能跨键盘复制校准记录，采集后不要擦除设置分区。按[60 键采集流程](calibration.zh-CN.md)操作。CRC 用于检测意外数据损坏，不是身份认证或电池安全机制。

按住 Fn，并在 **400 ms 内点按两次退格键**，清除当前蓝牙配置槽。单击或长按不会清除，该组合也不会擦除校准。首次调试准备另一把键盘，并保留 SWD 访问。

## 已执行检查

| 项目 | 证据及范围 |
|---|---|
| 目标构建 | 正常版及校准版 ARM ELF／HEX、E73 的 NFC GPIO UICR、LDO、链接后 USB 500 mA 描述符、USB 回调包装、HID 布局及扫描配置 |
| GPIO | [5 个正向场景、4 个被拒绝的错误改动](../audit/gpio-mode-policy.json)；150 次采样转换、模拟引脚断开模式、启动及故障关断 |
| 扫描控制 | [15 个正向场景、17 个被拒绝的错误改动](../audit/scan-control.json)；60 个有效键、15 个无效位置、串行校准采集、故障、唤醒／空闲，以及 128 项队列容纳 120 个突发事件 |
| 按键上报 | [6 个场景、4 个被拒绝的错误改动](../audit/key-pipeline.json)；实际编译后的映射和键绑定、跨层释放顺序、主机报告、六键同时上报及全部释放 |
| 校准记录 | [独立 CRC 核对](../audit/calibration.json)；512 组参考记录，拒绝 2,464 次单比特翻转、308 次字节反转、2,433 次滑动 32 比特突发损坏 |
| 存储中断 | [14,795 次有边界的 NVS 断电模型试验](../audit/nvs-powercut.json)；首次保存、重写、替换旧格式、垃圾回收及恢复中再中断；检查无关数据保留和恢复后再次保存 |
| 恢复手势 | [固定版本上游点按处理执行和 10 个 CMake 故障案例](../audit/firmware-recovery.json) |
| USB 与充电许可 | [11 个回调场景](../audit/usb-event-policy.json)，含取消配置、挂起、拔线和 GPIO 故障；保留 E73 的 GPIO1 测试设备 |
| 扫描波形 | [36 组无源 RC 敏感性分析和 2 个被拒绝的错误切换顺序](../audit/analog-waveform.json)；先释放钳位再拉高行线，先钳位再拉低行线 |
| 组合证据 | [验证汇总](../audit/firmware-suite.json)核对源码／输出哈希和实际编译版本关联；[12 项回归测试](../../tests/audit/test_firmware_suite.py)拒绝损坏及跨版本证据 |

波形分析使用假定的电容、开关电阻和 GPIO 延迟，是示意性的无源 RC 研究，没有完整运放动态模型，也不能证明 NiZ 信号裕量。诊断时钟为 32,768 Hz，并增加一个时钟周期的保守余量；估算值不是 SAADC 采样时间戳。主机消毒器测试及有边界的 NVS 闪存模型无法复现实物 RTOS 竞争、闪存欠压、USB 电气时序或电池行为。

## 复现

使用固定版本 Docker 工作区运行[构建脚本](../../scripts/build_yeti60_firmware.py)，再运行 `python3 scripts/run_audit.py --baseline HEAD`。总检查在组合验证前执行目标镜像、GPIO、扫描、按键流水线、CRC、恢复、NVS 和波形检查。`python3 scripts/check_yeti60_firmware_suite.py` 仅核对已有证据，不重建或重新执行测试。文件检查通过后，运行 `python3 scripts/run_e73_review.py --reuse-artifact-audit --require-design` 获取独立设计结论。在 USB 保护、电池插头检修、NiZ 移植或其他设计门槛未关闭时，设计验收返回非零仍是预期行为。

实物验收仍需首板电源、SWD、实际叠层逐键采集、60 键按下／释放、USB 枚举与充电同时工作、USB／蓝牙切换、空闲唤醒、写入中断、温度保护及射频／模拟信号测量。本文没有将任何实物项目记为通过。
