#!/usr/bin/env python3
"""Native-copper constrained four-layer repair; always follow with native DRC.

Run using KiCad Python. Compiles route_search.cpp into a temporary cache
with clang++, or uses the executable specified by KICAD_ROUTE_SEARCH.
"""
import sys,os,math,struct,subprocess,tempfile,json
from pathlib import Path
import route_native_clearance as r
from route_native_clearance import pcb,np,Image,ImageDraw,ImageFilter
B=r.board; STEP=.05
EXE=os.environ.get('KICAD_ROUTE_SEARCH')
if not EXE:
    import hashlib
    source=Path(__file__).with_name('route_search.cpp')
    EXE=str(Path(tempfile.gettempdir())/('yaeckb-route-search-'+hashlib.sha256(source.read_bytes()).hexdigest()[:12]))
    if not Path(EXE).exists():subprocess.run(['clang++','-O3',str(source),'-o',EXE],check=True)
def search(ca,cb,net,width,margin=5):
    # Larger connected copper is the multi-source side.
    if len(ca)<len(cb):ca,cb=cb,ca
    pts=[p for c in (ca,cb) for p,l in r.anchors(c)]
    xmin=math.floor((min(p[0] for p in pts)-margin)/STEP)*STEP;ymin=math.floor((min(p[1] for p in pts)-margin)/STEP)*STEP
    xmax=max(p[0] for p in pts)+margin;ymax=max(p[1] for p in pts)+margin
    w=math.ceil((xmax-xmin)/STEP)+1;h=math.ceil((ymax-ymin)/STEP)+1
    def pix(p):return (round((p[0]-xmin)/STEP),round((p[1]-ymin)/STEP))
    def paint(im,poly):
        for outer,holes in r.contours(poly):
            if len(outer)<3:continue
            ps=[pix(p) for p in outer];left=max(0,min(x for x,y in ps));top=max(0,min(y for x,y in ps));right=min(w,max(x for x,y in ps)+1);bottom=min(h,max(y for x,y in ps)+1)
            if left>=right or top>=bottom:continue
            mask=Image.new('1',(right-left,bottom-top));d=ImageDraw.Draw(mask);d.polygon([(x-left,y-top) for x,y in ps],fill=1)
            for hole in holes:
                if len(hole)>2:d.polygon([(pix(p)[0]-left,pix(p)[1]-top) for p in hole],fill=0)
            im.paste(1,(left,top),mask)
    def shape(im,item,layer,grow):
        poly=pcb.SHAPE_POLY_SET();item.TransformShapeToPolygon(poly,layer,pcb.FromMM(grow),pcb.FromMM(.003),pcb.ERROR_OUTSIDE);paint(im,poly)
    inside=Image.new('1',(w,h));paint(inside,r.outline)
    edge_cache={}
    def edge(radius):
        if radius not in edge_cache:
            poly=pcb.SHAPE_POLY_SET(r.outline);poly.Inflate(-pcb.FromMM(.5+radius+.04),pcb.CORNER_STRATEGY_ROUND_ALL_CORNERS,pcb.FromMM(.003))
            im=Image.new('1',(w,h));paint(im,poly);edge_cache[radius]=~np.asarray(im,dtype=bool)
        return edge_cache[radius]
    flags=np.zeros((4,h,w),dtype=np.uint8);via_bad=edge(.25)
    roi=pcb.BOX2I(pcb.VECTOR2I(pcb.FromMM(xmin-2),pcb.FromMM(ymin-2)),pcb.VECTOR2I(pcb.FromMM(xmax-xmin+4),pcb.FromMM(ymax-ymin+4)))
    items=[i for i in r.all_items() if i.GetBoundingBox().Intersects(roi)]
    for z,layer in enumerate(r.LAYERS):
        obs=Image.new('1',(w,h));vobs=Image.new('1',(w,h))
        for i in items:
            if not i.IsOnLayer(layer):continue
            same=i.GetNetname()==net;gap=max(r.clearance(net),r.clearance(i.GetNetname()))
            if i.GetClass()=='PAD' and i.GetAttribute()==pcb.PAD_ATTRIB_NPTH:gap=.85
            if i.GetClass()=='PCB_VIA':gap=max(gap,.25-(pcb.ToMM(i.GetWidth(layer))-pcb.ToMM(i.GetDrillValue()))/2)
            if not same:
                shape(obs,i,layer,gap+width/2+.01);shape(vobs,i,layer,max(.25+gap,.4)+.01)
            if i.GetClass()=='PAD' and i.GetAttribute()==pcb.PAD_ATTRIB_SMD:shape(vobs,i,layer,.34)
        for fp in B.GetFootprints():
            for zone in fp.Zones():
                if zone.GetLayerSet().Contains(layer):
                    for im,ban,grow in ((obs,zone.GetDoNotAllowTracks(),width/2+.01),(vobs,zone.GetDoNotAllowVias(),.26)):
                        if ban:
                            poly=pcb.SHAPE_POLY_SET(zone.Outline());poly.Inflate(pcb.FromMM(grow),pcb.CORNER_STRATEGY_ROUND_ALL_CORNERS,pcb.FromMM(.003));paint(im,poly)
        flags[z][np.asarray(obs,dtype=bool)|edge(width/2)]|=1
        via_bad|=np.asarray(vobs,dtype=bool)
        for group,bit in ((ca,4),(cb,8)):
            contact=Image.new('1',(w,h))
            for i in group:
                if i.IsOnLayer(layer):shape(contact,i,layer,max(0,width/2-.046))
            flags[z][np.asarray(contact,dtype=bool)]|=bit
    flags[:,via_bad]|=2
    print('SEARCH',net,w,h,'contacts',int(np.count_nonzero((flags&5)==4)),int(np.count_nonzero((flags&9)==8)),flush=True)
    with tempfile.TemporaryDirectory() as folder:
        ip=Path(folder)/'in';op=Path(folder)/'out';ip.write_bytes(struct.pack('III',w,h,4)+flags.tobytes())
        result=subprocess.run([EXE,str(ip),str(op)])
        if result.returncode:
            np.savez('/tmp/yaeckb-pcb-repair/failed-'+net.replace('/','_'),flags=flags,xmin=xmin,ymin=ymin,step=STEP)
            return False
        nodes=np.frombuffer(op.read_bytes(),dtype=np.uint32)
    path=[(int(n%w),int((n%(w*h))//w),int(n//(w*h))) for n in nodes]
    def physical(p):return (xmin+p[0]*STEP,ymin+p[1]*STEP)
    start=0;segments=0;vias=[]
    for j in range(1,len(path)):
        if path[j][2]!=path[j-1][2]:
            if j-1>start:r.add_path([physical(path[start]),physical(path[j-1])],r.LAYERS[path[start][2]],net,width);segments+=1
            p=physical(path[j]);v=pcb.PCB_VIA(B);v.SetPosition(pcb.VECTOR2I(pcb.FromMM(p[0]),pcb.FromMM(p[1])));v.SetWidth(pcb.FromMM(.5));v.SetDrill(pcb.FromMM(.3));v.SetViaType(pcb.VIATYPE_THROUGH);v.SetLayerPair(pcb.F_Cu,pcb.B_Cu);v.SetNet(B.FindNet(net));B.Add(v);vias.append(p);start=j
        elif j==len(path)-1 or (path[j][0]-path[j-1][0],path[j][1]-path[j-1][1])!=(path[j+1][0]-path[j][0],path[j+1][1]-path[j][1]) or path[j+1][2]!=path[j][2]:
            if j>start:r.add_path([physical(path[start]),physical(path[j])],r.LAYERS[path[start][2]],net,width);segments+=1
            start=j
    # End each route on the actual pad/via center or finite track centerline.
    # Merely touching copper at a raster cap can leave a native dangling-end
    # warning and makes whole-segment tail removal unsafe at a T connection.
    def landing(group,point,layer):
        options=[]
        for item in group:
            if not item.IsOnLayer(layer):continue
            if item.GetClass() in ('PAD','PCB_VIA'):q=r.xy(item.GetPosition())
            elif item.GetClass()=='PCB_TRACK':
                a,c=r.xy(item.GetStart()),r.xy(item.GetEnd());dx,dy=c[0]-a[0],c[1]-a[1];den=dx*dx+dy*dy
                t=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/den)) if den else 0
                q=(a[0]+t*dx,a[1]+t*dy)
            else:continue
            options.append((math.dist(q,point),q))
        return min(options)[1]
    for group,pnt in ((ca,path[0]),(cb,path[-1])):
        point=physical(pnt);layer=r.LAYERS[pnt[2]];q=landing(group,point,layer)
        if math.dist(q,point)>.000001:r.add_path([q,point],layer,net,width);segments+=1
    print('ROUTED',net,segments,'segments',len(vias),'vias',flush=True);return True

def groups():
    B.BuildConnectivity();by={};seen=set();conn=B.GetConnectivity()
    mapping={r.uid(i):i for i in r.all_items()}
    for fp in B.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNetname() or pad.GetNetname()=='GND' or r.uid(pad) in seen:continue
            c=[];todo=[pad]
            while todo:
                i=todo.pop();key=r.uid(i)
                if key in seen:continue
                seen.add(key);c.append(i)
                for o in conn.GetConnectedItems(i):
                    k=r.uid(o)
                    if o.GetNetCode()==pad.GetNetCode() and k in mapping and k not in seen:todo.append(mapping[k])
            by.setdefault(pad.GetNetname(),[]).append(c)
    return {n:g for n,g in by.items() if len(g)>1}
def save():
    B.BuildConnectivity();pcb.ZONE_FILLER(B).Fill(B.Zones());pcb.SaveBoard(str(r.PATH),B,True)
if __name__=='__main__':
    selected=set(sys.argv[1:]);fail=[]
    for net in list(groups()):
        if selected and net not in selected:continue
        if net in ('BUCK_L1','BUCK_L2'):continue
        for attempt in range(8):
            gs=groups().get(net,[])
            if len(gs)<2:break
            ca,cb=min(((a,b) for j,a in enumerate(gs) for b in gs[j+1:]),key=lambda ab:min(math.dist(p,q) for p,l in r.anchors(ab[0]) for q,k in r.anchors(ab[1])))
            if not search(ca,cb,net,.2 if net in ('+3.3V','USB_5V','BAT_CELL','VSYS') else .127):print('NO PATH',net,flush=True);fail.append(net);break
            save()
    save();print('REMAINING',list(groups()),flush=True)
