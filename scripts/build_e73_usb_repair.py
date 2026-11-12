#!/usr/bin/env python3
"""Replay the E73-specific USB topology repair without selecting it for fabrication.

Run with KiCad Python. Original E73 lands, sensing geometry, rules and non-USB
nets remain authoritative. Header land patterns are the existing checked SH
parts; the E73 routes are new and must pass independent native checks.
"""
import copy
import csv
import hashlib
import json
import math
import shutil
import subprocess
import uuid
from pathlib import Path
import pcbnew as pcb
from kicad_sexpr import Atom, child, children, dumps, form, loads, symbol_pins
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/ec60-nrf52840'
RAY=ROOT/'variants/raytac/hardware/usb-short-route'
OUT=ROOT/'hardware/e73-usb-repair'
NAME='EC60-nRF52840'
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
REMOVED={'D1','R30','R31'}
SPEC_PATH=ROOT/'hardware/e73-usb-repair-spec.json'
SPEC=json.loads(SPEC_PATH.read_text())
POSITIONS=SPEC['headers_pcb_mm']
DATA=SPEC['data_paths_B_Cu_mm']
LOCAL_POWER_REMOVED=set(SPEC['removed_C32_GND_fanout_UUIDs'])
CONTROL_REMOVED=set(SPEC['removed_ROW_DRV4_loop_item_UUIDs'])|set(SPEC['removed_RESET_B_item_UUIDs'])

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def uid(tag):return str(uuid.uuid5(uuid.NAMESPACE_URL,'yeti60-e73-usb-repair-v1/'+tag))
def reference(f):return next(p[2] for p in children(f,'property')if p[1]=='Reference')
def xy(v):return tuple(float(x)for x in v[1:3])
def same(a,b):return math.dist(a,b)<1e-6

def detach(sch,symbol,only=None):
    """Remove only each generated pin's own two-point label connection."""
    lib=next(s for s in children(child(sch,'lib_symbols'),'symbol')if s[1]==child(symbol,'lib_id')[1])
    at=child(symbol,'at');assert float(at[3])==0
    points=[]
    for number,pin in symbol_pins(lib).items():
        if only is not None and number not in only:continue
        assert float(at[3])==0
        points.append((float(at[1])+pin['at'][0],float(at[2])-pin['at'][1]))
    remove=[]
    for point in points:
        wires=[w for w in children(sch,'wire')if any(same(xy(p),point)for p in child(w,'pts')[1:])]
        assert len(wires)==1,(reference(symbol),point,len(wires))
        wire=wires[0];ends=[xy(p)for p in child(wire,'pts')[1:]];outer=next(p for p in ends if not same(p,point))
        labels=[g for g in children(sch,'global_label')if same(xy(child(g,'at')),outer)]
        assert len(labels)==1,(reference(symbol),point,'Shared or missing label')
        remove.extend([wire,labels[0]])
    for n in remove:sch.remove(n)
    return points

def schematic():
    sch=loads((SOURCE/(NAME+'.kicad_sch')).read_text())
    symbols={reference(s):s for s in children(sch,'symbol')}
    for ref in sorted(REMOVED):detach(sch,symbols[ref]);sch.remove(symbols[ref])
    for point in detach(sch,symbols['J1'],{'2','3'}):sch.append(form('no_connect',form('at',*point),form('uuid',uid('J1-NC-'+str(point)))))
    next(p for p in children(symbols['J1'],'property')if p[1]=='Value')[2]='USB_POWER_IN'
    ray=loads((RAY/(NAME+'.kicad_sch')).read_text());libs=child(sch,'lib_symbols')
    libs.append(copy.deepcopy(next(s for s in children(child(ray,'lib_symbols'),'symbol')if s[1]=='YAECKB:Conn_01x02')))
    for ref in POSITIONS:
        sym=next(s for s in children(ray,'symbol')if reference(s)==ref);at=xy(child(sym,'at'));sch.append(copy.deepcopy(sym))
        for n in ray[1:]:
            if not isinstance(n,list)or n[0]not in ['wire','global_label']:continue
            points=[xy(p)for p in child(n,'pts')[1:]] if n[0]=='wire' else [xy(child(n,'at'))]
            if all(abs(p[0]-at[0])<10 and abs(p[1]-at[1])<8 for p in points):sch.append(copy.deepcopy(n))
    (OUT/(NAME+'.kicad_sch')).write_text(dumps(sch)+'\n')
    lib=loads((SOURCE/'YAECKB.kicad_sym').read_text());raylib=loads((RAY/'YAECKB.kicad_sym').read_text())
    assert not any(s[1]=='Conn_01x02'for s in children(lib,'symbol'))
    lib.append(copy.deepcopy(next(s for s in children(raylib,'symbol')if s[1]=='Conn_01x02')))
    (OUT/'YAECKB.kicad_sym').write_text(dumps(lib)+'\n')

