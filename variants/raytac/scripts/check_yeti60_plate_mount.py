#!/usr/bin/env python3
"""Controlled NiZ/Cherry plate; preserve sensing datums, omit conflicting H26.

Profiles are constructed from functional frame dimensions with rectangle unions.
Published CAD generators are dimensional cross-checks, not code dependencies.
Default is read-only. --generate is an explicit design-output operation.
"""
import argparse,hashlib,json,math
from pathlib import Path
import ezdxf
from ezdxf.path import make_path
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'mechanical/felk60_plate_hhkb.audited.dxf'
TARGET=ROOT/'mechanical/felk60_plate_hhkb.plate-mount.dxf'
SPEC=ROOT/'mechanical/yeti60-key-mechanism.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dimensions(e):
    pts=list(e.get_points('xy'));xs,ys=zip(*pts)
    return (min(xs)+max(xs))/2,(min(ys)+max(ys))/2,max(xs)-min(xs),max(ys)-min(ys)
def kind(e):
    _,_,w,h=dimensions(e)
    if abs(w-14.6)<1e-6 and abs(h-14)<1e-6:return 'normal'
    if abs(w-32)<1e-6 and abs(h-14)<1e-6:return 'wide'
    if abs(w-13.462)<1e-6 and abs(h-13.741)<1e-6:return 'old-side'
    assert w>280 and h>100,'Unexpected baseline geometry'
    return 'outline'
def keys(source):
    result=[]
    for e in source.modelspace().query('LWPOLYLINE'):
        if kind(e) not in ['normal','wide']:continue
        x,y,w,h=dimensions(e);result.append({'x':-x,'y':-y,'cutout_width':14.0,'baseline_width':w})
    return sorted(result,key=lambda k:(-k['y'],k['x']))
def rectangle(x0,y0,x1,y1):return box(x0,y0,x1,y1)
def cutout(key,span=None):
    x,y=key['x'],key['y'];r=.2
    central=box(x-7+r,y-7+r,x+7-r,y+7-r).buffer(r,quad_segs=8)
    if span is None:return central
    half=span/2;parts=[central,box(x-half+3.35,y-2.3,x+half-3.35,y+2.3)]
    # Each frame housing has a 6.70 mm main opening, locking nib and outer
    # side latch. The key stem reference is y=0, not the opening bbox center.
    for sign in [-1,1]:
        cx=x+sign*half
        parts += [box(cx-3.35,y-5.53,cx+3.35,y+6.77),box(cx-1.65,y+6.77,cx+1.65,y+7.97)]
        a,b=sorted([cx+sign*3.35,cx+sign*4.2]);parts.append(box(a,y-2.3,b,y+.5))
    p=unary_union(parts);assert p.geom_type=='Polygon' and p.is_valid and not p.interiors
    return p

def expected(source,spec):
    active=keys(source);assert len(active)==60
    stabilized={s['active_index']:s for s in spec['stabilized_keys']}
    assert set(stabilized)=={41,42,57}
    assert [i for i,k in enumerate(active) if k['baseline_width']>30]==[41,42]
    return active,[cutout(k,stabilized[i]['stem_spacing_mm'] if i in stabilized else None) for i,k in enumerate(active)]

def retained_circles(source,spec):
    omitted=spec['unused_mount_center_case_mm'];keep=[];skipped=[]
    for c in source.modelspace().query('CIRCLE'):
        xy=(-c.dxf.center.x,-c.dxf.center.y)
        (skipped if math.dist(xy,omitted)<1e-6 else keep).append(c)
    assert len(keep)==28 and len(skipped)==1
    return keep,skipped

def generate(source,spec):
    active,profiles=expected(source,spec);doc=ezdxf.new('R2018');doc.units=4;m=doc.modelspace()
    outline=next(e for e in source.modelspace().query('LWPOLYLINE') if kind(e)=='outline')
    m.add_lwpolyline(outline.get_points('xyseb'),format='xyseb',close=True)
    for p in profiles:m.add_lwpolyline([(-x,-y) for x,y in list(p.exterior.coords)[:-1]],close=True)
    keep,_=retained_circles(source,spec)
    for c in keep:m.add_circle(tuple(c.dxf.center),c.dxf.radius)
    return doc

def verify(source,target,spec):
    assert source.units==target.units==4
    assert spec['plate_thickness_mm']==1.6 and spec['installed_mount_quantity']==28
    active,want=expected(source,spec);polys=list(target.modelspace().query('LWPOLYLINE'))
    assert len(polys)==61 and all(p.closed for p in polys)
    baseline=next(e for e in source.modelspace().query('LWPOLYLINE') if kind(e)=='outline')
    assert list(polys[0].get_points('xyseb'))==list(baseline.get_points('xyseb')),'Outer profile changed'
    actual=[]
    for i,(e,p) in enumerate(zip(polys[1:],want)):
        q=Polygon([(-v.x,-v.y) for v in make_path(e).flattening(.001)])
        assert q.is_valid and q.symmetric_difference(p).area<1e-8, f'Cutout {i} changed'
        assert q.contains(Point(active[i]['x'],active[i]['y']).buffer(3)),f'Sensing center {i} obstructed'
        actual.append(q)
    keep,skipped=retained_circles(source,spec);got=list(target.modelspace().query('CIRCLE'))
    assert len(got)==28
    for a,b in zip(keep,got):assert list(a.dxf.center)==list(b.dxf.center) and a.dxf.radius==b.dxf.radius,'Mount datum moved'
    webs=[p.distance(Point(-c.dxf.center.x,-c.dxf.center.y))-c.dxf.radius for p in actual for c in got]
    assert min(webs)>.5,'Too little material at a retained mount'
    assert actual[57].contains(Point(*spec['unused_mount_center_case_mm'])),'H26 conflict reason no longer applies'
    for i,p in enumerate(actual):
        for q in actual[i+1:]:assert p.intersection(q).area<1e-9,'Neighboring key cutouts merge'
    audit=target.audit();assert not audit.errors and not audit.fixes
    return {'status':'drawing-based-plate-mount-contract-passed','active_key_centers_preserved':60,'key_centers_preserved':60,'mount_centers_preserved':28,'PCB_native_mount_holes':29,'unused_pcb_mount_refs':['H26'],'installed_mount_sets':28,'normal_housings':60,'plate_stabilizer_pairs':3,'stabilizer_side_units':6,'short_wire_span_mm':23.8,'spacebar_side_spacing_mm':95.25,'minimum_cutout_to_retained_pilot_web_mm':min(webs),'PCB_mount_holes_added':0,'case_external_dimensions_changed':False,'physical_fit_verified':False,'limitations':['Supplier plastic profiles/heights and 6U wire bends not certified by this 2D contract','Full key stroke, NiZ clip retention, dome preload and cap fit require first article']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');a=p.parse_args();s=json.loads(SPEC.read_text());source=ezdxf.readfile(SOURCE)
    if a.generate:generate(source,s).saveas(TARGET)
    before=sha(TARGET);r=verify(source,ezdxf.readfile(TARGET),s);assert sha(TARGET)==before
    r['source_sha256']={str(p.relative_to(ROOT)):sha(p) for p in [SOURCE,TARGET,SPEC,Path(__file__)]}
    (ROOT/'docs/audit/plate-mount.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
