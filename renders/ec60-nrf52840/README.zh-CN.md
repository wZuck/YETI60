# EC60 单 nRF52840 PCB 渲染

以下图片和动画由当前已验证 PCB 的 KiCad 3D 渲染生成。动画逐帧旋转实际三维 PCB，展示感应面、器件面和板边；不是平面图片翻转。

![正反面总览](pcb-overview.png)

## 动画

![360° PCB 翻转动画](pcb-turntable.gif)

[下载 MP4](pcb-turntable.mp4) · [打开 GIF](pcb-turntable.gif)

MP4 为 1600×1000、24 fps、144 帧，时长 6 秒；GIF 为 960×600、12 fps，循环播放。

## 静态图

| 文件 | 内容 | 分辨率 |
|---|---|---|
| [pcb-front.png](pcb-front.png) | F.Cu，静电容感应面 | 2400×1500 |
| [pcb-back.png](pcb-back.png) | B.Cu，主控、电源与模拟前端器件面 | 2400×1500 |
| [pcb-overview.png](pcb-overview.png) | 正反面对照 | 2400×1900 |

## 模型与验证边界

- 输入是 `hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb`。脚本先核对当前板与 CAD 验证记录的 SHA256，结束时再次确认原板没有被改写。
- 渲染副本只调整 3D 模型引用。旧 KiCad 6 的模型路径解析到本机 KiCad 10 的对应 STEP；J1 使用同一型号的标准模型，并按原封装焊盘位置修正模型原点。
- U2/U4 删除失效的旧模型引用，保留原来已经存在的 SSOP STEP 模型。
- J2 和 SW100 使用项目自建的示意外形，外形高度未经机械验证；U5 使用同尺寸引脚排布的通用 WQFN 模型，不能据此确认真实封装高度。它们在图片底部明确注明。
- 感应电极、走线、孔位、主控位置等均来自设计 PCB。画布补边、文字和背景不改变 PCB 的长宽比例。KiCad 的分块渲染尺寸差异采用透明补边处理，不拉伸电路板。
- 这些是 PCB 可视化，不是外壳、轴体、键帽、电池及线束的完整装配图，也不构成实板、干扰或射频验证。

[render-manifest.json](render-manifest.json) 记录源 PCB 哈希、渲染脚本哈希、KiCad 版本、逐元件模型解析／替代记录及每个产物的哈希和字节数。

## 重建

需要 KiCad 10、其标准 3D 模型库、Pillow 和 ffmpeg。在项目根目录执行：

```sh
python3 -m pip install --target /tmp/yaeckb-render-python pillow==11.3.0
KICAD_AUDIT_PYTHONPATH=/tmp/yaeckb-render-python python3 scripts/render_single_nrf.py
```

也可使用已经安装相应依赖的 KiCad Python。`--stills-only` 仅生成静态图；`--frames`、`--fps`、`--jobs` 可调整动画长度和并发数。默认使用 macOS KiCad 路径，可通过 `KICAD_CLI`、`KICAD10_3DMODEL_DIR` 覆盖；字体可通过 `RENDER_FONT`、`RENDER_MONO_FONT` 覆盖。

临时渲染副本、原始帧和日志位于已忽略的 `.render-work/`。标准 KiCad 模型不重复拷入仓库；项目自建的两个示意模型保存在 `models/`。
