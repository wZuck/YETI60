#!/usr/bin/env python3
"""Audit the isolated USB repair against the frozen canonical Raytac baseline.

The candidate is not a fabrication release. No canonical files or rules are edited.
Run with KiCad Python, then run study_usb_short_route.py with the CAD runtime.
"""
import hashlib,json,subprocess,tempfile,shutil,csv
from collections import Counter
from itertools import combinations
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as pcb
from export_yeti60_usb_reference import polygons
from check_yeti60_signal_paths import extract
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/usb-short-route';AUD=BASE/'audit';WORK=ROOT/'.assembly-work/usb-short-audit';NAME='EC60-nRF52840';CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';REV='3dcbf2403df1226e11a04fcdcf641d00a97cfa99'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gitfile(rel):return subprocess.check_output(['git','show',REV+':variants/raytac/'+rel],cwd=ROOT)
def nodes(xml):return {(n.get('ref'),n.get('pin')):net.get('name') for net in xml.findall('./nets/net') for n in net.findall('node')}
def signature(xml):return ({n.get('ref'):(n.findtext('value'),n.findtext('footprint')) for n in xml.findall('./components/comp')},{n.get('name'):sorted((a.get('ref'),a.get('pin')) for a in n.findall('node')) for n in xml.findall('./nets/net')})
def geometry(board):
    out={}
    for f in board.GetFootprints():
        ref=f.GetReference()
        if ref in ['J4','J5','R30','R31']:continue
        # Preserve every retained footprint, including rear power/analog components.
        # J1's two intentionally unused nets change, but its pad geometry does not.
        out[ref]={'position':(f.GetPosition().x,f.GetPosition().y),'angle':f.GetOrientationDegrees(),'back':f.IsFlipped(),'footprint':f.GetFPID().GetLibItemName(),'pads':[(p.GetNumber(),p.GetNetname() if ref!='J1' else '',(p.GetDrillSize().x,p.GetDrillSize().y),polygons(p.GetEffectivePolygon(pcb.B_Cu if f.IsFlipped() else pcb.F_Cu))) for p in f.Pads()]}
    p=pcb.SHAPE_POLY_SET();assert board.GetBoardPolygonOutlines(p,False);return out,polygons(p)
def connected_groups(board):
    board.BuildConnectivity();conn=board.GetConnectivity();items={q.m_Uuid.AsString():q for q in [*board.GetTracks(),*[p for f in board.GetFootprints() for p in f.Pads()],*board.Zones()]};groups={};pads={(f.GetReference(),p.GetNumber()):p for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()}
    for p in pads.values():
        key=p.m_Uuid.AsString()
        if key in groups:continue
        stack=[p];seen=set();index=len(groups)
        while stack:
            q=stack.pop();u=q.m_Uuid.AsString()
            if u in seen:continue
            seen.add(u);groups[u]=index
            stack.extend(items[v.m_Uuid.AsString()] for v in conn.GetConnectedItems(q) if v.GetNetCode()==p.GetNetCode() and v.m_Uuid.AsString() in items and v.m_Uuid.AsString() not in seen)
    return {k:groups[p.m_Uuid.AsString()] for k,p in pads.items()}