def board():
    src=loads((SOURCE/(NAME+'.kicad_pcb')).read_text());ray=loads((RAY/(NAME+'.kicad_pcb')).read_text());removed_tracks=0
    for n in list(src[1:]):
        if not isinstance(n,list):continue
        if n[0]=='footprint'and reference(n)in REMOVED:src.remove(n)
        elif n[0]in ['segment','arc','via']and child(n,'uuid')[1]in LOCAL_POWER_REMOVED|CONTROL_REMOVED:src.remove(n)
        elif n[0]in ['segment','arc','via']and (child(n,'net')[1]in ['D-','D+','USB_DM','USB_DP'] or (n[0]=='segment' and child(n,'net')[1]=='USB_5V' and child(n,'layer')[1]=='B.Cu' and min(xy(child(n,'start'))[0],xy(child(n,'end'))[0])>=342.5)):
            src.remove(n);removed_tracks+=1
    c32=next(f for f in children(src,'footprint')if reference(f)=='C32');child(c32,'at')[1:]=SPEC['C32_pcb_mm']
    for pad in children(c32,'pad'):child(pad,'at')[3]=SPEC['C32_pcb_mm'][2]
    j1=next(f for f in children(src,'footprint')if reference(f)=='J1')
    next(p for p in children(j1,'property')if p[1]=='Value')[2]='USB_POWER_IN'
    for pad in children(j1,'pad'):
        if pad[1]in ['2','3']:child(pad,'net')[1]='unconnected-(J1-Pin_'+pad[1]+'-Pad'+pad[1]+')'
    for ref,pos in POSITIONS.items():
        f=copy.deepcopy(next(f for f in children(ray,'footprint')if reference(f)==ref));rotation=SPEC['header_orientation_deg'][ref];child(f,'at')[1:]=[*pos,rotation]
        for pad in children(f,'pad'):
            at=child(pad,'at');at[1:]=[*at[1:3],(float(at[3])if len(at)>3 else 0)+rotation]
        src.append(f)
    for net,path in DATA.items():
        for i,(a,b)in enumerate(zip(path,path[1:])):
            src.append(form('segment',form('start',*a),form('end',*b),form('width',.3),form('layer','B.Cu'),form('net',net),form('uuid',uid(net+'/'+str(i)))))
    via_points=set()
    for i,route in enumerate(SPEC['power_ground_routes']):
        net=route['net']
        for j,(a,b)in enumerate(zip(route['points'],route['points'][1:])):
            if a[2]!=b[2]:
                assert a[:2]==b[:2],('Non-coincident layer transition',a,b)
                via_points.add((net,tuple(a[:2])))
            else:
                assert a[:2]!=b[:2]
                src.append(form('segment',form('start',*a[:2]),form('end',*b[:2]),form('width',route['width']),form('layer',a[2]),form('net',net),form('uuid',uid('local-route/'+str(i)+'/'+str(j)))))
        if 'ground_via_at'in route:via_points.add((net,tuple(route['ground_via_at'])))
    for net,pos in sorted(via_points):
        src.append(form('via',form('at',*pos),form('size',SPEC['via_diameter_mm']),form('drill',SPEC['via_drill_mm']),form('layers','F.Cu','B.Cu'),form('tenting',form('front',Atom('yes')),form('back',Atom('yes'))),form('net',net),form('uuid',uid('via/'+net+str(pos)))))
    path=OUT/(NAME+'.kicad_pcb');path.write_text(dumps(src)+'\n')
    b=pcb.LoadBoard(str(path));before={t.m_Uuid.AsString():t.GetNetname()for t in b.GetTracks()};pcb.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity()
    assert before=={t.m_Uuid.AsString():t.GetNetname()for t in b.GetTracks()},'Zone fill reassigned a retained copper net'
    pcb.SaveBoard(str(path),b)
    return removed_tracks

def purchase_table(suffix=''):
    source=SOURCE.parent/'bom'/('mainboard-purchase'+suffix+'.csv')
    with source.open() as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    result=[]
    for row in rows:
        refs={r.strip()for r in row[fields[0]].split(',')}
        if refs&REMOVED:
            assert refs<=REMOVED,'Mixed stock allocation requires explicit reassessment'
            continue
        if refs=={'J1'}:row[fields[4]]='USB_POWER_IN'
        result.append(row)
    with (RAY/('mainboard-purchase'+suffix+'.csv')).open()as f:
        for row in csv.DictReader(f):
            if row[fields[0]]in POSITIONS:result.append({k:row[k]for k in fields})
    with (OUT/('mainboard-purchase'+suffix+'.csv')).open('w',newline='')as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");writer.writeheader();writer.writerows(result)
    counts={key:sum(int(r[fields[i]])for r in result)for key,i in [('Required',1),('Planned stock use',2),('Net purchase',3)]}
    assert counts=={'Required':75,'Planned stock use':8,'Net purchase':67}
    return counts

