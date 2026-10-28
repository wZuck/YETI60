#!/usr/bin/env python3
"""Read-only verification of the current plate against original FELK60 DXF."""
import hashlib
import json
from pathlib import Path
import ezdxf
ROOT = Path(__file__).resolve().parents[1]

def signature(doc):
    result = []
    for entity in doc.modelspace():
        if entity.dxftype() == 'CIRCLE':
            values = [*entity.dxf.center, entity.dxf.radius]
        elif entity.dxftype() == 'LWPOLYLINE':
            values = [int(entity.closed), *[v for p in entity.get_points('xyseb') for v in p]]
        else:
            raise ValueError('Unexpected plate entity: '+entity.dxftype())
        result.append([entity.dxftype(), entity.dxf.layer, [round(v,9) for v in values]])
    return result

def main():
    original = ROOT/'felk60/felk60_plate_hhkb.dxf'
    current = ROOT/'mechanical/felk60_plate_hhkb.audited.dxf'
    source = ezdxf.readfile(original); target = ezdxf.readfile(current)
    before = current.read_bytes(); audit = target.audit()
    assert source.units == target.units == 4
    assert signature(source) == signature(target), 'Plate geometry differs from FELK60'
    assert not audit.errors and not audit.fixes, 'Checked plate requires DXF repair'
    polylines = list(target.modelspace().query('LWPOLYLINE'))
    assert len(polylines)==63 and all(p.closed for p in polylines)
    assert len(target.modelspace().query('CIRCLE'))==29
    assert before == current.read_bytes(), 'Read-only plate check mutated source'
    report={'status':'passed','source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [original,current]},'closed_profiles':63,'screw_circles':29,'geometry_comparison_precision_mm':1e-9,'read_only':True,'scope':'Source geometry equivalence only; current PCB hole correspondence and provisional stack are checked separately'}
    (ROOT/'docs/audit/plate.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Plate source geometry matches; checked DXF was not rewritten')
if __name__=='__main__':main()
