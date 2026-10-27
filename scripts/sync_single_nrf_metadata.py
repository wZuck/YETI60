#!/usr/bin/env python3
"""Reconcile schematic/PCB purchase attributes and approved local footprint filters."""
import copy,json
from pathlib import Path
import pcbnew as pcb
from kicad_sexpr import Atom as A,loads,dumps,child,children,form as F
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840'
manifest=json.loads((BASE/'frozen-footprints.json').read_text());documents={};filters={};fields={};virtual=set()
for name in ('EC60-nRF52840','power','matrix','analog','mounting'):
    path=BASE/(name+'.kicad_sch');root=loads(path.read_text())
    for sym in children(root,'symbol'):
        props={p[1]:p for p in children(sym,'property')};ref=str(props['Reference'][2])
        if ref not in manifest:continue
        baseline=manifest[ref]['baseline'];geometry=(':ecs_pad_' in baseline or baseline.endswith(':HOLE_M2') or ref=='J3')
        if geometry:virtual.add(ref)
        child(sym,'in_bom')[1]=A('no' if geometry else 'yes')
        fields[ref]={k:str(v[2]) for k,v in props.items()}
        lib=str(child(sym,'lib_id')[1]).split(':')[-1]
        filters.setdefault(lib,set()).add('YAECKB:'+baseline.split(':')[-1]+'__*')
    documents[path]=root

def extend(definition):
    name=str(definition[1]).split(':')[-1]
    patterns=filters.get(name)
    if not patterns:return
    prop=next((p for p in children(definition,'property') if p[1]=='ki_fp_filters'),None)
    if prop is None:
        prop=F('property','ki_fp_filters','',F('at',0,0,0),F('effects',F('font',F('size',1.27,1.27)),F('hide',A('yes'))));definition.append(prop)
    prop[2]=' '.join(sorted(set(str(prop[2]).split())|patterns))
for path,root in documents.items():
    for definition in children(child(root,'lib_symbols'),'symbol'):extend(definition)
    path.write_text(dumps(root)+'\n')
path=BASE/'YAECKB.kicad_sym';root=loads(path.read_text())
for definition in children(root,'symbol'):extend(definition)
path.write_text(dumps(root)+'\n')
path=BASE/'EC60-nRF52840.kicad_pcb';board=pcb.LoadBoard(str(path))
for fp in board.GetFootprints():
    ref=fp.GetReference();attrs=fp.GetAttributes()
    if ref=='REF**':fp.SetAttributes(attrs|pcb.FP_BOARD_ONLY|pcb.FP_EXCLUDE_FROM_BOM|pcb.FP_EXCLUDE_FROM_POS_FILES);continue
    if ref not in fields:continue
    if ref in virtual:attrs|=pcb.FP_EXCLUDE_FROM_BOM|pcb.FP_EXCLUDE_FROM_POS_FILES
    else:attrs&=~pcb.FP_EXCLUDE_FROM_BOM
    fp.SetAttributes(attrs)
    for key,kind in (('Datasheet',pcb.FIELD_T_DATASHEET),('Description',pcb.FIELD_T_DESCRIPTION)):
        field=fp.GetField(kind)
        if field is None:field=pcb.PCB_FIELD(fp,kind);fp.Add(field)
        text=fields[ref].get(key,'')
        field.SetText('' if text=='~' else text);field.SetVisible(False)
    if ref not in virtual and not any(g.GetLayer() in (pcb.F_CrtYd,pcb.B_CrtYd) for g in fp.GraphicalItems()):
        box=fp.GetBoundingBox(False,False);box.Inflate(pcb.FromMM(.25))
        corners=[(box.GetLeft(),box.GetTop()),(box.GetRight(),box.GetTop()),(box.GetRight(),box.GetBottom()),(box.GetLeft(),box.GetBottom())]
        for a,b in zip(corners,corners[1:]+corners[:1]):
            line=pcb.PCB_SHAPE(fp);line.SetShape(pcb.SHAPE_T_SEGMENT);line.SetStart(pcb.VECTOR2I(*a));line.SetEnd(pcb.VECTOR2I(*b));line.SetWidth(pcb.FromMM(.05));line.SetLayer(pcb.B_CrtYd if fp.IsFlipped() else pcb.F_CrtYd);fp.Add(line)
pcb.SaveBoard(str(path),board,True)
(BASE/'metadata-audit.json').write_text(json.dumps({'non_purchased_geometry_references':sorted(virtual),'board_only_fixture':'REF**','filters':'original filters plus explicitly frozen physical package families','datasheet_fields':'matched to schematic','J1_courtyard':'body/pad envelope + 0.25mm'},indent=2)+'\n')
print('Reconciled',len(fields),'footprints;',len(virtual),'non-purchased PCB features')
