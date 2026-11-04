"""Conservative copper-item power paths; not an inductance or stability solver.

The graph follows the canonical electrical review's contacted-item method.
"""
import heapq
import math
import pcbnew as pcb


def measure_power_routes(b):
    b.BuildConnectivity()
    pads = {(f.GetReference(), p.GetNumber()): p for f in b.GetFootprints() for p in f.Pads()}
    layers = [pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu]
    cache = {}
    def length(a,c):
        start,goal=pads[a],pads[c];net=start.GetNetname();assert net==goal.GetNetname()
        if net not in cache:
            items=[p for p in pads.values() if p.GetNetname()==net]+[t for t in b.GetTracks() if t.GetNetname()==net];mapping={i.m_Uuid.AsString():n for n,i in enumerate(items)};shapes=[{l:i.GetEffectiveShape(l) for l in layers if i.IsOnLayer(l)} for i in items];adj=[[] for i in items]
            for j,i in enumerate(items):
                for k in range(j):
                    o=items[k]
                    if not i.GetBoundingBox().Intersects(o.GetBoundingBox()):continue
                    common=set(shapes[j])&set(shapes[k])
                    if any(pcb.SHAPE.Collide(shapes[j][l],shapes[k][l],0) for l in common):adj[j].append(k);adj[k].append(j)
            weights=[pcb.ToMM(i.GetLength()) if i.GetClass() in ('PCB_TRACK','PCB_ARC') else 0 for i in items];cache[net]=(items,mapping,adj,weights)
        items,mapping,adj,weights=cache[net];s=mapping[start.m_Uuid.AsString()];g=mapping[goal.m_Uuid.AsString()];q=[(0,s)];dist={s:0};prev={}
        while q:
            d,n=heapq.heappop(q)
            if d!=dist[n]:continue
            if n==g:break
            for k in adj[n]:
                nd=d+weights[k]
                if nd<dist.get(k,math.inf):dist[k]=nd;prev[k]=n;heapq.heappush(q,(nd,k))
        assert g in dist,(a,c,'No copper-item route')
        n=g;path=[]
        while n!=s:path.append(items[n]);n=prev[n]
        tracks=[i for i in path if i.GetClass()=='PCB_TRACK'];vias=[i for i in path if i.GetClass()=='PCB_VIA']
        track_layers=sorted({b.GetLayerName(i.GetLayer()) for i in tracks})
        # A contacted via can be a same-layer junction. Counting the object
        # does not imply that this route actually changes copper layers.
        return {'from':'.'.join(a),'to':'.'.join(c),'net':net,'conservative_track_length_mm':round(dist[g],3),'via_count':len(vias),'via_count_basis':'Contacted via objects, not layer transitions','track_layers':track_layers,'surface_only':track_layers==['B.Cu'],'min_trace_width_mm':round(min((pcb.ToMM(i.GetWidth()) for i in tracks),default=0),3)}
    pairs=[(('U6','4'),('L1','1')),(('U6','2'),('L1','2')),(('U6','5'),('C43','1')),(('U6','8'),('C44','1')),(('U6','1'),('C45','1')),(('U6','1'),('C46','1')),(('U6','1'),('U6','10')),(('U5','13'),('C40','1')),(('U5','2'),('C41','1')),(('U5','10'),('C42','1'))]
    return [length(a, c) for a, c in pairs]
