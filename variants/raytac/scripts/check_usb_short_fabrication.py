#!/usr/bin/env python3
"""Independent Gerber/Excellon/IPC readback; not a fabrication acceptance test."""
import csv
import hashlib
import importlib.metadata
import json
import math
import re
import tempfile
import warnings
import zipfile
from pathlib import Path
from gerbonara.rs274x import GerberFile
from gerbonara.excellon import ExcellonFile
from gerbonara.ipc356 import Netlist
from gerbonara import graphic_primitives as gp
from gerbonara.utils import MM, approximate_arc
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union, polygonize

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/usb-short-route'
OUT=BASE/'fabrication'
NAME='EC60-nRF52840'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())


def hashes(table):
    for p,h in table.items():assert sha(ROOT/p)==h,('Stale CAM source/output',p)


def near(a,b,tolerance):
    return max(abs(x-y) for x,y in zip(a,b))<=tolerance


def bbox_near(a,b,tolerance=.003):
    return near([*a[0],*a[1]],[*b[0],*b[1]],tolerance)


def same_net(exported,native):
    return exported==native or (exported in ['N/C','',None] and (not native or native.startswith('unconnected-')))


def line_points(p):
    if isinstance(p,gp.Line):return [(p.x1,p.y1),(p.x2,p.y2)]
    assert isinstance(p,gp.Arc),('Unexpected profile primitive',type(p).__name__)
    result=list(approximate_arc(p.cx,p.cy,p.x1,p.y1,p.x2,p.y2,p.clockwise,max_error=.001))
    result[0]=(p.x1,p.y1);result[-1]=(p.x2,p.y2)
    return result


def primitive_shape(p):
    if isinstance(p,gp.Circle):return Point(p.x,p.y).buffer(p.r,quad_segs=64)
    if isinstance(p,(gp.Line,gp.Arc)):
        return LineString(line_points(p)).buffer(p.width/2,quad_segs=32)
    if isinstance(p,gp.Rectangle):p=p.to_arc_poly()
    assert isinstance(p,gp.ArcPoly),('Unsupported aperture primitive',type(p).__name__)
    points=[]
    # gerbonara 1.5.0's ArcPoly.approximate_arcs has an undefined-variable
    # branch. Use the published primitive segments and unit-safe utility.
    for start,end,(clockwise,center) in p.segments:
        if clockwise is None:points.append(start)
        else:points.extend(list(approximate_arc(*center,*start,*end,clockwise,max_error=.001))[:-1])
    return Polygon(points).buffer(0)


def aperture_shape(objects):
    shape=Polygon()
    for obj in objects:
        for p in obj.to_primitives(MM):
            geometry=primitive_shape(p)
            shape=shape.union(geometry) if p.polarity_dark else shape.difference(geometry)
    return shape


def check_drills(files,native):
    actual=[]; parser_warnings=[]
    for plated,label in [(True,'PTH'),(False,'NPTH')]:
        path=files/(NAME+'-'+label+'.drl');text=path.read_text()
        required=('Plated' if plated else 'NonPlated')+',1,4,'+label
        assert 'TF.FileFunction,'+required in text,('Wrong drill layer span/plating',label)
        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter('always');drill=ExcellonFile.open(path)
        for warning in seen:
            message=str(warning.message).replace(str(files)+'/','')
            assert 'G90 header statement found after end of header' in message,('Unexpected drill parser warning',message)
            parser_warnings.append(message)
        for obj in drill.objects:
            primitives=list(obj.to_primitives(MM));assert len(primitives)==1
            p=primitives[0]
            if isinstance(p,gp.Circle):record=dict(kind='circle',plated=plated,center_mm=[p.x,p.y],size_mm=[2*p.r]*2)
            else:
                assert isinstance(p,gp.Line),'Unexpected drill routing primitive'
                record=dict(kind='slot',plated=plated,diameter_mm=p.width,endpoints_mm=[[p.x1,p.y1],[p.x2,p.y2]])
            actual.append(record)
    assert len(actual)==len(native['holes']),('Drill count mismatch',len(actual),len(native['holes']))
    remaining=list(actual)
    for expected in native['holes']:
        def match(h):
            if (h['kind'],h['plated'])!=(expected['kind'],expected['plated']):return False
            if h['kind']=='circle':return near(h['center_mm'],expected['center_mm'],.0015) and near(h['size_mm'],expected['size_mm'],.001)
            return abs(h['diameter_mm']-expected['diameter_mm'])<.001 and any(
                near(h['endpoints_mm'][0],ends[0],.0015) and near(h['endpoints_mm'][1],ends[1],.0015)
                for ends in [expected['endpoints_mm'],expected['endpoints_mm'][::-1]])
        found=next((i for i,h in enumerate(remaining) if match(h)),None)
        assert found is not None,('Missing/moved/drill-size/plating mismatch',expected)
        remaining.pop(found)
    assert not remaining
    return dict(total=len(actual),plated=sum(h['plated'] for h in actual),
                nonplated=sum(not h['plated'] for h in actual),slots=sum(h['kind']=='slot' for h in actual),
                center_tolerance_mm=.0015,parser_warnings=parser_warnings)


