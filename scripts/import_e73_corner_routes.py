#!/usr/bin/env python3
"""Extract new router copper without replacing native retained PCB geometry.

Run with the CAD runtime after a completed SES job. KiCad imports the session
into a disposable copy; classification uses actual native copper, not UUIDs
invented by the router. The output is an explicit replayable route patch.
Native DRC, reference and whole-board verification remain mandatory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import make_valid
from kicad_sexpr import child, children, dumps, loads, form, Atom

ROOT = Path(__file__).resolve().parents[1]
NATIVE = '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=Path,required=True)
    parser.add_argument('--output',type=Path,help='Patch output; defaults to the candidate route patch')
    parser.add_argument('--job-dir',type=Path,help='Directory containing hash-verified frozen routing inputs')
    parser.add_argument('--base',type=Path,help='Frozen placed PCB for an already running historical job')
    parser.add_argument('--spec-snapshot',type=Path,help='Frozen job specification; its recorded hash must match')
    args = parser.parse_args()
    session = args.session.resolve()
    work = ROOT/'.assembly-work/e73-corner'
    spec_path = ROOT/'hardware/e73-corner-spec.json'
    s = json.loads(spec_path.read_text())
    base = args.base.resolve() if args.base else ROOT/s['output_directory']/'EC60-nRF52840.kicad_pcb'
    sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    job_dir = args.job_dir.resolve() if args.job_dir else work
    input_path = job_dir/'routing-input.json'
    if args.job_dir and not args.base:
        base=job_dir/'EC60-nRF52840.kicad_pcb'
    inputs = json.loads(input_path.read_text())
    for name,digest in inputs['source_sha256'].items():
        input_file = job_dir/Path(name).name if args.job_dir else ROOT/name
        if name == s['output_directory']+'/EC60-nRF52840.kicad_pcb' and args.base:input_file=base
        if name == 'hardware/e73-corner-spec.json' and args.spec_snapshot:input_file=args.spec_snapshot.resolve()
        assert sha(input_file)==digest,('Stale router source',name)
    for name,digest in inputs['outputs'].items():
        input_file=job_dir/Path(name).name if args.job_dir else ROOT/name
        assert sha(input_file)==digest,('Changed router input',name)
    assert session.is_file() and session.stat().st_size>100
    imported = work/'imported-session.kicad_pcb'
    geometry = work/'route-comparison.json'
    code = '''import sys,json
from pathlib import Path
import pcbnew as p
sys.path.insert(0,str(Path.cwd()/'scripts'))
from export_e73_usb_ground import polygons
base,session,target,geometry=sys.argv[1:]
a=p.LoadBoard(base);b=p.LoadBoard(base)
assert p.ImportSpecctraSES(b,session),'Session import failed'
p.SaveBoard(target,b)
records={}
for name,board in [('base',a),('imported',b)]:
 tracks=[]
 for t in board.GetTracks():
  layers=[l for l in [p.F_Cu,p.In1_Cu,p.In2_Cu,p.B_Cu]if t.IsOnLayer(l)]
  row=dict(UUID=t.m_Uuid.AsString(),kind=t.GetClass(),net=t.GetNetname(),
   start=list(p.ToMM(t.GetStart())),end=list(p.ToMM(t.GetEnd())),by_layer={})
  for l in layers:
   poly=p.SHAPE_POLY_SET();t.TransformShapeToPolygon(poly,l,0,p.FromMM(.001),p.ERROR_OUTSIDE)
   row['by_layer'][board.GetLayerName(l)]=polygons(poly)
  if isinstance(t,p.PCB_VIA):row.update(diameter=p.ToMM(t.GetWidth(p.F_Cu)),drill=p.ToMM(t.GetDrillValue()),via_type=t.GetViaType())
  tracks.append(row)
 records[name]=tracks
Path(geometry).write_text(json.dumps(records))
'''
    subprocess.run([NATIVE,'-c',code,str(base),str(session),str(imported),str(geometry)],check=True,capture_output=True)
    data = json.loads(geometry.read_text())
    def poly(records):
        shapes=[]
        for q in records:
            p=Polygon(q['outer'],q['holes'])
            if not p.is_valid:p=make_valid(p)
            shapes.append(p)
        return unary_union(shapes)
    by_net_layer={}
    for t in data['base']:
        for layer,records in t['by_layer'].items():by_net_layer.setdefault((t['net'],layer),[]).append(poly(records))
    fixed={k:unary_union(v) for k,v in by_net_layer.items()}
    baseline_vias=[q for q in data['base']if q['kind']=='PCB_VIA']
    imported_tree=loads(imported.read_text())
    native={child(q,'uuid')[1]:q for kind in ['segment','arc','via']for q in children(imported_tree,kind)}
    nodes=[];fixed_copies=0;discarded_ground=0;discarded_closed=0
    for t in data['imported']:
        if t['kind']=='PCB_VIA':
            if any(q['net']==t['net'] and sum((a-b)**2 for a,b in zip(q['start'],t['start']))<.000002**2
                   and abs(q['diameter']-t['diameter'])<.000002 and abs(q['drill']-t['drill'])<.000002
                   and q['via_type']==t['via_type']for q in baseline_vias):
                fixed_copies+=1;continue
        else:
            # 3 um erosion accommodates DSN/native coordinate normalization;
            # any uncovered core is retained as new copper for native checks.
            if all(poly(records).buffer(-.003).difference(fixed.get((t['net'],layer),Polygon())).area<1e-9
                   for layer,records in t['by_layer'].items()):
                fixed_copies+=1;continue
        if t['net']=='GND':discarded_ground+=1;continue
        if t['net'] not in inputs['native_open_nets']:
            # Native closed nets remain exact. DSN custom-land approximations
            # must not cause the router to rewrite an already checked net.
            discarded_closed+=1;continue
        assert t['net'] not in ['USB_DM','USB_DP'],('Unexpected routed USB net',t['net'])
        node=native[t['UUID']]
        if t['kind']=='PCB_VIA':
            assert min(abs(t['diameter']-v) for v in [.5,.6])<.000002 and abs(t['drill']-.3)<.000002
            assert child(node,'layers')[1:]==['F.Cu','B.Cu']
            node[:]=[q for q in node if not(isinstance(q,list)and q and q[0]=='tenting')]
            node.append(form('tenting',form('front',Atom('yes')),form('back',Atom('yes'))))
        else:assert set(t['by_layer']).issubset({'B.Cu','In2.Cu'}),('New route on reserved layer',t)
        old_uuid=child(node,'uuid');node.remove(old_uuid)
        identity=dumps(node)
        node.append(form('uuid',str(uuid.uuid5(uuid.NAMESPACE_URL,'yeti60-e73-corner/router/'+identity))))
        nodes.append(node)
    unique = {}
    for node in nodes:
        identifier = str(child(node,'uuid')[1])
        if identifier in unique:assert dumps(node)==dumps(unique[identifier]), 'Route UUID collision'
        unique[identifier]=node
    duplicates=len(nodes)-len(unique)
    geometry_keys=set();deduplicated=[]
    for q in unique.values():
        if q[0]=='segment':
            key=(q[0],child(q,'net')[1],child(q,'layer')[1],float(child(q,'width')[1]),tuple(sorted(tuple(map(float,child(q,k)[1:3]))for k in ['start','end'])))
        else:key=(q[0],str(child(q,'uuid')[1]))
        if key in geometry_keys:
            duplicates+=1;continue
        geometry_keys.add(key);deduplicated.append(q)
    nodes=deduplicated
    assert nodes,'No new native routes extracted'
    patch=dict(status='route-patch-native-validation-required',manufacturing_released=False,physical_verification=False,
        base_board_sha256=sha(base),items=[dumps(q)for q in nodes],
        new_tracks=sum(q[0] in ['segment','arc']for q in nodes),new_vias=sum(q[0]=='via'for q in nodes),
        discarded_fixed_copies=fixed_copies,discarded_router_GND_items=discarded_ground,discarded_native_closed_items=discarded_closed,deduplicated_native_items=duplicates,
        provenance_sha256={str(p.relative_to(ROOT)):sha(p)for p in [session,input_path,imported,Path(__file__)]},
        limits=['Router completion is not native electrical acceptance','Retained native copper must remain exact; refill and verify the replayed PCB'])
    out=args.output.resolve() if args.output else ROOT/'hardware/e73-corner-routing.json'
    out.write_text(json.dumps(patch,indent=2)+'\n')
    print(json.dumps({k:patch[k]for k in ['status','new_tracks','new_vias','discarded_fixed_copies']},indent=2))


if __name__=='__main__':main()
