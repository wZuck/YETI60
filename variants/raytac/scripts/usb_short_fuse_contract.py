"""Validate the selected one-time F1 and manufacturer-derived native lands."""
import json
from pathlib import Path
from kicad_sexpr import loads, child, children, symbol_pins

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/usb-short-route'


def properties(node):
    return {str(p[1]):str(p[2]) for p in children(node,'property')}


def verify_fuse():
    record=json.loads((BASE/'parts-qualification.json').read_text())['F1']
    assert record['mpn']=='0466001.NRHF' and record['type']=='one-time fast-acting thin-film fuse; not PPTC'
    assert record['rated_current_A']==1 and record['rated_voltage_V_AC_DC']==63
    assert record['value']=='1A_FAST_0466001_NRHF'
    assert record['body_max_LWH_mm']==[3.302,1.651,.66]
    assert record['manufacturer_continuous_rerating_example']['available_continuous_A']==.6
    assert record['reflow_pad_size_mm']==[1.143,2.032]
    assert record['pad_centres_local_mm']==[[-1.3335,0],[1.3335,0]]
    board=loads((BASE/'EC60-nRF52840.kicad_pcb').read_text())
    f=next(f for f in children(board,'footprint') if properties(f)['Reference']=='F1')
    assert f[1]==record['footprint'] and child(f,'layer')[1]=='B.Cu'
    assert [float(v) for v in child(f,'at')[1:]]==record['position_PCB_XY_angle'],'Moved F1'
    assert properties(f)['Value']==record['value']
    lib=loads((BASE/'YAECKB.pretty'/(record['footprint'].split(':')[1]+'.kicad_mod')).read_text())
    for source in [f,lib]:
        model=child(source,'model')
        assert model[1]=='${KIPRJMOD}/'+record['native_model']['path']
        assert [float(v) for v in child(child(model,'offset'),'xyz')[1:]]==[0,0,0]
        assert [float(v) for v in child(child(model,'scale'),'xyz')[1:]]==[1,1,1]
        assert [float(v) for v in child(child(model,'rotate'),'xyz')[1:]]==[0,0,0]
        pads=sorted(children(source,'pad'),key=lambda p:p[1])
        assert [str(p[1]) for p in pads]==['1','2']
        for pad,centre in zip(pads,record['pad_centres_local_mm']):
            assert pad[3]=='rect' and [float(v) for v in child(pad,'size')[1:]]==record['reflow_pad_size_mm'],'Old/wrong F1 lands'
            assert [float(v) for v in child(pad,'at')[1:3]]==centre,'Wrong F1 pad pitch'
    sheet=loads((BASE/'EC60-nRF52840.kicad_sch').read_text())
    s=next(s for s in children(sheet,'symbol') if properties(s).get('Reference')=='F1')
    assert child(s,'lib_id')[1]==record['local_symbol'],'F1 is not the one-time fuse symbol'
    assert properties(s)['Value']==record['value'] and properties(s)['Footprint']==record['footprint']
    cache=next(s for s in children(child(sheet,'lib_symbols'),'symbol') if s[1]==record['local_symbol'])
    pins=symbol_pins(cache)
    assert pins['1']['at']==[0,3.81,270] and pins['2']['at']==[0,-3.81,90]
    return record
