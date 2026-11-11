#!/usr/bin/env python3
"""Continuous conservative axial plug-body checks; flexible/tool access stays open."""
import hashlib
import json
import subprocess
from pathlib import Path
from cad_geometry import bounds, intersection_volume, load
from check_yeti60_assembly import box, distance, move
from check_usb_short_closed_assembly import hashes
from check_yeti60_interconnects import near
from usb_short_battery_service import BASE, BASELINE, OFFSET, HOUSING_DEPTH, ROOT, verify_layout
from usb_short_harness import envelope_wire


def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def withdrawal(plug, header, separation=.5):
    assert separation >= .5, 'Insufficient post-withdrawal separation'
    travel = header[4]+separation-plug[1]
    assert travel > 0, 'Invalid starting mating geometry'
    swept = plug[:]
    swept[4] += travel
    parked = plug[:]
    parked[1] += travel
    parked[4] += travel
    assert abs(parked[1]-header[4]-separation)<1e-8
    return travel, swept, parked


def enlarged(bb, allowance, pcb_bottom):
    result = [v+(-allowance if i<3 else allowance) for i,v in enumerate(bb)]
    # The mating housing intentionally seats against the PCB underside datum.
    result[5] = min(result[5],pcb_bottom)
    return result


def screen(shape, obstacles, required_gap):
    rows = []
    for name, other in obstacles:
        if not near(bounds(shape),bounds(other),3): continue
        volume=intersection_volume(shape,other)
        gap=distance(shape,other)
        assert volume<1e-6 and gap>=required_gap-1e-6, ('Plug withdrawal obstruction',name,volume,gap)
        rows.append(dict(obstacle=name,intersection_mm3=volume,gap_mm=gap))
    assert rows, 'Empty plug-motion obstacle coverage'
    return rows


