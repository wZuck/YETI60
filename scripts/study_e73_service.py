#!/usr/bin/env python3
"""Screen the existing E73 PH plug's entire axial withdrawal, not endpoints."""
import hashlib,json
from pathlib import Path
from cad_geometry import load,intersection_volume
from check_yeti60_assembly import box,distance
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def withdrawal(plug,header,separation=.5):
    assert separation>=.5
    travel=header[4]+separation-plug[1];assert travel>0
    sweep=plug[:];sweep[4]+=travel
    detached=plug[:];detached[1]+=travel;detached[4]+=travel
    return travel,sweep,detached

def main():
    sources=[Path(__file__),ROOT/'docs/audit/yeti60-assembly.json',ROOT/'docs/audit/yeti60-interconnects.json',ROOT/'scripts/cad_geometry.py',ROOT/'scripts/check_yeti60_assembly.py',ROOT/'mechanical/interconnect-spec.json']
    assembly=json.loads(sources[1].read_text());harness=json.loads(sources[2].read_text())
    header=next(x for x in assembly['component_envelopes'] if x['ref']=='J2')['bounds_case_mm']
    plug=next(x for x in harness['mated_housings'] if x['name']=='main-PH')['bounds_case_mm'][:]
    # Full PH housing depth from the supplier drawing. The inherited route box
    # used 6.35 mm; 6.85 mm is the conservative complete rigid-body screen.
    plug[1]=plug[4]-6.85
    travel,sweep,detached=withdrawal(plug,header)
    bottom=ROOT/assembly['case_files']['bottom'];sources.append(bottom)
    obstacles=[('bottom',load(bottom))]
    for mount in assembly['mounting_hole_matches']:
        x,y=mount['pcb_center_case_mm']
        obstacles.append((mount['pcb_ref'],box([x-2.1,y-2.1,-3.9,x+2.1,y+2.1,-2])))
    records=[]
    for name,solid in obstacles:
        volume=intersection_volume(box(sweep),solid)
        gap=distance(box(sweep),solid)
        if gap<3:
            records.append(dict(obstacle=name,sweep_overlap_mm3=volume,gap_mm=gap,
                                seated_overlap_mm3=intersection_volume(box(plug),solid),
                                detached_overlap_mm3=intersection_volume(box(detached),solid)))
    assert records,'No nearby obstacles screened'
    passing=all(x['sweep_overlap_mm3']<1e-6 and x['gap_mm']>=.15 for x in records)
    report=dict(status='passed' if passing else 'design-obstruction-found',physical_verification=False,
                complete_service_path_qualified=False,manufacturing_released=False,
                plug_depth_mm=6.85,withdrawal_mm=travel,plug_case_bounds_mm=plug,sweep_case_bounds_mm=sweep,checks=records,
                scope='Nominal axial rigid PH body; case top removed; full sweep includes intermediate positions. No allowance inflation, wires, tools or extraction-force qualification.',
                primary_source='https://www.jst-mfg.com/product/pdf/eng/ePH.pdf',
                source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources})
    (ROOT/'docs/audit/e73-service-motion.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