def check_outline(gerber,native):
    coordinates=[]
    for obj in gerber.objects:
        for p in obj.to_primitives(MM):
            assert p.polarity_dark
            coordinates.append(line_points(p))
    # KiCad's rounded arc endpoints can differ by tens of nanometres.
    # Require one unique neighbour within 1 um before joining; never close
    # arbitrary broken outlines by buffering their full geometry.
    ends=[(i,k,pts[k]) for i,pts in enumerate(coordinates) for k in [0,-1]]
    maximum_gap=0
    for j,(i,k,point) in enumerate(ends):
        mates=[n for n,(other,_,p) in enumerate(ends) if other!=i and math.dist(point,p)<=.001]
        assert len(mates)==1,('Open/ambiguous Gerber profile endpoint',point,mates)
        n=mates[0];other,index,p=ends[n];maximum_gap=max(maximum_gap,math.dist(point,p))
        if n>j:
            joined=tuple((a+b)/2 for a,b in zip(point,p))
            coordinates[i][k]=joined;coordinates[other][index]=joined
    lines=unary_union([LineString(points) for points in coordinates])
    faces=list(polygonize(lines));assert len(faces)==1,'Profile must form one closed outer contour'
    expected=unary_union([Polygon(p) for p in native['outline_polygons_mm']])
    deviation=faces[0].boundary.hausdorff_distance(expected.boundary)
    assert deviation<=.01,('CAM outline differs from native',deviation)
    x0,y0,x1,y1=faces[0].bounds
    assert bbox_near([[x0,y0],[x1,y1]],native['bounds_mm'],.003)
    return dict(closed_outer_contours=1,centerline_bounds_mm=[[x0,y0],[x1,y1]],
                width_mm=x1-x0,height_mm=y1-y0,maximum_boundary_deviation_mm=deviation,
                boundary_comparison_tolerance_mm=.01,endpoint_join_tolerance_mm=.001,
                maximum_original_endpoint_gap_mm=maximum_gap,outline_stroke_is_not_board_size=True)


def check_pads(gerbers,native):
    candidates={}
    for layer in ['F.Cu','B.Cu']:
        for o in gerbers[layer].objects:
            attrs=o.attrs if isinstance(o.attrs,dict) else {}
            identity=attrs.get('.P',())
            if len(identity)>=2:candidates.setdefault((layer,*identity[:2]),[]).append(o)
    for p in native['fitted_pads']:
        key=(p['layer'],p['ref'],p['pin']);choices=candidates.get(key,[])
        matches=[o for o in choices if bbox_near(o.bounding_box(MM),p['bbox_mm'])]
        assert len(matches)==1,('Missing/wrong native copper land',p['ref'],p['pin'],p['bbox_mm'])
        attrs=matches[0].attrs;net=attrs.get('.N',('',))[0]
        assert same_net(net,p['net']),('CAM pad net mismatch',p,net)
    return dict(fitted_lands_checked=len(native['fitted_pads']),xy_bbox_tolerance_mm=.003,
                method='X2 reference/pin/net and aperture bounds, including all seven 0805 power capacitors')


