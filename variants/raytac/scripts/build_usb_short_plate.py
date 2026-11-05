#!/usr/bin/env python3
"""Inset the candidate plate exterior; preserve every interior entity verbatim."""
import hashlib
import json
import math
from pathlib import Path

import ezdxf
from ezdxf.path import make_path
from shapely.geometry import Point, Polygon
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.gp import gp_Vec

from cad_geometry import bounds
from check_yeti60_assembly import wire
from check_yeti60_interconnects import write_step

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'hardware/usb-short-route'


def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def profiles(doc, chord=.002):
    rows = []
    for e in doc.modelspace().query('LWPOLYLINE'):
        p = Polygon([(-v.x, -v.y) for v in make_path(e).flattening(chord)])
        assert p.is_valid
        rows.append((p.area, e, p))
    return sorted(rows, key=lambda row:-row[0])


def internal_contract(doc):
    outer = profiles(doc)[0][1]
    # DXF entity data excluding the changing external profile. Handles and
    # complete bulges/vertices are retained for all key/stabilizer/fastener cuts.
    return [str(e.dxfattribs()) + (str(list(e.get_points())) if e.dxftype() == 'LWPOLYLINE' else '')
            for e in doc.modelspace() if e is not outer]


def build_shape(doc, z, thickness):
    rows = profiles(doc)
    builder = BRepBuilderAPI_MakeFace(wire([(x,y,z) for x,y in rows[0][2].exterior.coords],True))
    for _, _, p in rows[1:]:
        builder.Add(wire([(x,y,z) for x,y in p.exterior.coords],False))
    for c in doc.modelspace().query('CIRCLE'):
        r = c.dxf.radius
        n = max(64, math.ceil(math.pi/math.acos(1-.002/r)))
        points = [(-c.dxf.center.x+r*math.cos(2*math.pi*i/n),
                   -c.dxf.center.y+r*math.sin(2*math.pi*i/n),z) for i in range(n)]
        builder.Add(wire(points,False))
    assert builder.IsDone()
    shape = BRepPrimAPI_MakePrism(builder.Face(),gp_Vec(0,0,thickness)).Shape()
    assert BRepCheck_Analyzer(shape).IsValid()
    return shape


def main():
    fit = read(BASE/'mechanical-fit-spec.json');p = fit['plate']
    source = ROOT/p['source'];doc = ezdxf.readfile(source)
    before = internal_contract(doc);rows = profiles(doc,p['profile_chord_mm'])
    old = rows[0][2];new = old.buffer(-p['outer_perimeter_inset_mm'],join_style='mitre')
    assert new.geom_type == 'Polygon' and new.is_valid and new.area < old.area
    gaps = [new.exterior.distance(poly) for _,_,poly in rows[1:]]
    assert all(new.contains(poly) for _,_,poly in rows[1:]),'Inset reaches a key/stabilizer opening'
    for c in doc.modelspace().query('CIRCLE'):
        disk = Point(-c.dxf.center.x,-c.dxf.center.y).buffer(c.dxf.radius,quad_segs=128)
        assert new.contains(disk),'Inset reaches a fastener hole'
        gaps.append(new.exterior.distance(disk))
    assert min(gaps) >= p['minimum_edge_web_mm'],'Inset leaves too little edge metal'
    rows[0][1].set_points([(-x,-y,0,0,0) for x,y in list(new.exterior.coords)[:-1]],format='xyseb')
    rows[0][1].closed = True
    doc.header['$INSUNITS'] = 4
    target = ROOT/p['output'];target.parent.mkdir(exist_ok=True)
    ezdxf.options.write_fixed_meta_data_for_testing = True
    doc.saveas(target)
    saved = ezdxf.readfile(target)
    assert internal_contract(saved) == before,'An interior cut or hole changed'
    assert old.buffer(.00001).contains(profiles(saved)[0][2]),'Plate grew outward'
    assembly = read(ROOT/'docs/audit/yeti60-assembly.json')
    stack = assembly['nominal_stack']
    shape = build_shape(saved,stack['plate_bottom_z'],stack['plate_thickness_mm'])
    step = ROOT/p['step'];write_step(shape,step)
    output = dict(status='candidate-inset-plate-built',physical_verification=False,
        source_plate=str(source.relative_to(ROOT)),candidate_plate=p['output'],candidate_STEP=p['step'],
        exterior_inset_mm=p['outer_perimeter_inset_mm'],original_outline_area_mm2=old.area,
        candidate_outline_area_mm2=new.area,minimum_edge_web_mm=min(gaps),
        unchanged_interior_entities=len(before),key_and_stabilizer_openings_unchanged=True,
        mounting_holes_unchanged=True,plate_bounds_case_mm=bounds(shape),
        source_sha256={str(q.relative_to(ROOT)):sha(q) for q in [Path(__file__),source,BASE/'mechanical-fit-spec.json',ROOT/'docs/audit/yeti60-assembly.json',ROOT/'scripts/check_yeti60_assembly.py',ROOT/'scripts/check_yeti60_interconnects.py']},
        outputs={str(q.relative_to(ROOT)):sha(q) for q in [target,step]})
    (BASE/'audit/plate-build.json').write_text(json.dumps(output,indent=2)+'\n')
    print('Inset plate built; all interior cuts unchanged; minimum edge web',min(gaps),flush=True)


if __name__ == '__main__':main()