def main():
    AUD.mkdir(exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    source_files=sorted(p for p in BASE.rglob('*') if p.is_file() and (p.parent.name=='YAECKB.pretty' or (p.parent==BASE and (p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym','.xml','.csv'] or p.name in ['components.json','frozen-footprints.json','metadata-audit.json','fp-lib-table','sym-lib-table']))))
    before={str(p.relative_to(ROOT)):sha(p) for p in source_files};assert (BASE/(NAME+'.kicad_pro')).read_bytes()==gitfile('hardware/ec60-nrf52840/'+NAME+'.kicad_pro'),'Project rules changed'
    oldxml=ET.fromstring(gitfile('hardware/ec60-nrf52840/netlist.xml'));saved=ET.parse(BASE/'netlist.xml').getroot()
    with tempfile.TemporaryDirectory(prefix='yeti60-short-usb-') as folder:
        temp=Path(folder);baseline=temp/'baseline.kicad_pcb';baseline.write_bytes(gitfile('hardware/ec60-nrf52840/'+NAME+'.kicad_pcb'));oldboard=pcb.LoadBoard(str(baseline));board=pcb.LoadBoard(str(BASE/(NAME+'.kicad_pcb')))
        assert geometry(board)==geometry(oldboard),'Sensing copper, mount positions or board outline changed'
        for p in BASE.glob('*.kicad_sch'):shutil.copyfile(p,temp/p.name)
        for name in ['fp-lib-table','sym-lib-table','YAECKB.kicad_sym',NAME+'.kicad_pcb']:shutil.copyfile(BASE/name,temp/name)
        (temp/'YAECKB.pretty').symlink_to((BASE/'YAECKB.pretty').resolve(),target_is_directory=True)
        config=json.loads((BASE/(NAME+'.kicad_pro')).read_text());enabled=[]
        for k,v in config['board']['design_settings']['rule_severities'].items():
            if v=='ignore':config['board']['design_settings']['rule_severities'][k]='error' if k=='footprint_type_mismatch' else 'warning';enabled.append(k)
        (temp/(NAME+'.kicad_pro')).write_text(json.dumps(config))
        subprocess.run([CLI,'sch','export','netlist','--format','kicadxml','-o',str(temp/'fresh.xml'),str(temp/(NAME+'.kicad_sch'))],check=True,capture_output=True)
        assert signature(ET.parse(temp/'fresh.xml').getroot())==signature(saved),'Stale saved netlist'
        subprocess.run([CLI,'sch','erc','--severity-all','--format','json','-o',str(AUD/'ERC.json'),str(temp/(NAME+'.kicad_sch'))],check=True,capture_output=True)
        erc=json.loads((AUD/'ERC.json').read_text());ec=Counter((v['severity'],v['type']) for s in erc['sheets'] for v in s['violations']);assert not any(k[0]=='error' or k[1]=='no_connect_connected' for k in ec),dict(ec)
        subprocess.run([CLI,'pcb','drc','--all-track-errors','--schematic-parity','--severity-all','--refill-zones','--format','json','-o',str(AUD/'DRC-strict.json'),str(temp/(NAME+'.kicad_pcb'))],check=True,capture_output=True)
        drc=json.loads((AUD/'DRC-strict.json').read_text());errors=[v for v in drc['violations'] if v['severity']=='error'];assert not errors and not drc['unconnected_items'] and not drc.get('schematic_parity'),(len(errors),len(drc['unconnected_items']),drc.get('schematic_parity'))
        assert all(c<199 for c in Counter(v['type'] for v in drc['violations']).values()),'DRC category may be truncated'
        virtual=set(json.loads((BASE/'metadata-audit.json').read_text())['non_purchased_geometry_references'])|{'REF**'};refs={f.m_Uuid.AsString():f.GetReference() for f in board.GetFootprints()}
        assert all(refs[i['uuid']] in virtual for v in drc['violations'] if v['type']=='missing_courtyard' for i in v['items'])
        a,b=nodes(oldxml),nodes(saved);oldparts,newparts=signature(oldxml)[0],signature(saved)[0];assert set(newparts)-set(oldparts)=={'J4','J5'} and set(oldparts)-set(newparts)=={'R30','R31'}
        assert all(oldparts[r]==v for r,v in newparts.items() if r not in ['J1','J4','J5']);assert oldparts['R30'][0]==oldparts['R31'][0]=='0'
        for key,net in a.items():
            if key[0] in ['R30','R31'] or key in [('J1','2'),('J1','3')]:continue
            assert b.get(key)==net,('Changed existing pin',key,net,b.get(key))
        expected={('J4','1'):'USB_FEED',('J4','2'):'USB_DM',('J4','3'):'USB_DP',('J4','4'):'GND',('J5','1'):'USB_FEED',('J5','2'):'GND',('J1','1'):'VBUS',('J1','4'):'GND',('U1','32'):'USB_5V',('U1','34'):'USB_DM',('U1','35'):'USB_DP'}
        assert all(b.get(k)==v for k,v in expected.items());assert all(b['J1',p].startswith('unconnected-') for p in ['2','3']);assert {k for k,v in b.items() if v=='USB_FEED'}=={('J4','1'),('J5','1')}
        contract=json.loads((BASE/'components.json').read_text());assert all(b.get((ref,pin))==net for ref,c in contract.items() if not ref.startswith('#') for pin,net in c['pins'].items());assert all(newparts[ref]==(c['value'],c['footprint']) for ref,c in contract.items() if not ref.startswith('#'))
        groups=connected_groups(board);checks=[]
        for net in saved.findall('./nets/net'):
            keys=[(v.get('ref'),v.get('pin')) for v in net.findall('node')]
            if len(keys)<2:continue
            for key in keys[1:]:checks.append({'net':net.get('name'),'from':keys[0],'to':key,'connected':groups[keys[0]]==groups[key]})
        assert all(q['connected'] for q in checks),'Unconnected native physical pin pair'
        # Current all-net connectivity plus unchanged non-USB pin/net identities preserves all unaffected functions.
        paths=extract(BASE/(NAME+'.kicad_pcb'));assert all(paths[q]['via_count']==0 and paths[q]['geometric_centerline_path_mm']<6 for q in ['positive','negative']);assert paths['geometric_path_difference_mm']<.01
        (AUD/'USB-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
        ground={}
        for l in [pcb.F_Cu,pcb.In1_Cu,pcb.In2_Cu,pcb.B_Cu]:
            shapes=[]
            for z in board.Zones():
                if z.IsOnLayer(l) and not z.GetIsRuleArea() and z.GetNetname()=='GND':shapes.extend(polygons(z.GetFilledPolysList(l)))
            for f in board.GetFootprints():
                for p in f.Pads():
                    if p.IsOnLayer(l) and p.GetNetname()=='GND':shapes.extend(polygons(p.GetEffectivePolygon(l)))
            for t in board.GetTracks():
                if t.IsOnLayer(l) and t.GetNetname()=='GND':
                    q=pcb.SHAPE_POLY_SET();t.TransformShapeToPolygon(q,l,0,pcb.FromMM(.002),pcb.ERROR_INSIDE);shapes.extend(polygons(q))
            ground[board.GetLayerName(l)]=shapes
        inputs={'ground_copper':ground,'ground_through_vias':[],'source_sha256':before,'new_headers':[]}
        oldtracks={q.m_Uuid.AsString() for q in oldboard.GetTracks()};newvias=[q for q in board.GetTracks() if isinstance(q,pcb.PCB_VIA) and q.m_Uuid.AsString() not in oldtracks];assert len(newvias)==3 and all(q.GetViaType()==pcb.VIATYPE_THROUGH and abs(pcb.ToMM(q.GetWidth(pcb.F_Cu))-.5)<1e-7 and abs(pcb.ToMM(q.GetDrillValue())-.3)<1e-7 for q in newvias)
        for f in board.GetFootprints():
            if f.GetReference() not in ['J4','J5']:continue
            q=f.GetBoundingBox(False,False);inputs['new_headers'].append({'ref':f.GetReference(),'position':[pcb.ToMM(f.GetPosition().x),pcb.ToMM(f.GetPosition().y)],'bbox':[pcb.ToMM(q.GetLeft()),pcb.ToMM(q.GetTop()),pcb.ToMM(q.GetRight()),pcb.ToMM(q.GetBottom())]})
        for h in inputs['new_headers']:
            f=next(f for f in board.GetFootprints() if f.GetReference()==h['ref']);pts=[]
            for item in f.GraphicalItems():
                if item.GetClass()=='PCB_SHAPE' and item.GetLayer()==pcb.B_Fab and abs(pcb.ToMM(item.GetWidth())-.1)<1e-7:
                    pts.extend([[pcb.ToMM(q.x),pcb.ToMM(q.y)] for q in [item.GetStart(),item.GetEnd()]])
            h['physical_body_bbox_pcb_mm']=[min(q[0] for q in pts),min(q[1] for q in pts),max(q[0] for q in pts),max(q[1] for q in pts)]
            h['contact_land_bboxes_pcb_mm']=[]
            for p in f.Pads():
                q=p.GetBoundingBox();h['contact_land_bboxes_pcb_mm'].append({'pin':p.GetNumber(),'bbox':[pcb.ToMM(q.GetLeft()),pcb.ToMM(q.GetTop()),pcb.ToMM(q.GetRight()),pcb.ToMM(q.GetBottom())]})
        for suffix in ['', '.zh-CN']:
            rows=list(csv.DictReader((BASE/('mainboard-purchase'+suffix+'.csv')).open()));ks=list(rows[0]);bomrefs={r.strip() for row in rows for r in row[ks[0]].split(',')}
            assert bomrefs==set(newparts)-virtual-{'JP1'}
            assert [sum(int(row[k]) for row in rows) for k in ks[1:4]]==[75,8,67]
        (WORK/'native-inputs.json').write_text(json.dumps(inputs,separators=(',',':'))+'\n')
        report={'status':'native-candidate-checks-passed','manufacturing_released':False,'baseline_commit':REV,'strict_DRC_errors':0,'schematic_parity_items':0,'unconnected_items':0,'enabled_previously_ignored_checks':enabled,'ERC_counts':{str(k):v for k,v in ec.items()},'DRC_warnings':dict(Counter(v['type'] for v in drc['violations'])),'physical_pin_pairs':checks,'physical_pin_pairs_checked':len(checks),'sensing_and_mount_geometry_unchanged':True,'all_retained_footprint_geometry_unchanged':True,'project_rules_unchanged':True,'removed_zero_ohm_links':['R30','R31'],'new_references':['J4','J5'],'new_ordinary_through_vias':3,'USB_positive_contact_path_mm':paths['positive']['geometric_centerline_path_mm'],'USB_negative_contact_path_mm':paths['negative']['geometric_centerline_path_mm'],'USB_geometric_skew_mm':paths['geometric_path_difference_mm'],'USB_data_vias_per_leg':0,'physical_verification':False,'source_sha256':before,'audit_script_sha256':sha(Path(__file__)),'remaining':['Final C5-to-J4 and J5-to-J1 cable geometry, enclosed collision checks and updated assembly illustrations','Full cable impedance/return and physical USB/BLE/charge/thermal validation','Supplier battery verification remains user-owned; use battery-vendor-checklist.md']}
        (AUD/'native-check.json').write_text(json.dumps(report,indent=2)+'\n')
    assert all(sha(ROOT/p)==h for p,h in before.items()),'Audit modified source'
    print({k:report[k] for k in ['status','strict_DRC_errors','schematic_parity_items','unconnected_items','physical_pin_pairs_checked','USB_positive_contact_path_mm','USB_negative_contact_path_mm']})
if __name__=='__main__':main()