def check_stencil(gerber,native):
    actual=[o for o in gerber.objects if list(o.to_primitives(MM))]
    assert len(actual)==len(native['paste_apertures']),('Unexpected paste aperture count',len(actual),len(native['paste_apertures']))
    remaining=list(actual)
    for p in native['paste_apertures']:
        matches=[i for i,o in enumerate(remaining) if bbox_near(o.bounding_box(MM),p['bbox_mm'])]
        assert len(matches)==1,('Missing/wrong stencil aperture',p)
        remaining.pop(matches[0])
    for p in native['excluded_paste']:
        assert not any(bbox_near(o.bounding_box(MM),p['bbox_mm']) for o in actual),'DNP JP1 still has paste apertures'
    return dict(apertures=len(actual),omitted_DNP=['JP1'],omitted_apertures=len(native['excluded_paste']))


def check_masks(front,back):
    front_shape=aperture_shape(front.objects);back_shape=aperture_shape(back.objects);rows=[]
    for ref,x,y in [('U5',117.65,-145),('U6',133,-140.8)]:
        hole_and_registration=Point(x,y).buffer(.2,quad_segs=64)
        assert front_shape.intersection(hole_and_registration).area<1e-8,('Front thermal via not tented in Gerber',ref)
        assert back_shape.intersection(hole_and_registration).area<1e-8,('Back thermal via not tented in Gerber',ref)
        rows.append(dict(ref=ref,center_mm=[x,y],drill_mm=.3,mask_registration_screen_mm=.05,
                         front_opening=False,back_opening=False))
    for x,y in [(118.5,-145),(117.25,-145),(117.65,-145.5),(133.45,-140.8),(133,-141.6)]:
        assert back_shape.buffer(1e-6).contains(Point(x,y).buffer(.02)), 'Thermal mask windows closed or altered'
    return rows


