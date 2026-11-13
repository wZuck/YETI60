#!/usr/bin/env python3
"""Plan a paired B.Cu path in actual In2 GND and away from fixed B copper.

Run with requirements-audit.txt after native geometry export. Planning does not
constitute electrical acceptance: refill the built PCB and independently check
every actual route and reference polygon afterwards.
"""
import heapq
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from shapely import contains_xy, make_valid
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union, nearest_points

ROOT = Path(__file__).resolve().parents[1]


def union(records):
    shapes = []
    for q in records:
        p = Polygon(q['outer'], q['holes'])
        if not p.is_valid:
            old = p.area
            p = make_valid(p)
            assert abs(p.area-old) < .01
        if not p.is_empty:
            shapes.append(p)
    return unary_union(shapes)


def astar(allowed, start, end, step, shape, xs, ys):
    directions = [(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]
    sx, sy = start
    ex, ey = end
    assert allowed[sy,sx] and allowed[ey,ex], ('Blocked route anchors', bool(allowed[sy,sx]), bool(allowed[ey,ex]))
    h, w = allowed.shape
    encode = lambda x,y,d: (y*w+x)*8+d
    origin = encode(sx,sy,0)
    costs = {origin:0.0}
    parent = {}
    queue = [(math.hypot(ex-sx,ey-sy)*step,0.0,origin)]
    found = None
    while queue:
        _, g, key = heapq.heappop(queue)
        if g != costs.get(key):
            continue
        d = key%8
        cell = key//8
        x,y = cell%w,cell//w
        if (x,y) == (ex,ey) and d == 4:
            found = key
            break
        for nd,(dx,dy) in enumerate(directions):
            if min((nd-d)%8,(d-nd)%8)>1:
                continue
            X,Y = x+dx,y+dy
            if not (0<=X<w and 0<=Y<h and allowed[Y,X]):
                continue
            if dx and dy and not (allowed[y,X] and allowed[Y,x]):
                # A diagonal can cross a narrow continuous 45-degree corridor
                # even when its two orthogonal neighbour grid cells are out.
                # Check the actual polygon instead of relaxing any margin.
                edge = LineString([(xs[x],ys[y]),(xs[X],ys[Y])])
                if not shape.covers(edge):
                    continue
            c = g+math.hypot(dx,dy)*step+.12*min((nd-d)%8,(d-nd)%8)
            nk = encode(X,Y,nd)
            if c < costs.get(nk,float('inf')):
                costs[nk] = c
                parent[nk] = key
                heapq.heappush(queue,(c+math.hypot(ex-X,ey-Y)*step,c,nk))
    assert found is not None, 'No paired route within the actual reference/clearance envelope'
    path = []
    while True:
        cell = found//8
        path.append((cell%w,cell//w))
        if found == origin:
            break
        found = parent[found]
    path.reverse()
    compressed = [path[0]]
    for a,b,z in zip(path,path[1:],path[2:]):
        if (b[0]-a[0],b[1]-a[1]) != (z[0]-b[0],z[1]-b[1]):
            compressed.append(b)
    compressed.append(path[-1])
    return compressed, len(costs)


def main():
    spec_path = ROOT/'hardware/e73-corner-spec.json'
    spec = json.loads(spec_path.read_text())
    input_path = ROOT/'.assembly-work/e73-corner/copper.json'
    data = json.loads(input_path.read_text())
    sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,digest in data['source_sha256'].items():
        assert sha(ROOT/name) == digest, ('Stale planning geometry',name)
    reference = union(data['ground_copper']['In2.Cu'])
    blockers = union(data['B_blockers'])
    outline = union(data['outline'])
    # Centreline half-spacing .25 plus trace half-width .15, with a .10 mm
    # reference reserve. Fixed-copper clearance adds a separate .15 mm.
    allowed_shape = reference.buffer(-.53).intersection(outline.buffer(-1.13)).difference(blockers.buffer(.64))
    x,y,X,Y = spec['provisional_antenna_keepout_PCB_mm']
    allowed_shape = allowed_shape.difference(box(x-.64,y-.64,X+.64,Y+.64))
    step = .1
    xs = np.arange(330,357.0001,step)
    ys = np.arange(109.05,198.5501,step)
    gx,gy = np.meshgrid(xs,ys)
    allowed = contains_xy(allowed_shape,gx,gy)
    start_xy,end_xy = (351,110.95),(340.2,195.75)
    grid = lambda q:(round((q[0]-xs[0])/step),round((q[1]-ys[0])/step))
    clipped = allowed_shape.intersection(box(xs[0],ys[0],xs[-1],ys[-1]))
    components = list(clipped.geoms) if hasattr(clipped,'geoms') else [clipped]
    launch_component = next(p for p in components if p.covers(Point(start_xy)))
    target_component = next(p for p in components if p.covers(Point(end_xy)))
    assert launch_component == target_component, ('Disconnected USB corridor',launch_component.distance(target_component),[list(p.coords) for p in nearest_points(launch_component,target_component)])
    path,visited = astar(allowed,grid(start_xy),grid(end_xy),step,allowed_shape,xs,ys)
    points = [(round(xs[i],6),round(ys[j],6)) for i,j in path]
    # Force the launch tangent. End-tangent west is part of the search state.
    points = [(350.6,110.95),*points,(339.2,195.75)]
    center = LineString(points)
    assert allowed_shape.buffer(.002).covers(center), 'Grid path cut a reference/clearance corner'
    minus = center.parallel_offset(.25,'left',join_style='mitre')
    plus = center.parallel_offset(.25,'right',join_style='mitre')
    assert minus.geom_type == plus.geom_type == 'LineString'
    def forward(line):
        p = list(line.coords)
        if math.dist(p[0],start_xy) > math.dist(p[-1],start_xy):
            p.reverse()
        return [[round(x,6),round(y,6)]for x,y in p]
    dm,dp = forward(minus),forward(plus)
    assert dm[0] == [350.6,111.2] and dp[0] == [350.6,110.7]
    assert dm[-1] == [339.2,195.5] and dp[-1] == [339.2,196.0], (dm[-5:],dp[-5:],points[-6:])
    dm = [[348.1,111.2],*dm,[337.14,195.5],[337.14,196.5]]
    dp = [[348.1,110.2],[348.5,110.2],[348.7,110.4],[350.3,110.4],*dp,[338.41,196.0],[338.41,196.5]]
    for q in [dm,dp]:
        assert all(a!=z for a,z in zip(q,q[1:]))
    spec['data_paths_B_Cu_mm']={'USB_DM':dm,'USB_DP':dp}
    input_hashes={str(input_path.relative_to(ROOT)):sha(input_path),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))}
    spec_path.write_text(json.dumps(spec,indent=2)+'\n')
    report=dict(status='paired-path-planned-native-validation-required',physical_verification=False,manufacturing_released=False,
                grid_mm=step,spacing_mm=.5,trace_width_mm=.3,reference_reserve_mm=.1,
                fixed_copper_clearance_mm=.2,board_edge_target_mm=.7,visited_states=visited,
                centerline_PCB_mm=points,lengths_B_mm={n:LineString(p).length for n,p in spec['data_paths_B_Cu_mm'].items()},
                source_sha256=input_hashes,output_spec_sha256=sha(spec_path))
    (ROOT/'.assembly-work/e73-corner/USB-plan.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','visited_states','lengths_B_mm']},indent=2))


if __name__=='__main__':
    main()
