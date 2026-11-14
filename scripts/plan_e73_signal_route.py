#!/usr/bin/env python3
"""Plan one incremental B/In2 route against actual native copper and keepouts.

The output is a work patch. Native DRC, pad/via geometry and connected-ground
checks must independently validate it before incorporation in the PCB build.
"""
import argparse
import fnmatch
import hashlib
import heapq
import json
import math
from pathlib import Path
import uuid
import numpy as np
from shapely import contains_xy, prepare
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from plan_e73_corner_usb import union
from kicad_sexpr import Atom,form,dumps

ROOT=Path(__file__).resolve().parents[1]
LAYERS=['B.Cu','In2.Cu']


def main():
    global LAYERS
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry',type=Path,default=ROOT/'.assembly-work/e73-corner/route-geometry.json')
    parser.add_argument('--net',required=True)
    parser.add_argument('--source',required=True,help='Native pad/track/via UUID')
    parser.add_argument('--target',required=True,help='Native pad/track/via UUID')
    parser.add_argument('--width',type=float,default=.127)
    parser.add_argument('--margin',type=float,default=12)
    parser.add_argument('--layers',nargs='+',choices=['B.Cu','In2.Cu','In1.Cu'],default=LAYERS)
    args=parser.parse_args()
    LAYERS=list(dict.fromkeys(args.layers));assert LAYERS and LAYERS[0]=='B.Cu'
    path=args.geometry.resolve()
    data=json.loads(path.read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    for name,digest in data['source_sha256'].items():assert sha(ROOT/name)==digest,('Stale routing geometry',name)
    copper=data['copper'];by_uuid={q['UUID']:q for q in copper}
    source,target=by_uuid[args.source],by_uuid[args.target]
    assert source['net']==target['net']==args.net
    width=args.width
    assert width>=.127
    rules=data['net_rules'];classes={q['name']:q for q in rules['classes']}
    def net_clearance(net):
        matches=[q for q in rules['netclass_patterns']if fnmatch.fnmatchcase(net,q['pattern'])]
        assert len(matches)<=1, ('Composite class needs explicit review',net)
        return classes[matches[0]['netclass'] if matches else 'Default']['clearance']
    own_clearance=net_clearance(args.net)
    outline=union(data['outline'])
    grouped={}
    for q in copper:
        if q['net']==args.net:continue
        gap=max(own_clearance,net_clearance(q['net']),q.get('local_clearance_mm',0))+.01
        for layer,polys in q['by_layer'].items():grouped.setdefault((layer,gap),[]).append(union(polys))
    allowed={l:outline.buffer(-.7-width/2) for l in LAYERS}
    via_allowed=outline.buffer(-.95)
    for (layer,gap),shapes in grouped.items():
        obstacles=unary_union(shapes)
        if layer in allowed:allowed[layer]=allowed[layer].difference(obstacles.buffer(width/2+gap))
        via_allowed=via_allowed.difference(obstacles.buffer(.25+gap))
    clearance=max(.2,own_clearance)+.002
    via_clearance=.25+clearance
    own_via_holes=unary_union([Point(q['point']).buffer(q['via_drill_mm']/2+.402)for q in copper if q['kind']=='via' and q['net']==args.net])
    via_allowed=via_allowed.difference(own_via_holes)
    smd=unary_union([union(polys)for q in copper if q.get('SMD') for polys in q['by_layer'].values()])
    via_allowed=via_allowed.difference(smd.buffer(.252))
    holes=unary_union([Point(q['point']).buffer(max(q['drill_mm'])/2)for q in copper if q['kind']=='pad' and max(q['drill_mm'])>0])
    via_allowed=via_allowed.difference(holes.buffer(.402))
    for l in LAYERS:allowed[l]=allowed[l].difference(holes.buffer(.252+width/2))
    for pad in copper:
        if pad['kind']!='pad' or not max(pad['drill_mm']):continue
        radius=max(pad['drill_mm'])/2
        gap=max(.25,own_clearance,pad.get('local_clearance_mm',0))+.01
        drill=Point(pad['point']).buffer(radius)
        for layer in LAYERS:allowed[layer]=allowed[layer].difference(drill.buffer(gap+width/2))
        via_allowed=via_allowed.difference(drill.buffer(max(.402,gap+.25)))
    mask=union(data['B_mask_openings'])
    allowed['B.Cu']=allowed['B.Cu'].difference(mask.buffer(width/2+clearance))
    via_allowed=via_allowed.difference(mask.buffer(via_clearance))
    for q in data['keepouts']:
        poly=union(q['polygons'])
        # The reserve lies on the USB reference layer. Copper immediately
        # outside it still clears GND around itself, which can cut into the
        # required reference. Reserve the 0.20 mm pour clearance and
        # the existing 0.254 mm minimum-width fill, with a small margin.
        reference_gap=.5 if q.get('name','').startswith('E73_USB_REFERENCE_') else 0
        if q['tracks']:
            for l in LAYERS:
                if l in q['layers']:allowed[l]=allowed[l].difference(poly.buffer(width/2+.01+reference_gap))
        if q['vias']:via_allowed=via_allowed.difference(poly.buffer(.26+reference_gap))
    for region in allowed.values():prepare(region)
    def anchors(item):
        points=[item['point']]
        if item['kind']=='trace':
            a,z=item['point'],item['end']
            points += [[a[i]+t*(z[i]-a[i])for i in [0,1]]for t in [.25,.5,.75,1]]
        return [(l,tuple(p))for l in LAYERS if l in item['by_layer'] for p in points]
    # An unrouted item may be on F/In1 while its connected escape via is on
    # both routing layers. Resolve the actual copper component; never infer a
    # connection merely from a shared net name.
    members=[q for q in copper if q['net']==args.net]
    parents=list(range(len(members)))
    def find(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for layer in ['F.Cu','In1.Cu','In2.Cu','B.Cu']:
        indices=[i for i,q in enumerate(members)if layer in q['by_layer']]
        shapes=[union(members[i]['by_layer'][layer]).buffer(.002)for i in indices]
        tree=STRtree(shapes)
        for j,shape in enumerate(shapes):
            for k in tree.query(shape,predicate='intersects'):
                a,z=find(indices[j]),find(indices[int(k)])
                if a!=z:parents[z]=a
    by_id={q['UUID']:i for i,q in enumerate(members)}
    a,z=find(by_id[args.source]),find(by_id[args.target])
    assert a!=z,'Requested anchors already share an actual copper component'
    def component_anchors(root):
        result=[]
        for i,q in enumerate(members):
            if find(i)!=root:continue
            for layer,pt in anchors(q):
                # Arc interpolation points need not lie on the curved copper.
                if union(q['by_layer'][layer]).buffer(.002).covers(Point(pt)):
                    result.append((layer,pt))
        return list(dict.fromkeys(result))
    starts_all,ends_all=component_anchors(a),component_anchors(z)
    assert starts_all and ends_all,'No B/In2 escape from a connected component'
    def nearest(ours,theirs):
        return sorted(ours,key=lambda q:min(math.dist(q[1],r[1])for r in theirs))[:24]
    start_anchors,end_anchors=nearest(starts_all,ends_all),nearest(ends_all,starts_all)
    all_points=[p for l,p in start_anchors+end_anchors]
    x0,y0=[math.floor((min(q[i]for q in all_points)-args.margin)*10)/10 for i in [0,1]]
    x1,y1=[math.ceil((max(q[i]for q in all_points)+args.margin)*10)/10 for i in [0,1]]
    step=.1;xs=np.arange(x0,x1+.0001,step);ys=np.arange(y0,y1+.0001,step);gx,gy=np.meshgrid(xs,ys)
    allowed_grid=[contains_xy(allowed[l],gx,gy)for l in LAYERS]
    via_grid=contains_xy(via_allowed,gx,gy)
    h,w=gx.shape
    encode=lambda l,x,y:(l*h+y)*w+x
    def decode(k):
        row,x=divmod(k,w);l,y=divmod(row,h);return l,x,y
    def candidates(anchors):
        result={}
        for layer,p in anchors:
            l=LAYERS.index(layer);x=round((p[0]-x0)/step);y=round((p[1]-y0)/step)
            point=(float(xs[x]),float(ys[y]))
            if allowed_grid[l][y,x] and allowed[layer].covers(LineString([p,point])):
                result[encode(l,x,y)]=p
        return result
    starts,ends=candidates(start_anchors),candidates(end_anchors)
    assert starts and ends,('No legal launch/landing',len(starts),len(ends))
    end_cells=[decode(k)for k in ends]
    def estimate(l,x,y):return min(math.hypot(X-x,Y-y)*step for L,X,Y in end_cells)
    costs={k:0. for k in starts};parents={};queue=[(estimate(*decode(k)),0.,k)for k in starts];heapq.heapify(queue)
    found=None;visited=0
    directions=[(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]
    while queue:
        _,g,k=heapq.heappop(queue)
        if g!=costs.get(k):continue
        visited+=1
        if k in ends:found=k;break
        l,x,y=decode(k)
        for dx,dy in directions:
            X,Y=x+dx,y+dy
            if not(0<=X<w and 0<=Y<h and allowed_grid[l][Y,X]):continue
            # Legal grid endpoints alone do not prove that a narrow obstacle
            # between them is clear, including for an orthogonal step.
            if not allowed[LAYERS[l]].covers(LineString([(xs[x],ys[y]),(xs[X],ys[Y])])):continue
            nk=encode(l,X,Y);ng=g+math.hypot(dx,dy)*step
            if ng<costs.get(nk,float('inf')):
                costs[nk]=ng;parents[nk]=k;heapq.heappush(queue,(ng+estimate(l,X,Y),ng,nk))
        if via_grid[y,x]:
            for next_layer in range(len(LAYERS)):
                if next_layer==l or not allowed_grid[next_layer][y,x]:continue
                nk=encode(next_layer,x,y);ng=g+5
                if ng<costs.get(nk,float('inf')):
                    costs[nk]=ng;parents[nk]=k;heapq.heappush(queue,(ng+estimate(next_layer,x,y),ng,nk))
    assert found is not None,('No actual-copper route in search bounds',visited,[x0,y0,x1,y1])
    goal=found;keys=[found]
    while found not in starts:found=parents[found];keys.append(found)
    keys.reverse();states=[decode(k)for k in keys]
    paths=[];vias=[];segment=[]
    for i,(l,x,y)in enumerate(states):
        point=[round(float(xs[x]),6),round(float(ys[y]),6)]
        if segment and segment[-1][0]!=l:
            paths.append((LAYERS[segment[0][0]],[p for L,p in segment]));vias.append(point);segment=[]
        segment.append((l,point))
    paths.append((LAYERS[segment[0][0]],[p for L,p in segment]))
    paths[0][1].insert(0,list(starts[keys[0]]));paths[-1][1].append(list(ends[goal]))
    items=[];length=0.
    tag='yeti60-e73-corner/actual-route/'+args.net+'/'+data['pcb_sha256']
    for layer,points in paths:
        compressed=[]
        for pt in points:
            if compressed and pt==compressed[-1]:continue
            while len(compressed)>1:
                a,z=compressed[-2:];u=(z[0]-a[0],z[1]-a[1]);v=(pt[0]-z[0],pt[1]-z[1])
                if abs(u[0]*v[1]-u[1]*v[0])<1e-8 and u[0]*v[0]+u[1]*v[1]>0:compressed.pop()
                else:break
            compressed.append(pt)
        assert allowed[layer].buffer(.000002).covers(LineString(compressed)), 'Compressed path left allowed copper region'
        # Grid staircases can contain hundreds of tiny alternating segments.
        # Pull each corner only where the full straight segment remains inside
        # the independently constructed clearance region.
        pulled=[compressed[0]];index=0
        while index<len(compressed)-1:
            end=len(compressed)-1
            while end>index+1 and not allowed[layer].covers(LineString([compressed[index],compressed[end]])):
                end-=1
            pulled.append(compressed[end]);index=end
        compressed=pulled
        for a,z in zip(compressed,compressed[1:]):
            identity=json.dumps([layer,a,z,width]);identifier=str(uuid.uuid5(uuid.NAMESPACE_URL,tag+identity))
            items.append(dumps(form('segment',form('start',*a),form('end',*z),form('width',width),form('layer',layer),form('net',args.net),form('uuid',identifier))))
            length+=math.dist(a,z)
    for point in vias:
        assert via_allowed.covers(Point(point))
        items.append(dumps(form('via',form('at',*point),form('size',.5),form('drill',.3),form('layers','F.Cu','B.Cu'),form('tenting',form('front',Atom('yes')),form('back',Atom('yes'))),form('net',args.net),form('uuid',str(uuid.uuid5(uuid.NAMESPACE_URL,tag+json.dumps(point)))))))
    output=ROOT/'.assembly-work/e73-corner'/('actual-route-'+args.net.replace('+','plus')+'.json')
    report=dict(status='planned-native-validation-required',physical_verification=False,manufacturing_released=False,
        base_board_sha256=data['pcb_sha256'],net=args.net,items=items,
        length_mm=length,new_vias=len(vias),visited_states=visited,source_anchor_UUID=args.source,target_anchor_UUID=args.target,
        grid_mm=step,trace_width_mm=width,minimum_fixed_copper_clearance_mm=own_clearance+.01,pair_clearance_policy='max(netclass and item clearances) plus 0.01 mm polygon reserve; local drill clearances retained',
        routing_layers=LAYERS,
        source_sha256={str(f.relative_to(ROOT)):sha(f)for f in [path,Path(__file__),ROOT/'scripts/plan_e73_corner_usb.py']})
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['status','net','length_mm','new_vias','visited_states']},indent=2))


if __name__=='__main__':main()
