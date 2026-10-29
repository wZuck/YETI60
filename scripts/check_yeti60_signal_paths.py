#!/usr/bin/env python3
"""Contact-aware USB centerline paths, branches and layer-use evidence.

This is geometric extraction, not an electromagnetic or USB compliance solver.
"""
import hashlib
import heapq
import json
import math
from pathlib import Path
import pcbnew as pcb

ROOT=Path(__file__).resolve().parents[1]
LAYERS=[pcb.F_Cu,pcb.In1_Cu,pcb.In2_Cu,pcb.B_Cu]
STACK=json.loads((ROOT/'mechanical/pcb-fabrication-spec.json').read_text())
outer,inner=STACK['outer_copper_mm'],STACK['inner_copper_mm']
front_dielectric,back_dielectric=STACK['outer_dielectrics_mm']
Z={pcb.F_Cu:outer/2,pcb.In1_Cu:outer+front_dielectric+inner/2,
   pcb.In2_Cu:outer+front_dielectric+inner+STACK['core_mm']+inner/2,
   pcb.B_Cu:outer+front_dielectric+2*inner+STACK['core_mm']+back_dielectric+outer/2}


def xy(p):return (pcb.ToMM(p.x),pcb.ToMM(p.y))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dot(a,b):return a[0]*b[0]+a[1]*b[1]
def sub(a,b):return (a[0]-b[0],a[1]-b[1])
def at(a,b,t):return (a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)


def projection(point,a,b):
    direction=sub(b,a);length=dot(direction,direction)
    t=max(0,min(1,dot(sub(point,a),direction)/length)) if length else 0
    return t,at(a,b,t)


def contacts(a,b,c,d):
    choices=[]
    for t,point in [(0,a),(1,b)]:
        s,other=projection(point,c,d);choices.append((math.dist(point,other),t,s))
    for s,point in [(0,c),(1,d)]:
        t,other=projection(point,a,b);choices.append((math.dist(point,other),t,s))
    u,v,w=sub(b,a),sub(d,c),sub(c,a);det=u[0]*v[1]-u[1]*v[0]
    if abs(det)>1e-16:
        t=(w[0]*v[1]-w[1]*v[0])/det;s=(w[0]*u[1]-w[1]*u[0])/det
        if 0<=t<=1 and 0<=s<=1:choices.append((0,t,s))
    best=min(q[0] for q in choices)
    return [(t,s) for dist,t,s in choices if dist<=best+1e-7]


def centerline(item):
    start,end=xy(item.GetStart()),xy(item.GetEnd())
    if item.GetClass()!='PCB_ARC':return [start,end]
    middle=xy(item.GetMid());a,b=sub(middle,start),sub(end,start)
    determinant=2*(a[0]*b[1]-a[1]*b[0])
    assert abs(determinant)>1e-16,'Degenerate arc'
    aa,bb=dot(a,a),dot(b,b)
    rel=((aa*b[1]-bb*a[1])/determinant,(a[0]*bb-b[0]*aa)/determinant)
    center=(start[0]+rel[0],start[1]+rel[1]);radius=math.dist(center,start)
    angle=lambda point:math.atan2(point[1]-center[1],point[0]-center[0])
    first=angle(start);sweep=(angle(end)-first)%(2*math.pi)
    if (angle(middle)-first)%(2*math.pi)>sweep+1e-8:sweep-=2*math.pi
    maximum=2*math.acos(max(-1,1-.002/radius))
    count=max(2,math.ceil(abs(sweep)/maximum))
    points=[(center[0]+radius*math.cos(first+sweep*i/count),center[1]+radius*math.sin(first+sweep*i/count)) for i in range(count+1)]
    points[0],points[-1]=start,end
    return points


class Graph:
    def __init__(self):self.adj={};self.edges=[]
    def add(self,a,b,length,kind,**data):
        index=len(self.edges);self.edges.append({'a':a,'b':b,'length_mm':length,'kind':kind,**data})
        self.adj.setdefault(a,[]).append((length,b,index));self.adj.setdefault(b,[]).append((length,a,index))
    def path(self,start,goals):
        queue=[(0,start)];dist={start:0};parent={};found=None
        while queue:
            length,node=heapq.heappop(queue)
            if length!=dist[node]:continue
            if node in goals:found=node;break
            for weight,next_node,edge in self.adj.get(node,[]):
                candidate=length+weight
                if candidate<dist.get(next_node,math.inf):
                    dist[next_node]=candidate;parent[next_node]=(node,edge);heapq.heappush(queue,(candidate,next_node))
        assert found is not None,'No actual contact-aware path to endpoint'
        nodes=[found];edges=[]
        while nodes[-1]!=start:
            node,edge=parent[nodes[-1]];nodes.append(node);edges.append(edge)
        return dist[found],list(reversed(nodes)),list(reversed(edges))


