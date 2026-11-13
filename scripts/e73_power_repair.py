"""Replay frozen common-part power geometry, then verify the actual E73 PCB.

The immutable reference supplies geometry, not another variant's acceptance.
The existing E73 battery routes, USB ingress, sensor lands and MCU stay local.
"""
import copy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess
from kicad_sexpr import child, children, dumps, loads, symbol_pins

ROOT=Path(__file__).resolve().parents[1]
SPEC_PATH=ROOT/'hardware/e73-power-repair-spec.json'


def spec():return json.loads(SPEC_PATH.read_text())
def ref(f):return next(p[2] for p in children(f,'property') if p[1]=='Reference')
def sha(data):return hashlib.sha256(data).hexdigest()
def items(tree):return {child(n,'uuid')[1]:n for k in ['segment','arc','via'] for n in children(tree,k)}


@lru_cache(None)
def reference_bytes(path):
    s=spec();data=subprocess.check_output(['git','show',s['reference_commit']+':'+path],cwd=ROOT)
    expected=s['reference_board_sha256'] if path==s['reference_board'] else s['reference_files'][path]
    assert sha(data)==expected,('Frozen reference differs',path)
    return data


def expected_footprints():
    s=spec();tree=loads(reference_bytes(s['reference_board']).decode());parts={ref(f):f for f in children(tree,'footprint')}
    comparison_bytes=subprocess.check_output(['git','show',s['reference_commit']+':'+s['comparison_board']],cwd=ROOT)
    assert sha(comparison_bytes)==s['comparison_board_sha256']
    comparison={ref(f):f for f in children(loads(comparison_bytes.decode()),'footprint')}
    result={}
    for name,data in s['parts'].items():
        f=copy.deepcopy(comparison[name] if data.get('reference_source')=='comparison_board' else parts[name]);angle=float(child(f,'at')[3]) if len(child(f,'at'))>3 else 0
        for p in children(f,'pad'):
            at=child(p,'at')
            if len(at)>3:at[3]=float(at[3])-angle+data['position_PCB_mm'][2]
        child(f,'at')[1:]=data['position_PCB_mm']
        next(p for p in children(f,'property') if p[1]=='Value')[2]=data['value']
        assert f[1]==data['footprint_id']
        # C32 keeps its E73 90-degree orientation and position; the other
        # common-part poses are the frozen local power-stage recipe.
        result[name]=f
    return result


def install_libraries(output):
    s=spec()
    for name,data in s['parts'].items():
        target=output/'YAECKB.pretty'/Path(data['library']).name
        target.write_bytes(reference_bytes(data['library']))
    for path in s['reference_files']:
        if '/models/' in path:
            target=output/'models'/Path(path).name;target.parent.mkdir(exist_ok=True)
            target.write_bytes(reference_bytes(path))


def apply(tree):
    s=spec();source=ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'
    assert sha(source.read_bytes())==s['source_E73_board_sha256'],'Unreviewed E73 power source'
    actual=items(tree)
    for identifier,record in s['retired_source_copper'].items():
        n=actual[identifier]
        assert sha(dumps(n).encode())==record['sha256'] and child(n,'net')[1]==record['net'],('Changed power source primitive',identifier)
        tree.remove(n)
    reference=loads(reference_bytes(s['reference_board']).decode());after=items(reference)
    tree.extend(copy.deepcopy(after[i]) for i in s['reference_copper_UUIDs'])
    keepout=next(z for z in children(reference,'zone') if child(z,'uuid')[1]==s['reference_keepout_UUID'])
    tree.append(copy.deepcopy(keepout))
    old={ref(f):f for f in children(tree,'footprint')}
    for name,f in expected_footprints().items():
        previous=old[name]
        assert child(previous,'uuid')==child(f,'uuid') and child(previous,'path')==child(f,'path'),('Changed power instance',name)
        role=lambda g:sorted((p[1],child(p,'net')[1] if child(p,'net') else None) for p in children(g,'pad') if p[1])
        assert role(previous)==role(f),('Changed numbered power pin roles',name)
        tree[tree.index(previous)]=f


def update_schematic(tree):
    for symbol in children(tree,'symbol'):
        name=ref(symbol)
        if name not in spec()['parts']:continue
        data=spec()['parts'][name]
        for field,value in [('Value',data['value']),('Footprint',data['footprint_id'])]:
            next(p for p in children(symbol,'property') if p[1]==field)[2]=value
        if name=='F1':
            cache=child(tree,'lib_symbols');old=next(s for s in children(cache,'symbol') if s[1]==child(symbol,'lib_id')[1])
            reference=loads(reference_bytes(spec()['reference_schematic']).decode())
            fuse=next(s for s in children(child(reference,'lib_symbols'),'symbol') if s[1]=='YAECKB:Fuse')
            assert {k:v['at'] for k,v in symbol_pins(old).items()}=={k:v['at'] for k,v in symbol_pins(fuse).items()},'F1 symbol would move electrical endpoints'
            if not any(s[1]=='YAECKB:Fuse' for s in children(cache,'symbol')):cache.append(copy.deepcopy(fuse))
            child(symbol,'lib_id')[1]='YAECKB:Fuse'
            cache[:]=[v for v in cache if not (isinstance(v,list) and v[0]=='symbol' and v[1]=='YAECKB:Polyfuse')]
            next(p for p in children(symbol,'property') if p[1]=='Datasheet')[2]=spec()['sources']['F1']


