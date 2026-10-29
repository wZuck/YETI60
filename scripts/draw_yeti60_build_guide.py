#!/usr/bin/env python3
"""Generate bilingual, source-linked step illustrations and build instructions."""
import csv
import hashlib
import json
import math
import re
from pathlib import Path
import textwrap
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, LineCollection
from matplotlib.patches import Circle, Rectangle, Polygon, FancyBboxPatch, Ellipse, Arc
from matplotlib import font_manager
from cad_geometry import load, bounds
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assembly/images'
MAP = ROOT / '.assembly-work/build-map.json'
STEPS = ROOT / 'docs/assembly/steps.json'
BG, INK, GREEN, GOLD, ACTIVE = '#f5f7fa', '#193745', '#20564f', '#d9b666', '#ed8e49'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wrap(text, zh, width=42):
    if zh:
        lines, current, used = [], '', 0
        for token in re.findall(r'[A-Za-z0-9_./+×≤≥-]+|.', text):
            size = sum(.55 if ord(c) < 128 else 1 for c in token)
            if used + size > width/2 and current:
                lines.append(current); current, used = '', 0
            current += token; used += size
        return '\n'.join(lines + ([current] if current else []))
    return textwrap.fill(text, width, break_long_words=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    native = json.loads(MAP.read_text())
    steps = json.loads(STEPS.read_text())['steps']
    fitpath = ROOT / 'docs/audit/yeti60-assembly.json'
    fit = json.loads(fitpath.read_text())
    mesh = json.loads((ROOT / '.assembly-work/render-meshes.json').read_text())
    spec = json.loads((ROOT / 'mechanical/assembly-spec.json').read_text())
    wires = json.loads((ROOT / 'docs/audit/yeti60-interconnects.json').read_text())
    assert native['pcb_sha256'] == sha(ROOT / native['pcb_source'])
    assert mesh['assembly_report_sha256'] == sha(fitpath)
    assert mesh['interconnect_report_sha256'] == sha(ROOT / 'docs/audit/yeti60-interconnects.json')
    for path, digest in mesh['geometry_sources'].items():
        assert sha(ROOT / path) == digest, path
    parts = native['parts']
    with (ROOT / 'hardware/bom/mainboard.csv').open() as source:
        bom = list(csv.DictReader(source))
    all_refs = set(native['fitted_references'])
    installed = set()
    for step in steps:
        value = step.get('install', [])
        refs = sorted(r for r in all_refs if r.startswith(value)) if isinstance(value, str) else value
        assert not installed.intersection(refs), 'Part appears in two placement steps'
        step['references'] = refs
        installed.update(refs)
    assert installed == all_refs and len(installed) == 76
    assert [s['id'] for s in steps] == [f'{i:02}' for i in range(1, 29)]
    key_geometry = json.loads((ROOT / 'docs/audit/yeti60-key-geometry.json').read_text())
    for path, digest in key_geometry['source_sha256'].items():
        assert sha(ROOT / path) == digest, path
    active_electrodes = [m['electrode'] for m in key_geometry['matches']]
    assert len(active_electrodes) == 60
    # Read the four actual underside pocket floors, not invented corner positions.
    feet = []
    shape = load(ROOT / 'mechanical/generated/yeti60-bottom.step')
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = TopoDS.Face(explorer.Current())
        if BRepAdaptor_Surface(face).GetType() == GeomAbs_Plane:
            box = bounds(face)
            if 40 < box[3]-box[0] < 44 and 4 < box[4]-box[1] < 8 and box[5] < 0:
                feet.append([(box[i]+box[i+3])/2 for i in range(3)])
        explorer.Next()
    assert len(feet) == 4
    plt.rcParams.update({'svg.fonttype': 'path', 'svg.hashsalt': 'YETI60-build-P2',
                         'font.size': 10, 'text.color': INK, 'savefig.facecolor': BG})

    def xy(points, back=True):
        a = np.asarray(points, dtype=float)
        return a * [-1 if back else 1, -1]

    def axis(fig, box=(.045, .29, .65, .53)):
        ax = fig.add_axes(box)
        ax.set_aspect('equal'); ax.axis('off')
        return ax

    def pcb(ax, selected=(), region=None, front=False, paste=False, numbers=False, labels=True):
        back = not front
        region = region or [70, 102, 359, 201]
        label_sites = []
        for outline in native['outline']:
            ax.add_patch(Polygon(xy(outline, back), fc=GREEN, ec='#173d38', lw=1))
        for hole in native['holes']:
            p = xy([hole['at']], back)[0]
            ax.add_patch(Circle(p, hole['drill'][0]/2, fc=BG, ec='#87a49d', lw=.4))
        if front:
            for ref, e in native['electrodes'].items():
                ax.add_collection(PolyCollection([xy(p, False) for p in e['polygons']],
                                  facecolors=GOLD if ref in active_electrodes else '#788d78',
                                  edgecolors='none', alpha=.86 if ref in active_electrodes else .32))
        else:
            for ref, part in parts.items():
                if paste and ref == 'JP1':
                    continue
                chosen = ref in selected
                color = ACTIVE if chosen else '#718d7c'
                polygons = part['paste'] if paste else [p for pad in part['pads'] for p in pad['polygons']]
                ax.add_collection(PolyCollection([xy(p) for p in polygons], facecolors=color,
                                  edgecolors='none', alpha=1 if chosen else .6))
                for fab in part['fab']:
                    if fab['kind'] in ('line', 'arc'):
                        line = xy(fab['points'])
                        ax.plot(line[:, 0], line[:, 1], c='#f2ead5' if chosen else '#52766b', lw=.65 if chosen else .32)
                    elif fab['kind'] == 'circle':
                        ax.add_patch(Circle(xy([fab['center']])[0], fab['radius'], fill=False,
                                            ec='#f2ead5' if chosen else '#52766b', lw=.4))
                if chosen and labels:
                    x,y = part['at']
                    if region[0]+.3 < x < region[2]-.3 and region[1]+.3 < y < region[3]-.3:
                        label_sites.append((ref, xy([part['at']])[0]))
                if chosen and numbers:
                    for pad in part['pads']:
                        if not pad['number'] or ref == 'U1' and pad['number'] not in ['1','5','12','19','23','24','26','27','29','31','37','39']:
                            continue
                        p = xy([pad['at']])[0]
                        ax.text(*p, pad['number'], ha='center', va='center', fontsize=7, color='#182f2a')
                if chosen and ref.startswith(('U', 'D', 'J')):
                    for pad in part['pads']:
                        if pad['number'] == '1':
                            ax.add_patch(Circle(xy([pad['at']])[0], .6, fill=False, ec='#ffdb7a', lw=1.7))
        corners = xy([[region[0], region[1]], [region[2], region[3]]], back)
        ax.set_xlim(min(corners[:,0]), max(corners[:,0])); ax.set_ylim(min(corners[:,1]), max(corners[:,1]))
        ax.apply_aspect()
        used = []; frame = ax.get_window_extent(); scale = ax.figure.dpi/72
        offsets = [(0,10),(0,-13),(-20,10),(20,10),(-20,-13),(20,-13)]
        offsets += [(dx,dy) for dy in [22,-25,34,-37,46,-49] for dx in [0,-22,22,-44,44]]
        for ref,p in sorted(label_sites,key=lambda item:(item[1][1],item[1][0])):
            q = ax.transData.transform(p); width = max(17,len(ref)*5.5)*scale; height = 12*scale
            chosen_offset = offsets[0]
            for dx,dy in offsets:
                x,y = q+[dx*scale,dy*scale]; box=(x-width/2,y-height/2,x+width/2,y+height/2)
                if not (frame.x0+2 < box[0] and box[2] < frame.x1-2 and frame.y0+2 < box[1] and box[3] < frame.y1-2):continue
                if any(not (box[2]<a or box[0]>c or box[3]<b or box[1]>d) for a,b,c,d in used):continue
                used.append(box); chosen_offset=(dx,dy);break
            ax.annotate(ref,p,xytext=chosen_offset,textcoords='offset points',ha='center',va='center',fontsize=8,color='white',
                        arrowprops={'arrowstyle':'-','lw':.45,'color':'#b5cdc6'},
                        bbox={'fc':'#193e38','ec':'none','pad':.8,'alpha':.94})

    def project(vertices, offset=0, underside=False):
        v = np.asarray(vertices).copy(); v[:,0] -= 214.312707; v[:,1] += 153.70968
        v[:,2] = (-v[:,2] if underside else v[:,2]) + offset
        return np.column_stack((.95*v[:,0]+.32*v[:,1], -.1*v[:,0]+.5*v[:,1]+.94*v[:,2]))

    def cad(ax, name, offset=0, color=None, underside=False):
        data = mesh['meshes'][name]; v = np.asarray(data['vertices_mm']); t = np.asarray(data['triangles'])
        p = project(v, offset, underside)
        depth = (-v[:,2] if underside else v[:,2]) - .6*v[:,1]
        ids = np.argsort(np.mean(depth[t], axis=1))
        c = color or {'bottom':'#a7b6ba','top':'#cad2d3','plate':'#b5c9ce','pcb':GREEN}.get(name, '#6f9691')
        ax.add_collection(PolyCollection(p[t[ids]], facecolors=c, edgecolors='none', rasterized=True))

    def box3(ax, b, color, offset=0):
        x,y,z,X,Y,Z = b
        points = [(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)]
        p = project(points, offset)
        faces = [[0,1,2,3],[0,1,5,4],[1,2,6,5],[3,2,6,7],[0,3,7,4],[4,5,6,7]]
        ax.add_collection(PolyCollection(p[faces], facecolors=color, edgecolors='#49636a', linewidths=.35))

    def cad_limits(ax, tall=False):
        ax.set_xlim(-184, 184); ax.set_ylim(-64, 120 if tall else 75)

    def marker(ax, points, label, color=ACTIVE, offset=0, underside=False):
        points = project(points, offset, underside)
        ax.scatter(points[:,0], points[:,1], s=46, fc=color, ec=BG, lw=1.1, zorder=8)
        if label:
            ax.text(points[0,0]+5, points[0,1]+7, label, fontsize=10, fontweight='bold')

    def caps(ax, offset=0):
        for key in fit['active_key_positions']:
            w = max(14, key['cutout_width'] - .7)
            box3(ax, [key['x']-w/2,key['y']-7,12.3,key['x']+w/2,key['y']+7,19], '#dfdccf', offset)

    def label(ax, text, target, at, **kwargs):
        ax.annotate(text, target, xytext=at, fontsize=10, color=INK,
                    arrowprops={'arrowstyle':'->','color':'#557881','lw':1},
                    bbox={'fc':BG,'ec':'none','pad':2}, **kwargs)

    def connector_diagram(ax, zh, swd=False):
        ax.set_xlim(0, 100); ax.set_ylim(0, 68)
        colors = ['#cf5949','#91a7b0','#408b61','#344451']
        for i, net in enumerate(['VBUS','D-','D+','GND']):
            y = 49-i*10
            ax.add_patch(FancyBboxPatch((5,y-3),19,6,boxstyle='round,pad=0.5',fc='#dbe6e9',ec='#6f8a94'))
            ax.add_patch(FancyBboxPatch((76,y-3),19,6,boxstyle='round,pad=0.5',fc='#dbe6e9',ec='#6f8a94'))
            ax.text(14.5,y,f'{i+1}  {net}',ha='center',va='center',fontsize=11)
            ax.text(85.5,y,f'{i+1}  {net}',ha='center',va='center',fontsize=11)
            ax.plot([25,75],[y,y],lw=4,color=colors[i],solid_capstyle='round')
            ax.text(50,y+2.2,f'{i+1} -> {i+1}',ha='center',fontsize=9)
        ax.text(14,60,'C5 J2',ha='center',fontsize=15,fontweight='bold')
        ax.text(86,60,'Main J1' if not zh else '主板 J1',ha='center',fontsize=15,fontweight='bold')
        ax.text(50,4,'Numbered electrical continuity, not a plug face view' if not zh else '按编号测量的电气连接，不代表插头端面视图',ha='center',fontsize=11)

    def section(ax, zh, fastener=False):
        ax.set_xlim(-12, 20); ax.set_ylim(-7, 11)
        ptop = fit['nominal_stack']['pcb_top_z']; plate = fit['nominal_stack']['plate_bottom_z']
        ax.add_patch(Rectangle((-9,-2),18,1.6062,fc=GREEN,ec=INK))
        ax.add_patch(Rectangle((-9,plate),18,1.2,fc='#becbd1',ec=INK))
        if fastener:
            for rect, color in [((-1.75,ptop+.1,3.5,4.5),GOLD),((-2.25,ptop,4.5,.1),'#df8544'),
                                ((-2,-2.8,4,.8),'#577c8e'),((-.8,-2.8,1.6,5),'#a0b0b8'),
                                ((-1.6,-3.9,3.2,1.1),'#8d9ca2'),((-1,plate,2,1),GOLD)]:
                ax.add_patch(Rectangle(rect[:2],rect[2],rect[3],fc=color,ec=INK,lw=.6))
            label(ax,'0.10 mm '+('绝缘环' if zh else 'film'),(2,ptop+.05),(7,-.2))
            label(ax,'0.8 mm PEEK',(2,-2.4),(7,-3.5))
            label(ax,'M1.6 x 5',(0,-3.6),(-10,-5.8))
            label(ax,'4.50 mm '+('黄铜肩' if zh else 'shoulder'),(1.7,2),(-11,8.4))
        else:
            ax.add_patch(Rectangle((-5,5.4),10,3.3,fc='#798b8c',ec=INK))
            ax.add_patch(Rectangle((-.8,3.8),1.6,4,fc='#b4bec0',ec=INK))
            ax.add_patch(Arc((0,.1),9,6.9,theta1=0,theta2=180,lw=6,color='#6c8d89'))
            yy = np.linspace(0,2.7,160); rr = 2.7*(1-yy/3.4); xx=rr*np.cos(yy*math.pi*7)
            ax.plot(xx,yy,c='#b69d58',lw=1.5)
            label(ax,'Slider' if not zh else '滑块',(0,7.5),(7,9))
            label(ax,'Dome crown' if not zh else '胶碗顶部',(1.7,3),(7,6))
            label(ax,'Narrow tip' if not zh else '弹簧窄端',(.3,2.7),(7,2.9))
            label(ax,'Wide base' if not zh else '弹簧宽底',(2.5,.1),(7,-3.2))
            ax.text(-10,-6,'Dome/spring/housing shapes illustrative' if not zh else '胶碗、弹簧和轴壳外形为示意',fontsize=10)
        ax.annotate('',(-10.2,ptop),(-10.2,plate),arrowprops={'arrowstyle':'<->','color':'#467786'})
        ax.text(-10.6,(ptop+plate)/2,'4.60',rotation=90,ha='right',va='center',fontsize=10)

    outputs, records = {}, []
    for zh in [False, True]:
        lang = int(zh)
        font = font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc' if zh else '/System/Library/Fonts/Helvetica.ttc')
        plt.rcParams['font.family'] = font.get_name()
        for step in steps:
            fig = plt.figure(figsize=(16,10), facecolor=BG)
            fig.text(.045,.94,f"{step['id']}  {step['title'][lang]}",fontsize=24,fontweight='bold',ha='left')
            fig.text(.045,.895,('YETI60 / P2 / 工程样机安装图' if zh else 'YETI60 / P2 / Engineering prototype build'),fontsize=11,color='#5a7680')
            info = fig.add_axes([.73,.29,.235,.54]); info.axis('off')
            for i, line in enumerate(step['labels'][lang]):
                info.text(0,.98-i*.25,f'{i+1:02}',fontsize=15,color='#b5692e',fontweight='bold',va='top')
                info.text(.16,.98-i*.25,wrap(line,zh,28),fontsize=12,va='top',linespacing=1.7)
            info.text(0,.1,wrap('Illustration; verify actual parts before assembly' if not zh else '工程示意图；装配前核对实物',zh,29),fontsize=10,color='#667d86')
            figure = step['figure']; refs = step['references']
            ax = axis(fig)
            if figure in ('prepare','faces'):
                pcb(ax, front=True)
                if figure == 'faces':
                    ax.set_position([.045,.52,.65,.30]); other=axis(fig,[.045,.27,.65,.30]); pcb(other)
                    ax.set_title('Front / sensing face' if not zh else '正面／感应面',loc='left',fontsize=12)
                    other.set_title('Back / component face, mirrored X' if not zh else '背面／元件面，X 已镜像',loc='left',fontsize=12)
                else:
                    ax.set_position([.045,.43,.65,.37])
                    fig.text(.07,.33,'0402  /  QFN  /  SH-PH  /  SWD  /  DMM',fontsize=20,color='#557c83')
            elif figure in ('paste','pcb','inspection','power','swd'):
                if figure == 'pcb' and step.get('install') in ('R','C'):
                    ax.remove()
                    for i,region in enumerate([[77,110,164,160],[286,110,357,194],[77,160,164,195],[164,110,286,195]]):
                        a=axis(fig,[.045+(i%2)*.335,.57-(i//2)*.28,.315,.25]);pcb(a,refs,region,labels=True)
                elif step['id'] == '07':
                    ax.remove()
                    for i,(ref,region) in enumerate([('U3',[97,141,111,159]),('U2',[137,172,153,193]),('U4',[299,169,315,190])]):
                        a=axis(fig,[.045+i*.22,.31,.21,.49]);pcb(a,[ref],region,numbers=True)
                elif step['id'] == '08': pcb(ax,refs,[336,116,357,134],numbers=True)
                elif step['id'] == '09':
                    ax.remove()
                    for i,(group,region) in enumerate([(['J1','SW100'],[104,115,131,132]),(['J2'],[143,116,162,134]),(['SW1','D2'],[310,115,334,132])]):
                        a=axis(fig,[.045+i*.22,.31,.21,.49]);pcb(a,group,region,numbers=True)
                elif figure == 'swd':
                    pcb(ax,['J3'],[312.5,118.5,327,126.3],numbers=True,labels=False)
                    for pad in parts['J3']['pads']:
                        p=xy([pad['at']])[0]; dx=-2 if pad['at'][0]>320 else 2
                        ax.annotate(f"{pad['number']} {pad['net']}",p,xytext=(p[0]+dx,p[1]),ha='right' if dx<0 else 'left',va='center',fontsize=10,
                                    arrowprops={'arrowstyle':'-','color':'#dce6dc'},color='white')
                else:
                    selected = refs or ['U5','U6','C40','C43','C45','JP1']
                    pcb(ax,selected,[101,133,151,158],paste=figure=='paste',numbers=figure in ('paste','power'),labels=True)
                    if figure=='power':
                        for r in ['C40','C43','C45']:
                            p=next(p for p in parts[r]['pads'] if p['number']=='1')
                            ax.add_patch(Circle(xy([p['at']])[0],.7,fc='none',ec='#f5e9ba',lw=2))
            elif figure == 'reflow':
                ax.set_xlim(0,100); ax.set_ylim(0,60)
                for x,txt in [(0,'Profile' if not zh else '实测曲线'),(34,'Cool' if not zh else '冷却'),(68,'Inspect' if not zh else '检查')]:
                    ax.add_patch(FancyBboxPatch((x+2,43),28,10,boxstyle='round,pad=1',fc='#e1e9ed',ec='#89a2ac'))
                    ax.text(x+16,48,txt,ha='center',va='center',fontsize=15)
                ax.plot([30,34],[48,48],color='#607e86');ax.plot([64,68],[48,48],color='#607e86')
                ax.add_patch(Rectangle((8,14),84,4,fc=GREEN));ax.add_patch(Rectangle((23,23),54,10,fc='#334d55'))
                ax.add_patch(Rectangle((29,18),42,5,fc=GOLD));ax.add_patch(Rectangle((24,18),4,5,fc='#b8c7cc'))
                ax.text(50,8,'Inspect the hidden underside joint' if not zh else '检查底部隐藏焊点',ha='center',fontsize=13)
                label(ax,'Package' if not zh else '封装',(68,29),(79,35))
                label(ax,'Solder joint' if not zh else '焊接层',(60,20),(70,4))
            elif figure=='daughter':
                d=native['daughterboard'];p=lambda a:xy(a,False)
                for o in d['outline']:ax.add_patch(Polygon(p(o),fc=GREEN,ec=INK))
                for ref,part in d['parts'].items():
                    polys=[p(poly) for pad in part['pads'] for poly in pad['polygons']]
                    ax.add_collection(PolyCollection(polys,facecolors=ACTIVE,edgecolors='none'))
                    q=p([part['at']])[0];ax.annotate(ref,q,xytext=(0,10),textcoords='offset points',ha='center',color='white',fontsize=10,fontweight='bold',bbox={'fc':GREEN,'ec':'none','pad':1})
                    if ref in ('U1','D1'):
                        for pad in part['pads']:
                            if pad['number']=='1':ax.add_patch(Circle(p([pad['at']])[0],.55,fc='none',ec='#fff0aa',lw=1.5))
                pts=p([v for o in d['outline'] for v in o]);ax.set_xlim(pts[:,0].min()-2,pts[:,0].max()+2);ax.set_ylim(pts[:,1].min()-2,pts[:,1].max()+2)
                ax.set_title('C5 JSH / F.Cu component view' if not zh else 'C5 JSH／F.Cu 元件面',loc='left',fontsize=12)
            elif figure=='harness': connector_diagram(ax,zh)
            elif figure in ('ec-stack','fasteners'): section(ax,zh,figure=='fasteners')
            elif figure in ('calibration','test'):
                ax.set_xlim(0,100);ax.set_ylim(0,60)
                if figure=='calibration':
                    ax.add_patch(FancyBboxPatch((1,15),97,39,boxstyle='round,pad=1',fc='#1f3b44',ec='#5d7881'))
                    for i,line in enumerate(['yeti_calibrate release','yeti_calibrate press','yeti_calibrate save']):
                        ax.text(6,45-i*10,line,color='#d8e5c4',fontfamily='monospace',fontsize=16)
                    ax.text(50,4,'Normal HEX: preserve 0xF0000-0xFFFFF' if not zh else '普通固件：保留 0xF0000–0xFFFFF',ha='center',fontsize=12)
                else:
                    tests = ['USB HID  /  60 keys','BLE  /  profiles 0 1 2 3 4','USB500  /  suspend  /  USB100'] if not zh else ['USB HID ／60 个按键','蓝牙／配置 0 1 2 3 4','USB500 ／挂起／USB100']
                    for i,line in enumerate(tests):
                        y=48-i*16;ax.add_patch(Rectangle((5,y-3),5,5,fill=False,ec='#64808a',lw=1.4));ax.text(15,y,line,va='center',fontsize=17)
            else:
                underside=figure=='feet';cad(ax,'bottom',underside=underside)
                if figure=='inserts':
                    cad(ax,'top',85);marker(ax,[[x,y,4.79] for x,y in spec['case']['top_screw_axes']],'4 x M3 inserts' if not zh else '4 个 M3 嵌件',offset=85)
                    marker(ax,[[x,y,-10.91] for x,y in spec['case']['daughterboard_screw_axes']],'4 x M2 inserts' if not zh else '4 个 M2 嵌件');cad_limits(ax,True)
                elif figure=='plate':
                    ax.cla();ax.axis('off');ax.set_aspect('equal');cad(ax,'plate')
                    for k in fit['active_key_positions']:box3(ax,[k['x']-6.8,k['y']-6.5,5.4,k['x']+6.8,k['y']+6.5,10.9],'#627e82')
                    cad_limits(ax)
                elif figure=='lower':
                    for name in ['C5-pcb','C5-usb','C5-sh','interconnect-rear-1-base','interconnect-rear-2-base','interconnect-front-base']:
                        cad(ax,name,color=GREEN if name=='C5-pcb' else '#7c9da4')
                    marker(ax,[[x,y,-10.91] for x,y in spec['case']['daughterboard_screw_axes']],'4 x M2');cad_limits(ax)
                elif figure in ('battery','routing'):
                    box3(ax,fit['battery_candidates'][0]['bounds_case_mm'],'#6f9f94')
                    for name in ['C5-pcb','C5-usb','C5-sh']:cad(ax,name,color='#678b8a')
                    if figure=='routing':
                        for extra in mesh['extra_parts']:
                            if extra['group']=='interconnect':
                                col={'red':'#bd4433','white':'#e4e4d5','green':'#2c7854','black':'#30434a','yellow':'#c89c28'}.get(extra['color'],'#89a8ac')
                                cad(ax,extra['mesh'],color=col)
                    cad_limits(ax)
                    if figure=='battery':marker(ax,[[228.5,-135,-5]],'J2 / NTC')
                elif figure in ('caps','close'):
                    cad(ax,'plate');cad(ax,'pcb')
                    if figure=='close':cad(ax,'top')
                    caps(ax);cad_limits(ax)
                    if figure=='close':marker(ax,[[x,y,2.59] for x,y in spec['case']['top_screw_axes']],'4 x M3')
                elif figure=='feet':
                    marker(ax,feet,'4 x SKUF',underside=True)
                    for x,y,z in feet:
                        # Dimensional envelope, 41.8 x 5.8 x 2 along the inclined floor.
                        angle=math.radians(7)
                        v=np.array([[x+sx*20.9,y+sy*2.9*math.cos(angle)-h*math.sin(angle),
                                     z-sy*2.9*math.sin(angle)-h*math.cos(angle)]
                                    for h in [0,2] for sx,sy in [(-1,-1),(1,-1),(1,1),(-1,1)]])
                        p=project(v,underside=True)
                        ax.add_collection(PolyCollection(p[[[0,1,5,4],[1,2,6,5],[4,5,6,7]]],facecolors='#435c61',edgecolors=BG,linewidths=.5,zorder=7))
                    service=spec['case']['service_port']['center_xy'];marker(ax,[[*service,-12]],'SW100',color='#d78845',underside=True);cad_limits(ax)
            locator=axis(fig,[.045,.045,.65,.19]); pcb(locator,refs or ['U1','J1','J2'],front=figure in ('plate','ec-stack','caps','calibration','test'))
            fig.text(.73,.16,wrap('Rear / number-row side stays up in PCB views. Back view is mirrored horizontally.' if not zh else 'PCB 图均以后侧数字行朝上；背面图已水平镜像。',zh,31),fontsize=10,color='#627d86')
            fig.text(.045,.245,'Placement only; tracks omitted; pad coordinates from native KiCad' if not zh else '布局示意：省略线路，焊盘坐标来自原生 KiCad',fontsize=9,color='#66818b')
            stem=step['id']+('-step.zh-CN' if zh else '-step')
            for ext in ['png','svg']:
                path=OUT/(stem+'.'+ext)
                fig.savefig(path,dpi=150,metadata={'Date':None} if ext=='svg' else None)
                if ext=='svg':path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
                outputs[str(path.relative_to(ROOT))]=sha(path)
            plt.close(fig)
            records.append({'id':step['id'],'language':'zh-CN' if zh else 'en','references':refs,'optional':step.get('optional',False),'image':str((OUT/(stem+'.png')).relative_to(ROOT))})
        suffix='.zh-CN' if zh else ''
        lines=[('中文 | [English](build-guide.md)' if zh else 'English | [Chinese](build-guide.zh-CN.md)'),'',
               '# '+('YETI60 逐步焊接与安装指南' if zh else 'YETI60 illustrated soldering and assembly guide'),'',
               ('本指南按 P2 当前主板、C5 JSH、1600 mAh 单电芯及原尺寸 FELK60 派生外壳生成。每一步均配独立示意图。尚无实物，图示是工程装配说明，不是已完成的操作照片。实际物料、胶碗／轴壳、钢网、充电及首件验收条件仍然适用。' if zh else 'This guide follows the current P2 mainboard, C5 JSH, 1600 mAh single-cell pack and source-sized FELK60-derived case. Every step has a separate illustration. No physical unit exists yet: these are engineering illustrations, not photographs of a completed build. Actual part, dome/housing, stencil, charging and first-article acceptance requirements still apply.'),'',
               ('[需要制作的 PCB 与完整材料](../../README.zh-CN.md#需要下单制作哪些-pcb) · [主板补购表](../../hardware/bom/mainboard-purchase.zh-CN.csv) · [子板自焊材料](../../hardware/bom/daughterboard.zh-CN.csv) · [结构尺寸](../engineering/assembly.zh-CN.md)' if zh else '[PCBs to fabricate and complete materials](../../README.md#which-pcbs-to-fabricate) · [Mainboard purchase plan](../../hardware/bom/mainboard-purchase.csv) · [C5 self-build parts](../../hardware/bom/daughterboard.csv) · [Assembly dimensions](../engineering/assembly.md)'),'',
               ('主板元件位于背面，主板图已按背面观察进行水平镜像；C5 图从 F.Cu 元件面观察。数字行侧为后方。金黄色圆圈标出原生焊盘 1，仍须与实际器件封装标识核对。PCB 线路省略，机械分解高度及未定型胶碗／轴壳／键帽外形为示意。' if zh else 'Mainboard parts are on the back; mainboard views are mirrored horizontally for looking at that face. C5 views look at its F.Cu component face. Rear means the number-row side. Gold rings identify native pad 1; compare them with the actual package mark. PCB tracks are omitted. Mechanical exploded offsets and unqualified dome/housing/cap shapes are illustrative.'),'',
               ('步骤 12–13 仅用于自焊 C5，购买成品时跳过；其余步骤仍需执行。' if zh else 'Steps 12–13 apply only to a bare C5 build; skip them with a populated daughterboard. The other checks still apply.'),'']
        lines += [('步骤目录' if zh else 'Step index'), '']
        lines += [f"- [{step['id']} {step['title'][lang]}](#step-{step['id']})" for step in steps]
        lines += ['']
        for step in steps:
            stem=step['id']+('-step.zh-CN' if zh else '-step')
            lines += [f"<a id=\"step-{step['id']}\"></a>",'','## '+step['id']+' — '+step['title'][lang],'',f"![{step['title'][lang]}](images/{stem}.png)",'',
                      ('[放大矢量图]' if zh else '[Vector enlargement]')+f'(images/{stem}.svg)','']
            lines += [f'{i}. {action}' for i,action in enumerate(step['actions'][lang],1)]
            lines += ['',('**检查后再继续：** ' if zh else '**Check before continuing:** ')+step['check'][lang],'']
            if step['references']:
                lines += [('本步放置位号：' if zh else 'References placed in this step: ')+', '.join(step['references'])+'.','',
                          ('| 位号 | 数量 | 设计值 | 封装 |' if zh else '| References | Quantity | Design value | Package |'),'|---|---:|---|---|']
                for row in bom:
                    rr=[r for r in row['References'].split(', ') if r in step['references']]
                    if rr:lines += [f"| {', '.join(rr)} | {len(rr)} | {row['Design value']} | {row['Package']} |"]
                lines += ['']
        lines += [('## 重建与依据' if zh else '## Rebuild and sources'),'',
                  ('使用 KiCad Python 执行 `scripts/export_yeti60_build_map.py`，再用 `requirements-audit.txt` 的 CAD 环境执行 `scripts/draw_yeti60_build_guide.py`。生成器核对 76 只主板元件均在放置步骤中出现一次、60 个实际电极、29 个安装孔及当前装配／线束来源。文件和图像哈希见 [指南验证记录](../audit/yeti60-build-guide.json)。' if zh else 'Run `scripts/export_yeti60_build_map.py` with KiCad Python, then `scripts/draw_yeti60_build_guide.py` with the CAD environment from `requirements-audit.txt`. The generator checks that all 76 mainboard components are placed exactly once, and checks the 60 active electrodes, 29 mounts and current assembly/harness sources. See the [guide evidence](../audit/yeti60-build-guide.json) for source and image hashes.'),'',
                  ('编排参考 [DELTA OMEGA 安装指南](https://github.com/wZuck/delta-omega/blob/main/docs/BUILD_GUIDES.md) 的逐工序图示形式；图像及位号按 YETI60 原生数据重新绘制，不沿用 MX 焊接步骤。' if zh else 'The per-operation illustrated format follows the [DELTA OMEGA build guide](https://github.com/wZuck/delta-omega/blob/main/docs/BUILD_GUIDES.md). Images and references are redrawn from YETI60 native data; its MX soldering operations do not apply here.'),'',
                  ('焊接依据：[TI QFN／SON 装配说明 SLUA271C](https://www.ti.com/lit/an/slua271c/slua271c.pdf) 的钢网、回流和隐藏焊点检查章节；[Ebyte E73-2G4M08S1C 资料](https://www.ebyte.com/product/444.html) 的模组引脚、尺寸及独立焊接工艺包；[C&K JS 系列资料](https://www.ckswitches.com/media/1422/js.pdf) 的开关封装和焊接限制。电源、线束及固件步骤另按本仓库 [电源计算](../engineering/power-budget.zh-CN.md)、[线束规格](../engineering/interconnects.zh-CN.md)、[目标固件说明](../../firmware/target/README.zh-CN.md)。' if zh else 'Soldering references: [TI QFN/SON attachment SLUA271C](https://www.ti.com/lit/an/slua271c/slua271c.pdf), stencil, reflow and hidden-joint inspection sections; [Ebyte E73-2G4M08S1C documentation](https://www.ebyte.com/product/444.html), module pin/dimension data and separate solder-process package; [C&K JS data](https://www.ckswitches.com/media/1422/js.pdf), switch package and soldering limits. Power, cable and firmware instructions also follow the repository [power calculations](../engineering/power-budget.md), [interconnect specification](../engineering/interconnects.md) and [target firmware procedure](../../firmware/target/README.md).'),'']
        doc=ROOT/('docs/assembly/build-guide'+suffix+'.md');doc.write_text('\n'.join(lines));outputs[str(doc.relative_to(ROOT))]=sha(doc)
    source_paths=[STEPS,ROOT/native['pcb_source'],ROOT/native['daughterboard']['source'],
                  ROOT/'hardware/bom/mainboard.csv',ROOT/'hardware/bom/daughterboard.csv',
                  ROOT/'mechanical/assembly-spec.json',ROOT/'mechanical/interconnect-spec.json',
                  ROOT/'docs/audit/yeti60-assembly.json',ROOT/'docs/audit/yeti60-interconnects.json',
                  ROOT/'docs/audit/yeti60-key-geometry.json',
                  ROOT/'firmware/target/README.md',ROOT/'firmware/target/config/yeti60.keymap',
                  ROOT/'firmware/target/boards/yeti/yeti60/yeti60.dts',
                  ROOT/'scripts/export_yeti60_build_map.py',Path(__file__).resolve()]
    report={'status':'source-linked-illustrated-prototype-guide','production_approved':False,
            'steps_per_language':28,'fitted_mainboard_references_placed_once':sorted(installed),
            'active_electrodes':active_electrodes,'mounting_holes':29,'underside_foot_pocket_centers_case_mm':feet,
            'mainboard_view':'component side, native X mirrored; rear row at top',
            'daughterboard_view':'F.Cu component side, native X retained; not a mating-plug view',
            'native_map_sha256':sha(MAP),'geometry_sources':mesh['geometry_sources'],
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in source_paths},
            'outputs':outputs,'steps':records,
            'limits':['Engineering illustrations, no physical assembly evidence','Actual part/paste/stencil/profile qualification required',
                      'Dome/housing/cap shapes and exploded offsets illustrative; actual selected parts require local acceptance',
                      'No RF/SI, lifetime, charging or production certification']}
    (ROOT/'docs/audit/yeti60-build-guide.json').write_text(json.dumps(report,indent=2)+'\n')
    print('28 illustrated steps per language; 112 PNG/SVG assets; all 76 mainboard placements covered once')


if __name__=='__main__':
    main()