def extract(path):
    board=pcb.LoadBoard(str(path));board.BuildConnectivity();conn=board.GetConnectivity()
    pads={(f.GetReference(),p.GetNumber()):p for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()}
    nets={'D+','D-','USB_DP','USB_DM'}
    items=[i for i in [*board.GetTracks(),*pads.values()] if i.GetNetname() in nets]
    uid=lambda i:i.m_Uuid.AsString()
    by_id={uid(i):i for i in items};graph=Graph();segments={};splits={};ports={}
    point_node=lambda key,layer,point:(key,layer,round(point[0],6),round(point[1],6))
    for item in items:
        key=uid(item)
        if item.GetClass() in ['PCB_TRACK','PCB_ARC']:
            points=centerline(item);segments[key]=list(zip(points,points[1:]));splits[key]=[{0.,1.} for _ in segments[key]]
        else:
            nodes=[point_node(key,l,xy(item.GetPosition())) for l in LAYERS if item.IsOnLayer(l)]
            for a,b in zip(nodes,nodes[1:]):
                graph.add(a,b,abs(Z[a[1]]-Z[b[1]]) if isinstance(item,pcb.PCB_VIA) else 0,
                          'via' if isinstance(item,pcb.PCB_VIA) else 'pad',item=key)
            if item.GetClass()=='PAD':ports[(item.GetParentFootprint().GetReference(),item.GetNumber())]=nodes[0]
    def node(item,layer,point):return point_node(uid(item),layer,point)
    def join(a,b,layer):
        ka,kb=uid(a),uid(b)
        if ka in segments and kb in segments:
            candidates=[]
            for ia,(s,e) in enumerate(segments[ka]):
                for ib,(t,u) in enumerate(segments[kb]):
                    for pa,pb in contacts(s,e,t,u):candidates.append((math.dist(at(s,e,pa),at(t,u,pb)),ia,ib,pa,pb))
            minimum=min(q[0] for q in candidates)
            for distance,ia,ib,pa,pb in candidates:
                if distance>minimum+1e-7:continue
                splits[ka][ia].add(pa);splits[kb][ib].add(pb)
                aa,bb=at(*segments[ka][ia],pa),at(*segments[kb][ib],pb)
                graph.add(node(a,layer,aa),node(b,layer,bb),distance,'junction')
        elif ka in segments or kb in segments:
            track,part=(a,b) if ka in segments else (b,a);key=uid(track);point=xy(part.GetPosition())
            choices=[]
            for index,(s,e) in enumerate(segments[key]):
                parameter,closest=projection(point,s,e);choices.append((math.dist(point,closest),index,parameter,closest))
            distance,index,parameter,closest=min(choices)
            splits[key][index].add(parameter)
            graph.add(node(track,layer,closest),node(part,layer,point),distance,'pad-access' if part.GetClass()=='PAD' else 'via-access')
        else:
            graph.add(node(a,layer,xy(a.GetPosition())),node(b,layer,xy(b.GetPosition())),math.dist(xy(a.GetPosition()),xy(b.GetPosition())),'junction')
    seen=set()
    for item in items:
        for other in conn.GetConnectedItems(item):
            if uid(other) not in by_id or uid(other)==uid(item):continue
            pair=tuple(sorted([uid(item),uid(other)]))
            if pair in seen:continue
            seen.add(pair)
            for layer in LAYERS:
                if item.IsOnLayer(layer) and other.IsOnLayer(layer) and pcb.SHAPE.Collide(item.GetEffectiveShape(layer),other.GetEffectiveShape(layer),0):join(item,other,layer)
    for key,parts in segments.items():
        item=by_id[key];layer=item.GetLayer()
        for (a,b),parameters in zip(parts,splits[key]):
            ordered=sorted(parameters)
            for first,last in zip(ordered,ordered[1:]):
                s,e=at(a,b,first),at(a,b,last)
                graph.add(node(item,layer,s),node(item,layer,e),math.dist(s,e),'trace',item=key,
                          net=item.GetNetname(),layer=board.GetLayerName(layer),width_mm=pcb.ToMM(item.GetWidth()),start=list(s),end=list(e))
    for ref in ['R30','R31']:
        a,b=ports[ref,'1'],ports[ref,'2'];graph.add(a,b,math.dist(a[2:],b[2:]),'series-package',reference=ref)
    output={}
    for name,pin,net,front in [('positive','3','USB_DP','D+'),('negative','2','USB_DM','D-')]:
        tvs=next(number for (ref,number),pad in pads.items() if ref=='D1' and number in ['2','3'] and pad.GetNetname()==front)
        endpoint=next(k for k,p in pads.items() if k[0]=='U1' and p.GetNetname()==net)
        length,nodes,edge_ids=graph.path(ports['J1',pin],{ports[endpoint]})
        edges=[graph.edges[i] for i in edge_ids]
        stub,_,stub_ids=graph.path(ports['D1',tvs],set(nodes))
        output[name]={'from':'J1.'+pin,'to':'.'.join(endpoint),'geometric_centerline_path_mm':length,
                      'actual_trace_centerline_mm':sum(e['length_mm'] for e in edges if e['kind']=='trace'),
                      'ESD_branch_to_main_path_mm':stub,'ESD_branch_path':[graph.edges[i] for i in stub_ids],'layers':sorted({e['layer'] for e in edges if e['kind']=='trace'}),
                      'via_count':len({e['item'] for e in edges if e['kind']=='via'}),'ordered_path':edges}
    output['geometric_path_difference_mm']=abs(output['positive']['geometric_centerline_path_mm']-output['negative']['geometric_centerline_path_mm'])
    output['status']='extracted-SI-qualification-open'
    output['source_sha256']={str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path):sha(path)}
    return output


def main():
    report={'status':'contact-aware-USB-paths-extracted','physical_verification':False,'production_approved':False,
            'variants':{name:extract(folder/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb') for name,folder in [('e73',ROOT),('raytac',ROOT/'variants/raytac')]},
            'source_sha256':{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__)),
                             'mechanical/pcb-fabrication-spec.json':sha(ROOT/'mechanical/pcb-fabrication-spec.json')},
            'limits':['Centerline geometry with pad-access/junction bridges and series-package spans, not propagation delay or impedance',
                      'Arc chord error <=0.002mm; actual current distribution within pads/junctions is not solved',
                      'C5, cable, module-internal routes and connector internals excluded',
                      'Full-speed USB eye, return continuity and differential coupling remain required']}
    (ROOT/'docs/audit/USB-signal-paths.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,data in report['variants'].items():print(name,{n:{k:v for k,v in data[n].items() if k!='ordered_path'} for n in ['positive','negative']})


if __name__=='__main__':main()
