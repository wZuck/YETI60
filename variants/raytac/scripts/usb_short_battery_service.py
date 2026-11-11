"""Explicit J2 relocation and ordinary-through-via repair, replayable from Git.

Preserve sensing pads, mounting axes, component identities and pin assignments.
This contract describes native geometry, not actual connector/tool qualification.
"""
import copy
import json
import uuid
from pathlib import Path
from kicad_sexpr import Atom, child, children, form, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'
BASELINE = '3db2f94f72f6125d426afa5a24fd7e4a45c8d019'
POSITION = [155.5, 129.0]
OFFSET = [3.5, 4.0]
HOUSING_DEPTH = 5.0
HOUSING_WIDTH = 4.0
REMOVED = {
    'f2714538-8c66-5a31-ab65-06308dc834c9',  # Obsolete ground stub beyond the filled plane.
    'd9d5a722-8115-4571-849c-6fd2cee8a016', 'fb5d5162-afda-4e60-814f-56576f93b03d',
    '3cf714ea-19fa-4c72-afb4-b281cbf6ac5b', '85fe2728-7bc8-4293-bb60-20ccb41a7401',
    '4af0abd8-ae8e-4e63-89c2-cc972b65ba15', 'ca5e5025-6b2b-4969-a289-4065c9137c8a',
    '4b65869f-f252-4441-abe5-f8c40827c6d9', '76375df4-cd80-4941-98c9-642503f4f369',
    'e88590ae-4038-472c-adc2-5c2163aeec01', 'f866a47e-30b3-4c47-ad74-8f19041bbd18',
    '39b1fdfa-9461-45d7-95dc-2593b0b326cf', '1b938990-5ee8-431b-b9eb-be6d0a683a9b',
    'f3d74554-034a-4f75-8350-14991f44a115', '37823d1a-d346-42cc-952b-918cd2b1f2be',
}
ROUTES = [
    ('BAT_CELL', .2, 'B.Cu', [(149.0083,124.3134),(149.4,123.9217),(154.5,123.9217),(154.5,131)]),
    ('GND', .25, 'B.Cu', [(155.5,131),(155.5,133.85)]),
    ('BAT_NTC', .127, 'B.Cu', [(156.5,131),(156.5,135.25),(151.8,135.25),(147.9,139.15)]),
    ('APLEX_EN_PIN_0', .127, 'B.Cu', [(148.613743,120.196979),(154.5,120.196979),(154.5,120.3)]),
    ('APLEX_EN_PIN_0', .127, 'In2.Cu', [(154.5,120.3),(154.527364,124.096979)]),
    ('APLEX_EN_PIN_0', .25, 'In2.Cu', [(156.485817,126.055432),(156.485817,136.8)]),
    ('APLEX_EN_PIN_0', .25, 'B.Cu', [(156.485817,136.8),(156.485817,139.584773)]),
]


def new_items():
    result = []
    for i, point in enumerate([(154.5,120.3),(156.485817,136.8)]):
        identifier = str(uuid.uuid5(uuid.NAMESPACE_URL, 'yeti60-j2-aplex-via-'+str(i)))
        result.append(form('via', form('at',*point), form('size',.5), form('drill',.3),
                           form('layers','F.Cu','B.Cu'),
                           form('tenting',form('front',Atom('yes')),form('back',Atom('yes'))),
                           form('net','APLEX_EN_PIN_0'),form('uuid',identifier)))
    for net, width, layer, path in ROUTES:
        for i, (a,b) in enumerate(zip(path,path[1:])):
            identifier = str(uuid.uuid5(uuid.NAMESPACE_URL, 'yeti60-j2-repair-'+net+'-'+layer+'-'+str(a)+'-'+str(i)))
            result.append(form('segment',form('start',*a),form('end',*b),form('width',width),
                               form('layer',layer),form('net',net),form('uuid',identifier)))
    return result


def via_ids():
    return {child(item,'uuid')[1] for item in new_items() if item[0]=='via'}