def main():
    verify_layout()
    assembly=read(BASE/'audit/assembly.json')
    closed=read(BASE/'audit/closed-assembly.json')
    guides=read(BASE/'audit/guides.json')
    for report in [assembly,closed,guides]: hashes(report['source_sha256'])
    hashes(guides['outputs'])
    spec=read(BASE/'interconnect-spec.json')
    profile=read(ROOT/'mechanical/pcb-fabrication-spec.json')
    nominal=profile['CAD_finished_envelope_mm']
    pcb_bottom=assembly['nominal_stack']['pcb_bottom_z']
    byref={p['ref']:p for p in assembly['component_envelopes']}
    assert byref['J2']['position_pcb_mm']==[155.5,129]
    pack=box(assembly['battery_candidates'][0]['bounds_case_mm'])
    case=load(BASE/'mechanical/yeti60-bottom-short-usb.step')
    pcb=load(ROOT/'.assembly-work/pcb-placed.step')
    fixed=[(p['name'],load(ROOT/p['path'])) for p in guides['render_parts']]
    wire_allowance=spec['wire']['case_and_route_position_allowance']
    foreign_wires={family:[envelope_wire(path,spec['wire']['insulation_od_max']+2*wire_allowance)
                          for path in paths.values()] for family,paths in closed['nominal']['routes'].items()}
    rows=[]
    for thickness in [nominal,*profile['ordinary_thickness_acceptance_range_mm']]:
        delta=nominal-thickness
        for ref,family in [('J4','usb'),('J2','battery')]:
            plug=next(p for p in assembly['mated_housings'] if p['owner']==ref)['bounds_case_mm']
            if ref=='J2': assert abs(plug[4]-plug[1]-HOUSING_DEPTH)<1e-8
            header=byref[ref]['bounds_case_mm']
            travel,swept,parked=withdrawal(plug,header)
            swept=[v+(delta if i in [2,5] else 0) for i,v in enumerate(swept)]
            solid=box(enlarged(swept,wire_allowance,pcb_bottom+delta))
            assert intersection_volume(solid,move(pcb,z=delta))<1e-6, 'Housing cuts into PCB during withdrawal'
            obstacles=[('bottom',case),('pack',pack)]
            obstacles += [(p['ref'],move(box(p['bounds_case_mm']),z=delta)) for p in assembly['component_envelopes'] if p['ref']!=ref]
            for match in assembly['mounting_hole_matches']:
                x,y=match['pcb_center_case_mm']
                obstacles.append(('mount-'+match['pcb_ref'],box([x-2.1,y-2.1,-3.9+delta,x+2.1,y+2.1,-2+delta])))
            for name,obj in fixed:
                obstacles.append((name,move(obj,z=delta if name.startswith('PWR') else 0)))
            for other_family,shapes in foreign_wires.items():
                if other_family!=family:
                    # Covers the fixed nominal route with its inspected envelope;
                    # moving/loose wires are explicitly outside this body screen.
                    obstacles += [(other_family+'-wire-'+str(i),obj) for i,obj in enumerate(shapes)]
            for p in assembly['mated_housings']:
                if p['owner']!=ref:
                    obstacles.append((p['name'],move(box(p['bounds_case_mm']),z=0 if p['owner']=='C5' else delta)))
            checks=screen(solid,obstacles,.15)
            rows.append(dict(ref=ref,pcb_thickness_mm=thickness,withdrawal_axis_case=[0,1,0],
                             travel_mm=travel,nominal_sweep_bounds_case_mm=swept,
                             nominal_detached_bounds_case_mm=parked,
                             moving_housing_allowance_mm=wire_allowance,
                             minimum_foreign_gap_mm=min(v['gap_mm'] for v in checks),obstacles=checks))
    # Independent pre-repair native evidence, not an invented obstructing box.
    previous= json.loads(subprocess.check_output(['git','show',BASELINE+':variants/raytac/hardware/usb-short-route/audit/assembly.json'],cwd=ROOT))
    old_plug=next(p for p in previous['mated_housings'] if p['owner']=='J2')['bounds_case_mm'][:]
    old_plug[1]=old_plug[4]-6.85
    old_header=next(p for p in previous['component_envelopes'] if p['ref']=='J2')['bounds_case_mm']
    old_sweep=box(withdrawal(old_plug,old_header)[1])
    mount=next(p for p in previous['mounting_hole_matches'] if p['pcb_ref']=='H8')
    x,y=mount['pcb_center_case_mm']
    regressions=dict(H8_overlap_mm3=intersection_volume(old_sweep,box([x-2.1,y-2.1,-3.9,x+2.1,y+2.1,-2])),
                     bottom_overlap_mm3=intersection_volume(old_sweep,case))
    assert min(regressions.values())>0, 'Pre-repair withdrawal no longer reproduces both obstructions'
    inputs=[Path(__file__),ROOT/'scripts/usb_short_battery_service.py',ROOT/'scripts/cad_geometry.py',
            ROOT/'scripts/check_yeti60_assembly.py',ROOT/'scripts/check_usb_short_closed_assembly.py',
            ROOT/'scripts/usb_short_harness.py',ROOT/'scripts/interconnect_geometry.py',
            BASE/'interconnect-spec.json',ROOT/'mechanical/pcb-fabrication-spec.json',
            BASE/'EC60-nRF52840.kicad_pcb',BASE/'audit/assembly.json',BASE/'audit/closed-assembly.json',
            BASE/'audit/guides.json',BASE/'mechanical/yeti60-bottom-short-usb.step',ROOT/'.assembly-work/pcb-placed.step']
    report=dict(status='continuous-rigid-plug-withdrawal-screen-passed',physical_verification=False,
                complete_service_path_qualified=False,manufacturing_released=False,checks=rows,
                J2_shift_PCB_mm=OFFSET,SH_housing_depth_screen_mm=HOUSING_DEPTH,
                pre_repair_baseline_commit=BASELINE,pre_repair_regression=regressions,
                scope='Case top removed; straight axial rigid housings at seated PCB datum; full continuous box sweeps, reversible for insertion',
                not_qualified=['Actual housing tolerance/latches and insertion/withdrawal forces',
                               'Tool/finger approach, own-wire deformation, strain relief and loose-plug parking',
                               'Connected stack lifting, full flexible service and physical assembly'],
                primary_sources=['https://www.jst-mfg.com/product/pdf/eng/ePH.pdf',
                                 'https://www.jst-mfg.com/product/pdf/eng/handling_e.pdf'],
                source_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
    (BASE/'audit/plug-motion.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Six continuous rigid plug-body screens passed; complete tool/flexible service remains open')


if __name__=='__main__': main()
