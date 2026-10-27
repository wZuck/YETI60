"""Shared, pure-Python reconciliation for verified local footprint snapshots."""
from kicad_sexpr import Atom as A,child,children,form as F

def extend_filters(definition,approved):
    patterns=approved.get(str(definition[1]).split(':')[-1],set())
    if not patterns:return
    prop=next((p for p in children(definition,'property') if p[1]=='ki_fp_filters'),None)
    if prop is None:
        prop=F('property','ki_fp_filters','',F('at',0,0,0),F('effects',F('font',F('size',1.27,1.27)),F('hide',A('yes'))));definition.append(prop)
    prop[2]=' '.join(sorted(set(str(prop[2]).split())|patterns))

def reconcile(root,manifest,approved):
    for instance in children(root,'symbol'):
        props={p[1]:p for p in children(instance,'property')}
        ref=str(props.get('Reference',[None,None,''])[2])
        if ref not in manifest:continue
        baseline=manifest[ref]['baseline']
        if ':ecs_pad_' in baseline or baseline.endswith(':HOLE_M2') or ref=='J3':
            child(instance,'in_bom')[1]=A('no')
        if 'Footprint' in props:props['Footprint'][2]=manifest[ref]['id']
        name=str(child(instance,'lib_id')[1]).split(':')[-1]
        approved.setdefault(name,set()).add('YAECKB:'+baseline.split(':')[-1]+'__*')
    libs=child(root,'lib_symbols')
    if libs:
        for definition in children(libs,'symbol'):extend_filters(definition,approved)
