[English](README.md) | 简体中文

# YETI60 单 nRF52840 PCB 渲染

图片和动画已从**当前通过 CAD 检查的 PCB**重新生成。每一帧旋转真实三维电路板，不是平面图翻转。

![正反面对照](pcb-overview.png)

![360 度旋转](pcb-turntable.gif)

[MP4](pcb-turntable.mp4) · [GIF](pcb-turntable.gif) · [感应面](pcb-front.png) · [器件面](pcb-back.png)

MP4 为 1600×1000、24 fps、144 帧、6 秒；循环 GIF 为 960×600、12 fps。正反 PNG 为 2400×1500，总览为 2400×1900。

脚本先核对 CAD 源哈希，结束时确认源文件未变，只在渲染副本中调整模型引用。旧 KiCad 6 WRL 路径解析到标准 STEP；J1 使用同型号标准件并按原焊盘修正原点，U2/U4 去掉失效重复模型并保留原 SSOP STEP。

J2 使用厂家侧插 PH 的 5.5 mm 高度建立示意本体，完整对插几何未验证；SW100 为示意，U5 为通用 WQFN。图注标明这些限制。原生分块尺寸差异用透明补边处理，不拉伸 PCB；模型、脚本、源文件、产物哈希及替代记录在 `render-manifest.json`。

在根目录安装 KiCad 10、标准模型库、ffmpeg 和 Pillow 后执行：

```sh
python3 -m pip install --target /tmp/yeti60-render-python pillow==11.3.0
KICAD_AUDIT_PYTHONPATH=/tmp/yeti60-render-python python3 scripts/render_single_nrf.py
```

`--stills-only`、`--frames`、`--fps`、`--jobs` 控制输出；环境变量可覆盖 `KICAD_CLI`、`KICAD10_3DMODEL_DIR`、`RENDER_FONT`、`RENDER_MONO_FONT`。缓存关联源、脚本、模型哈希、渲染器版本及动画参数。临时副本和帧位于已忽略的 `.render-work/`；`models/` 只保留项目自建示意模型。

这些是 PCB 可视化；[整机装配研究](../yeti60-assembly/README.zh-CN.md)单独提供且有明确条件，两者均不批准制造、固件、信号或射频表现。
