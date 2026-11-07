#!/usr/bin/env python3
"""Check current native model closure, actual STEP geometry and SMT landing."""
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
from kicad_sexpr import child, children, dumps, loads
from usb_short_model_contract import BASE, ROOT, SPEC, fitted_refs, resolve, sha, validate_native

WORK = ROOT / '.assembly-work/usb-short-models'
CLI = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
NATIVE = os.environ.get('KICAD_PYTHON', '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3')
CONTACTS = {'J1': 6, 'J2': 5, 'J4': 6, 'J5': 4, 'U2': 16, 'U4': 16, 'L1': 2}


def pin1_marker(shape, part):
    """The TSSOP dot must occupy pin 1's quadrant; symmetric feet cannot prove this."""
    low=bounds(shape)[2];faces=TopExp_Explorer(shape,TopAbs_FACE);marks=[]
    while faces.More():
        b=bounds(faces.Current());faces.Next()
        if .05<b[3]-b[0]<1 and .05<b[4]-b[1]<1 and abs(b[2]-low)<1e-5 and abs(b[5]-low)<1e-5:
            marks.append([(b[0]+b[3])/2,(b[1]+b[4])/2])
    assert len(marks)==1,'TSSOP pin-1 dot not uniquely identified'
    marker=marks[0];pin=next(p['center_native_XY_mm'] for p in part['pads'] if p['pin']=='1')
    origin=[part['position_pcb_mm'][0],-part['position_pcb_mm'][1]]
    assert all((marker[i]-origin[i])*(pin[i]-origin[i])>0 for i in range(2)),('TSSOP pin-1 mark in wrong quadrant',marker,pin,origin)
    return dict(marker_native_XY_mm=marker,pin1_native_XY_mm=pin,quadrant_matches=True)


