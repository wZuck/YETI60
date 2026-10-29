#!/usr/bin/env python3
"""Export the pinned daughterboard contract and a resolved render-only STEP."""
import hashlib,json,subprocess,tempfile,sys,re
from pathlib import Path
import pcbnew as pcb
from kicad_sexpr import loads,dumps,children,child,Atom
ROOT=Path(__file__).resolve().parents[1];UP=ROOT/'hardware/usb-daughterboard/upstream';WORK=ROOT/'.assembly-work/daughterboard';WORK.mkdir(parents=True,exist_ok=True)
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';MODELS=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def normalize_step(path):
    # KiCad/OpenCascade emits presentation styles in a nondeterministic order.
    # This pipeline assigns its own materials; retain all geometric entities.
    styles={'MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION','STYLED_ITEM','PRESENTATION_STYLE_ASSIGNMENT','SURFACE_STYLE_USAGE','SURFACE_SIDE_STYLE','SURFACE_STYLE_FILL_AREA','FILL_AREA_STYLE','FILL_AREA_STYLE_COLOUR','COLOUR_RGB','CURVE_STYLE','DRAUGHTING_PRE_DEFINED_COLOUR','DRAUGHTING_PRE_DEFINED_CURVE_FONT','SURFACE_STYLE_RENDERING','SURFACE_STYLE_RENDERING_WITH_PROPERTIES'}
    text=re.sub(r"(FILE_NAME\('[^']*',')[^']*",r"\g<1>2000-01-01T00:00:00",path.read_text())
    text=re.sub(r'#\d+\s*=\s*(\w+)\([\s\S]*?;\n',lambda m:'' if m[1] in styles else m[0],text)
    path.write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n')

def main():
    commit=subprocess.check_output(['git','-C',str(UP),'rev-parse','HEAD'],text=True).strip()
    assert commit=='2b6c52aa2de6f9f60ca99c6250e4bdf01e8f4eea'
    original=UP/'UDB.kicad_pcb';b=pcb.LoadBoard(str(original));fps={f.GetReference():f for f in b.GetFootprints()}
    pads={(f.GetReference(),a.GetNumber()):a for f in b.GetFootprints() for a in f.Pads() if a.GetNumber()}
    assert {str(i):pads['J2',str(i)].GetNetname() for i in range(1,5)}=={'1':'VCOM','2':'DN','3':'DP','4':'GND'}
    for ref,cc in [('R1','A5'),('R2','B5')]:
        assert fps[ref].GetValue()=='5.1k'
        assert pads[ref,'1'].GetNetname()==pads['J1',cc].GetNetname() and pads[ref,'2'].GetNetname()=='GND'
    assert pads['R1','1'].GetNetname()!=pads['R2','1'].GetNetname()
    assert pads['F1','1'].GetNetname()==pads['J1','A4'].GetNetname()=='VBUS'
    assert pads['F1','2'].GetNetname()==pads['J2','1'].GetNetname()=='VCOM'
    target=WORK/'daughterboard.kicad_pcb';pcb.SaveBoard(str(target),b,True);tree=loads(target.read_text());resolved=[]
    byname={p.name:p for p in MODELS.rglob('*.step')}
    for fp in children(tree,'footprint'):
        ref=next(str(v[2]) for v in children(fp,'property') if str(v[1])=='Reference')
        for model in children(fp,'model'):
            old=str(model[1])
            if ref=='J1':path=UP/'libraries/locallib.pretty/HRO  TYPE-C-31-M-12.step'
            elif ref=='J2':
                path=byname['JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal.step']
                child(child(model,'offset'),'xyz')[1:]=[Atom('0'),Atom('-1.45'),Atom('0')]
                child(child(model,'rotate'),'xyz')[1:]=[Atom('0'),Atom('0'),Atom('0')]
            else:
                name=Path(old).name.replace('.wrl','.step');path=byname.get(name)
                if path is None:raise FileNotFoundError(ref+' model '+name)
            assert path.is_file();model[1]=str(path)
            resolved.append({'reference':ref,'original':old,'model_root':'repository' if path.is_relative_to(ROOT) else 'kicad-3dmodels','path':str(path.relative_to(ROOT if path.is_relative_to(ROOT) else MODELS)),'sha256':sha(path),'kind':'source HRO connector' if ref=='J1' else 'standard package geometry; J2 is a mating-compatible JST substitute'})
    target.write_text(dumps(tree)+'\n')
    subprocess.run([CLI,'pcb','export','step','--user-origin','0x0mm','-f','-o',str(WORK/'daughterboard.step'),str(target)],check=True,capture_output=True)
    step=WORK/'daughterboard.step';content=re.sub(r"(FILE_NAME\('[^']*',')[^']*",r"\g<1>2000-01-01T00:00:00",step.read_text());step.write_text('\n'.join(line.rstrip() for line in content.splitlines())+'\n')
    normalize_step(step)
    render_parts={}
    for label,options in [('pcb',['--board-only']),('usb',['--no-board-body','--component-filter','J1']),('sh',['--no-board-body','--component-filter','J2']),('components',['--no-board-body','--component-filter','F1,R1,R2,U1,D1'])]:
        part=WORK/(label+'.step')
        subprocess.run([CLI,'pcb','export','step',*options,'--user-origin','0x0mm','-f','-o',str(part),str(target)],check=True,capture_output=True)
        text=re.sub(r"(FILE_NAME\('[^']*',')[^']*",r"\g<1>2000-01-01T00:00:00",part.read_text());part.write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n')
        normalize_step(part)
        render_parts[label]={'path':str(part.relative_to(ROOT)),'sha256':sha(part)}
    report={'exported_step_sha256':sha(step),'status':'contract-passed','source_commit':commit,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [original,UP/'UDB.kicad_sch']},'finished_pcb_thickness_mm':pcb.ToMM(b.GetDesignSettings().GetBoardThickness()),'mount_holes_pcb_mm':[[pcb.ToMM(fps[r].GetPosition().x),pcb.ToMM(fps[r].GetPosition().y)] for r in ['MH1','MH2','MH3','MH4']],'connector_pin_contract':{'1':'VBUS through F1','2':'D-','3':'D+','4':'GND'},'separate_CC_terminations_ohm':[5100,5100],'model_resolutions':resolved,'exported_step':str((WORK/'daughterboard.step').relative_to(ROOT)),'render_parts':render_parts,'SH_model_offset_xyz_mm':[0,-1.45,0],'SH_alignment_basis':'Native signal pad row y=-0.55 minus standard JST row y=-2 gives +1.45 PCB Y; STEP model offset is -1.45 Y. Previous +2.425 placed the body 3.875mm too far rearward.','export_recipe_sha256':sha(Path(__file__).resolve()),'limits':['Standard package substitutions do not qualify the supplier part height','JST mating harness uses a separately checked conservative housing envelope']}
    (ROOT/'docs/audit/yeti60-daughterboard.json').write_text(json.dumps(report,indent=2)+'\n');print('Pinned daughterboard pin/CC contract and native STEP exported')
if __name__=='__main__':main()
