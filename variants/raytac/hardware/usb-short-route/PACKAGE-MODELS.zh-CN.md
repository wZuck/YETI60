中文 | [English](PACKAGE-MODELS.md)

# 当前原生模型与散热焊盘工艺

使用本候选板的完整工程、本地封装库及 `models/` 目录，并安装 KiCad 10.0.7 的标准三维库。75 个实装元件各有一个模型；电极和不装的 JP1 没有模型。保留的长 USB 参考板不属于本轮修补。标准模型仍依赖安装库，哈希及本地模型来源见[模型清单](models/model-sources.json)。

U2／U4 改为采购型号对应的 TSSOP16，去掉重复 SSOP 模型；L1 改为高度 2.0 mm 的 3020 模型。依据为 [Nexperia 封装图](https://assets.nexperia.com/documents/package-information/SOT403-1.pdf)及 [Wurth 器件图](https://www.we-online.com/components/products/datasheet/74438336015.pdf)。J2 使用注明 Mark Harris 来源的 Celestial SMT 标称模型，平移后核对三只信号脚及两只固定脚与原生焊盘的对应关系；其[许可](models/CELESTIAL-LICENSE.txt)独立保留。U5、SW100 使用项目生成的尺寸示意模型，模具细节为近似，不能据此认定供应商公差合格。

## 影响打板及焊接的修改

- U5 中央铜焊盘改为 **1.68×1.68 mm**，外围焊盘为 **0.60×0.24 mm**、间距 0.50 mm，依据 [TI RGT0016C](https://www.ti.com/lit/ds/symlink/bq24074.pdf) 的封装及推荐落脚图。BAT_NTC／ICHG_SET 两处焊盘趾部连接已延伸。保留旧 `EP1.6x1.6` 文件名作为技术标识，它不代表当前铜尺寸。
- U5／U6 保留短接地路径及普通 **孔径 0.30／焊盘 0.50 mm 通孔**，正反面均设置阻焊遮孔。元件面以 **0.50×0.50 mm 阻焊岛**覆盖散热孔，周围四个定制开窗露出其余散热铜。这是普通阻焊图形，不需要树脂填孔或电镀盖帽。
- 每颗芯片保留四个圆角锡膏窗，避开阻焊岛。覆盖率公式为 `sum(w*h - (4-pi)*r*r) / EP_area`：U5 **1.639816／2.8224＝58.100%**；U6 **1.218910／2.4＝50.788%**。内部钢网桥宽最小 **0.16 mm**。这些是几何印刷比例，不是实测焊料体积或空洞率。[TI SLUA271C 第 4.4 节](https://www.ti.com/lit/an/slua271c/slua271c.pdf)给出典型 50–70% 起点，实际工艺仍需验证。

PCB 与过滤掉 JP1 的背面钢网必须使用当前配套文件。选择普通过孔盖油，并**向板厂注明保留 U5／U6 阻焊岛及定制开窗**。JLC 分别说明了[盖油与填孔的区别](https://jlcpcb.com/help/article/pcb-via-covering)，以及[有意设计的阻焊限定图形需告知工程审核](https://jlcpcb.com/help/article/how-to-order-boards-with-solder-mask-defined-pads)。普通盖油不保证每个实物孔口完全封闭；需经板厂 DFM 和到货检查确认，不能刮除阻焊岛或沿用旧钢网。

印锡膏前用放大设备检查两处散热孔阻焊覆盖及周边露铜开窗。若有破损、针孔或图形被改动，该板不能直接按本工艺装配。受控回流、隐藏焊点及温升检查仍是首板要求；源码几何通过不代表焊点、充电安全或空洞率已经合格。

## 验证与固件

[原生模型记录](audit/native-models.json)包含 75 个导出实体及七组落脚检查。SH／PH／TSSOP 平脚应落在原生铜区域；MAPI 模型存在有意的内侧趾部悬出，与原厂焊盘对应的标称平面重叠率为 **91.66%**。Panasonic／C&K 定位柱会进入 NPTH 孔，完整尺寸公差仍需实物验收。

碰撞包络纳入完整标称模型及引脚，并加 0.10 mm 建模余量；SW100 使用独立的 3.60 mm 安装高度验收上限。建模余量不是供应商公差。PCB 指纹变化后必须重建配套固件；当前校准版与正常版必须一起使用，旧指纹的阈值需重新采集。继续按[当前装配入口](ASSEMBLY.zh-CN.md)及[无外壳检查](../../OPEN-BENCH.zh-CN.md)操作。
