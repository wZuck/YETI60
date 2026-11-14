#!/usr/bin/env python3
"""Draw the actual corner PCB geometry; this is not an assembly photograph."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

ROOT = Path(__file__).resolve().parents[1]


def main():
    spec_path = ROOT / 'hardware/e73-corner-spec.json'
    s = json.loads(spec_path.read_text())
    base = ROOT / s['output_directory']
    pcb_path = base / 'EC60-nRF52840.kicad_pcb'
    proof_path = base / 'audit/placement-check.json'
    proof = json.loads(proof_path.read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, digest in proof['source_sha256'].items():
        assert sha(ROOT / name) == digest, ('Stale drawing proof', name)
    data = json.loads((ROOT / '.assembly-work/e73-corner/native-layout.json').read_text())
    assert data['pcb_sha256'] == sha(pcb_path)
    plt.rcParams['font.family'] = ['Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['svg.hashsalt'] = 'yeti60-e73-hhkb-corner'
    outputs = {}
    for zh in [False, True]:
        fig = plt.figure(figsize=(14, 8), facecolor='#f8faf9')
        grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.15], width_ratios=[1.5, 1])
        overview = fig.add_subplot(grid[0, :])
        zoom = fig.add_subplot(grid[1, 0])
        info = fig.add_subplot(grid[1, 1])
        for ax in [overview, zoom]:
            for p in data['outline']:
                ax.add_patch(Polygon(p, closed=True, facecolor='#e2eee6', edgecolor='#587260', lw=.8))
            for q in data['electrodes']:
                for p in q['polygons']:
                    ax.add_patch(Polygon(p, closed=True, facecolor='#bb9343' if q['active'] else '#bdc6be', edgecolor='none', alpha=.65))
            for q in data['parts']:
                if q['ref'].startswith('H'):
                    ax.plot(*q['xy'], marker='+', color='#303b34', ms=4, mew=.8)
                    if ax is zoom and q['xy'][0] > 308 and q['xy'][1] > 176:
                        ax.text(q['xy'][0], q['xy'][1]-1.2, q['ref'], ha='center', fontsize=8)
                else:
                    x, y, X, Y = q['bbox']
                    ax.add_patch(Rectangle((x,y),X-x,Y-y,facecolor='#deddd8',edgecolor='#626c65',lw=.7))
                    if ax is zoom:
                        ax.text((x+X)/2,(y+Y)/2,q['ref'],ha='center',va='center',fontsize=8)
            x, y, X, Y = data['body']
            ax.add_patch(Rectangle((x,y),X-x,Y-y,facecolor='#3072a0',edgecolor='#124c72',alpha=.8,lw=1.3))
            ax.text((x+X)/2,(y+Y)/2,'E73\nU1',ha='center',va='center',color='white',fontsize=11)
            x, y, X, Y = data['antenna']
            ax.add_patch(Rectangle((x,y),X-x,Y-y,facecolor='#e9ac52',edgecolor='#a96a19',hatch='///',lw=.8))
            for net, points in s['data_paths_B_Cu_mm'].items():
                ax.plot(*zip(*points), color='#3758a2' if net == 'USB_DM' else '#a33e71', lw=1.2)
            ax.set_aspect('equal')
            ax.grid(alpha=.12)
            ax.tick_params(labelsize=8)
        overview.set(xlim=(69,360),ylim=(201,101))
        overview.set_title('实际 PCB 顶视；正面与背面元件均投影到同一平面' if zh else 'Actual PCB top view; front and back components projected onto one plane',fontsize=12,loc='left')
        overview.add_patch(Rectangle((311,177),45,22,fill=False,edgecolor='#ba6040',lw=1.5))
        zoom.set(xlim=(307,358),ylim=(201,175))
        zoom.set_xlabel('PCB X 坐标（毫米）' if zh else 'PCB X (mm)')
        zoom.set_ylabel('PCB Y 坐标（毫米）' if zh else 'PCB Y (mm)')
        zoom.set_title('右下角放大：删除 SW72／SW73 电极' if zh else 'Lower-right detail: SW72/SW73 electrodes removed',fontsize=11,loc='left')
        info.axis('off')
        info.text(.02,.95,'右下空角，模组正面安装' if zh else 'Front-mounted module in the empty corner',fontsize=13,weight='bold',va='top',color='#194e6d')
        lines = (['60 个有效感应位置保留','43 个模组焊盘用途保持一致','28 处已用安装孔保留，H26 仍不装','天线朝右侧；金属定位板仍覆盖其上方',
                  '蓝／紫线：新的背面 USB 差分走线','仅模组在正面','C31 随模组迁移，靠近 3.3 V 供电脚','仍需装配／无线验收，不能据此下单'] if zh else
                 ['60 effective sensing positions retained','43 module pad roles preserved','28 installed mounts retained; H26 stays unused','Antenna toward right; steel plate remains above it',
                  'Blue/purple: new back-layer USB routes','Only U1 is front-mounted','C31 moved beside the 3.3 V supply launch','Assembly/RF open; not a fabrication release'])
        for index, text in enumerate(lines):
            info.text(.02,.82-index*.095,text,fontsize=10,va='top',color='#314038')
        fig.suptitle('YETI60 · E73 右下角迁移候选' if zh else 'YETI60 · E73 lower-right placement candidate',fontsize=16,x=.05,ha='left')
        fig.text(.05,.025,'原生铜箔及尺寸驱动的工程图；不是完整装配或无线性能证明。' if zh else 'Native copper and dimension-driven engineering view; not full assembly or RF acceptance.',fontsize=9,color='#5c6860')
        fig.subplots_adjust(left=.06,right=.97,top=.90,bottom=.10,hspace=.35,wspace=.16)
        for ext in ['png','svg']:
            path = base / 'audit' / ('corner-layout'+('.zh-CN' if zh else '')+'.'+ext)
            fig.savefig(path,dpi=170,metadata={'Date':None} if ext == 'svg' else None)
            if ext == 'svg':
                path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
            outputs[str(path.relative_to(ROOT))] = sha(path)
        plt.close(fig)
    report = dict(status='native-placement-drawings-generated', physical_verification=False,
                  source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [spec_path,pcb_path,proof_path,Path(__file__)]},outputs=outputs)
    (base/'audit/drawing.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Generated paired English/Chinese engineering views from current native geometry')


if __name__ == '__main__':
    main()