def apply_tree(tree):
    """Apply only the documented repair; idempotent for regeneration."""
    footprint = next(f for f in children(tree,'footprint') if any(p[1]=='Reference' and p[2]=='J2' for p in children(f,'property')))
    assert list(map(float,child(footprint,'at')[1:3])) in ([152,125], POSITION), 'Unexpected original J2 position'
    record=json.loads((BASE/'battery-service-j2.json').read_text())
    template=loads(record['native_BCu_footprint'])
    assert child(footprint,'uuid')==child(template,'uuid')
    tree[tree.index(footprint)]=template
    for item in list(tree):
        if isinstance(item,list) and item and item[0] in ['segment','arc'] and child(item,'uuid')[1] in REMOVED:
            tree.remove(item)
    arc = next(a for a in children(tree,'arc') if child(a,'uuid')[1]=='7981c3d2-1c52-41b8-8ff3-62d33f5a1f99')
    child(arc,'layer')[1] = 'In2.Cu'
    old_ids = {child(item,'uuid')[1] for kind in ['segment','via'] for item in children(tree,kind)}
    tree.extend(item for item in new_items() if child(item,'uuid')[1] not in old_ids)
    return tree


def verify_vias(vias):
    for item in [i for i in new_items() if i[0]=='via']:
        actual = vias[child(item,'uuid')[1]]
        assert actual == dict(net='APLEX_EN_PIN_0', position=list(map(float,child(item,'at')[1:])),
                             land_mm=.5, drill_mm=.3, layers=['F.Cu','B.Cu'],
                             tenting=['tenting',['front','yes'],['back','yes']], type='through'), 'Changed J2 service via'


def verify_layout():
    tree = loads((BASE/'EC60-nRF52840.kicad_pcb').read_text())
    footprint = next(f for f in children(tree,'footprint') if any(p[1]=='Reference' and p[2]=='J2' for p in children(f,'property')))
    assert list(map(float,child(footprint,'at')[1:3])) == POSITION, 'Wrong J2 service position'
    assert child(footprint,'layer')[1]=='B.Cu'
    from repair_usb_short_models import geometry_sha
    record=json.loads((BASE/'battery-service-j2.json').read_text())
    assert geometry_sha(footprint)==geometry_sha(loads(record['native_BCu_footprint'])), 'Changed SH3 native footprint'
    library=loads((BASE/record['frozen_FCu_library']).read_text())
    assert geometry_sha(library)==record['frozen_library_non_model_sha256'], 'Changed SH3 frozen library'
    actual = {child(item,'uuid')[1]:item for kind in ['segment','arc','via'] for item in children(tree,kind)}
    assert not REMOVED.intersection(actual), 'Obsolete J2 branches restored'
    # Serialize numeric forms to avoid comparing parsed atoms with Python floats.
    from kicad_sexpr import dumps
    for item in new_items():
        identifier=child(item,'uuid')[1]
        assert dumps(actual[identifier])==dumps(item), 'Changed J2 reconnect: '+identifier
    assert child(actual['7981c3d2-1c52-41b8-8ff3-62d33f5a1f99'],'layer')[1]=='In2.Cu'
    return dict(position_PCB_mm=POSITION, shift_PCB_mm=OFFSET, added_ordinary_through_vias=2,
                SH_housing_depth_screen_mm=HOUSING_DEPTH, header='SM03B-SRSS-TB(LF)(SN)', physical_verification=False)


def apply_envelope(assembly):
    result = copy.deepcopy(assembly)
    part = next(p for p in result['component_envelopes'] if p['ref']=='J2')
    assert part['position_pcb_mm']==[152,125], 'Service envelope must start from held reference'
    part['position_pcb_mm'] = POSITION[:]
    part['bounds_case_mm']=[152.1,-132.28,-5.2,158.9,-125.72,-2]
    part['height_envelope_mm']=3.2
    part['height_basis']='SH3 project installed maximum 3.2 mm including solder; measure incoming assembly; not a supplier guarantee'
    part['physical_body_bbox_pcb_mm']=[152.1,125.72,158.9,132.28]
    part['xy_courtyard_and_graphics_bbox_pcb_mm']=[152.1,125.72,158.9,132.28]
    return result
