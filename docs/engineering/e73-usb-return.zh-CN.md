[English](e73-usb-return.md) | 中文

# E73 USB 参考面及局部模型阶段记录

**历史阶段记录：**本文描述提交 `7aab295`，证据链接已冻结到该提交，复现也应使用该提交。之后的电源布局修补使本地旧报告失效；当前开发方向为[E73 右下角迁移](e73-hhkb-corner.zh-CN.md)。本文不作为迁移后候选的放行依据。

**候选仍未放行。** 本轮完成[独立 USB 修补方案](e73-usb-repair.zh-CN.md)中的部分主板几何及标称模型检查，不代表整机、线束、电池、射频表现或 USB 合规通过。当前正式选用的 PCB、固件和制造包未替换，继续保留现有 C5 子板。

## 当前检查

| 范围 | 结果 | 证据 |
|---|---|---|
| 实际 USB 路径 | 两路均约 9.969 mm，无数据过孔；计算差值小于 0.001 mm，满足项目 0.05 mm 门槛 | [原生候选检查](https://github.com/wZuck/YETI60/blob/7aab295c219d1e1cf696efc4cdb52380bec64e19/hardware/e73-usb-repair/audit/native-check.json) |
| 数据走线 | 0.3 mm 底层走线；耦合直线段中心距 0.6 mm，焊盘引出和补偿段单独测量 | [受控走线规格](../../hardware/e73-usb-repair-spec.json) |
| 相邻接地参考 | 内层二接地覆盖两路路径中心线，以及全部 18 段数据走线、四个数据焊盘的完整原生铜箔面积 | [回流几何检查](https://github.com/wZuck/YETI60/blob/7aab295c219d1e1cf696efc4cdb52380bec64e19/hardware/e73-usb-repair/audit/return-check.json) |
| 独立接地连通 | 整体为一个连通接地网络，各层仅通过实际接地电镀过孔／通孔焊盘连接 | [回流几何检查](https://github.com/wZuck/YETI60/blob/7aab295c219d1e1cf696efc4cdb52380bec64e19/hardware/e73-usb-repair/audit/return-check.json) |
| 参考面故障 | 能检出修补前 COL14 穿越、USB 下方接地条带被删除、接地电镀桥接缺失 | [三项回归／故障案例](https://github.com/wZuck/YETI60/blob/7aab295c219d1e1cf696efc4cdb52380bec64e19/hardware/e73-usb-repair/audit/return-faults.json) |
| 局部原生模型 | E73 实际位置的 J4、J5、C32 模型分别匹配 6、4、2 处焊接落点；错位连接器不能通过检查 | [局部模型检查](https://github.com/wZuck/YETI60/blob/7aab295c219d1e1cf696efc4cdb52380bec64e19/hardware/e73-usb-repair/audit/local-models.json) |

长度差是 CAD 算术结果，不代表实际蚀刻精度或电气时延。报告中的邻线距离只是几何接近程度检查，不是阻抗测量或 USB 标准门槛。

## 本轮改动

COL14 原先直接切开 USB 接口下方的参考面。现在局部内层二走线绕开数据保护区域，再接回原下方列线主干。感应焊盘、原感应过孔、网络节点及 MCU 分配不变，这次模拟列线改道没有新增过孔；模拟余量和噪声仍需单独验收。

USB 两路现收敛到间距更近的主干，补偿段留在主耦合段之外。检查使用每段实际数据铜箔及完整焊盘多边形，也包含最短接触路径绕过的焊盘内部铜箔。

扩大检查范围后，还发现 USB_FEED 切开了 J4.2 下方的参考面。电源现在从内层一离开局部区域，再在更靠左的位置换至内层二，采用三个普通 0.5／0.3 mm 通孔，没有新增焊盘内过孔或特殊过孔工艺。完整电流、压降和温升验收仍未完成。

修补前回归取自固定提交 `aaa3292547c9831fd3fddfc1c02d843156aec34a`。脚本通过同一个原生读取器导出该实际 PCB 和当前 PCB。连通性及参考覆盖使用相同的规范化正面积接地多边形，数值修复和 1 nm 拼接容差均明确记录。整体接地连通不能单独证明局部参考完整。

## 模型范围

J4、J5、C32 通过 KiCad 原生导出器从此候选逐件导出 STEP，再将实际平面焊脚与此 PCB 的内接铜箔多边形比较，没有继承 Raytac 的装配验收结论。

STEP 文件在本地 `.assembly-work/e73-usb-local-models/` 缓存中生成，报告记录文件哈希、标准模型来源哈希、边界及焊盘匹配结果。使用匹配的 KiCad 10 模型库复现。这些标称模型不能验收供应商尺寸、实物共面度、焊点、最大安装包络、外壳配合或插头退出；其余 72 个实装元件及完整装配尚未完成这项模型闭合检查。

## 复现

J2 现在由 [SH 三针电池检查](e73-battery-service.zh-CN.md)独立检查。两项局部模型研究合计覆盖四个装板元件的落点，其余 71 个装板元件及完整装配仍需完成模型检查。

使用 KiCad Python 生成并检查候选后，执行固定版本的 CAD 环境：

```sh
uv run --python 3.14.7 --with-requirements requirements-audit.txt python scripts/study_e73_usb_return.py
uv run --python 3.14.7 --with-requirements requirements-audit.txt python scripts/check_e73_usb_local_models.py
```

两条命令均支持 `--kicad-python /path/to/kicad/python`。回归需要包含基线提交的 Git 检出目录，仅有源码 ZIP 无法复现该案例。重新生成候选会使派生报告失效，应重新运行原生检查及这两项研究。

后续的[局部接头匹配度检查](e73-usb-local-fit.zh-CN.md)增加候选内部底面修补，以及按先 J5、后 J4 顺序进行的刚性胶壳拔出检查，并计入了明确公差。其他元件模型、柔性线束与整机装配仍不在该结果范围内。

尚需完成：完整元件模型、完整外壳／紧固件公差和带线检修运动、九根导线的线束及理线件、完整 SH 三针电池检修、左侧电源／封装／热设计、候选绑定固件与校准标识及制造包、供应商电池验收，以及实物 USB／蓝牙／模拟采集／射频／充电测试。本阶段没有豁免这些项目。
