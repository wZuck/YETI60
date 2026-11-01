#!/usr/bin/env python3
"""Generate/check the controlled Deskeys plate without changing FELK60 datums.

Dimensions are drawing-based engineering selections, not physical qualification.
Default is read-only; --generate writes the derived DXF only.
"""
import argparse, hashlib, json, math
from collections import Counter
from pathlib import Path
import ezdxf
from ezdxf.path import make_path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'mechanical/felk60_plate_hhkb.audited.dxf'
TARGET = ROOT/'mechanical/felk60_plate_hhkb.deskeys.dxf'
SPEC = ROOT/'mechanical/yeti60-deskeys.json'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def dimensions(e):
    pts=list(e.get_points('xy')); xs,ys=zip(*pts)
    return (min(xs)+max(xs))/2,(min(ys)+max(ys))/2,max(xs)-min(xs),max(ys)-min(ys)

def kind(e):
    _,_,w,h=dimensions(e)
    if abs(w-14.6)<1e-6 and abs(h-14)<1e-6:return 'normal'
    if abs(w-32)<1e-6 and abs(h-14)<1e-6:return 'wide'
    if abs(w-13.462)<1e-6 and abs(h-13.741)<1e-6:return 'spacebar-side'
    assert w>280 and h>100, 'Unexpected FELK60 cutout'
    return 'outline'

def expected(e, spec):
    k=kind(e)
    if k=='outline':return list(e.get_points('xyseb'))
    x,y,_,_=dimensions(e);w,h=spec['cutouts_mm'][k]['size'];a=x-w/2;b=y-h/2;A=x+w/2;B=y+h/2
    if k=='normal':
        r=.5;v=math.tan(math.pi/8)
        return [(a+r,b,0,0,0),(A-r,b,0,0,v),(A,b+r,0,0,0),(A,B-r,0,0,v),
                (A-r,B,0,0,0),(a+r,B,0,0,v),(a,B-r,0,0,0),(a,b+r,0,0,v)]
    if k=='wide':
        # FELK60's original asymmetric orientation is retained. The bevel is
        # at high source Y (towards the front after the assembly transform).
        return [(a,b,0,0,0),(a,B-math.sqrt(3),0,0,0),(a+3,B,0,0,0),
                (A-3,B,0,0,0),(A,B-math.sqrt(3),0,0,0),(A,b,0,0,0)]
    c=.5
    return [(a+c,b,0,0,0),(A-c,b,0,0,0),(A,b+c,0,0,0),(A,B-c,0,0,0),
            (A-c,B,0,0,0),(a+c,B,0,0,0),(a,B-c,0,0,0),(a,b+c,0,0,0)]

def generate(source, spec):
    doc=ezdxf.readfile(source)
    for e in doc.modelspace().query('LWPOLYLINE'):
        if kind(e)!='outline':e.set_points(expected(e,spec),format='xyseb')
    return doc

def point_segment(p,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

def verify(source, target, spec):
    assert source.units==target.units==4
    se=list(source.modelspace());te=list(target.modelspace());assert len(se)==len(te)==92
    counts=Counter();centers=[];sides=[];cuts=[];circles=[]
    for a,b in zip(se,te):
        assert a.dxftype()==b.dxftype() and a.dxf.layer==b.dxf.layer
        if a.dxftype()=='CIRCLE':
            assert list(a.dxf.center)==list(b.dxf.center) and a.dxf.radius==b.dxf.radius, 'Mount datum moved'
            circles.append(b);continue
        assert b.closed
        want=expected(a,spec);actual=list(b.get_points('xyseb'))
        assert len(want)==len(actual) and all(abs(x-y)<1e-8 for p,q in zip(want,actual) for x,y in zip(p,q)), 'Cutout or outline contract changed'
        k=kind(a);counts[k]+=1
        if k=='outline':continue
        x,y,_,_=dimensions(b)
        assert math.dist((x,y),dimensions(a)[:2])<1e-8, 'Key datum moved'
        (sides if k=='spacebar-side' else centers).append((x,y))
        pts=[(p.x,p.y) for p in make_path(b).flattening(.001)]
        cuts.append((k,pts))
    assert counts=={'normal':58,'wide':2,'spacebar-side':2,'outline':1}
    assert len(circles)==29 and len(centers)==60
    sides.sort();assert abs(math.dist(*sides)-95.25)<1e-7
    middle=tuple((a+b)/2 for a,b in zip(*sides))
    assert min(math.dist(middle,p) for p in centers)<1e-7, 'Spacebar is not centered'
    webs=[]
    for c in circles:
        p=(c.dxf.center.x,c.dxf.center.y)
        for k,pts in cuts:
            distance=min(point_segment(p,a,b) for a,b in zip(pts,pts[1:]+pts[:1]))
            webs.append(distance-c.dxf.radius)
    assert min(webs)>.25, 'Cutout too close to mounting pilot'
    audit=target.audit();assert not audit.errors and not audit.fixes
    return {'cutouts':dict(counts),'mount_centers_preserved':29,'key_centers_preserved':60,
            'spacebar_side_spacing_mm':95.25,'spacebar_centered':True,
            'minimum_cutout_to_original_mount_pilot_web_mm':min(webs),
            'physical_fit_verified':False,'PCB_mount_holes_added':0,'case_external_dimensions_changed':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');args=p.parse_args()
    spec=json.loads(SPEC.read_text())
    if args.generate:generate(SOURCE,spec).saveas(TARGET)
    before=sha(TARGET);result=verify(ezdxf.readfile(SOURCE),ezdxf.readfile(TARGET),spec);assert sha(TARGET)==before
    result.update(status='drawing-based-plate-contract-passed',source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [SOURCE,TARGET,SPEC,Path(__file__)]})
    (ROOT/'docs/audit/deskeys-plate.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