def update_symbol_library(tree):
    reference=loads(reference_bytes(spec()['reference_symbols']).decode())
    fuse=next(s for s in children(reference,'symbol') if s[1]=='Fuse')
    tree[:]=[v for v in tree if not (isinstance(v,list) and v[0]=='symbol' and v[1]=='Polyfuse')]
    if not any(s[1]=='Fuse' for s in children(tree,'symbol')):tree.append(copy.deepcopy(fuse))


def update_components(parts):
    s=spec();source=json.loads(reference_bytes(s['reference_components']))
    for name,data in s['parts'].items():
        assert parts[name]['pins']==source[name]['pins'],'Power component roles differ'
        parts[name]['value']=data['value'];parts[name]['footprint']=data['footprint_id']
        parts[name]['symbol']=source[name]['symbol'];parts[name]['datasheet']=source[name]['datasheet']


def purchase_rows(rows,fields,zh):
    """Split unallocated rows so changed package/value/height limits stay local."""
    s=spec();result=[]
    for row in rows:
        refs=[r.strip() for r in row[fields[0]].split(',')]
        if not set(refs)&set(s['parts']):result.append(row);continue
        assert int(row[fields[2]])==0,'Reassess inventory allocation before changing a stocked power group'
        for name in refs:
            r=dict(row);r[fields[0]]=name;r[fields[1]]='1';r[fields[3]]='1'
            if name in s['parts']:
                d=s['parts'][name];r[fields[4]]=d['value'];r[fields[5]]=d['footprint_id'].split(':')[-1].split('__')[0]
                if name=='L1':r[fields[5]]='WE-MAPI 3020, 3.0 x 3.0 x 2.0 mm';r[fields[7]]='Wuerth 74438336015'
                if name=='F1':r[fields[7]]='Littelfuse 0466001.NRHF'+('（1 A 快断、不可恢复）' if zh else ' (1 A fast, not resettable)')
                if name in s['capacitors']:
                    c=s['capacitors'][name]
                    package='0603' if name=='C32' else '0805'
                    note=(f'普通 {package}，{c["dielectric"][0]}／{c["dielectric"][1]}；在 {c["bias_V"]:g} V 偏压且计入容差、温度和老化后，有效容量须至少 {c["effective_target_uF"]:g} uF；仅标称容量不能验收。' if zh else
                          f'{package} X5R/X7R; require effective capacitance >= {c["effective_target_uF"]:g} uF at {c["bias_V"]:g} V including tolerance/temperature/aging; nominal value alone is insufficient.')
                    r[fields[-1]]+=('；' if zh else '; ')+note
            result.append(r)
    return result


def verify(board,source):
    """Geometry proof against frozen parts/copper; native graph/DRC is separate."""
    s=spec();parts={ref(f):f for f in children(board,'footprint')};before={ref(f):f for f in children(source,'footprint')}
    def body(f):
        # Version/UUID formatting is serializer metadata; every actual pad,
        # mask/paste rectangle and model/graphics datum remains in the check.
        def canonical(v):
            if not isinstance(v,list):
                try:return round(float(v),9)
                except (ValueError,TypeError):return str(v)
            if v and v[0] in ['uuid','tstamp','version']:return None
            out = [q for n in v if (q:=canonical(n)) is not None]
            # KiCad omits zero pad/footprint angles and writes filled graphics
            # as yes. Both forms retain identical manufacturing geometry.
            if out and out[0] == 'at' and len(out) == 3:out.append(0.0)
            if out == ['fill','solid']:out = ['fill','yes']
            # S-expression sibling serialization order has no geometric role;
            # preserve ordered coordinate lists and every duplicate child.
            if out and out[0] in ['footprint','pad','zone','segment','arc','via']:
                scalars = [n for n in out if not isinstance(n,list)]
                nodes = sorted((n for n in out if isinstance(n,list)),key=repr)
                return scalars+nodes
            return out
        return canonical(f)
    for name,expected in expected_footprints().items():
        actual=parts[name]
        # KiCad may add default empty description fields when saving. Those
        # are permitted only if absent in the immutable geometry template.
        actual=copy.deepcopy(actual)
        for p in list(children(actual,'property')):
            if p[1] in ['Description','Datasheet'] and not p[2] and not any(q[1]==p[1] for q in children(expected,'property')):actual.remove(p)
        assert body(actual)==body(expected),('Power footprint/paste/mask/model differs',name)
        assert child(before[name],'uuid')==child(parts[name],'uuid')
    actual=items(board);target=items(loads(reference_bytes(s['reference_board']).decode()))
    for identifier in s['reference_copper_UUIDs']:
        assert body(actual[identifier])==body(target[identifier]),('Power copper differs',identifier)
    for identifier in set(s['retired_source_copper'])-set(s['reference_copper_UUIDs']):assert identifier not in actual
    zone=next(z for z in children(board,'zone') if child(z,'uuid')[1]==s['reference_keepout_UUID'])
    expected=next(z for z in children(loads(reference_bytes(s['reference_board']).decode()),'zone') if child(z,'uuid')[1]==s['reference_keepout_UUID'])
    assert body(zone)==body(expected),'Changed inductor inter-land keepout'
    return dict(parts=sorted(s['parts']),retired_or_replaced_source_items=len(s['retired_source_copper']),frozen_target_items=len(s['reference_copper_UUIDs']),
                physical_verification=False,manufacturing_released=False,reference_commit=s['reference_commit'])
