#!/usr/bin/env python3
"""Snapshot exact placed footprint geometry into a normalized local library.

References get separate library entries so upstream variants and intentional
EC guard edits cannot silently overwrite one another. Copper is not changed.
"""
import json
from pathlib import Path
import pcbnew as pcb
from kicad_sexpr import loads,dumps,child,children
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840'
path=BASE/'EC60-nRF52840.kicad_pcb';board=pcb.LoadBoard(str(path))
manifest_path=BASE/'frozen-footprints.json';old=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
manifest={};plugin=pcb.PCB_IO_KICAD_SEXPR()
for fp in board.GetFootprints():
    ref=fp.GetReference()
    for g in fp.GraphicalItems():
        if g.GetLayer() in (pcb.F_SilkS,pcb.B_SilkS):g.SetLayer(pcb.F_Fab if g.GetLayer()==pcb.F_SilkS else pcb.B_Fab)
    baseline=old.get(ref,{}).get('baseline',str(fp.GetFPID().GetLibNickname())+':'+str(fp.GetFPID().GetLibItemName()))
    name=baseline.split(':')[-1]+'__'+ref.replace('*','_')
    id='YAECKB:'+name;fp.SetFPID(pcb.LIB_ID('YAECKB',name))
    clone=pcb.Cast_to_FOOTPRINT(fp.Duplicate(False))
    if clone.IsFlipped():clone.Flip(clone.GetPosition(),False)
    clone.SetOrientationDegrees(0);clone.SetPosition(pcb.VECTOR2I(0,0))
    plugin.FootprintSave(str(BASE/'YAECKB.pretty'),clone)
    manifest[ref]={'id':id,'baseline':baseline}
for g in board.GetDrawings():
    if g.GetLayer() in (pcb.F_SilkS,pcb.B_SilkS):
        if isinstance(g,pcb.PCB_TEXT) and g.GetText() in ('YAECKB / EC60 by Cipulot','NRF-1.0-dev / REAR USB'):continue
        g.SetLayer(pcb.F_Fab if g.GetLayer()==pcb.F_SilkS else pcb.B_Fab)
pcb.SaveBoard(str(path),board,True)
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
for name in ('EC60-nRF52840','power','matrix','analog','mounting'):
    p=BASE/(name+'.kicad_sch');x=loads(p.read_text())
    for sym in children(x,'symbol'):
        props={v[1]:v for v in children(sym,'property')}
        ref=props.get('Reference',[None,None,None])[2]
        if ref in manifest and 'Footprint' in props:props['Footprint'][2]=manifest[ref]['id']
    p.write_text(dumps(x)+'\n')
p=BASE/'components.json';parts=json.loads(p.read_text())
for ref,part in parts.items():
    if ref in manifest:part['footprint']=manifest[ref]['id']
p.write_text(json.dumps(parts,ensure_ascii=False,indent=2)+'\n')
print('Frozen',len(manifest),'footprints without changing placed geometry')
