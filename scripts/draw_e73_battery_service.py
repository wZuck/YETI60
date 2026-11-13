#!/usr/bin/env python3
"""E73 battery connector envelope and numbered wiring drawings, from fit data."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/e73-usb-repair'


def draw(report):
    assert report['status']=='e73-sh3-native-landing-and-bounded-rigid-service-passed'
    plt.rcParams['font.family']=['Arial Unicode MS','DejaVu Sans'];plt.rcParams['svg.hashsalt']='yeti60-e73-battery-sh3'
    result={};old=report['pre_repair_regression'];new=report
    for zh in [False,True]:
        fig,axes=plt.subplots(1,3,figsize=(13.5,6),gridspec_kw={'width_ratios':[1,1,.95]})
        for ax,legacy in zip(axes[:2],[True,False]):
            header=old['PH_header_proxy_bounds_case_mm'] if legacy else new['header_required_body_bounds_case_mm']
            plug=old['PH_plug_bounds_case_mm'] if legacy else new['mated_housing_bounds_case_mm']
            sweep=old['PH_sweep_bounds_case_mm'] if legacy else new['continuous_withdrawal_bounds_case_mm']
            color='#ad4943' if legacy else '#278767'
            h=old['H8_proxy_bounds_case_mm']
            ax.add_patch(Rectangle((h[0],h[1]),h[3]-h[0],h[4]-h[1],fc='#c8cdd4',ec='#5e6773',hatch='//',alpha=.6))
            ax.text((h[0]+h[3])/2,h[4]+.7,'H8',ha='center',fontsize=10)
            ax.add_patch(Rectangle((header[0],header[1]),header[3]-header[0],header[4]-header[1],fc='#aeb8c1',alpha=.7))
            ax.add_patch(Rectangle((sweep[0],sweep[1]),sweep[3]-sweep[0],sweep[4]-sweep[1],fill=False,ec=color,lw=1.8,ls='--'))
            ax.add_patch(Rectangle((plug[0],plug[1]),plug[3]-plug[0],plug[4]-plug[1],fc=color,alpha=.35))
            x=(plug[0]+plug[3])/2;y=(plug[1]+plug[4])/2
            ax.annotate('',xy=(x,y+4),xytext=(x,y),arrowprops={'arrowstyle':'->','color':color,'lw':2})
            ax.text(x,y-1,'PHR-3' if legacy else 'SHR-03V-S',ha='center',fontsize=9,color=color)
            ax.set(xlim=(143.5,162),ylim=(-134.5,-108.5),aspect='equal',xlabel='外壳 X (mm)' if zh else 'Case X (mm)')
            ax.set_ylabel('外壳 Y (mm)' if zh else 'Case Y (mm)');ax.grid(alpha=.18)
            ax.set_title(('修补前：PH 包络不通过' if zh else 'Before: PH envelope rejected') if legacy else
                         ('修补后：SH3 局部包络通过' if zh else 'After: SH3 local envelope passed'),fontsize=11)
        ax=axes[2];ax.axis('off')
        ax.text(.5,.92,'按针号测量通断' if zh else 'Check continuity by pin number',ha='center',fontsize=12)
        rows=[('1','PACK+','#be4a45'),('2','PACK−','#444b55'),('3','NTC','#a78221')]
        for k,(pin,role,color) in enumerate(rows):
            y=.75-k*.14
            ax.add_patch(Rectangle((.04,y-.05),.92,.1,fc='#f0f3f6',ec='#ced5dc'))
            ax.text(.13,y,pin,color=color,fontsize=15,va='center')
            ax.text(.39,y,role,color=color,fontsize=13,va='center')
        ax.text(.5,.29,'NTC 接保护包负极\n无凸耳胶壳，1 mm 间距\n不是插头端面观察图' if zh else
                'NTC referenced to protected PACK−\nHousing without protrusions, 1 mm pitch\nNot a mating-face orientation drawing',ha='center',va='center',fontsize=10,linespacing=1.7)
        min_gap=min(r['remaining_case_air_gap_mm'] for r in report['checks'])
        ax.text(.5,.1,(f'最小剩余外壳间隙\n{min_gap:.3f} mm' if zh else f'Minimum remaining case gap\n{min_gap:.3f} mm'),ha='center',fontsize=12,color='#267956')
        fig.suptitle('E73 三线电池接口：PH → SH3' if zh else 'E73 three-wire battery interface: PH → SH3',fontsize=15)
        fig.text(.5,.08,'平面名义包络；检查使用计入公差的连续三维实体。电池保护、工具及完整带线检修尚未验收。' if zh else
                 'Nominal plan envelopes; checks use continuous expanded 3D solids. Battery safety, tools and complete connected service remain unqualified.',ha='center',fontsize=9)
        fig.text(.5,.025,'胶壳为 SHR-03V-S，不用带凸耳的 SHR-03V-S-B。线长及柔性停放路径另行确定。' if zh else
                 'Use SHR-03V-S, not the protruding SHR-03V-S-B. Lead lengths and flexible parking paths require separate closure.',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.12,1,.93))
        for extension in ['svg','png']:
            path=BASE/'audit'/('battery-service'+('.zh-CN' if zh else '')+'.'+extension)
            fig.savefig(path,dpi=160,metadata={'Date':None} if extension=='svg' else None)
            if extension=='svg':path.write_text('\n'.join(s.rstrip() for s in path.read_text().splitlines())+'\n')
            result[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        plt.close(fig)
    return result


if __name__=='__main__':
    report=json.loads((BASE/'audit/battery-service.json').read_text())
    for path,digest in report['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,('Stale battery drawing input',path)
    for path,digest in draw(report).items():assert report['outputs'][path]==digest,('Drawing reproduction changed',path)
