#!/usr/bin/env python3
"""Counted exploded assembly sheet and native 75-reference map; not a fit solver."""
import csv,hashlib,json,re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,FancyBboxPatch
from matplotlib import font_manager
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/engineering/images';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(r):return (re.sub(r'\d','',r),int(re.search(r'\d+',r)[0]))
def main():
 sources=[ROOT/'.assembly-work/build-map.json',ROOT/'docs/audit/yeti60-assembly.json',ROOT/'docs/audit/yeti60-interconnects.json',ROOT/'hardware/bom/mainboard.csv',ROOT/'mechanical/assembly-spec.json',Path(__file__)]
 m=json.loads(sources[0].read_text());a=json.loads(sources[1].read_text());h=json.loads(sources[2].read_text())
 assert m['pcb_sha256']==sha(ROOT/m['pcb_source'])
 refs=sorted(m['fitted_references'],key=key);assert len(refs)==75 and 'D1' not in refs
 assert len(h['wires']['usb'])==4 and len(h['wires']['battery'])==3
 for p in ['/System/Library/Fonts/PingFang.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf']:
  if Path(p).exists():font_manager.fontManager.addfont(p)
 plt.rcParams.update({'font.family':['Arial Unicode MS','PingFang SC','DejaVu Sans'],'svg.fonttype':'none','axes.unicode_minus':False})
 layers=[('A01','60 keycaps','60 个键帽'),('A02','Top shell / 1','上壳／1 件'),('A03','60 housings + sliders; stabilizer set','60 套轴座／滑块；稳定机构 1 套'),('A04','1.2 mm stainless plate / 1','1.2 mm 不锈钢定位板／1 件'),('A05','60 dome positions','胶碗／60 个位置'),('A06','60 conical sensing springs','锥形感应弹簧／60 个'),('A07','29 standoffs + 29 insulating rings','29 个支柱＋29 个隔离环'),('A08','Main PCB / 1; fitted components / 75','主板／1 块；实装元件／75 只'),('A09','29 PEEK washers + 29 M1.6 screws','29 个 PEEK 垫片＋29 颗 M1.6 螺钉'),('A10','C5 JSH / 1; protected battery / 1','C5 JSH／1 块；保护电池包／1 包'),('A11','USB 4 wires + battery 3 wires; 5 guides','USB 4 根线＋电池 3 根线；支架 5 件'),('A12','Bottom shell; 8 inserts + 8 screws/shims','底壳；8 个嵌件＋8 套螺钉／垫片'),('A13','Gasket + insulation/retention sets; 4 feet','胶棉／绝缘固定材料各 1 套；脚垫 4 个')]
 outputs={}
 for zh in [False,True]:
  suffix='.zh-CN' if zh else '';fig=plt.figure(figsize=(22,15),facecolor='#f5f2ea');gs=fig.add_gridspec(3,2,width_ratios=[1,1.45],height_ratios=[1,.50,.73],left=.035,right=.98,top=.91,bottom=.055,wspace=.12,hspace=.16)
  left=fig.add_subplot(gs[:,0]);left.set_xlim(0,400);left.set_ylim(-12,570);left.axis('off')
  for i,(tag,en,cn) in enumerate(layers):
   y=540-i*42;face='#dfe5db' if i%2 else '#e9dfc9'
   left.add_patch(Polygon([(18,y-17),(267,y-17),(302,y-6),(53,y-6)],closed=True,facecolor=face,edgecolor='#63746d',linewidth=.7))
   left.text(18,y+1,tag+'  '+(cn if zh else en),fontsize=9.7,color='#263a32',weight='bold')
   if i<12:left.plot([155,155],[y-18,y-33],color='#9a9f95',ls='--',lw=.7)
   if i in [0,2,4,5]:
    for row in range(5):
     for col in range(12):left.plot(32+col*18+row*5,y-15+row*1.7,'.',color='#63746d',markersize=1.7)
   if i==10:
    for j,c in enumerate(['red','#ccc','green','#222','red','#222','#d6a72b']):left.plot([35,115,150,250],[y-12+j*.7,y-12+j*.7,y-9+j*.7,y-9+j*.7],color=c,lw=.8)
  left.text(18,-5,'分层示意：间距不按比例；实际外形见 CAD 渲染。' if zh else 'Layer sequence schematic; separation not to scale. See CAD render for shape.',fontsize=8.2,color='#59685f')
  ax=fig.add_subplot(gs[0,1]);ax.set_aspect('equal');ax.axis('off')
  allpts=[v for poly in m['outline'] for v in poly];xmin=min(p[0] for p in allpts);xmax=max(p[0] for p in allpts)
  def xy(p):return [xmin+xmax-p[0],p[1]]
  for poly in m['outline']:ax.add_patch(Polygon([xy(p) for p in poly],facecolor='#d7e2cf',edgecolor='#586b5d',lw=.7))
  for hole in m['holes']:
   p=xy(hole['at']);ax.plot(*p,'o',ms=2.5,mfc='#f5f2ea',mec='#7b8a7a',mew=.5)
  for n,ref in enumerate(refs,1):
   part=m['parts'][ref]
   for pad in part['pads']:
    for poly in pad['polygons']:ax.add_patch(Polygon([xy(p) for p in poly],facecolor='#b39862',edgecolor='none'))
   x,y=xy(part['at']);ax.annotate(str(n),(x,y),(x,y+(-2.7 if n%2 else 2.7)),ha='center',va='center',fontsize=5.2,color='#182f26',arrowprops={'arrowstyle':'-','lw':.3,'color':'#59685f'})
  ax.set_xlim(xmin-3,xmax+3);ys=[v[1] for v in allpts];ax.set_ylim(max(ys)+4,min(ys)-4)
  ax.set_title('B01  背面实装元件定位：75 只；按原生坐标镜像，JP1 不装、J3 为探针焊盘' if zh else 'B01  Rear placement: all 75 fitted references; JP1 DNP, J3 probe pads',loc='left',fontsize=11,weight='bold',pad=12)
  legend=fig.add_subplot(gs[1,1]);legend.axis('off')
  for i,ref in enumerate(refs):
   col=i//15;row=i%15;legend.text(col*.20,1-row*.067,f'{i+1:02}  {ref}  {m["parts"][ref]["value"][:17]}',transform=legend.transAxes,fontsize=7.4,color='#263a32')
  detail=fig.add_subplot(gs[2,1]);detail.axis('off')
  lines=['C01  线束、连接器及子板核对','USB：J1 1→C5 SH 1 正电源；2→2 D−；3→3 D+；4→4 地。','电池：主板 J2.1 正极／J2.2 地／J2.3 独立 10k NTC。','两端 SH 插壳共 2 个、压接端子 8 个；电池 PH 插壳 1 个、端子 3 个。','C5 自焊共 7 件：J1、J2、R1、R2、U1、D1、F1，不能省掉保护件。','线束：4 根 USB＋3 根电池线；2 个后底座＋2 个桥＋1 个前支架。','外壳／PCB／定位板／线束按原生数据；胶碗、弹簧、轴座、键帽形状为示意。','板上元件图对应实装位号；尺寸和封装以原生焊盘及材料表为准。','M3 合壳嵌件、螺钉、薄垫各 4；M2 子板嵌件、螺钉、绝缘垫各 4。','胶棉裁形、固定胶与隔离材料按装配手册，不能挤压电池或覆盖电极。','总入口：variants/raytac/BUILD.zh-CN.md；本图不是实物验收证明。'] if zh else ['C01  Harness / connector / daughterboard checklist','USB: J1 1 to C5 SH 1 power; 2 to 2 D-; 3 to 3 D+; 4 to 4 ground.','Battery: main J2.1 positive / J2.2 ground / J2.3 independent 10k NTC.','Two SH housings, eight contacts; one battery PH housing, three contacts.','C5 has seven parts: J1, J2, R1, R2, U1, D1, F1; protection parts mandatory.','Four USB + three battery wires; two rear bases, two bridges, one front base.','Native case/PCB/plate/harness data; dome/spring/housing/cap profiles illustrative.','Placement map contains actual fitted references; native pads/BOM govern sizes.','Four each M3 case inserts/screws/shims and M2 C5 inserts/screws/insulating washers.','Trim gaskets/retention supplies per handbook; no pack compression or electrode covering.','Entry: variants/raytac/BUILD.md. This sheet does not certify a physical assembly.']
  for i,line in enumerate(lines):detail.text(0,1-i*.089,line,transform=detail.transAxes,fontsize=10.5 if i==0 else 9,color='#263a32',weight='bold' if i==0 else 'normal',va='top')
  fig.suptitle('YETI60 RAYTAC  /  完整分解与元件对照图' if zh else 'YETI60 RAYTAC  /  COMPLETE EXPLODED ASSEMBLY & PART INDEX',x=.035,ha='left',fontsize=21,weight='bold',color='#20382d')
  fig.text(.035,.935,'13 层装配结构 · 75 只主板元件 · 7 根内部导线 · 所有数量按一把键盘' if zh else '13 assembly layers · 75 mainboard components · 7 internal wires · quantities per keyboard',fontsize=12,color='#63746d')
  for ext in ['png','svg']:
   p=OUT/f'complete-exploded{suffix}.{ext}';fig.savefig(p,dpi=180,facecolor=fig.get_facecolor())
   if ext=='svg':p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
   outputs[str(p.relative_to(ROOT))]=sha(p)
  plt.close(fig)
 report={'status':'counted-native-part-map-generated','production_approved':False,'physical_verification':False,'fitted_mainboard_references':refs,'mainboard_parts':75,'C5_parts':7,'USB_wires':4,'battery_wires':3,'mount_sets':29,'active_keys':60,'outputs':outputs,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},'limits':['Layer separations and layered silhouettes schematic, not a dimensional assembly drawing','Actual shell/board shapes are in the native CAD studio render','Key mechanism supplier shapes and pack remain unqualified']}
 (ROOT/'docs/audit/complete-exploded.json').write_text(json.dumps(report,indent=2)+'\n');print('Complete exploded sheets: 75 native references, 7 wires, 29 mounts, 60 keys, both languages')
if __name__=='__main__':main()
