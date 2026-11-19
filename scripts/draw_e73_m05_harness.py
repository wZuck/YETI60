#!/usr/bin/env python3
"""Export the checked M05 seated conductor routes and winding stations."""

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle

from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound

from build_e73_m05_harness import OUT, matched_spec
from check_e73_corner_harness import datums
from check_e73_corner_service import AUDIT, ROOT, WORK, read, sha, verify
from check_yeti60_interconnects import write_step
from e73_corner_harness_paths import paired_data, point_at, sweep_wire
from e73_service_leads import BATTERY_GUIDE_STATIONS, flex_routes


def draw(routes, outlines, exits, phase_windows, zh):
    plt.rcParams['font.family'] = ['Arial Unicode MS', 'DejaVu Sans']
    fig, ax = plt.subplots(figsize=(12, 6.3), layout='constrained')
    for outline in outlines:
        ring = outline['outer']
        ax.plot([x for x,y in ring]+[ring[0][0]], [-y for x,y in ring]+[-ring[0][1]], color='#a6adaa', linewidth=1)
    labels = ('USB 线束', '板载电源桥', '保护包引线') if zh else ('USB harness', 'PCB power bridge', 'Pack leads')
    for label, color, family in zip(labels, ('#245788', '#ad583a', '#39745a'), ('usb', 'power', 'battery')):
        for pin, lead in routes[family].items():
            points = [tuple(p) for segment in lead for p in
                      (segment['points'] if segment['kind']=='twist' else [point_at(segment, i/16) for i in range(17)])]
            ax.plot([p[0] for p in points],[p[1] for p in points], color=color, linewidth=1.0,
                    label=label if pin=='1' else None)
    for ref in ('J1','J2','J4','J5','C5','pack'):
        x,y,_ = exits[ref]
        ax.scatter(x, y, color='#111827', s=9)
        ax.annotate(ref if ref!='pack' or not zh else '保护包', (x,y), xytext=(4,-10),
                    textcoords='offset points', fontsize=9)
    for index, x in enumerate(BATTERY_GUIDE_STATIONS, 1):
        ax.add_patch(Rectangle((x-1,-109.5),2,5.8, linewidth=1.0, linestyle='--',
                               edgecolor='#163b26', facecolor='none'))
        ax.annotate(str(index), (x,-102.2), ha='center', va='bottom', fontsize=9)
    for index, phase in enumerate(phase_windows, 1):
        start, end = phase['center_start_case_mm'], phase['center_end_case_mm']
        xy = ((start[0]+end[0])/2, (start[1]+end[1])/2)
        ax.annotate('T'+str(index), xy, xytext=(5,6), textcoords='offset points', fontsize=9)
    ax.set(xlim=(67,363),ylim=(-203,-93),aspect='equal',xlabel='X (mm)',ylabel='Y (mm)')
    ax.grid(alpha=.19)
    ax.legend(loc='lower right')
    ax.set_title('M05 坐合状态线束与理线位置 · 从上往下看' if zh
                 else 'M05 seated harness and guide stations · top view')
    path = AUDIT/('m05-harness-plan.zh-CN.png' if zh else 'm05-harness-plan.png')
    fig.savefig(path, dpi=155)
    plt.close(fig)
    return path


def main():
    evidence_path = AUDIT/'m05-harness.json'
    evidence = read(evidence_path)
    verify(evidence)
    spec = matched_spec(read(ROOT/'hardware/e73-corner-harness-spec.json'))
    assembly = read(ROOT/'mechanical/assembly-spec.json')
    _, exits = datums(read(AUDIT/'harness-native.json'), assembly, spec)
    routes, center, _ = flex_routes(spec, exits, exits, 0)
    data, twists = paired_data(center, spec)
    routes['usb'].update(data)
    winding = [
        {'role': item['role'],
         'center_start_case_mm': item['centre_piece']['start'],
         'center_end_case_mm': item['centre_piece']['end'],
         'center_span_mm': item['length_mm'],
         'turns': evidence['nominal_winding_turns']['twist_'+item['role']+'_turns']}
        for item in twists
    ]
    export = read(WORK/'copper.json')
    verify(export)
    assert sha(WORK/'copper.json') == read(AUDIT/'service-motion.json')['derived_copper_export_sha256']
    outputs = [draw(routes, export['outline'], exits, winding, zh) for zh in (False,True)]
    assembly_shape = TopoDS_Compound()
    maker = BRep_Builder()
    maker.MakeCompound(assembly_shape)
    for family in routes.values():
        for route in family.values():
            maker.Add(assembly_shape,sweep_wire(route,spec['wire']['insulation_od_max']))
    target = OUT/'harness'/'seated-wires-REFERENCE.step'
    write_step(assembly_shape, target)
    outputs.append(target)
    sources = [evidence_path, Path(__file__)]
    (AUDIT/'m05-harness-plan.json').write_text(json.dumps({
        'status': 'checked-M05-seated-harness-plan',
        'source_sha256': dict(evidence['source_sha256'], **{str(p.relative_to(ROOT)):sha(p) for p in sources}),
        'outputs': {str(p.relative_to(ROOT)):sha(p) for p in outputs},
        'winding_stations': winding,
        'max_insulated_OD_mm': spec['wire']['insulation_od_max'],
        'reference_only_STEP': target.name,
        'physical_verification': False,
    }, indent=2)+'\n')


if __name__ == '__main__':
    main()
