#!/usr/bin/env python3
"""Verify exact retained header lands and export aligned main SH CAD only."""
import hashlib,json,subprocess,re
from pathlib import Path
from kicad_sexpr import loads,dumps,children,child,Atom
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/ec60-nrf52840';WORK=ROOT/'.assembly-work/interconnect';WORK.mkdir(parents=True,exist_ok=True)
KICAD=Path('/Applications/KiCad/KiCad.app/Contents');FOOT=KICAD/'SharedSupport/footprints/Connector_JST.pretty';MODEL=KICAD/'SharedSupport/3dmodels/Connector_JST.3dshapes';CLI=str(KICAD/'MacOS/kicad-cli')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def properties(n):return {str(v[1]):str(v[2]) for v in children(n,'property')}
def pads(n):return {str(p[1]):p for p in children(n,'pad') if str(p[1]) in ['1','2','3','4']}
def main():
    contract=json.loads((BASE/'components.json').read_text());spec=json.loads((ROOT/'mechanical/interconnect-spec.json').read_text());assembly=json.loads((ROOT/'docs/audit/yeti60-assembly.json').read_text());tree=loads((BASE/'EC60-nRF52840.kicad_pcb').read_text());byref={properties(f)['Reference']:f for f in children(tree,'footprint')};records={};sources=[]
    for ref,name in [('J1','JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal'),('J2','JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal')]:
        native=BASE/'YAECKB.pretty'/(contract[ref]['footprint'].split(':')[1]+'.kicad_mod');standard=FOOT/(name+'.kicad_mod');old,new=loads(native.read_text()),loads(standard.read_text());a,b=pads(old),pads(new)
        shifts=[[float(child(a[k],'at')[i])-float(child(b[k],'at')[i]) for i in [1,2]] for k in b];shift=shifts[0]
        assert all(abs(x-y)<1e-8 for pair in shifts for x,y in zip(pair,shift)),'Non-rigid header pad mismatch'
        assert all(child(a[k],'size')[1:]==child(b[k],'size')[1:] for k in b),'Changed contact-land sizes'
        old_mp=sorted([float(child(p,'at')[1]),float(child(p,'at')[2]),*map(float,child(p,'size')[1:])] for p in children(old,'pad') if str(p[1]) in ['', 'MP'])
        new_mp=sorted([float(child(p,'at')[1])+shift[0],float(child(p,'at')[2])+shift[1],*map(float,child(p,'size')[1:])] for p in children(new,'pad') if str(p[1])=='MP')
        assert all(abs(x-y)<1e-8 for aa,bb in zip(old_mp,new_mp) for x,y in zip(aa,bb)) and len(old_mp)==len(new_mp)
        expected=[0,.0625] if ref=='J1' else [0,0];assert shift==expected
        records[ref]={'status':'rigidly-matching-land-pattern','native_to_standard_origin_shift_local_pcb_mm':shift,'standard_footprint':name,'standard_sha256':sha(standard),'native_sha256':sha(native),'signal_land_count':len(b),'mechanical_land_count':len(old_mp),'board_position_pcb_mm':[float(x) for x in child(byref[ref],'at')[1:3]],'board_angle_deg':(float(child(byref[ref],'at')[3]) if len(child(byref[ref],'at'))>3 else 0)}
        sources.append(native)
    f=byref['J1'];models=children(f,'model');assert len(models)==1;model=MODEL/'JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal.step';models[0][1]=str(model);child(child(models[0],'offset'),'xyz')[1:]=[0,-.0625,0]
    target=WORK/'main-headers.kicad_pcb';target.write_text(dumps(tree)+'\n');step=WORK/'main-sh.step'
    subprocess.run([CLI,'pcb','export','step','--no-board-body','--component-filter','J1','--user-origin','0x0mm','-f','-o',str(step),str(target)],check=True,capture_output=True)
    text=re.sub(r"(FILE_NAME\('[^']*',')[^']*",r"\g<1>2000-01-01T00:00:00",step.read_text());step.write_text('\n'.join(l.rstrip() for l in text.splitlines())+'\n')
    records['J1']['step']={'path':str(step.relative_to(ROOT)),'sha256':sha(step),'model_source':'KiCad Connector_JST.3dshapes/'+model.name,'model_source_sha256':sha(model)}
    # Convert the standard header origin into the case frame. J1 is B.Cu/-90, J2 B.Cu/0.
    assert records['J1']['board_angle_deg']==-90 and records['J2']['board_angle_deg']==0
    x,y=records['J1']['board_position_pcb_mm'];pcb_bottom=assembly['nominal_stack']['pcb_bottom_z'];sh=spec['sources']['SH'];ph=spec['sources']['PH']
    main_exit=[x+.0625+sh['header_back_local_y']+sh['mated_depth_reference'],-y,pcb_bottom-spec['usb']['main_exit_below_pcb']]
    x,y=records['J2']['board_position_pcb_mm'];battery_exit=[x,-y+ph['header_back_local_y']+ph['mated_depth_reference'],pcb_bottom-spec['battery']['main_exit_below_pcb']]
    report={'status':'header-lands-and-frame-passed','headers':records,'main_usb_wire_exit_case_mm':main_exit,'main_battery_wire_exit_case_mm':battery_exit,'prose_scope':'Matching lands and conservative envelopes do not qualify supplier tolerances or crimp quality','source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [BASE/'EC60-nRF52840.kicad_pcb',BASE/'components.json',ROOT/'mechanical/interconnect-spec.json',ROOT/'docs/audit/yeti60-assembly.json',*sources,Path(__file__).resolve()]}}
    (ROOT/'docs/audit/yeti60-interconnect-connectors.json').write_text(json.dumps(report,indent=2)+'\n');print('J1 and J2 signal/mechanical lands match standard JST footprints by rigid translations; main SH CAD aligned')
if __name__=='__main__':main()
