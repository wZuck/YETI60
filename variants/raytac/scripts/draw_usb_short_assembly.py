#!/usr/bin/env python3
"""Draw separate EN/CN instructions from checked candidate geometry."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from check_usb_short_closed_assembly import hashes
from usb_short_harness import point_at

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'
OUT = BASE / 'assembly'
COLORS = {'red': '#b52d25', 'white': '#fffdf0', 'green': '#1c8753', 'black': '#28333b', 'yellow': '#cca414'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def sample(path):
    return np.array([v for p in path for v in (p['points'] if p['kind'] == 'twist'
                    else [point_at(p, t) for t in np.linspace(0, 1, 25 if p['kind'] == 'arc' else 2)])])


def main():
    OUT.mkdir(exist_ok=True)
    closed = read(BASE / 'audit/closed-assembly.json')
    assembly = read(BASE / 'audit/assembly.json')
    guides = read(BASE / 'audit/guides.json')
    spec = read(BASE / 'interconnect-spec.json')
    mesh = read(ROOT / '.assembly-work/usb-short-assembly/render-meshes.json')
    hashes(closed['source_sha256']); hashes(guides['source_sha256']); hashes(assembly['source_sha256'])
    assert mesh['assembly_report_sha256'] == sha(BASE / 'audit/assembly.json')
    plt.rcParams.update({'svg.fonttype': 'path', 'svg.hashsalt': 'YETI60-SHORT-ASSEMBLY', 'font.size': 9})
    outputs = {}

    def save(fig, stem):
        for ext in ['png', 'svg']:
            target = OUT / (stem + '.' + ext)
            fig.savefig(target, dpi=180, metadata={'Date': None} if ext == 'svg' else {'Software': 'YETI60'})
            if ext == 'svg':
                target.write_text('\n'.join(line.rstrip() for line in target.read_text().splitlines()) + '\n')
            outputs[str(target.relative_to(ROOT))] = sha(target)
        plt.close(fig)

    def plan(ax, families, crop, guide_labels=False, substrate=True):
        bottom = mesh['meshes']['bottom']; v = np.array(bottom['vertices_mm']); t = np.array(bottom['triangles'])
        ax.add_collection(PolyCollection(v[t, :2], facecolors='#e4e8eb', edgecolors='none', rasterized=True))
        b = assembly['battery_candidates'][0]['bounds_case_mm']
        ax.add_patch(Rectangle(b[:2], b[3]-b[0], b[4]-b[1], fc='#d4e3d6', ec='#718874', lw=.8))
        ax.text((b[0]+b[3])/2, (b[1]+b[4])/2, '85 × 43 × 4.8 mm\n1600 mAh / 1S', ha='center', va='center', fontsize=9)
        for name in ['C5-pcb', 'C5-usb']:
            b = mesh['meshes'][name]['brep_bounds_mm']
            ax.add_patch(Rectangle(b[:2], b[3]-b[0], b[4]-b[1], fc='#94ac9e' if name.endswith('pcb') else '#adb5bc', ec='#59666c', lw=.7))
        if substrate:
            for p in assembly['component_envelopes']:
                b = p['bounds_case_mm']
                ax.add_patch(Rectangle(b[:2], b[3]-b[0], b[4]-b[1], fc='#697b86', alpha=.16, lw=0))
        for h in assembly['mounting_hole_matches']:
            x, y = h['pcb_center_case_mm']
            ax.add_patch(plt.Circle((x,y),2.1,fill=False,ec='#73818b',lw=.5))
        for h in assembly['mated_housings']:
            b = h['bounds_case_mm']
            ax.add_patch(Rectangle(b[:2], b[3]-b[0], b[4]-b[1], fc='#ece4d0', ec='#96886d', lw=.8))
        for family in families:
            for pin, path in closed['nominal']['routes'][family].items():
                p = sample(path)
                ax.plot(p[:,0],p[:,1],color='#5e6870',lw=2.2,zorder=5)
                ax.plot(p[:,0],p[:,1],color=COLORS[spec[family]['colors'][pin]],lw=1.35,zorder=6)
        for p in guides['parts']:
            if p['harness'] not in families and families:
                continue
            b = p['bounds_case_mm']
            ax.add_patch(Rectangle(b[:2],b[3]-b[0],b[4]-b[1],fill=False,ec='#397a92',lw=.65,zorder=7))
            if guide_labels and not p['name'].endswith('lid'):
                ax.annotate(p['name'],((b[0]+b[3])/2,(b[1]+b[4])/2),xytext=(4,9),textcoords='offset points',fontsize=6,color='#1f6078')
        labels = [('J1',(121,-129)),('J2',(152,-132)),('C5',(214,-113)),('J5',(340,-117)),('J4',(350,-121))]
        for name, (x,y) in labels:
            ax.text(x,y,name,ha='center',fontsize=9,fontweight='bold')
        ax.set(xlim=crop[:2],ylim=crop[2:],aspect='equal',xlabel='外壳 X / mm' if zh else 'Case X / mm',ylabel='外壳 Y / mm' if zh else 'Case Y / mm')
        ax.grid(alpha=.12); ax.set_facecolor('#f8fafb')

    steps = [
        ('Inspect the relieved bottom', '检查内槽底壳', [], (50,379,-210,-90),
         'Use the candidate bottom.\nThe original exterior is retained.\n\nNew relief:\nX 190…354 / Y −106.3…−98\nZ −5.25…−1.9 mm\n\n2.16 mm nominal checked skin;\n2.01 mm after case tolerance.\n\nRF service notch: X 357.25…365.25\nY −132.75…−113.75 / Z −4.45…12.3\nPrint 16 guides at 1:1; tolerance ±0.05 mm.',
         '使用候选方案底壳。\n保留原版外轮廓。\n\n新增内槽：\nX 190…354 / Y −106.3…−98\nZ −5.25…−1.9 mm\n\n检查区域壁厚标称 2.16 mm；\n扣除外壳公差后 2.01 mm。\n\n射频检修槽：X 357.25…365.25\nY −132.75…−113.75／Z −4.45…12.3\n16 件按 1:1 打印，公差 ±0.05 mm。'),
        ('Build the PCB power jumper', '安装主板供电跳线', ['power'], (117,351,-132,-104),
         'Mainboard remains unpowered.\nFit J4 and J5; omit R30/R31.\n\nJ5.1 → J1.1: supply\nJ5.2 → J1.4: ground\nJ1.2 and J1.3: empty\n\nFit PWR-R1…R5 under the PCB.\nAt J1, red uses the upper guide;\nblack uses the removable lower guide.\nMeter pin numbers, not housing left/right.',
         '主板保持断电。\n焊接 J4、J5；不装 R30／R31。\n\nJ5.1 → J1.1：供电\nJ5.2 → J1.4：地\nJ1.2、J1.3：空置\n\n在 PCB 下安装 PWR-R1…R5。\nJ1 附近红线在上层；\n黑线在可拆下层。\n按针号测通断，不按胶壳左右猜测。'),
        ('Preform the four-wire USB cable', '预成形四线 USB 线束', ['usb'], (185,357,-176,-98),
         'C5 1/2/3/4 → J4 1/2/3/4\nSupply / D− / D+ / ground\n\nThree full rear pair twists.\nHalf-turn on each front leg.\nGeometric pair skew ≈0.314 mm.\n\nFit USB-R1…R3 roof clips.\nFit USB-F1/F2 bases, then lids.\nPlace wires through open halves;\ndo not pull crimp housings through grooves.',
         'C5 1／2／3／4 → J4 1／2／3／4\n供电／D−／D+／地\n\n后方数据对绞三整圈。\n前方两条直线各半圈。\n几何长度差约 0.314 mm。\n\n安装 USB-R1…R3 顶挂夹。\n安装 USB-F1／F2 底座，再装盖。\n导线放入敞开的槽；\n不要把压接胶壳硬拉过槽口。'),
        ('Fit C5 and the protected pack', '安装 C5 与保护电池包', ['battery'], (140,319,-153,-101),
         'Use the selected 1S 4.2 V protected pack.\nFull pack ≤85 × 43 × 4.8 mm.\nSupplier must confirm its complete drawing.\n\nJ2.1: PACK+\nJ2.2: PACK−\nJ2.3: 10k NTC to PACK−\n\nFit BAT-R1/R2 and insulation.\nConfirm polarity before mating.\nDo not compress the pouch or its PCM.',
         '使用选定的 1S、4.2 V 保护电池包。\n完整包络不超过 85 × 43 × 4.8 mm。\n必须由供方确认完整图纸。\n\nJ2.1：PACK+\nJ2.2：PACK−\nJ2.3：10k NTC，另一端接 PACK−\n\n安装 BAT-R1／R2 与绝缘。\n插接前测量正负极。\n不得挤压软包或保护板。'),
        ('Check the three harnesses together', '联合检查三组线束', ['usb','power','battery'], (116,357,-176,-98),
         'Check both power crossover dips.\nKeep every guide/film releasable.\nRoute position must remain within 0.25 mm.\n\nUse 13 fixed bond faces at 0.1 mm.\nThree removable interfaces at 0.05 mm.\nTwelve retention films ≤0.1 mm total each.\n\nThis view proves installed geometry only.\nThe lifting/mating path and springback\nstill require a first-article trial.',
         '检查两处供电线下沉交叉。\n理线盖和压膜必须可释放。\n线位偏离控制路径不超过 0.25 mm。\n\n13 处固定粘接面：0.1 mm。\n3 处可拆界面：0.05 mm。\n12 条压膜：每条总厚度不超过 0.1 mm。\n\n本图只说明最终安装位置。\n抬起／插接路径与导线回弹\n仍需首件试装验证。'),
        ('Bench-test before closing', '关壳前进行台架验证', ['usb','power','battery'], (50,379,-210,-90),
         '1  Meter shorts, pin mapping and polarity.\n2  USB alone: enumerate and test every key.\n3  Battery alone: test BLE and sleep/wake.\n4  USB + battery: USB typing while charging.\n5  Verify NTC response and temperature.\n6  Trial-fit slowly; never force closure.\n\nRelease retention before lifting the PCB.\nRecord measured results in the test log.\nNo physical acceptance is claimed here.',
         '1  测短路、针号与极性。\n2  仅 USB：枚举并逐键测试。\n3  仅电池：测试蓝牙、休眠与唤醒。\n4  USB＋电池：边充电边经 USB 输入。\n5  测 NTC 响应与温升。\n6  缓慢试合，禁止强行压紧。\n\n抬起 PCB 前先释放线束固定。\n把实测结果填入验收记录。\n这里没有声称已经通过实物验收。')]
    for zh in [False, True]:
        plt.rcParams['font.family'] = 'Arial Unicode MS' if zh else 'DejaVu Sans'
        suffix = '.zh-CN' if zh else ''
        for i, (en, cn, families, crop, note_en, note_cn) in enumerate(steps, 1):
            fig = plt.figure(figsize=(15,8),facecolor='#f6f8fa')
            grid = fig.add_gridspec(1,2,width_ratios=[2.2,1])
            ax = fig.add_subplot(grid[0]); plan(ax,families,crop,guide_labels=i in [2,3,4])
            text = fig.add_subplot(grid[1]); text.axis('off'); text.text(0,.96,note_cn if zh else note_en,va='top',fontsize=10.5,linespacing=1.7)
            if i == 1:
                x0,y0,z0,x1,y1,z1 = spec['case_pocket']['bounds_case_mm']
                ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#bd7a25',alpha=.5))
                x0,y0,z0,x1,y1,z1=spec['case_service_relief']['bounds_case_mm']
                ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#b53c50',alpha=.65))
            fig.suptitle(f'YETI60  /  {i:02d}  '+(cn if zh else en),x=.05,ha='left',fontsize=19,fontweight='bold')
            fig.text(.05,.035,'单位 mm；由检查过的原始尺寸几何生成。胶壳为保守包络，非供应商精细外观。' if zh else 'Dimensions in mm; drawn from checked source-sized geometry. Mating plugs are conservative envelopes, not detailed supplier surfaces.',fontsize=9)
            fig.subplots_adjust(left=.05,right=.98,bottom=.13,top=.9,wspace=.15)
            save(fig,f'step-{i:02d}'+suffix)
        fig=plt.figure(figsize=(15,12),facecolor='#f6f8fa')
        for index,p in enumerate(guides['parts'],1):
            ax=fig.add_subplot(4,4,index,projection='3d',proj_type='ortho')
            m=mesh['meshes']['guide-'+p['name']];v=np.array(m['vertices_mm']);t=np.array(m['triangles']);b=p['bounds_case_mm']
            v-=v.min(axis=0)
            if p['print_flip_about_X_deg']==180:v[:,1:]*=-1
            v-=v.min(axis=0);size=v.max(axis=0);tri=v[t]
            normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);lengths=np.linalg.norm(normals,axis=1);normals/=np.maximum(lengths[:,None],1e-12)
            light=np.array([-.3,-.4,1]);light/=np.linalg.norm(light)
            shade=.5+.5*np.maximum(normals@light,0);colors=shade[:,None]*np.array([.42,.57,.62])[None,:]
            ax.add_collection3d(Poly3DCollection(tri,facecolors=colors,edgecolors='none',rasterized=True))
            ax.set(xlim=(0,size[0]),ylim=(0,size[1]),zlim=(0,size[2]));ax.set_box_aspect(size)
            ax.view_init(elev=28,azim=-55);ax.set_axis_off()
            ax.set_title(p['name']+'  ×1',fontsize=11,loc='left')
            ax.text2D(.5,-.03,' × '.join(f'{b[i+3]-b[i]:.2f}' for i in range(3))+' mm',ha='center',transform=ax.transAxes,fontsize=9)
        fig.suptitle('YETI60  /  '+('16 件理线件索引：打印朝向的轴测图' if zh else '16-piece guide index: print-orientation isometric views'),x=.05,ha='left',fontsize=18,fontweight='bold')
        fig.text(.05,.025,'标注为 X × Y × Z 包络；打印用 STL 已调整朝向并移到原点。不可从图片量取打印比例。' if zh else 'Labels give X × Y × Z envelopes. Print STLs are oriented and moved to the origin. Do not derive print scale from this sheet.',fontsize=10)
        fig.subplots_adjust(left=.05,right=.97,bottom=.08,top=.91,wspace=.3,hspace=.65)
        save(fig,'guide-index'+suffix)
    dependencies=[BASE/'audit/closed-assembly.json',BASE/'audit/assembly.json',BASE/'audit/guides.json',BASE/'interconnect-spec.json',
                  ROOT/'scripts/usb_short_harness.py',ROOT/'scripts/interconnect_geometry.py',Path(__file__)]
    report=dict(status='source-derived-candidate-steps-generated',outputs=outputs,
                source_sha256={str(p.relative_to(ROOT)):sha(p) for p in dependencies},physical_verification=False,
                limits=['2D projections are instructions, not additional clearance proof', 'Service swept path, retention and supplier part qualification remain open'])
    (BASE/'audit/assembly-drawings.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Six assembly sheets and 16-part index generated in separate English and Chinese versions')


if __name__=='__main__':
    main()
