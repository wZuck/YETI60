"""Verify manufacturer-driven RGT lands and ordinary masked thermal vias."""
import math
from pathlib import Path
import json
from shapely.geometry import Point, box
from shapely.ops import unary_union
from kicad_sexpr import child, children, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'


def window(pad):
    x,y=map(float,child(pad,'at')[1:3]);w,h=map(float,child(pad,'size')[1:])
    radius=min(w,h)*float(child(pad,'roundrect_rratio')[1])
    return dict(center=[x,y],size=[w,h],radius=radius,
                rectangle=box(x-w/2,y-h/2,x+w/2,y+h/2),
                exact_area_mm2=w*h-(4-math.pi)*radius*radius)


def verify_footprint(f, ref):
    pads=children(f,'pad');ep=next(p for p in pads if p[1]==('17' if ref=='U5' else '11'))
    size=list(map(float,child(ep,'size')[1:]));assert size==([1.68,1.68] if ref=='U5' else [1.2,2]),'Wrong thermal copper size'
    assert not any(str(layer).endswith('.Mask') for layer in child(ep,'layers')[1:]),'Thermal pad must use isolated custom mask windows'
    side=child(f,'layer')[1].split('.')[0]
    mask=[r for r in children(f,'fp_rect') if child(r,'layer')[1]==side+'.Mask']
    assert len(mask)==4 and all(child(r,'fill')[1]=='solid' and float(child(child(r,'stroke'),'width')[1])==0 for r in mask),'Missing/changed mask windows'
    openings=unary_union([box(*list(map(float,child(r,'start')[1:])),*list(map(float,child(r,'end')[1:]))) for r in mask])
    cx=-.35 if ref=='U5' else 0
    island=box(cx-.25,-.25,cx+.25,.25)
    expected=box(-size[0]/2-.05,-size[1]/2-.05,size[0]/2+.05,size[1]/2+.05).difference(island)
    assert openings.symmetric_difference(expected).area<1e-9,'Wrong mask-island extent'
    # The cap exceeds the 0.3 mm hole by 0.1 mm per side; a further 0.05 mm
    # registration screen remains completely covered by normal solder mask.
    assert openings.intersection(Point(cx,0).buffer(.2,quad_segs=64)).area<1e-10,'Thermal-hole screen exposed in mask'
    paste=[window(p) for p in pads if not p[1] and child(p,'layers')[1:]==[side+'.Paste']]
    assert len(paste)==4,'Wrong thermal paste-window count'
    copper=box(-size[0]/2,-size[1]/2,size[0]/2,size[1]/2)
    for p in paste:
        assert copper.buffer(1e-8).covers(p['rectangle']),'Paste outside thermal copper'
        assert openings.buffer(1e-8).covers(p['rectangle']),'Paste printed on mask island'
        assert p['rectangle'].distance(island)>=.05-1e-8,'Paste registration allowance lost at mask island'
    for i,p in enumerate(paste):
        for q in paste[i+1:]:assert p['rectangle'].distance(q['rectangle'])>=.15-1e-8,'Narrow thermal stencil web'
    ratio=sum(p['exact_area_mm2'] for p in paste)/(size[0]*size[1])
    assert .5<=ratio<=.7,('Thermal paste ratio outside selected TI guide range',ref,ratio)
    if ref=='U5':
        for pad in [p for p in pads if p[1] and p[1]!='17']:
            x,y=map(float,child(pad,'at')[1:3]);w,h=map(float,child(pad,'size')[1:])
            assert sorted([w,h])==[.24,.6] and (abs(x)==1.4 or abs(y)==1.4),'Wrong RGT lead lands'
            assert min(abs(x)-w/2 if abs(x)>1 else abs(y)-h/2,10)-.84>=.2-1e-8,'Thermal-to-lead copper gap below 0.2 mm'
    return dict(ref=ref,thermal_copper_size_mm=size,mask_island_size_mm=[.5,.5],
                paste_area_mm2=sum(p['exact_area_mm2'] for p in paste),
                thermal_copper_area_mm2=size[0]*size[1],paste_coverage_ratio=ratio,
                minimum_stencil_web_mm=min(p['rectangle'].distance(q['rectangle']) for i,p in enumerate(paste) for q in paste[i+1:]))


def verify_charger_package():
    tree=loads((BASE/'EC60-nRF52840.kicad_pcb').read_text());rows=[]
    for ref in ['U5','U6']:
        f=next(f for f in children(tree,'footprint') if any(p[1]=='Reference' and p[2]==ref for p in children(f,'property')))
        rows.append(verify_footprint(f,ref))
        library=loads((BASE/'YAECKB.pretty'/(f[1].split(':')[1]+'.kicad_mod')).read_text())
        verify_footprint(library,ref)
    via_positions=[[117.65,145],[133,140.8]]
    for position in via_positions:
        via=next(v for v in children(tree,'via') if list(map(float,child(v,'at')[1:]))==position and child(v,'net')[1]=='GND')
        assert float(child(via,'size')[1])==.5 and float(child(via,'drill')[1])==.3
        assert child(via,'tenting')==['tenting',['front','yes'],['back','yes']],'Thermal via must be mask-tented on both faces'
    return rows
