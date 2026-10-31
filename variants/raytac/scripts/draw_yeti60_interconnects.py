#!/usr/bin/env python3
"""Draw controlled cable plans and guide sections from the checked geometry."""
import hashlib
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle, Circle
from matplotlib import font_manager
import numpy as np
from interconnect_geometry import offset_path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/engineering/images'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample(path):
    points=[]
    for piece in path:
        if piece['kind']=='line':
            points.extend([piece['start'],piece['end']]);continue
        center=np.array(piece['center']);v=np.array(piece['start'])-center
        n=np.array(piece['normal']);angle=piece['length']/piece['radius']
        for t in np.linspace(0,angle,25):
            points.append(center+v*math.cos(t)+np.cross(n,v)*math.sin(t))
    return np.array(points)


def main():
    inputs=[ROOT/'docs/audit/yeti60-interconnects.json',ROOT/'docs/audit/yeti60-assembly.json',
            ROOT/'mechanical/interconnect-spec.json',ROOT/'scripts/interconnect_geometry.py',Path(__file__)]
    r=json.loads(inputs[0].read_text());assembly=json.loads(inputs[1].read_text());spec=json.loads(inputs[2].read_text())
    mesh=json.loads((ROOT/'.assembly-work/render-meshes.json').read_text())
    assert mesh['interconnect_report_sha256']==sha(inputs[0])
    for p,h in r['source_sha256'].items():assert sha(ROOT/p)==h,p
    plt.rcParams.update({'svg.fonttype':'path','svg.hashsalt':'YETI60-INTERCONNECT','font.size':9})
    colors={'red':'#bb2920','white':'#f6f4e8','green':'#258455','black':'#28333b','yellow':'#d9af18'}
    outputs={}
    for zh in [False,True]:
        plt.rcParams['font.family']='Arial Unicode MS' if zh else 'DejaVu Sans'
        fig=plt.figure(figsize=(15,8),facecolor='#f6f8fa');grid=fig.add_gridspec(2,2,width_ratios=[2.3,1],height_ratios=[1,1])
        ax=fig.add_subplot(grid[:,0]);ax.set_facecolor('#e8edf0')
        d=mesh['meshes']['bottom'];v=np.array(d['vertices_mm']);tri=np.array(d['triangles'])
        ax.add_collection(PolyCollection(v[tri,:2],facecolors='#dfe6eb',edgecolors='none',rasterized=True))
        for part in assembly['component_envelopes']:
            b=part['bounds_case_mm'];ax.add_patch(Rectangle(b[:2],b[3]-b[0],b[4]-b[1],fc='#98a6b0',alpha=.45))
        b=assembly['battery_candidates'][0]['bounds_case_mm'];ax.add_patch(Rectangle(b[:2],b[3]-b[0],b[4]-b[1],fc='#cfddcf',ec='#58725a'))
        ax.text((b[0]+b[3])/2,(b[1]+b[4])/2,'1600 mAh\n85 x 43 x 4.8 mm',ha='center',va='center')
        for plug in r['mated_housings']:
            b=plug['bounds_case_mm'];ax.add_patch(Rectangle(b[:2],b[3]-b[0],b[4]-b[1],fc='#e7dabc',ec='#97845f',lw=.7))
        for name,path in r['centerline_recipes'].items():
            for i,lateral in enumerate(spec[name]['lateral_offsets'],1):
                points=sample(offset_path(path,lateral));color=colors[spec[name]['colors'][str(i)]]
                ax.plot(points[:,0],points[:,1],c='#48545b',lw=2.3)
                ax.plot(points[:,0],points[:,1],c=color,lw=1.6)
        for station in r['guide_stations']:
            x,y=station['center_xy'];ax.add_patch(Rectangle((x-1.2,y-3),2.4,6,fill=False,ec='#4b5f6d',lw=1.2))
        for label,xy in [('J1',(120,-126)),('J2',(152,-121)),('C5 JSH',(211,-114))]:ax.text(*xy,label,ha='center',fontsize=10,fontweight='bold')
        ax.set(xlim=(101,321),ylim=(-157,-100),aspect='equal',xlabel='X / mm',ylabel='Y / mm')
        ax.set_title('01  '+('壳体坐标内布线路径' if zh else 'Controlled routes in the case frame'),loc='left',pad=16)
        ax.grid(alpha=.15)
        cross=fig.add_subplot(grid[0,1]);cross.set_title('02  '+('后侧固定座剖面' if zh else 'Rear guide section'),loc='left',pad=12)
        cross.set_facecolor('#f6f8fa');g=spec['guides'];floor=-5.91;lower=spec['battery']['rear_z'];upper=spec['usb']['high_z'];w=g['rear_width']
        cross.add_patch(Rectangle((-w/2,floor+.1),w,lower-floor-.1,fc='#aeb9c0',ec='#627481'))
        cross.add_patch(Rectangle((-w/2,lower+.05),w,upper-lower-.05,fc='#8b9ca8',ec='#627481'))
        for name,z in [('battery',lower),('usb',upper)]:
            for i,y in enumerate(spec[name]['lateral_offsets'],1):
                cross.add_patch(Circle((y,z),g['groove_radius'],fc='#f6f8fa',ec='#627481',lw=.6))
                cross.add_patch(Circle((y,z),spec['wire']['insulation_od_max']/2,fc=colors[spec[name]['colors'][str(i)]],ec='#47545a',lw=.6))
        cross.plot([-w/2,-w/2,-2,2,w/2,w/2],[upper,upper+.4,upper+.4,upper+.4,upper+.4,upper],c='#b38f38',lw=2)
        cross.text(0,-6.15,'0.8 mm OD / R 0.5 mm',ha='center',fontsize=9)
        cross.set(xlim=(-3.2,3.2),ylim=(-6.4,-2.5),aspect='equal',xlabel='Y offset / mm',ylabel='Z / mm');cross.grid(alpha=.15)
        table=fig.add_subplot(grid[1,1]);table.axis('off');table.set_title('03  '+('出线口间自由长度 / mm' if zh else 'Wire-exit free lengths / mm'),loc='left',pad=12)
        rows=[[('USB' if name=='usb' else ('电池' if zh else 'Battery'))+' '+str(w['pin']),f"{w['free_length_mm']:.2f}",f"{w['minimum_bend_radius_mm']:.1f}"] for name,wires in r['wires'].items() for w in wires]
        t=table.table(cellText=rows,colLabels=['针号','长度','最小半径'] if zh else ['Pin','L','R min'],loc='upper center',cellLoc='center',colWidths=[.45,.28,.27]);t.auto_set_font_size(False);t.set_fontsize(9);t.scale(1,1.25)
        table.text(0,-.05,('长度不是压接下料尺寸；须按路径预成形。\n底座冷粘、桥可拆；实物弹性／插拔未验收。' if zh else 'Lengths are not crimp cut lengths; preform to path.\nBond bases; removable bridges. Flex/mating unqualified.'),fontsize=8,va='top')
        fig.suptitle('YETI60  /  '+('内部连接装配图' if zh else 'Internal interconnect assembly'),x=.055,ha='left',fontsize=19,fontweight='bold')
        fig.text(.055,.04,('尺寸单位 mm；碰撞检查使用连续实体，图上曲线取样仅用于显示。外壳不缩放，线束供方基准仍待确认。' if zh else 'Dimensions in mm. Collision checks use continuous solids; curve samples are display only. Unscaled case; supplier lead datums pending.'),fontsize=9)
        fig.subplots_adjust(left=.055,right=.97,bottom=.15,top=.88,wspace=.17,hspace=.5)
        stem='interconnects'+('.zh-CN' if zh else '')
        for ext in ['png','svg']:
            path=OUT/(stem+'.'+ext);fig.savefig(path,dpi=180,metadata={'Date':None} if ext=='svg' else {'Software':'YETI60'});
            if ext=='svg':path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
            outputs[str(path.relative_to(ROOT))]=sha(path)
        plt.close(fig)
    report={'status':'generated','source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in inputs},'outputs':outputs,'production_approved':False,'limits':['Guide section is explanatory; STEP solids and written dimensions govern','No physical wire springback, crimp or service qualification']}
    (ROOT/'docs/audit/yeti60-interconnect-drawings.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Separate English/Chinese cable plans and guide sections generated')


if __name__=='__main__':
    main()
