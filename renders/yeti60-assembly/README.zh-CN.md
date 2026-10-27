[English](README.md) | 简体中文

# YETI60 装配渲染

这些图是**有条件的装配研究，不是生产批准**。原 FELK60 上下壳、当前 PCB 成品厚度包络及审查后的 1.2 mm HHKB 定位板，采用与[装配检查](../../docs/audit/yeti60-assembly.json)相同的坐标；PCB 到定位板的 4.6 mm 间距暂定。轴体、轴心、键帽、元件外形、材质颜色及电池体积块为示意。

![合盖装配](assembled.png)

![爆炸图](exploded.png)

![电池空间预算](battery-space.png)

绿色块是尚未选型的最大电池空间，不是电池型号或采购推荐，其厚度取决于最终胶碗／轴体结构。

`render-manifest.json` 记录源几何、装配报告、渲染脚本及产物哈希。为展示水平桌面上的键盘，整体按原 7° 楔形旋转；尺寸测量仍使用源坐标。

刷新 KiCad Python `scripts/export_yeti60_mechanical_metadata.py` 的元数据后，在具有 `requirements-audit.txt`、Pillow、KiCad 的环境执行：

```sh
python scripts/check_yeti60_assembly.py
python scripts/render_yeti60_assembly.py
```

本几何研究省略表面铜图案，铜面外观请看独立的 KiCad 原生 PCB 渲染。临时几何／帧保存在已忽略的 `.assembly-work/`。解读匹配结果前请看[完整复查](../../docs/audit/yeti60-comprehensive-review.zh-CN.md)。
