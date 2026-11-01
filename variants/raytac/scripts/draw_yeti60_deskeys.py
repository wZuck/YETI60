#!/usr/bin/env python3
"""Paired assembly guides with native plate geometry; supplier parts schematic."""
import hashlib,json
from pathlib import Path
import ezdxf
from ezdxf.path import make_path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle,Circle
from matplotlib import font_manager
from check_yeti60_deskeys_plate import SOURCE,TARGET,SPEC,ROOT,kind

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    doc=ezdxf.readfile(TARGET);source=ezdxf.readfile(SOURCE)
    for p in ['/System/Library/Fonts/PingFang.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf']:
        if Path(p).exists():font_manager.fontManager.addfont(p)
    plt.rcParams.update({'font.family':['Arial Unicode MS','PingFang SC','DejaVu Sans'],'svg.fonttype':'none','svg.hashsalt':'YETI60-DES-1'})
    outputs={};out=ROOT/'docs/engineering/images'
    for zh in [False,True]:
        suffix='.zh-CN' if zh else '';fig=plt.figure(figsize=(17,11),facecolor='#f5f2ea')
        gs=fig.add_gridspec(2,2,height_ratios=[1.35,1],left=.05,right=.97,top=.88,bottom=.07,wspace=.15,hspace=.23)
        ax=fig.add_subplot(gs[0,:]);ax.set_aspect('equal');ax.axis('off')
        for a,e in zip(source.modelspace(),doc.modelspace()):
            if e.dxftype()=='CIRCLE':ax.add_patch(Circle((-e.dxf.center.x,-e.dxf.center.y),e.dxf.radius,fc='#f5f2ea',ec='#927b4d',lw=.6));continue
            k=kind(a);pts=[(-p.x,-p.y) for p in make_path(e).flattening(.002)]
            ax.add_patch(Polygon(pts,closed=True,facecolor={'outline':'#d4dfd1','normal':'#f5f2ea','wide':'#dba77f','spacebar-side':'#8cb9c9'}[k],edgecolor='#485d52',lw=.5,zorder=0 if k=='outline' else 2))
        ax.set_xlim(65,365);ax.set_ylim(-210,-90)
        ax.text(70,-208,'A  60 个有效按键＋2 个空格侧轴孔；29 个安装轴与外轮廓保留' if zh else 'A  60 active keys + 2 passive side openings; 29 mounts and outer profile preserved',fontsize=12,color='#253f33')
        ax=fig.add_subplot(gs[1,0]);ax.set_xlim(-65,65);ax.set_ylim(-18,23);ax.set_aspect('equal');ax.axis('off')
        for x,color in [(-47.625,'#8cb9c9'),(0,'#dba77f'),(47.625,'#8cb9c9')]:
            ax.add_patch(Rectangle((x-6.8,-6.95),13.6,13.9,fc=color,ec='#485d52',lw=.8))
            ax.plot(x,0,'+',c='#263f34',ms=8)
        ax.plot([-47.625,-47.625,47.625,47.625],[0,-11,-11,0],c='#7b8790',lw=2)
        ax.annotate('',(-47.625,13),(47.625,13),arrowprops={'arrowstyle':'<->','color':'#485d52'})
        ax.text(0,15,'95.25 mm',ha='center',fontsize=12)
        ax.text(0,23,'B  居中 6U 空格' if zh else 'B  Centered 6U spacebar',ha='center',fontsize=14,weight='bold')
        ax.text(0,-17,'左／右：被动侧轴；中央：1 个胶碗＋1 个感应锥簧' if zh else 'Sides: passive stabilizers; center: 1 dome + 1 sensing spring',ha='center',fontsize=10)
        ax=fig.add_subplot(gs[1,1]);ax.axis('off')
        lines=(['C  实际安装顺序','① 普通轴座试装；宽键装钢丝；空格接 6U 钢丝','② 滑块装配套 #5 圈，检查 MX 辅助柱避空','③ 背面安装 60 个胶碗、60 个感应锥簧','④ 29 个支柱＋绝缘环＋PCB＋PEEK 垫片／螺钉','⑤ 装 60 个键帽，检查全行程和两端回弹','默认间距：4.50 mm 肩长＋0.10 mm 膜＝4.60 mm','部件外形及钢丝走向为示意；真实配合须首件确认。'] if zh else ['C  Installation sequence','1  Trial-fit housings; engage wide and 6U spacebar wires','2  Fit matched #5 rings; check MX auxiliary-stem relief','3  Install 60 domes and 60 conical sensing springs below','4  29 standoffs + films + PCB + PEEK washers / screws','5  Fit 60 caps; check full travel and off-center return','Nominal gap: 4.50 mm shoulder + 0.10 mm film = 4.60 mm','Supplier bodies/wire path schematic; physical fit pending.'])
        for i,t in enumerate(lines):ax.text(0,1-i*.135,t,transform=ax.transAxes,fontsize=13 if i==0 else 10.5,weight='bold' if i==0 else 'normal',color='#253f33')
        fig.suptitle('YETI60 RAYTAC  /  DESKEYS 装配方案' if zh else 'YETI60 RAYTAC  /  DESKEYS ASSEMBLY PLAN',x=.05,ha='left',fontsize=23,weight='bold',color='#253f33')
        fig.text(.05,.915,'1.20 mm 不锈钢 · T1 42g · MX 接口 · NicePBT BoW 居中 6U' if zh else '1.20 mm stainless · T1 42g · MX sliders · NicePBT BoW centered 6U',fontsize=13,color='#5e7566')
        for ext in ['png','svg']:
            p=out/('deskeys-mechanism'+suffix+'.'+ext);fig.savefig(p,dpi=160,metadata={'Date':None} if ext=='svg' else None)
            if ext=='svg':p.write_text('\n'.join(x.rstrip() for x in p.read_text().splitlines())+'\n')
            outputs[str(p.relative_to(ROOT))]=sha(p)
        plt.close(fig)
    report={'status':'native-plate-mechanism-guide-generated','supplier_shapes':'schematic, not qualified vendor MCAD','physical_fit_verified':False,'outputs':outputs,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [SOURCE,TARGET,SPEC,Path(__file__)]}}
    (ROOT/'docs/audit/deskeys-mechanism-drawing.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Deskeys native plate / centered spacebar / installation sheets generated in both languages')

if __name__=='__main__':main()
