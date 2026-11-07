#!/usr/bin/env python3
"""Apply current RGT lands and ordinary solder-mask/stencil via isolation."""
import json
import uuid
from pathlib import Path
from kicad_sexpr import Atom, child, children, dumps, form, loads
from usb_short_power_contract import via_map
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'

def number(value):
    return Atom(format(value, '.12g'))

def mask_windows(footprint, ref):
    side = child(footprint, 'layer')[1].split('.')[0]
    w, h, cx = (1.68, 1.68, -.35) if ref == 'U5' else (1.2, 2, 0)
    x0, y0, x1, y1 = -w/2-.05, -h/2-.05, w/2+.05, h/2+.05
    left, right, low, high = cx-.25, cx+.25, -.25, .25
    rectangles = [(x0,y0,left,y1),(right,y0,x1,y1),(left,y0,right,low),(left,high,right,y1)]
    identifiers = [str(uuid.uuid5(uuid.NAMESPACE_URL, 'YETI60-mask-island-'+ref+'-'+str(i))) for i in range(4)]
    footprint[:] = [v for v in footprint if not (isinstance(v,list) and v and v[0]=='fp_rect' and child(v,'uuid') and child(v,'uuid')[1] in identifiers)]
    for identifier, (a,b,c,d) in zip(identifiers, rectangles):
        footprint.append(form('fp_rect',form('start',number(a),number(b)),form('end',number(c),number(d)),
                              form('stroke',form('width',number(0)),form('type',Atom('default'))),
                              form('fill',Atom('solid')),form('layer',side+'.Mask'),form('uuid',identifier)))

def lands(footprint, ref='U5'):
    for pad in children(footprint, 'pad'):
        pin = pad[1]; at = child(pad, 'at'); size = child(pad, 'size')
        if pin == ('17' if ref=='U5' else '11'):
            if ref=='U5': size[1:] = [number(1.68),number(1.68)]
            layers=child(pad,'layers');layers[:] = [v for v in layers if v not in ['F.Mask','B.Mask']]
        elif pin and ref=='U5':
            assert 1 <= int(pin) <= 16
            if abs(float(at[1]))>1:
                at[1]=number(1.4 if float(at[1])>0 else -1.4);size[1:]=[number(.6),number(.24)]
            else:
                at[2]=number(1.4 if float(at[2])>0 else -1.4);size[1:]=[number(.24),number(.6)]
            child(pad,'roundrect_rratio')[1]=number(.05/.24)
        elif not pin:
            assert child(pad,'layers')[1:] in (['B.Paste'],['F.Paste'])
            sign=1 if float(at[2])>0 else -1
            if ref=='U5':
                x,cy,w,h=(-.47,.545,.64,.49) if float(at[1])<0 else (.42,.425,.74,.69)
                radius=.05
            else:
                x,cy,w,h=(-.315 if float(at[1])<0 else .315),.625,.47,.65
                radius=.03
            at[1:3]=[number(x),number(sign*cy)];size[1:]=[number(w),number(h)]
            child(pad,'roundrect_rratio')[1]=number(radius/min(w,h))
    mask_windows(footprint,ref)

def apply_tree(tree):
    for ref in ['U5','U6']:
        f=next(f for f in children(tree,'footprint') if any(p[1]=='Reference' and p[2]==ref for p in children(f,'property')))
        lands(f,ref)
    uid6='bd7c6e02-592d-46f4-91c6-9f93a4948ee5'
    via6=next(v for v in children(tree,'via') if child(v,'uuid')[1]==uid6)
    child(via6,'at')[1:]=[number(133),number(140.8)]
    via5=next(v for v in children(tree,'via') if child(v,'net')[1]=='GND' and list(map(float,child(v,'at')[1:]))==[117.65,145])
    for via in [via5,via6]:
        for side in ['front','back']:child(child(via,'tenting'),side)[1]=Atom('yes')
    for net,start,end in [('BAT_NTC',[116.15,145.9],[116.6,145.75]),('ICHG_SET',[117.15,146.9],[117.25,146.4])]:
        identifier=str(uuid.uuid5(uuid.NAMESPACE_URL,'YETI60-RGT0016C-reconnect-'+net))
        if not any(child(s,'uuid')[1]==identifier for s in children(tree,'segment')):
            tree.append(form('segment',form('start',*[number(v) for v in start]),form('end',*[number(v) for v in end]),form('width',number(.127)),form('layer','B.Cu'),form('net',net),form('uuid',identifier)))
    return via5,via6

def main():
    path=BASE/'EC60-nRF52840.kicad_pcb';tree=loads(path.read_text());via5,via6=apply_tree(tree)
    for ref in ['U5','U6']:
        f=next(f for f in children(tree,'footprint') if any(p[1]=='Reference' and p[2]==ref for p in children(f,'property')))
        library_path=BASE/'YAECKB.pretty'/(f[1].split(':')[1]+'.kicad_mod');library=loads(library_path.read_text());lands(library,ref);library_path.write_text(dumps(library)+'\n')
    spec_path=BASE/'power-layout.json';spec=json.loads(spec_path.read_text());uid6=spec['U6_thermal_via_uuid']
    before5=dict(via_map(tree)[child(via5,'uuid')[1]]);before5['tenting']=['tenting',['front','yes'],['back','none']]
    spec['via_changes']['moved'][child(via5,'uuid')[1]]=dict(before=before5,after=via_map(tree)[child(via5,'uuid')[1]])
    spec['via_changes']['added'][uid6]=via_map(tree)[uid6]
    spec['U6_thermal_via_position_mm']=[133,140.8]
    spec['U6_thermal_via_location']='Retained at EP center; ordinary solder mask on both faces, 0.5 mm component-side mask island and stencil keepout; no resin fill or copper cap'
    path.write_text(dumps(tree)+'\n');spec_path.write_text(json.dumps(spec,indent=2)+'\n')
    print('RGT lands and two toe reconnections applied; U5/U6 retain short ground paths with ordinary mask-island tenting; refill zones before audit')
if __name__=='__main__':main()