def main():
    OUT.mkdir(exist_ok=True);(OUT/'audit').mkdir(exist_ok=True)
    # An interrupted/failed rebuild must never leave a previous green report
    # looking like evidence for partly rewritten candidate files.
    for name in ['build.json','native-check.json','DRC-strict.json','ERC.json','fault-tests.json']:
        (OUT/'audit'/name).unlink(missing_ok=True)
    assert sha(SOURCE/(NAME+'.kicad_pcb'))==SPEC['source_board_sha256'],'Repair source PCB changed; review before replay'
    for name in ['analog.kicad_sch','matrix.kicad_sch','mounting.kicad_sch','power.kicad_sch',NAME+'.kicad_pro','sym-lib-table','fp-lib-table','frozen-footprints.json']:
        shutil.copyfile(SOURCE/name,OUT/name)
    shutil.copytree(SOURCE/'YAECKB.pretty',OUT/'YAECKB.pretty',dirs_exist_ok=True)
    for name in ['JST-SR-4__J4.kicad_mod','JST_SH_SM02B_SRSS_TB__J5.kicad_mod']:
        shutil.copyfile(RAY/'YAECKB.pretty'/name,OUT/'YAECKB.pretty'/name)
    frozen=json.loads((OUT/'frozen-footprints.json').read_text())
    for ref in REMOVED:
        (OUT/'YAECKB.pretty'/(frozen[ref]['id'].split(':')[-1]+'.kicad_mod')).unlink(missing_ok=True)
        del frozen[ref]
    frozen.update({ref:json.loads((RAY/'frozen-footprints.json').read_text())[ref]for ref in POSITIONS})
    (OUT/'frozen-footprints.json').write_text(json.dumps(frozen,indent=2)+'\n')
    schematic();removed_tracks=board()
    subprocess.run([CLI,'sch','export','netlist','--format','kicadxml','-o',str(OUT/'netlist.xml'),str(OUT/(NAME+'.kicad_sch'))],check=True,capture_output=True)
    parts=json.loads((SOURCE/'components.json').read_text());rayparts=json.loads((RAY/'components.json').read_text())
    for ref in REMOVED:del parts[ref]
    parts['J1']['value']='USB_POWER_IN'
    for pin in ['2','3']:parts['J1']['pins'][pin]='unconnected-(J1-Pin_'+pin+'-Pad'+pin+')'
    for ref in POSITIONS:parts[ref]=rayparts[ref]
    (OUT/'components.json').write_text(json.dumps(parts,indent=2)+'\n')
    purchase=purchase_table();purchase_table('.zh-CN')
    inputs=[Path(__file__),SPEC_PATH,SOURCE/(NAME+'.kicad_pcb'),SOURCE/(NAME+'.kicad_sch'),SOURCE/(NAME+'.kicad_pro'),SOURCE/'components.json',SOURCE/'YAECKB.kicad_sym',RAY/(NAME+'.kicad_pcb'),RAY/(NAME+'.kicad_sch'),RAY/'components.json',RAY/'frozen-footprints.json',RAY/'YAECKB.kicad_sym']
    inputs += sorted(p for p in SOURCE.rglob('*')if p.is_file() and p.suffix in ['.kicad_sch','.kicad_mod'])
    inputs += [SOURCE/n for n in ['frozen-footprints.json','sym-lib-table','fp-lib-table']]
    inputs += [RAY/'YAECKB.pretty'/n for n in ['JST-SR-4__J4.kicad_mod','JST_SH_SM02B_SRSS_TB__J5.kicad_mod']]
    inputs += [folder/('mainboard-purchase'+suffix+'.csv')for folder in [SOURCE.parent/'bom',RAY]for suffix in ['', '.zh-CN']]
    inputs=list(dict.fromkeys(inputs))
    report=dict(status='built-native-validation-pending',module='E73-2G4M08S1C',selected_by_assembly=False,manufacturing_released=False,physical_verification=False,
                removed_references=sorted(REMOVED),new_header_positions_pcb_mm=POSITIONS,removed_data_and_local_USB_5V_items=removed_tracks,
                purchase_counts=purchase,explicitly_repaired_control_nets=['ROW_DRV4','RESET_N'],
                source_sha256={str(p.relative_to(ROOT)):sha(p)for p in inputs},outputs={str(p.relative_to(ROOT)):sha(p)for p in sorted(OUT.rglob('*'))if p.is_file() and 'audit'not in p.relative_to(OUT).parts and (p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_sym','.kicad_pro','.kicad_mod','.xml','.json','.csv'] or p.name in ['sym-lib-table','fp-lib-table'])})
    (OUT/'audit/build.json').write_text(json.dumps(report,indent=2)+'\n')
    print('E73 USB repair built; native DRC, parity, reference and physical checks still required')
if __name__=='__main__':main()
