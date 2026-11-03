#!/usr/bin/env python3
"""Diagnose sampled rigid vertical lift; never certify a swept service path."""
import hashlib
import json
from pathlib import Path
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from cad_geometry import load, bounds, intersection_volume
from check_yeti60_assembly import move

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/usb-short-route'


def main():
    files={'bottom':BASE/'mechanical/yeti60-bottom-short-usb.step',
           'PCB':ROOT/'.assembly-work/pcb-placed.step',
           'plate':ROOT/'.assembly-work/plate.step'}
    solids={k:load(p) for k,p in files.items()}
    samples=[]
    for dz in [0,.5,1,2,3,5,8]:
        row={'vertical_displacement_mm':dz}
        for name in ['PCB','plate']:
            moved=move(solids[name],z=dz)
            volume=intersection_volume(solids['bottom'],moved)
            item={'intersection_volume_mm3':volume}
            if volume>1e-6:
                op=BRepAlgoAPI_Common(solids['bottom'],moved);op.Build()
                assert op.IsDone()
                item['intersection_bounds_case_mm']=bounds(op.Shape())
            row[name]=item
        samples.append(row)
        print(json.dumps(row),flush=True)
    held=any(row[name]['intersection_volume_mm3']>1e-6 for row in samples for name in ['PCB','plate'])
    sources=[Path(__file__),ROOT/'scripts/cad_geometry.py',ROOT/'scripts/check_yeti60_assembly.py',*files.values()]
    report={'status':'vertical-lift-interference-found' if held else 'no-interference-at-sampled-poses',
        'manufacturing_released':False,'physical_verification':False,'service_path_qualified':False,
        'scope':'Nominal PCB and plate rigid translations against bottom only; no continuous sweep, cables, plugs, tools or tolerance qualification',
        'part_bounds_case_mm':{k:bounds(v) for k,v in solids.items()},'samples':samples,
        'next_work':['Resolve right wing versus internal step using verified insertion/removal geometry',
                     'Include connected leads, guide release, mating plugs and tool access in service qualification',
                     'Check tolerances, preserved exterior, insert/support loads and first-article behavior'],
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (BASE/'audit/service-probe.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
