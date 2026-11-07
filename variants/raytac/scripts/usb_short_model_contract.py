"""Current native-model closure and conservative assembly-envelope agreement."""
import copy
import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path
from kicad_sexpr import child, children, loads
from repair_usb_short_models import geometry_sha

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'
SPEC = BASE / 'models/model-sources.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(path):
    if path.startswith('${KIPRJMOD}/'):
        return BASE / path.split('}/', 1)[1]
    assert path.startswith('${KICAD10_3DMODEL_DIR}/'), 'Unresolved/private model reference: ' + path
    default = ('/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels'
               if os.name != 'nt' and Path('/Applications/KiCad').exists()
               else '/usr/share/kicad/3dmodels')
    return Path(os.environ.get('KICAD10_3DMODEL_DIR', default)) / path.split('}/', 1)[1]


def fitted_refs():
    with (BASE / 'mainboard-purchase.csv').open() as stream:
        refs = [ref.strip() for row in csv.DictReader(stream) for ref in row['References'].split(',')]
    assert len(refs) == len(set(refs)) == 75
    return set(refs)


def validate_native(tree, spec):
    footprints = {next(p[2] for p in children(f, 'property') if p[1] == 'Reference'): f
                  for f in children(tree, 'footprint')}
    expected = fitted_refs()
    assert set(spec['parts']) == expected, 'Model/BOM reference coverage differs'
    actual = {ref for ref, f in footprints.items() if children(f, 'model')}
    assert actual == expected, 'Missing/extra models, DNP body or legacy electrode housing'
    for ref, f in footprints.items():
        models = children(f, 'model')
        if ref not in expected:
            assert not models
            continue
        assert len(models) == 1 and not child(models[0], 'hide'), 'Duplicate/hidden model: ' + ref
        model = models[0]
        assert model == spec['parts'][ref]['model'], 'Wrong model identity/pose: ' + ref
        file = resolve(model[1])
        assert file.is_file(), 'Install the matching KiCad 10 3D library or restore the local model: ' + str(file)
        assert sha(file) == spec['sources'][model[1]]['sha256'], 'Model source changed: ' + str(file)
        footprint_id = f[1].split(':')[1]
        library = loads((BASE / 'YAECKB.pretty' / (footprint_id + '.kicad_mod')).read_text())
        assert children(library, 'model') == models, 'Native/library model mismatch: ' + ref
    baseline = json.loads((BASE / 'models/non-model-baseline.json').read_text())
    from repair_usb_short_charger_package import apply_tree, lands
    def no_fills(value):
        if not isinstance(value,list):return value
        return [no_fills(v) for v in value if not (isinstance(v,list) and v and v[0] in ['filled_polygon','fill_segments'])]
    original=loads(subprocess.check_output(['git','show',baseline['baseline_commit']+':variants/raytac/hardware/usb-short-route/EC60-nRF52840.kicad_pcb'],cwd=ROOT).decode())
    assert geometry_sha(original)==baseline['non_model_sha256']['hardware/usb-short-route/EC60-nRF52840.kicad_pcb']
    apply_tree(original)
    assert geometry_sha(no_fills(tree))==geometry_sha(no_fills(original)),'Unlisted non-model board change beyond the documented thermal-package repair'
    for path,digest in baseline['non_model_sha256'].items():
        if path.endswith('.kicad_pcb'):continue
        current=loads((ROOT/path).read_text())
        ref=next((ref for ref in ['U5','U6'] if path.endswith('__'+ref+'.kicad_mod')),None)
        if ref:
            previous=loads(subprocess.check_output(['git','show',baseline['baseline_commit']+':variants/raytac/'+path],cwd=ROOT).decode())
            assert geometry_sha(previous)==digest
            lands(previous,ref)
            assert geometry_sha(current)==geometry_sha(previous),'Unlisted thermal footprint change: '+ref
        else:
            assert geometry_sha(current)==digest,'Non-model footprint data changed: '+path
    return footprints


def verify_report(report, check_payloads=True):
    assert report['status'] == 'native-model-closure-and-landing-passed'
    assert not report['physical_verification'] and not report['manufacturer_tolerances_qualified']
    assert report['fitted_models'] == 75 and set(report['parts']) == fitted_refs()
    for path, digest in report['source_sha256'].items():
        assert sha(ROOT / path) == digest, 'Stale native-model input: ' + path
    for path, digest in report['external_model_sha256'].items():
        assert sha(resolve(path)) == digest, 'Changed standard model: ' + path
    if check_payloads:
        for part in report['parts'].values():
            assert sha(ROOT / part['path']) == part['sha256'], 'Changed native part STEP'


def apply_model_envelopes(assembly):
    """Enlarge existing bounds to include complete nominal models and terminals.

    The extra margin is a modeling allowance, not a manufacturer tolerance.
    Never extend it through the intentional PCB mounting plane.
    """
    report = json.loads((BASE / 'audit/native-models.json').read_text())
    verify_report(report)
    data = copy.deepcopy(assembly)
    z = data['nominal_stack']['pcb_bottom_z']
    byref = {p['ref']: p for p in data['component_envelopes'] if p['ref'] not in {'R30', 'R31', 'JP1'}}
    margin = report['envelope_modeling_allowance_mm']
    for ref, part in report['parts'].items():
        b = [v + (z if i in (2, 5) else 0) for i, v in enumerate(part['bounds_native_mm'])]
        local_margin=0 if ref=='SW100' else margin
        enlarged = [v + (-local_margin if i < 3 else local_margin) for i, v in enumerate(b)]
        enlarged[5] = min(enlarged[5], z)
        if ref not in byref:
            byref[ref] = dict(ref=ref, value=part['value'], back=True,
                             position_pcb_mm=part['position_pcb_mm'], angle_deg=part['angle_deg'],
                             bounds_case_mm=enlarged, height_envelope_mm=z-enlarged[2],
                             height_basis='Native nominal model plus engineering modeling allowance; not supplier-qualified')
        component = byref[ref]
        previous = component['bounds_case_mm']
        component.setdefault('previous_envelope_bounds_case_mm', previous)
        component['bounds_case_mm'] = [min(previous[i], enlarged[i]) if i < 3 else max(previous[i], enlarged[i]) for i in range(6)]
        component['native_model_bounds_case_mm'] = b
        component['native_modeling_allowance_mm'] = margin
        component['height_envelope_mm'] = z-component['bounds_case_mm'][2]
    assert set(byref) == fitted_refs()
    data['component_envelopes'] = list(byref.values())
    data['native_model_report_sha256'] = sha(BASE / 'audit/native-models.json')
    return data
