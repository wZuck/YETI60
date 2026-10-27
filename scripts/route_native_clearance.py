#!/usr/bin/env python3
"""Repair review-board routes against native copper/holes, then require KiCad DRC.

Uses a conservative 0.05 mm grid, exact KiCad buffered copper polygons, and
single-layer 45-degree paths. Does not alter pads, vias, footprints or rules.
Requires numpy/Pillow on KICAD_AUDIT_PYTHONPATH; run with KiCad Python.
"""
import heapq,json,math,os,sys,tempfile
from pathlib import Path
sys.path.insert(0,os.environ.get('KICAD_AUDIT_PYTHONPATH','/tmp/yaeckb-pcb-audit/python'))
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
import pcbnew as pcb
from kicad_sexpr import loads,dumps,child
from configure_single_nrf_rules import nrf_nets
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840'
PATH=BASE/'EC60-nRF52840.kicad_pcb'
board=pcb.LoadBoard(str(PATH));board.BuildConnectivity()
LAYERS=(pcb.F_Cu,pcb.In1_Cu,pcb.In2_Cu,pcb.B_Cu)
fine=set(nrf_nets());removed=set();stats=[]
STEP=.05;GUARD=.04
protected=set(json.loads((BASE/'retained-copper.json').read_text())['uuids'])
outline=pcb.SHAPE_POLY_SET()
if not board.GetBoardPolygonOutlines(outline,False):raise ValueError('Invalid board outline')

def uid(item):return item.m_Uuid.AsString()
def xy(p):return (pcb.ToMM(p.x),pcb.ToMM(p.y))
def points(chain):return [xy(chain.CPoint(n)) for n in range(chain.PointCount())]
def contours(poly):
    return [(points(poly.COutline(i)),[points(poly.CHole(i,j)) for j in range(poly.HoleCount(i))]) for i in range(poly.OutlineCount())]
def all_items():
    return [p for f in board.GetFootprints() for p in f.Pads()]+[t for t in board.GetTracks() if uid(t) not in removed]
def clearance(net):return .15 if net in fine else .2

