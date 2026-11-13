"""E73 SH3 repair derived from its own source copper and frozen KiCad pattern.

Geometry is shared through the standard library. No Raytac acceptance result
or native copper is imported. PCB construction requires KiCad Python.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import uuid
from kicad_sexpr import Atom, child, children, dumps, form, loads

ROOT=Path(__file__).resolve().parents[1]
SPEC_PATH=ROOT/'hardware/e73-battery-service-spec.json'


def spec(): return json.loads(SPEC_PATH.read_text())
def digest(item): return hashlib.sha256(dumps(item).encode()).hexdigest()
def uid(tag): return str(uuid.uuid5(uuid.NAMESPACE_URL,'yeti60-e73-battery-sh3/'+tag))
def ref(f): return next(p[2] for p in children(f,'property') if p[1]=='Reference')


def new_items():
    s=spec();items=[]
    for i,v in enumerate(s['through_vias']):
        items.append(form('via',form('at',*v['position_PCB_mm']),form('size',v['land_mm']),form('drill',v['drill_mm']),
                          form('layers','F.Cu','B.Cu'),form('tenting',form('front',Atom('yes')),form('back',Atom('yes'))),
                          form('net',v['net']),form('uuid',uid('via/'+str(i)))))
    for i,r in enumerate(s['routes']):
        for j,(a,b) in enumerate(zip(r['points'],r['points'][1:])):
            items.append(form('segment',form('start',*a),form('end',*b),form('width',r['width_mm']),
                              form('layer',r['layer']),form('net',r['net']),form('uuid',uid(f'route/{i}/{j}'))))
    return items


def footprint(original):
    import pcbnew as pcb
    s=spec();source=ROOT/s['source_library']
    assert hashlib.sha256(source.read_bytes()).hexdigest()==s['source_library_sha256']
    assert [float(v) for v in child(original,'at')[1:3]]==[152,125], 'Unexpected source J2 position'
    assert {p[1]:child(p,'net')[1] for p in children(original,'pad') if p[1] in s['pin_nets']}==s['pin_nets']
    board=pcb.BOARD();part=pcb.FootprintLoad(str(source.parent),source.stem)
    assert part is not None
    part.SetFPID(pcb.LIB_ID('YAECKB',source.stem));part.SetReference('J2')
    part.SetValue(next(p[2] for p in children(original,'property') if p[1]=='Value'))
    board.Add(part);part.Flip(pcb.VECTOR2I(0,0),False);part.SetOrientationDegrees(s['orientation_deg'])
    part.SetPosition(pcb.VECTOR2I(*[pcb.FromMM(v) for v in s['position_PCB_mm']]))
    assert part.IsFlipped()
    for p in part.Pads():
        if p.GetNumber() in s['pin_nets']:
            expected=[s['position_PCB_mm'][0]+int(p.GetNumber())-2,s['position_PCB_mm'][1]+2]
            assert [pcb.ToMM(p.GetPosition().x),pcb.ToMM(p.GetPosition().y)]==expected,('Wrong SH3 flip/orientation',p.GetNumber())
    with tempfile.TemporaryDirectory(prefix='e73-sh3-template-') as directory:
        path=Path(directory)/'template.kicad_pcb';pcb.SaveBoard(str(path),board)
        result=children(loads(path.read_text()),'footprint')[0]
    def identities(node,path='template'):
        if not isinstance(node,list):return
        if node and node[0]=='uuid':node[1]=uid(path);return
        for i,n in enumerate(node):
            if isinstance(n,list):identities(n,path+'/'+str(i))
    identities(result)
    child(result,'uuid')[1]=child(original,'uuid')[1]
    old_path=child(original,'path')
    assert old_path is not None
    if child(result,'path'):result.remove(child(result,'path'))
    result.append(copy.deepcopy(old_path))
    old_pads=sorted(children(original,'pad'),key=lambda p:(p[1],float(child(p,'at')[1])))
    new_pads=sorted(children(result,'pad'),key=lambda p:(p[1],float(child(p,'at')[1])))
    assert [p[1] for p in old_pads]==[p[1] for p in new_pads]
    for old,new in zip(old_pads,new_pads):
        child(new,'uuid')[1]=child(old,'uuid')[1]
        if child(new,'net'):new.remove(child(new,'net'))
        if child(old,'net'):new.append(copy.deepcopy(child(old,'net')))
    assert result[1]==s['footprint_id']
    return result


def apply(tree):
    s=spec();old=next(f for f in children(tree,'footprint') if ref(f)=='J2')
    canonical=ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'
    assert hashlib.sha256(canonical.read_bytes()).hexdigest()==s['source_board_sha256'],'Unreviewed E73 battery repair source'
    items={child(n,'uuid')[1]:n for k in ['segment','arc','via'] for n in children(tree,k)}
    for identifier,record in s['removed_source_items'].items():
        n=items[identifier]
        assert n[0]==record['kind'] and child(n,'net')[1]==record['net'] and digest(n)==record['sha256'],('Source copper differs',identifier)
        tree.remove(n)
    arc=items[s['changed_arc']['UUID']]
    assert digest(arc)==s['changed_arc']['source_sha256'] and child(arc,'layer')[1]==s['changed_arc']['source_layer']
    child(arc,'layer')[1]=s['changed_arc']['target_layer']
    tree[tree.index(old)]=footprint(old)
    tree.extend(new_items())


def verify(board,source):
    """Check actual E73 pins, pose, standard pattern and all explicit reconnects."""
    import pcbnew as pcb
    s=spec();part=next(f for f in board.GetFootprints() if f.GetReference()=='J2')
    original=next(f for f in source.GetFootprints() if f.GetReference()=='J2')
    assert part.IsFlipped() and part.GetFPIDAsString()==s['footprint_id']
    assert part.GetPosition()==pcb.VECTOR2I(*[pcb.FromMM(v) for v in s['position_PCB_mm']])
    assert abs(part.GetOrientationDegrees()-s['orientation_deg'])<1e-6
    assert part.m_Uuid.AsString()==original.m_Uuid.AsString() and part.GetValue()==original.GetValue()
    pads=[p for p in part.Pads() if p.GetNumber() in s['pin_nets']]
    assert len(pads)==3 and len(list(part.Pads()))==5
    for p in pads:
        number=p.GetNumber();x=s['position_PCB_mm'][0]+int(number)-2;y=s['position_PCB_mm'][1]+2
        assert p.GetPosition()==pcb.VECTOR2I(pcb.FromMM(x),pcb.FromMM(y))
        assert p.GetNetname()==s['pin_nets'][number],('SH3 pin role changed',number)
        assert p.GetSize()==pcb.VECTOR2I(pcb.FromMM(.6),pcb.FromMM(1.55))
    mounts=sorted([p for p in part.Pads() if p.GetNumber()=='MP'],key=lambda p:p.GetPosition().x)
    for p,offset in zip(mounts,[-2.3,2.3]):
        assert p.GetPosition()==pcb.VECTOR2I(pcb.FromMM(s['position_PCB_mm'][0]+offset),pcb.FromMM(s['position_PCB_mm'][1]-1.875))
        assert p.GetSize()==pcb.VECTOR2I(pcb.FromMM(1.2),pcb.FromMM(1.8)) and not p.GetNetname()
    actual={t.m_Uuid.AsString():t for t in board.GetTracks()}
    assert not set(s['removed_source_items'])&set(actual)
    arc=actual[s['changed_arc']['UUID']]
    assert arc.GetNetname()==s['changed_arc']['net'] and board.GetLayerName(arc.GetLayer())==s['changed_arc']['target_layer']
    for item in new_items():
        t=actual[child(item,'uuid')[1]]
        assert t.GetNetname()==child(item,'net')[1]
        if item[0]=='via':
            assert isinstance(t,pcb.PCB_VIA) and t.GetViaType()==pcb.VIATYPE_THROUGH
            assert t.GetPosition()==pcb.VECTOR2I(*[pcb.FromMM(float(v)) for v in child(item,'at')[1:]])
            assert t.GetWidth(pcb.F_Cu)==pcb.FromMM(float(child(item,'size')[1])) and t.GetDrillValue()==pcb.FromMM(float(child(item,'drill')[1]))
        else:
            for key,getter in [('start',t.GetStart),('end',t.GetEnd)]:
                assert getter()==pcb.VECTOR2I(*[pcb.FromMM(float(v)) for v in child(item,key)[1:]])
            assert board.GetLayerName(t.GetLayer())==child(item,'layer')[1] and t.GetWidth()==pcb.FromMM(float(child(item,'width')[1]))
    return dict(header=s['header'],housing=s['housing'],pins=s['pin_nets'],position_PCB_mm=s['position_PCB_mm'],new_ordinary_through_vias=2,
                all_other_logical_nodes_preserved=True,physical_verification=False)
