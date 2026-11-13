#!/usr/bin/env python3
"""Export/check the actual E73 J4/J5/C32 models, not a Raytac assembly result.

Run with the CAD audit runtime. Other fitted models and supplier tolerances
remain outside this local closure; no full assembly/production approval.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from shapely.geometry import Polygon, box as rectangle
from shapely.ops import unary_union
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from cad_geometry import bounds, load
from check_yeti60_assembly import move
from kicad_sexpr import child, children, dumps, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/e73-usb-repair'
WORK = ROOT / '.assembly-work/e73-usb-local-models'
CLI = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def landing(shape, pads, expected):
    """Same conservative planar-foot method as the Raytac local model audit.

    Evaluate these E73 STEP faces against these E73 inscribed copper polygons.
    The 0.15 mm band describes modeled coplanarity, not a supplier tolerance.
    """
    plane = bounds(shape)[5]
    copper = [unary_union([Polygon(p['outer'], p['holes']) for p in pad['polygons_native_XY_mm']]) for pad in pads]
    feet = []
    visited = set()
    faces = TopExp_Explorer(shape, TopAbs_FACE)
    while faces.More():
        bb = bounds(faces.Current()); faces.Next()
        if abs(bb[2] - bb[5]) > .00001 or not plane - .150001 <= bb[5] <= plane + .000001 or (bb[3] - bb[0]) * (bb[4] - bb[1]) < .00001:
            continue
        foot = rectangle(bb[0], bb[1], bb[3], bb[4])
        owners = [i for i, polygon in enumerate(copper) if polygon.buffer(.000001).covers(foot)]
        if not owners:
            assert abs(bb[5] - plane) > .00001, ('Modeled seating face misses copper', bb)
            continue
        assert len(owners) == 1, 'Ambiguous model foot'
        i = owners[0]; visited.add(i)
        feet.append({'pin': pads[i]['pin'], 'bounds_native_mm': bb,
                     'foot_copper_overlap_fraction': foot.intersection(copper[i]).area / foot.area})
    assert len(visited) == expected, ('Model lands miss E73 copper', len(visited), expected)
    return {'matched_lands': len(visited), 'planar_feet': feet, 'modeled_seating_plane_native_Z_mm': plane}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-python', default='/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3')
    args = parser.parse_args()
    report_path = BASE / 'audit/local-models.json'
    report_path.unlink(missing_ok=True)
    native_path = WORK / 'native-inputs.json'
    WORK.mkdir(parents=True, exist_ok=True)
    subprocess.run([args.kicad_python, str(ROOT / 'scripts/export_e73_usb_ground.py'), '--output', str(native_path)], check=True, capture_output=True)
    native = json.loads(native_path.read_text())
    for name, digest in native['source_sha256'].items():
        assert sha(ROOT / name) == digest
    board_path = BASE / 'EC60-nRF52840.kicad_pcb'
    tree = loads(board_path.read_text())
    footprints = {next(p[2] for p in children(f, 'property') if p[1] == 'Reference'): f for f in children(tree, 'footprint')}
    model_dir = Path(os.environ.get('KICAD10_3DMODEL_DIR', '/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels'))
    model_sources = {}
    for ref in ['J4', 'J5', 'C32']:
        models = children(footprints[ref], 'model')
        assert len(models) == 1 and not child(models[0], 'hide'), ('Missing/hidden model', ref)
        model = models[0]
        assert model[1].startswith('${KICAD10_3DMODEL_DIR}/')
        source = model_dir / model[1].split('}/', 1)[1]
        assert source.is_file(), ('Missing standard KiCad model', source)
        model_sources[ref] = {'path': str(source), 'sha256': sha(source)}
        model[1] = str(source)
    resolved = WORK / 'resolved.kicad_pcb'
    resolved.write_text(dumps(tree) + '\n')
    parts = {}
    # KiCad STEP/model-cache resources are not reliably isolated across
    # simultaneous CLI exports. Keep the three exports sequential.
    for ref, count in [('J4', 6), ('J5', 4), ('C32', 2)]:
        target = WORK / (ref + '.step')
        result = subprocess.run([CLI, 'pcb', 'export', 'step', '--no-board-body', '--component-filter', ref,
                                 '--user-origin', '0x0mm', '-f', '-o', str(target), str(resolved)], text=True, capture_output=True)
        assert result.returncode == 0, (ref, (result.stdout + result.stderr)[-3000:])
        header, data = target.read_text().split('DATA;', 1)
        header = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?', '2000-01-01T00:00:00', header)
        target.write_text('\n'.join(line.rstrip() for line in (header + 'DATA;' + data).splitlines()) + '\n')
        shape = load(target)
        bb = bounds(shape)
        assert bb[5] <= 0 and bb[2] < bb[5], ('Empty/front-side model', ref, bb)
        contact = landing(shape, native['local_model_pads'][ref], count)
        if ref == 'J4':
            try:
                landing(move(shape, x=1), native['local_model_pads'][ref], count)
            except AssertionError:
                pass
            else:
                raise AssertionError('Shifted solder feet were accepted')
        fab=native['local_model_Fab_bounds_native_XY_mm'][ref]
        envelope=[min(bb[0],fab[0]),min(bb[1],fab[1]),bb[2],max(bb[3],fab[2]),max(bb[4],fab[3]),bb[5]]
        parts[ref] = {'path': str(target.relative_to(ROOT)), 'sha256': sha(target), 'bounds_native_mm': bb,
                      'native_Fab_bounds_native_XY_mm':fab,'nominal_model_and_Fab_union_bounds_native_mm':envelope,
                      'landing': contact, 'model_source': model_sources[ref]}
    inputs = [Path(__file__), board_path, ROOT / 'scripts/export_e73_usb_ground.py', ROOT / 'scripts/cad_geometry.py',
              ROOT / 'scripts/check_yeti60_assembly.py', ROOT / 'scripts/kicad_sexpr.py']
    report = {'status': 'local-native-model-and-landing-passed', 'parts': parts,
              'manufacturing_released': False, 'physical_verification': False, 'complete_model_closure': False,
              'shifted_header_foot_fault_detected': True,
              'kicad_version': subprocess.check_output([CLI, 'version'], text=True).strip(),
              'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in inputs},
              'limits': ['Only J4/J5/C32 nominal geometry; other fitted parts and the E73 module remain outside this local closure',
                         'Nominal standard-model seating is not a physical coplanarity or supplier-tolerance acceptance',
                         'Actual selected MPN dimensions, solder/board bow and mechanical envelopes require separate checks']}
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], {r: p['landing']['matched_lands'] for r, p in parts.items()})


if __name__ == '__main__':
    main()
