#!/usr/bin/env python3
"""Remove conflicting inherited routes using a current DRC report; export DSN.

Never removes pads, board edges, electrodes or schematic connections. Run using
KiCad Python, passing the DRC JSON of the current unrouted board as argv[1].
"""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import uuid
import pcbnew as pcb
from kicad_sexpr import Atom as A, loads, dumps, child, children, form as F
from configure_single_nrf_rules import nrf_nets

BASE = Path(__file__).resolve().parents[1] / 'hardware/ec60-nrf52840'
NAME = 'EC60-nRF52840'
path = BASE / (NAME + '.unrouted.kicad_pcb')
report = json.loads(Path(sys.argv[1]).read_text())
bad = {i['uuid'] for v in report['violations'] if v['severity'] == 'error' for i in v['items']}
source = loads(path.read_text())
for fp in children(source, 'footprint'):
    if str(fp[1]).startswith('YAECKB:ecs_pad_'):
        for zone in children(fp, 'zone'):
            keepout = child(zone, 'keepout')
            if keepout:
                for kind in ('tracks', 'vias', 'pads'):
                    if child(keepout, kind)[1] != 'allowed':
                        raise ValueError('Electrode has an actual routing exclusion: ' + str(fp[1]))
removed = [item for item in source[1:] if isinstance(item, list) and item[0] in ('segment','arc','via')
           and child(item, 'uuid') and child(item, 'uuid')[1] in bad]
source[:] = [item for item in source if not any(item is r for r in removed)]
path.write_text(dumps(source) + '\n')
# Give the router a fine approximation of arcs. Native Specctra export uses
# coarse chords that can both invent collisions and miss the actual copper.
routing=[]
for item in source:
    if not isinstance(item,list) or item[0]!='arc':
        routing.append(item)
        continue
    (ax,ay),(bx,by),(cx,cy)=[tuple(float(v) for v in child(item,k)[1:]) for k in ('start','mid','end')]
    det=2*(ax*(by-cy)+bx*(cy-ay)+cx*(ay-by))
    if abs(det)<1e-12:raise ValueError('Degenerate retained arc')
    aa,bb,cc=ax*ax+ay*ay,bx*bx+by*by,cx*cx+cy*cy
    ox=(aa*(by-cy)+bb*(cy-ay)+cc*(ay-by))/det
    oy=(aa*(cx-bx)+bb*(ax-cx)+cc*(bx-ax))/det
    radius=math.hypot(ax-ox,ay-oy)
    start,mid,end=[math.atan2(y-oy,x-ox) for x,y in ((ax,ay),(bx,by),(cx,cy))]
    turn=(end-start)%(2*math.pi)
    if (mid-start)%(2*math.pi)>turn:turn-=2*math.pi
    count=max(2,math.ceil(abs(turn)/(2*math.acos(max(-1,1-.001/radius)))))
    points=[(round(ox+radius*math.cos(start+turn*n/count),6),round(oy+radius*math.sin(start+turn*n/count),6)) for n in range(count+1)]
    points[0],points[-1]=(ax,ay),(cx,cy)
    for n,(a,b) in enumerate(zip(points,points[1:])):
        routing.append(F('segment',F('start',*a),F('end',*b),copy.deepcopy(child(item,'width')),
                         copy.deepcopy(child(item,'layer')),copy.deepcopy(child(item,'net')),
                         F('uuid',str(uuid.uuid5(uuid.NAMESPACE_URL,str(child(item,'uuid')[1])+'/dsn/'+str(n))))))
with tempfile.TemporaryDirectory(prefix='yaeckb-dsn-arcs-') as folder:
    fine=Path(folder)/'routing.kicad_pcb'
    fine.write_text(dumps(routing)+'\n')
    board = pcb.LoadBoard(str(fine))
for zone in list(board.Zones()):
    if not zone.GetIsRuleArea(): board.Remove(zone)
dsn = BASE / (NAME + '.dsn')
assert pcb.ExportSpecctraDSN(board, str(dsn))
s = dsn.read_text().replace('(string_quote ")', '')
x = loads(s)
for padstack in children(child(x,'library'),'padstack'):
    # HOLE_M2 uses a 2.2mm NPTH with a local 0.85mm copper clearance. The
    # Specctra padstack loses this override; inflate only its routing obstacle.
    if str(padstack[1])=='Round[A]Pad_2200.000000_um':
        for shape in children(padstack,'shape'):
            circle=child(shape,'circle')
            if circle:circle[2]=3700
# KiCad's Specctra export turns EC electrode copper-pour-only exclusions into
# generic keepouts. Their native rules explicitly ALLOW tracks/vias/pads, so
# removing these routing-only keepouts restores the original rule semantics.
# Actual copper pour exclusions stay in the KiCad board; module antenna rules
# and all other library-image keepouts remain unchanged.
for image in children(child(x, 'library'), 'image'):
    if str(image[1]).startswith('YAECKB:ecs_pad_'):
        image[:] = [v for v in image if not (isinstance(v, list) and v and v[0] == 'keepout')]
network = child(x, 'network')
original = children(network, 'class')[0]
original.remove(A('GND'))
plane = F('class', A('GND_PLANE'), A('GND'), *[copy.deepcopy(v) for v in original if isinstance(v,list)])
network.append(plane)
for rules in [child(child(x,'structure'),'rule')]+[child(c,'rule') for c in children(network,'class')]:
    if rules:
        for clearance in children(rules,'clearance'):
            if len(clearance)==2:clearance[1]=200
fine_nets=nrf_nets()
original[:]=[v for v in original if isinstance(v,list) or str(v) not in fine_nets]
via_name='Via[0-3]_500:300_um'
library=child(x,'library')
template=next(p for p in children(library,'padstack') if str(p[1])=='Via[0-3]_600:300_um')
small=copy.deepcopy(template);small[1]=via_name
for shape in children(small,'shape'):
    circle=child(shape,'circle')
    if circle:circle[2]=500
library.append(small)
child(child(x,'structure'),'via').append(via_name)
network.append(F('class',A('NRF_IO'),*fine_nets,
    F('circuit',F('use_via',via_name)),F('rule',F('width',127),F('clearance',150))))
# Restore Specctra's nonstandard quote declaration after using the KiCad parser.
child(x, 'parser').insert(1, F('string_quote', A('"')))
dsn.write_text(dumps(x) + '\n')
print('Removed',len(removed),'conflicting inherited tracks/vias; exported DSN with GND_PLANE class')
