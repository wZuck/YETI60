#!/usr/bin/env python3
"""Draw dimensioned E73 local envelopes from the checked fit payload."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/e73-usb-repair'


def draw(report,spec):
    assert report['status']=='e73-local-usb-body-and-ordered-withdrawal-screen-passed'
    plt.rcParams['font.family']=['Arial Unicode MS','DejaVu Sans']
    plt.rcParams['svg.hashsalt']='yeti60-e73-usb-fit-m02'
    outputs={}
    for zh in [False,True]:
        fig,(ax,budget)=plt.subplots(1,2,figsize=(12,6),gridspec_kw={'width_ratios':[1.15,1]})
        bb=spec['floor_relief']['bounds_case_mm']
        ax.add_patch(FancyBboxPatch((bb[0],bb[1]),bb[3]-bb[0],bb[4]-bb[1],
                                   boxstyle=f"round,pad=0,rounding_size={spec['floor_relief']['corner_radius_mm']}",
                                   fc='#edf2fa',ec='#7189a9',lw=1.5))
        ax.text(332.4,-121.4,'M02 内凹边界' if zh else 'M02 relief boundary',fontsize=9,color='#526a89')
        colors={'J4':'#277e9a','J5':'#b97225','C32':'#617c47'}
        for ref,body in report['required_body_bounds_case_mm'].items():
            ax.add_patch(Rectangle((body[0],body[1]),body[3]-body[0],body[4]-body[1],fc=colors[ref],alpha=.8))
            if ref=='C32':
                ax.text((body[0]+body[3])/2,body[1]-.7,ref,ha='center',va='center',color='#405929',fontsize=10)
            else:
                ax.text((body[0]+body[3])/2,(body[1]+body[4])/2,ref,ha='center',va='center',color='white',fontsize=10)
        for ref,data in report['mating_housings'].items():
            p=data['bounds_case_mm'];i,direction=data['axis'];stroke=spec['withdrawal_stroke_mm']
            sweep=p[:];sweep[i if direction<0 else i+3]+=direction*stroke
            ax.add_patch(Rectangle((sweep[0],sweep[1]),sweep[3]-sweep[0],sweep[4]-sweep[1],fill=False,ec=colors[ref],ls='--',lw=1.5))
            ax.add_patch(Rectangle((p[0],p[1]),p[3]-p[0],p[4]-p[1],fc='#fff3d8',ec=colors[ref],alpha=.75))
            center=[(p[0]+p[3])/2,(p[1]+p[4])/2];end=center[:];end[i]+=direction*stroke
            ax.annotate('',xy=end,xytext=center,arrowprops={'arrowstyle':'->','lw':2,'color':colors[ref]})
            label=('1：先拔 J5' if zh else '1: unplug J5 first') if ref=='J5' else ('2：再拔 J4' if zh else '2: unplug J4 second')
            ax.text(end[0]-.2,end[1]+1.0,label,fontsize=9,color=colors[ref],ha='center')
        ax.set(xlim=(330.8,353),ylim=(-123.5,-104),aspect='equal',
               xlabel='外壳 X (mm)' if zh else 'Case X (mm)',ylabel='外壳 Y (mm)' if zh else 'Case Y (mm)')
        ax.set_title('原始尺寸平面包络' if zh else 'Plan envelopes at source dimensions',fontsize=12)
        ax.grid(alpha=.18)
        minimum=min(c['remaining_case_air_gap_mm'] for c in report['checks'])
        wall=report['case_repair']['minimum_remaining_selected_exterior_wall_after_allowances_mm']
        rows=[('安装包络高度上限' if zh else 'Installed height limit',spec['maximum_height_below_local_PCB_mm']['J4']),
              ('板厚向下增加' if zh else 'Board thickness growth',max(report['PCB_thickness_acceptance_interval_mm'])-report['PCB_nominal_thickness_mm'])]
        rows += [('定位板安装' if zh else 'Installed plate',report['vertical_error_terms_mm']['plate']),
                 ('支柱长度' if zh else 'Shoulder length',report['vertical_error_terms_mm']['shoulder']),
                 ('绝缘膜厚度' if zh else 'Insulating film',report['vertical_error_terms_mm']['film']),
                 ('装配板弯' if zh else 'Mounted PCB bow',report['vertical_error_terms_mm']['bow']),
                 ('外壳坐标误差 L2' if zh else 'Case coordinate error L2',report['case_coordinate_error_L2_mm']),
                 ('计算保护量' if zh else 'Computation guard',report['geometric_computation_guard_mm']),
                 ('剩余最小间隙' if zh else 'Minimum remaining gap',minimum)]
        for k,(label,value) in enumerate(rows):
            budget.barh(k,value,color='#2c8b68' if k==len(rows)-1 else '#97a8bb',height=.6)
            budget.text(value+.04,k,f'{value:.3f}',va='center',fontsize=9)
        budget.set_yticks(range(len(rows)),[r[0] for r in rows],fontsize=9)
        budget.invert_yaxis();budget.set_xlim(0,3.8);budget.set_xlabel('mm')
        budget.set_title('竖向预算与结果' if zh else 'Vertical budget and result',fontsize=12)
        budget.spines[['top','right']].set_visible(False)
        fig.suptitle('E73 USB 局部装配：J5 → J4 拆卸顺序' if zh else 'E73 local USB assembly: unplug J5 before J4',fontsize=15)
        note=(f'内凹底面 Z = {bb[2]:.2f} mm；扣除误差后壁厚 ≥ {wall:.3f} mm。线束、工具和整机装配尚未验收。' if zh else
              f'Relief floor Z = {bb[2]:.2f} mm; wall after allowances ≥ {wall:.3f} mm. Wires, tools and complete assembly remain unqualified.')
        fig.text(.5,.07,note,ha='center',fontsize=9)
        stroke=spec['withdrawal_stroke_mm']
        fig.text(.5,.025,f'实线：名义平面尺寸；虚线：{stroke:g} mm 连续拔出包络。检查使用另加公差的三维实体。' if zh else
                 f'Solid: nominal plan sizes. Dashed: continuous {stroke:g} mm withdrawal. Checks use expanded 3D solids.',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.12,1,.93))
        for extension in ['svg','png']:
            path=BASE/'audit'/('USB-local-fit'+('.zh-CN' if zh else '')+'.'+extension)
            fig.savefig(path,dpi=160,metadata={'Date':None} if extension=='svg' else None)
            if extension=='svg':path.write_text('\n'.join(s.rstrip() for s in path.read_text().splitlines())+'\n')
            outputs[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        plt.close(fig)
    return outputs


if __name__=='__main__':
    report=json.loads((BASE/'audit/local-fit.json').read_text())
    for name,digest in report['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,('Stale fit input',name)
    paths=draw(report,json.loads((ROOT/'hardware/e73-usb-local-fit-spec.json').read_text()))
    assert all(report['outputs'][name]==digest for name,digest in paths.items()),'Drawing reproduction differs'