def route(a,b,layer,net,width,margin=4):
    # Bound work and enforce the actual board edge, including gasket notches.
    xmin,ymin=min(a[0],b[0])-margin,min(a[1],b[1])-margin
    xmax,ymax=max(a[0],b[0])+margin,max(a[1],b[1])+margin
    box=board.GetBoardEdgesBoundingBox()
    xmin=max(xmin,pcb.ToMM(box.GetLeft())-1);xmax=min(xmax,pcb.ToMM(box.GetRight())+1)
    ymin=max(ymin,pcb.ToMM(box.GetTop())-1);ymax=min(ymax,pcb.ToMM(box.GetBottom())+1)
    w,h=int(math.ceil((xmax-xmin)/STEP))+1,int(math.ceil((ymax-ymin)/STEP))+1
    def pix(p):return (int(round((p[0]-xmin)/STEP)),int(round((p[1]-ymin)/STEP)))
    def polygon(image,poly,fill):
        # Composite each shape through its own mask: a polygon hole must not
        # erase copper belonging to a previously drawn, different shape.
        for outer,holes in contours(poly):
            if len(outer)<3:continue
            pts=[pix(p) for p in outer]
            left=max(0,min(p[0] for p in pts));top=max(0,min(p[1] for p in pts))
            right=min(w,max(p[0] for p in pts)+1);bottom=min(h,max(p[1] for p in pts)+1)
            if left>=right or top>=bottom:continue
            mask=Image.new('1',(right-left,bottom-top),0);md=ImageDraw.Draw(mask)
            md.polygon([(x-left,y-top) for x,y in pts],fill=1)
            for hole in holes:
                if len(hole)>2:md.polygon([(pix(p)[0]-left,pix(p)[1]-top) for p in hole],fill=0)
            image.paste(fill,(left,top),mask)
    inside=Image.new('1',(w,h),0);polygon(inside,outline,1)
    edge=math.ceil((.5+width/2+GUARD)/STEP)
    inside=inside.filter(ImageFilter.MinFilter(edge*2+1))
    obstacles=Image.new('1',(w,h),0);draw=ImageDraw.Draw(obstacles)
    roi=pcb.BOX2I(pcb.VECTOR2I(pcb.FromMM(xmin-2),pcb.FromMM(ymin-2)),pcb.VECTOR2I(pcb.FromMM(xmax-xmin+4),pcb.FromMM(ymax-ymin+4)))
    for item in all_items():
        if item.GetNetname()==net or not item.IsOnLayer(layer):continue
        bb=item.GetBoundingBox()
        if not bb.Intersects(roi):continue
        gap=max(clearance(net),clearance(item.GetNetname()))
        if item.GetClass()=='PAD' and item.GetAttribute()==pcb.PAD_ATTRIB_NPTH:gap=.85
        # Via-to-copper hole clearance can dominate a fine IO net's clearance.
        if item.GetClass()=='PCB_VIA':gap=max(gap,.25-(pcb.ToMM(item.GetWidth(layer))-pcb.ToMM(item.GetDrillValue()))/2)
        poly=pcb.SHAPE_POLY_SET()
        item.TransformShapeToPolygon(poly,layer,pcb.FromMM(gap+width/2+GUARD),pcb.FromMM(.002),pcb.ERROR_OUTSIDE)
        polygon(obstacles,poly,1)
    for fp in board.GetFootprints():
        for zone in fp.Zones():
            if zone.GetDoNotAllowTracks() and zone.GetLayerSet().Contains(layer):
                poly=pcb.SHAPE_POLY_SET(zone.Outline());poly.Inflate(pcb.FromMM(width/2+GUARD),pcb.CORNER_STRATEGY_ROUND_ALL_CORNERS,pcb.FromMM(.002));polygon(obstacles,poly,1)
    blocked=np.logical_or(np.asarray(obstacles,dtype=bool),~np.asarray(inside,dtype=bool))
    sx,sy=pix(a);tx,ty=pix(b)
    if not(0<=sx<w and 0<=sy<h and 0<=tx<w and 0<=ty<h):return None
    if blocked[sy,sx] or blocked[ty,tx]:return None
    start=sy*w+sx;goal=ty*w+tx
    dist=np.full(w*h,np.inf,dtype=np.float32);prev=np.full(w*h,-1,dtype=np.int8);dist[start]=0
    moves=((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1))
    def heuristic(x,y):
        dx,dy=abs(x-tx),abs(y-ty);return max(dx,dy)+.41421356*min(dx,dy)
    queue=[(heuristic(sx,sy),0,start)];found=False;count=0
    while queue:
        _,g,node=heapq.heappop(queue)
        if g>float(dist[node])+.001:continue
        if node==goal:found=True;break
        y,x=divmod(node,w);count+=1
        if count>1800000:break
        for k,(dx,dy) in enumerate(moves):
            nx,ny=x+dx,y+dy
            if not(0<=nx<w and 0<=ny<h) or blocked[ny,nx]:continue
            if dx and dy and (blocked[y,nx] or blocked[ny,x]):continue
            nn=ny*w+nx;ng=g+(1.41421356 if dx and dy else 1)
            if ng+.001<float(dist[nn]):
                dist[nn]=ng;prev[nn]=k;heapq.heappush(queue,(ng+heuristic(nx,ny),ng,nn))
    if not found:return None
    path=[];node=goal
    while node!=start:
        y,x=divmod(node,w);path.append((x,y));k=int(prev[node]);dx,dy=moves[k];node-=dy*w+dx
    path.append((sx,sy));path.reverse()
    simple=[path[0]]
    for i in range(1,len(path)-1):
        if (path[i][0]-path[i-1][0],path[i][1]-path[i-1][1])!=(path[i+1][0]-path[i][0],path[i+1][1]-path[i][1]):simple.append(path[i])
    if path[-1]!=simple[-1]:simple.append(path[-1])
    result=[a]+[(xmin+x*STEP,ymin+y*STEP) for x,y in simple]+[b]
    return [p for n,p in enumerate(result) if n==0 or math.dist(p,result[n-1])>.00001]

def add_path(path,layer,net,width):
    for a,b in zip(path,path[1:]):
        t=pcb.PCB_TRACK(board);t.SetStart(pcb.VECTOR2I(pcb.FromMM(a[0]),pcb.FromMM(a[1])));t.SetEnd(pcb.VECTOR2I(pcb.FromMM(b[0]),pcb.FromMM(b[1])));t.SetLayer(layer);t.SetWidth(pcb.FromMM(width));t.SetNet(board.FindNet(net));board.Add(t)