def check_positions(native):
    with (OUT/'positions.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    assert {r['Ref'] for r in rows}==set(native['positions']) and len(rows)==75
    for row in rows:
        p=native['positions'][row['Ref']]
        assert near([float(row['PosX']),float(row['PosY'])],[p['x_mm'],p['y_mm']],.000002),('Placement origin/mirror mismatch',row)
        assert row['Side']==p['side'] and row['Val']==p['value']
        assert row['Package']==p['package'],('Placement package mismatch',row)
        delta=(float(row['Rot'])-p['angle_deg'])%360
        assert min(delta,360-delta)<.000001,('Placement rotation mismatch',row)
    return 75


def check_ipc(native):
    path=OUT/'mainboard.ipc';netlist=Netlist.open(path);matched=0
    # KiCad uses alphanumeric long-net aliases; the pinned reader leaves
    # some base-36 aliases unexpanded. Resolve the file's own definitions.
    aliases=dict(re.findall(r'^P\s+NNAME(\S+)\s+(.+?)\s*$',path.read_text(),re.MULTILINE))
    connected={p['net'] for p in native['ipc_pad_sites'] if p['net'] and not p['net'].startswith('unconnected-')}
    assert len({n.casefold() for n in connected})==len(connected),'IPC uppercasing merges distinct native nets'
    used=set()
    for p in native['ipc_pad_sites']:
        choices=[r for r in netlist.test_records if r.ref_des==p['ref'] and getattr(r,'pin',None)==p['pin']
                 and r.access_layer==p['access_layer']
                 and near([MM.convert_from(r.unit,r.x),MM.convert_from(r.unit,r.y)],p['center_mm'],.003)]
        assert len(choices)==1,('IPC origin/pad mismatch',p['ref'],p['pin'],p['center_mm'])
        net=aliases.get(choices[0].net_name,choices[0].net_name)
        # IPC exporters uppercase short net labels; preserve X2 case checks
        # above and permit this only after proving no native case collision.
        assert same_net(net.casefold() if net else net,p['net'].casefold()),('IPC net mismatch',p,net)
        assert choices[0].access_layer==p['access_layer'],('IPC pad side mismatch',p)
        assert id(choices[0]) not in used,'IPC test record reused for multiple pads'
        used.add(id(choices[0]))
        matched+=1
    via_sites=[h for h in native['holes'] if 'net' in h]
    for via in via_sites:
        choices=[r for r in netlist.test_records if r.is_via and near(
            [MM.convert_from(r.unit,r.x),MM.convert_from(r.unit,r.y)],via['center_mm'],.003)]
        assert len(choices)==1,('IPC via origin/missing/duplicate mismatch',via['owner'])
        record=choices[0];net=aliases.get(record.net_name,record.net_name)
        assert same_net(net.casefold() if net else net,via['net'].casefold()),('IPC via net mismatch',via)
        assert record.is_plated and record.access_layer==0
        assert abs(MM.convert_from(record.unit,record.hole_dia)-via['size_mm'][0])<=.003
        assert id(record) not in used;used.add(id(record))
    assert len(used)==len(netlist.test_records),'Unmatched IPC records'
    return dict(fitted_pin_sites_checked=len(native['fitted_pads']),all_pad_sites_checked=matched,
                via_sites_checked=len(via_sites),all_test_records_checked=len(used),coordinate_tolerance_mm=.003,
                origin='Absolute native XY, Y negated; temporary IPC auxiliary origin set to zero',
                parsed_records=len(netlist.test_records),long_net_aliases=len(aliases))


def verify():
    exported=read(BASE/'audit/fabrication-export.json');hashes(exported['source_sha256']);hashes(exported['outputs'])
    native=read(OUT/'native-map.json');hashes(native['source_sha256'])
    with tempfile.TemporaryDirectory(prefix='yeti60-cam-readback-') as d:
        work=Path(d)
        with zipfile.ZipFile(OUT/'yeti60-raytac-candidate-gerbers.zip') as z:
            assert len(z.namelist())==len(set(z.namelist()))==12
            assert all(Path(n).name==n for n in z.namelist());z.extractall(work)
        gerbers={}
        layers=['F.Cu','In1.Cu','In2.Cu','B.Cu','F.Mask','B.Mask','F.SilkS','B.SilkS','Edge.Cuts']
        for layer in layers:
            path=work/(NAME+'-'+layer.replace('SilkS','Silkscreen').replace('.','_')+'.gbr')
            assert path.exists(),('Missing CAM layer',layer)
            gerbers[layer]=GerberFile.open(path)
            if layer in layers[:4]:
                index=layers.index(layer)+1
                assert '%TF.FileFunction,Copper,L'+str(index)+',' in path.read_text(),('Wrong copper layer order',layer)
        job=read(work/(NAME+'-job.gbrjob'))
        assert {Path(r['Path']).name for r in job['FilesAttributes']}=={p.name for p in work.glob('*.gbr')},'Gerber job references missing/mixed layers'
        drill=check_drills(work,native);outline=check_outline(gerbers['Edge.Cuts'],native)
        pads=check_pads(gerbers,native);mask=check_masks(gerbers['F.Mask'],gerbers['B.Mask'])
        with zipfile.ZipFile(OUT/'yeti60-raytac-candidate-bottom-stencil.zip') as z:
            assert sorted(z.namelist())==[NAME+'-B_Paste.gbr',NAME+'-Edge_Cuts.gbr'];z.extractall(work/'stencil')
        stencil=check_stencil(GerberFile.open(work/'stencil'/(NAME+'-B_Paste.gbr')),native)
    return dict(status='candidate-CAM-native-roundtrip-passed',manufacturing_released=False,
                production_approved=False,physical_verification=False,drills=drill,outline=outline,
                copper_lands=pads,thermal_via_masks=mask,stencil=stencil,
                fitted_placements=check_positions(native),IPC=check_ipc(native),
                parser_versions={p:importlib.metadata.version(p) for p in ['gerbonara','shapely']},
                source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'requirements-cam.txt',BASE/'audit/fabrication-export.json']},
                limits=['Independent CAM/native parity is not supplier DFM approval, a passing USB eye or physical operation',
                        'Ordinary mask-tented U5/U6 thermal vias require receiving inspection of mask islands and first-article reflow/thermal qualification; tenting is not resin filling or copper capping',
                        'C5 is a separate board; the mainboard archive does not include daughterboard fabrication'])


def main():
    report=verify();(BASE/'audit/fabrication-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],report['drills'],report['copper_lands'])


if __name__=='__main__':main()
