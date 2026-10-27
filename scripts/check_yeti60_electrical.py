#!/usr/bin/env python3
"""Functional pin checks and conservative local power-route measurements.

Run with KiCad Python. Complements DRC; never claims SI or power-loop stability.
"""
import json,heapq,math,hashlib
from pathlib import Path
import pcbnew as pcb
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/ec60-nrf52840';PATH=BASE/'EC60-nRF52840.kicad_pcb'
b=pcb.LoadBoard(str(PATH));b.BuildConnectivity();pads={(f.GetReference(),p.GetNumber()):p for f in b.GetFootprints() for p in f.Pads()};fps={f.GetReference():f for f in b.GetFootprints()};layers=[pcb.F_Cu,pcb.In1_Cu,pcb.In2_Cu,pcb.B_Cu]
assert fps['R30'].GetValue()=='0' and fps['R31'].GetValue()=='0','nRF USB PHY contains its own series termination; external links must be 0R'
assert pads['U1','20'].GetNetname()=='ADC' and pads['U1','21'].GetNetname()=='BAT_ADC'
cache={}
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
    return {'from':'.'.join(a),'to':'.'.join(c),'net':net,'conservative_track_length_mm':round(dist[g],3),'via_count':len(vias),'min_trace_width_mm':round(min((pcb.ToMM(i.GetWidth()) for i in tracks),default=0),3)}
pairs=[(('U6','4'),('L1','1')),(('U6','2'),('L1','2')),(('U6','5'),('C43','1')),(('U6','8'),('C44','1')),(('U6','1'),('C45','1')),(('U6','1'),('C46','1')),(('U6','1'),('U6','10')),(('U5','13'),('C40','1')),(('U5','2'),('C41','1')),(('U5','10'),('C42','1'))]
measurements=[length(a,c) for a,c in pairs]
report={'status':'functional-contract-passed-layout-review-required','source_sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'checks':{'usb_series_links_0_ohm':True,'scan_adc_module_pin20_P0_04_AIN2':True,'battery_adc_module_pin21_P0_05_AIN3':True},'power_routes':measurements,'measurement_limit':'Sum of complete contacted track primitives: conservative graph-path length, not an exact geometric trace-length or loop-inductance extraction. Ground return is not included.','remaining':['No regulator transient/SPICE or capacitor-derating validation','USB pair impedance/return-path SI is deferred with signal interference analysis','Rear Type-C daughterboard and its separate CC1/CC2 5.1k resistors remain an external assembly requirement'],'sources':['https://devzone.nordicsemi.com/f/nordic-q-a/94955/resistors-for-d-and-d-','https://www.ti.com/lit/ds/symlink/tps63031.pdf','https://www.ti.com/lit/gpn/bq24074']}
(ROOT/'docs/audit/yeti60-electrical.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