def components(item):
    conn=board.GetConnectivity();mapping={uid(i):i for i in all_items()};seen=set();todo=[item];result=[]
    while todo:
        current=todo.pop();key=uid(current)
        if key in seen or key in removed:continue
        seen.add(key)
        if key in mapping:result.append(mapping[key])
        for other in conn.GetConnectedItems(current):
            if other.GetNetCode()==item.GetNetCode() and uid(other) in mapping:todo.append(mapping[uid(other)])
    return result

def anchors(items):
    result=[]
    for item in items:
        pts=[xy(item.GetPosition())] if item.GetClass() in ('PAD','PCB_VIA') else [xy(item.GetStart()),xy(item.GetEnd())]
        for layer in LAYERS:
            if item.IsOnLayer(layer):result.extend((p,layer) for p in pts)
    return list(set(result))

if __name__=='__main__':
    report=json.loads((BASE/'DRC-routed.json').read_text());mode=sys.argv[1] if len(sys.argv)>1 else 'errors'
    if mode=='errors':
        selected={}
        current={uid(i):i for i in all_items()}
        for violation in report['violations']:
            if violation['severity']!='error':continue
            candidates=[current[i['uuid']] for i in violation['items'] if i['uuid'] in current and i['uuid'] not in protected and current[i['uuid']].GetClass()=='PCB_TRACK']
            if candidates:
                t=min(candidates,key=lambda t:t.GetLength());selected[uid(t)]=t
        for key,t in selected.items():
            removed.add(key);net=t.GetNetname();width=pcb.ToMM(t.GetWidth());a,b=xy(t.GetStart()),xy(t.GetEnd())
            path=route(a,b,t.GetLayer(),net,width)
            if path:
                add_path(path,t.GetLayer(),net,width);stats.append({'net':net,'operation':'clearance-repair','segments':len(path)-1});print('REPAIRED',net,len(path)-1,flush=True)
            else:removed.remove(key);print('NO LOCAL PATH',net,flush=True)
    else:
        for violation in report['unconnected_items']:
            board.BuildConnectivity();mapping={uid(i):i for i in all_items()};aa,bb=violation['items']
            a,b=mapping.get(aa['uuid']),mapping.get(bb['uuid'])
            if a is None or b is None:
                if a is None and b is not None and b.GetNetname()=='GND':a,b=b,a
                if a is not None and a.GetNetname()=='GND':
                    options=[t for t in board.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND']
                    b=min(options,key=lambda t:math.dist(xy(a.GetPosition()),xy(t.GetPosition())))
                else:continue
            net=a.GetNetname();ca=components(a);cb=components(b)
            if {uid(i) for i in ca}&{uid(i) for i in cb}:continue
            ac,bc=anchors(ca),anchors(cb)
            choices=sorted(((math.dist(pa,pb),pa,pb,la) for pa,la in ac for pb,lb in bc if la==lb),key=lambda x:x[0])
            width=.127 if net in fine else .2;success=False;tried=set()
            for _,pa,pb,layer in choices:
                if layer in tried:continue
                tried.add(layer)
                if net in ('BUCK_L1','BUCK_L2') and layer!=pcb.B_Cu:continue
                path=route(pa,pb,layer,net,width,margin=6)
                if path:
                    add_path(path,layer,net,width);stats.append({'net':net,'operation':'complete-connection','layer':pcb.LayerName(layer),'segments':len(path)-1});print('CONNECTED',net,pcb.LayerName(layer),len(path)-1,flush=True);success=True;break
            if not success:print('NO PATH',net,flush=True)

    with tempfile.TemporaryDirectory(prefix='yaeckb-native-routes-') as folder:
        tmp=Path(folder)/'board.kicad_pcb';pcb.SaveBoard(str(tmp),board,True)
        doc=loads(tmp.read_text());doc[:]=[v for v in doc if not(isinstance(v,list) and v[0] in ('segment','arc','via') and str(child(v,'uuid')[1]) in removed)]
        tmp.write_text(dumps(doc)+'\n');board=pcb.LoadBoard(str(tmp))
    board.BuildConnectivity();pcb.ZONE_FILLER(board).Fill(board.Zones());pcb.SaveBoard(str(PATH),board,True)
    (BASE/('native-routing-'+mode+'.json')).write_text(json.dumps({'changes':stats,'removed_routes':sorted(removed),'requires_native_DRC':True},indent=2)+'\n')
