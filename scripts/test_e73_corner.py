#!/usr/bin/env python3
"""Exercise actual PCB mutations in isolated KiCad processes.

Reseal fixture hashes deliberately, so rejection must come from native semantic
or copper geometry checks, not merely a changed-file hash. No source is edited.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from kicad_sexpr import child, children, dumps, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/e73-hhkb-corner'
WORK = ROOT / '.assembly-work/e73-corner/faults'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original = {p: sha(p) for p in [ROOT/'hardware/e73-corner-spec.json', BASE/'EC60-nRF52840.kicad_pcb']}
    results = []
    for case, expected in [('control', ''), ('wrong-GPIO-net', 'Changed pin identity or role'),
                           ('body-over-effective-key', 'Module overlaps effective sensing copper'),
                           ('missing-antenna-keepout', 'Copper in provisional antenna band')]:
        folder = WORK / case
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        for p in BASE.iterdir():
            if p.is_file() and (p.suffix in ['.kicad_pcb', '.kicad_sch', '.kicad_pro', '.kicad_sym'] or p.name in ['sym-lib-table', 'fp-lib-table']):
                shutil.copyfile(p, folder / p.name)
        (folder / 'YAECKB.pretty').symlink_to((BASE / 'YAECKB.pretty').resolve(), target_is_directory=True)
        (folder / 'audit').mkdir()
        spec = json.loads((ROOT / 'hardware/e73-corner-spec.json').read_text())
        spec['output_directory'] = str(folder.relative_to(ROOT))
        path = folder / 'EC60-nRF52840.kicad_pcb'
        tree = loads(path.read_text())
        ref = lambda f: next(p[2] for p in children(f, 'property') if p[1] == 'Reference')
        module = next(f for f in children(tree, 'footprint') if ref(f) == 'U1')
        refill = False
        if case == 'wrong-GPIO-net':
            pad = next(p for p in children(module, 'pad') if p[1] == '4')
            child(pad, 'net')[1] = 'USB_5V'
        elif case == 'body-over-effective-key':
            child(module, 'at')[2] = float(child(module, 'at')[2])-6
            spec['module_origin_PCB_mm'][1] -= 6
            for key in ['module_body_PCB_mm', 'provisional_antenna_PCB_mm']:
                spec[key][1] -= 6
                spec[key][3] -= 6
        elif case == 'missing-antenna-keepout':
            zone = next(z for z in children(tree, 'zone') if child(z, 'name') and child(z, 'name')[1] == 'E73_CORNER_ANTENNA_PROVISIONAL')
            tree.remove(zone)
            refill = True
        path.write_text(dumps(tree)+'\n')
        if refill:
            code = ('import pcbnew as p; b=p.LoadBoard('+repr(str(path))+'); '
                    'p.ZONE_FILLER(b).Fill(b.Zones()); b.BuildConnectivity(); p.SaveBoard('+repr(str(path))+',b)')
            subprocess.run([sys.executable, '-c', code], check=True, capture_output=True)
        spec_path = folder / 'fixture-spec.json'
        spec_path.write_text(json.dumps(spec, indent=2)+'\n')
        build = json.loads((BASE / 'audit/placement-build.json').read_text())
        build['source_sha256'].pop('hardware/e73-corner-spec.json')
        build['source_sha256'][str(spec_path.relative_to(ROOT))] = sha(spec_path)
        build['pcb_sha256'] = sha(path)
        (folder / 'audit/placement-build.json').write_text(json.dumps(build, indent=2)+'\n')
        code = 'import sys; sys.path.insert(0,'+repr(str(ROOT/'scripts'))+'); import check_e73_corner as c; c.SPEC=c.Path('+repr(str(spec_path))+'); c.main()'
        result = subprocess.run([sys.executable, '-c', code], text=True, capture_output=True)
        (folder / 'check.log').write_text(result.stdout+result.stderr)
        if case == 'control':
            assert result.returncode == 0, result.stderr[-2000:]
        else:
            assert result.returncode != 0 and expected in result.stderr, (case, result.returncode, result.stderr[-2000:])
        results.append(dict(case=case, expected_rejection=expected or None, rejected=bool(expected), exit_code=result.returncode))
    assert all(sha(p) == digest for p,digest in original.items()), 'Mutation test edited its source'
    sources = [ROOT/'hardware/e73-corner-spec.json', BASE/'EC60-nRF52840.kicad_pcb',
               BASE/'audit/placement-build.json', ROOT/'scripts/check_e73_corner.py',
               ROOT/'scripts/kicad_sexpr.py', Path(__file__)]
    report = dict(status='native-placement-mutation-checks-passed', physical_verification=False,
                  manufacturing_released=False, control_runs=1, rejected_mutations=3, cases=results,
                  resealed_fixture_hashes=True, source_unchanged=True,
                  source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources},
                  limits=['Placement and provisional copper-band checks only', 'Does not establish routing completion, RF or EC hardware acceptance'])
    (BASE/'audit/placement-faults.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