def landing(shape, pads, expected, allow_core=False):
    """Bound each planar seating face against actual inscribed copper polygons."""
    plane = bounds(shape)[5]
    copper = [unary_union([Polygon(p['outer'], p['holes']) for p in pad['polygons_native_XY_mm']])
              for pad in pads]
    feet = []
    unmatched = []
    visited = set()
    faces = TopExp_Explorer(shape, TopAbs_FACE)
    while faces.More():
        b = bounds(faces.Current())
        faces.Next()
        if abs(b[2]-b[5]) > 1e-5 or not plane-.15-1e-6 <= b[5] <= plane+1e-6 or (b[3]-b[0])*(b[4]-b[1]) < 1e-5:
            continue
        foot = rectangle(b[0], b[1], b[3], b[4])
        ratios = [foot.intersection(polygon).area/foot.area for polygon in copper]
        owners = [i for i, polygon in enumerate(copper)
                  if (ratios[i] >= .8 if allow_core else polygon.buffer(1e-6).covers(foot))]
        if not owners:
            if abs(b[5]-plane) < 1e-5:
                unmatched.append(b)
            continue
        assert len(owners) == 1, 'Ambiguous native solder-foot ownership'
        at = owners[0]
        visited.add(at)
        feet.append({'pin': pads[at]['pin'], 'bounds_native_mm': b,
                     'modeled_seating_plane_difference_mm': plane-b[5],
                     'modeled_flat_face_copper_overlap_ratio': ratios[at],
                     'minimum_copper_edge_margin_mm': foot.distance(copper[at].boundary)})
    assert len(visited) == expected, ('Native solder feet miss copper lands', len(visited), expected, unmatched)
    assert allow_core or not unmatched, ('Native seating faces outside copper', unmatched)
    return dict(seating_plane_native_Z_mm=plane, matched_lands=len(visited), planar_feet=feet,
                nonmetal_core_seating_faces=unmatched,
                modeled_seating_band_mm=.15,
                minimum_required_overlap_ratio=.8 if allow_core else 1,
                method='Exact planar STEP-face bounds within 0.15 mm of PCBward seating, compared with native copper polygons approximated 0.002 mm inward. SH/PH/TSSOP feet require full containment; L1 follows the manufacturer lands with intended inward heel overhang and requires >=80% nominal flat-face overlap. SH modeled seating heights are not physical coplanarity acceptance. Only L1 may ignore a nonmetal core face')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force-export', action='store_true')
    args = parser.parse_args()
    pcb = BASE / 'EC60-nRF52840.kicad_pcb'
    tree = loads(pcb.read_text())
    spec = json.loads(SPEC.read_text())
    footprints = validate_native(tree, spec)
    WORK.mkdir(parents=True, exist_ok=True)
    subprocess.run([NATIVE, str(ROOT / 'scripts/export_usb_short_model_inputs.py')], check=True)
    native = json.loads((WORK / 'native-inputs.json').read_text())
    assert native['PCB_sha256'] == sha(pcb) and set(native['parts']) == fitted_refs()
    for f in children(tree, 'footprint'):
        for m in children(f, 'model'):
            m[1] = str(resolve(m[1]))
    source = WORK / 'resolved.kicad_pcb'
    source.write_text(dumps(tree) + '\n')
    version = subprocess.check_output([CLI, 'version'], text=True).strip()
    cache_path = WORK / 'export-cache.json'
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    parts_dir = WORK / 'parts'
    parts_dir.mkdir(exist_ok=True)
    def export(ref):
        target = parts_dir / (ref + '.step')
        model = spec['parts'][ref]['model'][1]
        key = hashlib.sha256((sha(pcb)+sha(resolve(model))+version+sha(Path(__file__))).encode()).hexdigest()
        saved = cache.get(ref, {})
        if args.force_export or not target.exists() or saved.get('key') != key or saved.get('sha256') != sha(target):
            result = subprocess.run([CLI, 'pcb', 'export', 'step', '--no-board-body', '--component-filter', ref,
                                     '--user-origin', '0x0mm', '-f', '-o', str(target), str(source)], text=True, capture_output=True)
            if result.returncode:
                raise RuntimeError('Native model export failed for '+ref+':\n'+(result.stdout+result.stderr)[-4000:])
            text = target.read_text()
            header, data = text.split('DATA;', 1)
            header = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?', '2000-01-01T00:00:00', header)
            target.write_text('\n'.join(line.rstrip() for line in (header+'DATA;'+data).splitlines())+'\n')
        return ref, target, {'key': key, 'sha256': sha(target)}
    # KiCad's model/cache resources are not reliably isolated across concurrent
    # CLI processes on the tested macOS installation. Export deterministically.
    exports = []
    for ref in sorted(fitted_refs()):
        exports.append(export(ref))
        if len(exports) % 10 == 0:
            print('Native component STEP exports:', len(exports), '/ 75', flush=True)
    cache_path.write_text(json.dumps({ref: record for ref, _, record in exports}, indent=2)+'\n')
    parts = {}
    for ref, target, record in exports:
        shape = load(target)
        b = bounds(shape)
        assert native['parts'][ref]['back'] and b[5] <= (1.5 if ref == 'SW100' else .5 if ref=='SW1' else 1e-6), ('Model on wrong PCB side', ref, b)
        item = dict(path=str(target.relative_to(ROOT)), sha256=record['sha256'], bounds_native_mm=b,
                    value=spec['parts'][ref]['value'],
                    **{k: native['parts'][ref][k] for k in ['position_pcb_mm', 'angle_deg']})
        if ref in CONTACTS:
            item['landing'] = landing(shape, native['parts'][ref]['pads'], CONTACTS[ref], ref == 'L1')
        if ref in ['U2','U4']:
            item['pin1_marker']=pin1_marker(shape,native['parts'][ref])
        if ref=='SW1':
            pegs=[p for p in native['parts'][ref]['pads'] if p['is_npth']]
            assert len(pegs)==2 and all(p['drill_mm']==[.75,.75] for p in pegs)
            item['intentional_mount_penetration']={'type':'Panasonic locating pegs in two 0.75 mm NPTH holes','tolerance_qualified':False}
        if ref == 'SW100':
            pegs = [p for p in native['parts'][ref]['pads'] if p['is_npth']]
            assert len(pegs) == 2 and all(p['drill_mm'] == [.9, .9] for p in pegs)
            assert abs(abs(pegs[0]['center_native_XY_mm'][0]-pegs[1]['center_native_XY_mm'][0])-6.8) < 1e-6
            item['intentional_mount_penetration'] = {'type': 'Two 0.8 mm nominal pegs in 0.9 mm NPTH, 6.8 mm pitch',
                                                     'nominal_diametral_gap_mm': .1, 'tolerance_qualified': False}
        parts[ref] = item
    source_files = [pcb, SPEC, BASE/'models/non-model-baseline.json', BASE/'frozen-footprints.json',
                    BASE/'mainboard-purchase.csv', BASE/'models/CELESTIAL-LICENSE.txt',
                    ROOT/'scripts/usb_short_model_contract.py', ROOT/'scripts/repair_usb_short_models.py',
                    ROOT/'scripts/kicad_sexpr.py', ROOT/'scripts/cad_geometry.py',
                    ROOT/'scripts/export_usb_short_model_inputs.py', Path(__file__)]
    source_files += [ROOT/'scripts/build_usb_short_package_models.py',ROOT/'scripts/repair_usb_short_charger_package.py',ROOT/'scripts/usb_short_charger_contract.py']
    from usb_short_charger_contract import verify_charger_package
    charger_windows=verify_charger_package()
    source_files += sorted((BASE/'YAECKB.pretty').glob('*.kicad_mod'))
    source_files += [resolve(p) for p in spec['sources'] if p.startswith('${KIPRJMOD}')]
    report = dict(status='native-model-closure-and-landing-passed', physical_verification=False,
                  manufacturer_tolerances_qualified=False, fitted_models=75,
                  only_documented_thermal_package_and_model_changes=True, external_KiCad_version=version,
                  envelope_modeling_allowance_mm=.1, parts=parts, thermal_package_windows=charger_windows,
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in source_files},
                  external_model_sha256={p: sha(resolve(p)) for p in spec['sources'] if not p.startswith('${KIPRJMOD}')},
                  limits=['Native models are nominal visual/landing geometry, not supplier maximum tolerance envelopes',
                          'J2 is the attributed Celestial nominal model; supplier molded-part tolerance acceptance remains open',
                          'Pin landing does not prove solder quality or electrical operation',
                          'The retained long-USB reference PCB is outside this current-candidate native-model repair'])
    (BASE/'audit/native-models.json').write_text(json.dumps(report, indent=2)+'\n')
    print('75 native models resolved and exported; seven package landing checks passed; only documented thermal-package and native-model changes')


if __name__ == '__main__':
    main()
