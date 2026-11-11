#!/usr/bin/env python3
"""Repair only current-candidate native models; retain electrical/mechanical CAD."""
import copy
import hashlib
import json
from pathlib import Path
from kicad_sexpr import child, children, dumps, form, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'
PCB = BASE / 'EC60-nRF52840.kicad_pcb'
STANDARD = '${KICAD10_3DMODEL_DIR}/'
CHOICES = {
    'J1': (STANDARD + 'Connector_JST.3dshapes/JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal.step', [0, -.0625, 0], [0, 0, 0]),
    'J2': (STANDARD + 'Connector_JST.3dshapes/JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal.step', [0, 0, 0], [0, 0, 0]),
    'U2': (STANDARD + 'Package_SO.3dshapes/TSSOP-16_4.4x5mm_P0.65mm.step', [0, 0, 0], [0, 0, -90]),
    'U4': (STANDARD + 'Package_SO.3dshapes/TSSOP-16_4.4x5mm_P0.65mm.step', [0, 0, 0], [0, 0, -90]),
    'L1': (STANDARD + 'Inductor_SMD.3dshapes/L_Wuerth_MAPI-3020.step', [0, 0, 0], [0, 0, 0]),
    'U5': ('${KIPRJMOD}/models/TI_RGT16_3x3_EP1p68_dimensioned.step', [0, 0, 0], [0, 0, 0]),
    'SW100': ('${KIPRJMOD}/models/CK_JS102011SAQN_dimensioned.step', [0, 0, 0], [0, 0, 0]),
}


def without_models(tree):
    if not isinstance(tree, list):
        return tree
    return [without_models(item) for item in tree
            if not (isinstance(item, list) and item and item[0] == 'model')]


def geometry_sha(tree):
    return hashlib.sha256(dumps(without_models(tree)).encode()).hexdigest()


def repair(ref, footprint):
    previous = geometry_sha(footprint)
    models = children(footprint, 'model')
    if ref in CHOICES:
        path, offset, rotate = CHOICES[ref]
        models = [form('model', path, form('offset', form('xyz', *offset)),
                       form('scale', form('xyz', 1, 1, 1)), form('rotate', form('xyz', *rotate)))]
    elif ref.startswith('SW') and ref != 'SW100' and ref != 'SW1' or ref == 'JP1':
        # EC electrodes are on the PCB; NiZ housings belong to the plate.
        # The old Topre bodies also depicted unpopulated positions. JP1 is DNP.
        models = []
    else:
        models = copy.deepcopy(models)
        for model in models:
            model[1] = model[1].replace('${KICAD6_3DMODEL_DIR}', '${KICAD10_3DMODEL_DIR}')
            if model[1].endswith('.wrl'):
                model[1] = model[1][:-4] + '.step'
    footprint[:] = without_models(footprint) + models
    assert geometry_sha(footprint) == previous, 'Non-model footprint change: ' + ref


def main():
    tree = loads(PCB.read_text())
    before = geometry_sha(tree)
    frozen = json.loads((BASE / 'frozen-footprints.json').read_text())
    for footprint in children(tree, 'footprint'):
        ref = next(p[2] for p in children(footprint, 'property') if p[1] == 'Reference')
        repair(ref, footprint)
        path = BASE / 'YAECKB.pretty' / (frozen[ref]['id'].split(':')[1] + '.kicad_mod')
        library = loads(path.read_text())
        repair(ref, library)
        path.write_text(dumps(library) + '\n')
    assert geometry_sha(tree) == before, 'Non-model PCB data changed'
    PCB.write_text(dumps(tree) + '\n')
    print('Native models repaired; all non-model board/footprint data unchanged')


if __name__ == '__main__':
    main()
