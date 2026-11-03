#!/usr/bin/env python3
"""Bounded geometry/reference study for the isolated short-USB candidate.

Run after check_usb_short_route.py, using the project's CAD Python environment.
This deliberately does not qualify the two replacement cable routes.
"""
import hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from cad_geometry import load,intersection_volume
from check_yeti60_assembly import box,distance,move
from study_yeti60_prototype import usb_study
from usb_short_passive_contract import apply_passive_envelopes
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/usb-short-route';AUD=BASE/'audit'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def main():
    native=read(ROOT/'.assembly-work/usb-short-audit/native-inputs.json');proof=read(AUD/'native-check.json');paths=read(AUD/'USB-paths.json')
    assert proof['status']=='native-candidate-checks-passed'
    for p,h in native['source_sha256'].items():assert sha(ROOT/p)==h,('Stale candidate',p)
    screen,_,normalizations=usb_study(native,paths)
    assembly=apply_passive_envelopes(read(ROOT/'docs/audit/yeti60-assembly.json'),native);spec=read(ROOT/'mechanical/pcb-fabrication-spec.json');nominal=assembly['nominal_stack']['pcb_bottom_z'];cases=[load(ROOT/'mechanical/generated'/('yeti60-'+s+'.step')) for s in ['bottom','top']]
    obstacles=[]
    for p in assembly['component_envelopes']:
        if p['ref'] not in ['R30','R31']:obstacles.append((p['ref'],box(p['bounds_case_mm'])))
    for h in assembly['mounting_hole_matches']:
        x,y=h['pcb_center_case_mm'];obstacles.append(('mount-'+h['pcb_ref'] if 'pcb_ref' in h else 'mount',box([x-2.1,y-2.1,-3.9,x+2.1,y+2.1,-2])))
    envelopes=[]
    for p in native['new_headers']:
        ref=p['ref'];x,y=p['position'];x0,y0,x1,y1=p['physical_body_bbox_pcb_mm'];envelopes.append((ref,[x0,-y1,nominal-3,x1,-y0,nominal],ref))
        # Actual SH drawing: 6.25 mm mated depth, -1.675 mm header rear datum.
        exit_y=-y-1.675+6.25;width=5 if ref=='J4' else 3
        for pad in p['contact_land_bboxes_pcb_mm']:
            a,b,c,d=pad['bbox'];envelopes.append((ref+'-contact-'+pad['pin'],[a,-d,nominal-.5,c,-b,nominal],ref))
        envelopes.append((ref+'-mating-plug',[x-width/2,exit_y-5,nominal-3.1,x+width/2,exit_y,nominal-.1],ref))
    results=[];gap=.15;allow=.25
    for thick in [spec['CAD_finished_envelope_mm'],*spec['ordinary_thickness_acceptance_range_mm']]:
        delta=spec['CAD_finished_envelope_mm']-thick
        for name,bb,owner in envelopes:
            actual=[v+(delta if i in [2,5] else 0) for i,v in enumerate(bb)];expanded=[v+(-allow if i<3 else allow) for i,v in enumerate(actual)];shape=box(expanded);case_gap=min(distance(shape,c) for c in cases);assert case_gap>=gap,(name,'case',thick,case_gap)
            collisions=[intersection_volume(shape,c) for c in cases];assert max(collisions)<1e-6
            others=[]
            for ref,other in obstacles:others.append((ref,distance(shape,move(other,z=delta))))
            nearest=min(others,key=lambda v:v[1]);assert nearest[1]>=gap,(name,'component/mount',nearest)
            for other,obb,oowner in envelopes:
                if oowner==owner:continue
                shifted=[v+(delta if i in [2,5] else 0) for i,v in enumerate(obb)];d=distance(shape,box(shifted));assert d>=gap,(name,other,d)
            results.append({'envelope':name,'pcb_thickness_mm':thick,'bounds_case_mm':actual,'allowance_mm':allow,'minimum_case_gap_mm':case_gap,'nearest_retained_part_or_mount':nearest[0],'minimum_retained_part_or_mount_gap_mm':nearest[1]})
    for side in ['positive','negative']:
        assert screen[side]['nearest_adjacent_GND_coverage_fraction']>.999,'New short USB path has a reference gap'
    report={'status':'local-header-fit-and-reference-passed','manufacturing_released':False,'physical_verification':False,'USB_reference_screen':screen,'ground_polygon_normalizations':normalizations,'local_connector_and_mating_housing_checks':results,'source_sha256':{'hardware/usb-short-route/audit/native-check.json':sha(AUD/'native-check.json'),'hardware/usb-short-route/audit/USB-paths.json':sha(AUD/'USB-paths.json'),'scripts/study_usb_short_route.py':sha(Path(__file__)),'docs/audit/yeti60-assembly.json':sha(ROOT/'docs/audit/yeti60-assembly.json'),'mechanical/generated/yeti60-bottom.step':sha(ROOT/'mechanical/generated/yeti60-bottom.step'),'mechanical/generated/yeti60-top.step':sha(ROOT/'mechanical/generated/yeti60-top.step')},'not_verified':['Full C5-to-J4 and J5-to-J1 cable sweeps, bend radii, serviceability and enclosed routing','Connector MPN height and supplier mating-housing tolerances','Pair impedance, current distribution, propagation delay and eye diagram','Actual USB data with simultaneous battery charging']}
    (AUD/'geometry-check.json').write_text(json.dumps(report,indent=2)+'\n')
    for zh in [False,True]:
        plt.rcParams['svg.hashsalt']='yeti60-short-usb';plt.rcParams['font.family']=['Arial Unicode MS','DejaVu Sans']
        fig,ax=plt.subplots(figsize=(11,6));colors={'positive':'#2c924e','negative':'#2362b4'}
        for p in native['new_headers']:
            x0,y0,x1,y1=p['bbox'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,edgecolor='#8b8f97'));ax.text(p['position'][0],p['position'][1],p['ref'],ha='center',fontsize=12)
        for side in ['negative','positive']:
            for e in paths[side]['ordered_path']:
                if e['kind']=='trace':ax.plot([e['start'][0],e['end'][0]],[e['start'][1],e['end'][1]],color=colors[side],lw=2)
                elif e['kind'] in ['pad-access','junction']:
                    ax.plot([e['a'][2],e['b'][2]],[e['a'][3],e['b'][3]],color=colors[side],lw=1,ls=':')
        ax.scatter([350.1,350.9],[120.6,120.6],color=['#2362b4','#2c924e'],s=35);ax.text(350.5,121.1,'U1: 34 / 35',ha='center');ax.set(xlim=(336,356),ylim=(123,109),aspect='equal',xlabel='PCB X (mm)',ylabel='PCB Y (mm)')
        ax.set_title('USB 短线修补候选：原生坐标与等长数据线路' if zh else 'USB repair candidate: native coordinates and equal-length data paths');ax.grid(alpha=.18)
        fig.text(.5,.03,'两路接触路径均为 5.286 mm；无数据过孔。未验收完整线束。' if zh else 'Both contact paths: 5.286 mm; no data vias. Complete harnesses remain unqualified.',ha='center');fig.tight_layout(rect=(0,.06,1,1));suffix='.zh-CN' if zh else ''
        for ext in ['svg','png']:fig.savefig(AUD/('USB-local-layout'+suffix+'.'+ext),dpi=150,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)
        svg=AUD/('USB-local-layout'+suffix+'.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    print('Local header/mating-plug envelopes passed; reference coverage:',{k:screen[k]['nearest_adjacent_GND_coverage_fraction'] for k in ['positive','negative']})
if __name__=='__main__':main()
