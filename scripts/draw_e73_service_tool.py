#!/usr/bin/env python3
"""Illustrate the blade profile and the M05 tool's opposing grips."""

import json
from pathlib import Path

import ezdxf
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

from build_e73_service_tool import BLADE_WIDTH, CLAMP_Z, GUIDES_Z, ROOT, AUDIT, TOOLS
from check_e73_corner_service import read, sha, verify


def draw(profile, zh):
    plt.rcParams['font.family'] = ['Arial Unicode MS','DejaVu Sans']
    fig, (ax, front) = plt.subplots(1, 2, figsize=(8.8,5.0), layout='constrained')
    ax.add_patch(Polygon(profile['outline'], closed=True, facecolor='#bacece', edgecolor='#2c4f50'))
    for x,z,r in profile['holes']:
        ax.add_patch(Circle((x,z), r, facecolor='white', edgecolor='#2c4f50'))
    ax.add_patch(Rectangle((-6,-10),12,10, fill=False, edgecolor='#805c34', linestyle='--', linewidth=1.2))
    ax.set(title='夹片侧视 · 夹片固定孔' if zh else 'Blade profile and fastening holes',
           xlim=(-7.5,7.5), ylim=(-12,20), xlabel='U (mm)', ylabel='Z (mm)', aspect='equal')
    v = 2.0
    top = max(y for _,y in profile['outline'])
    for side in (-1,1):
        xl, xr = sorted((side*(v+.07),side*(v+5.07)))
        front.add_patch(Rectangle((xl,-10), xr-xl, 10, edgecolor='#805c34', facecolor='#f1ddca'))
        xl,xr = sorted((side*v,side*(v+BLADE_WIDTH)))
        front.add_patch(Rectangle((xl,-6.5),xr-xl,top+6.5,edgecolor='#2c4f50',facecolor='#bacece'))
    for y, thick, color in [(GUIDES_Z,2,'#5e7688'), (CLAMP_Z,3,'#805d48')]:
        front.add_patch(Rectangle((-12.5,y-thick/2),25,thick,edgecolor=color, facecolor=color, alpha=.72))
    front.add_patch(Rectangle((-2,top-2.1),4,2.9,edgecolor='#777',facecolor='#f0f2eb',linestyle=':'))
    front.annotate('导杆' if zh else 'Guide pins', (7,GUIDES_Z), xytext=(7,5), ha='center',
                   arrowprops={'arrowstyle':'->','color':'#555'}, fontsize=10)
    front.annotate('M3', (8,CLAMP_Z), xytext=(8,-11.7), ha='center',
                   arrowprops={'arrowstyle':'->','color':'#555'}, fontsize=10)
    front.set(title='J2 夹紧状态参考' if zh else 'J2 clamped pose reference',
              xlim=(-14,14), ylim=(-14,20), xlabel='V (mm)', ylabel='Z (mm)', aspect='equal')
    fig.suptitle('M05 平行夹头试制工具' if zh else 'M05 parallel-jaw service tool')
    for axis in (ax,front):
        axis.grid(alpha=.18)
    out = AUDIT/('m05-tool-drawing.zh-CN.png' if zh else 'm05-tool-drawing.png')
    fig.savefig(out,dpi=165)
    plt.close(fig)
    return out


def main():
    evidence = AUDIT/'m05-tool.json'
    tool = read(evidence)
    verify(tool)
    source = TOOLS/'blade-06mm-profile.dxf'
    doc = ezdxf.readfile(source)
    assert doc.units == 4
    space = doc.modelspace()
    (outline,) = list(space.query('LWPOLYLINE[layer=="PROFILE"]'))
    circles = list(space.query('CIRCLE[layer=="DRILL"]'))
    assert outline.closed and len(circles)==2
    profile = {'outline':[(x,y)for x,y in outline.get_points('xy')],
               'holes':[(c.dxf.center.x,c.dxf.center.y,c.dxf.radius) for c in circles]}
    outputs = [draw(profile, zh) for zh in (False,True)]
    sources = [evidence, source, Path(__file__)]
    (AUDIT/'m05-tool-drawing.json').write_text(json.dumps({
        'status':'M05-tool-fabrication-drawing-exported',
        'source_sha256':dict(tool['source_sha256'], **{str(p.relative_to(ROOT)):sha(p) for p in sources}),
        'outputs':{str(p.relative_to(ROOT)):sha(p) for p in outputs},
        'physical_verification':False,
    }, indent=2)+'\n')


if __name__ == '__main__':
    main()
