#!/usr/bin/env python3
"""Replay and independently check the combined power routing and solder trial."""

import csv
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
import shutil
import subprocess

import pcbnew as pcb

from check_e73_corner_power import BASE, BOARD, ROOT, charge_screen, layer_shapes, process_checks, route_checks
from kicad_sexpr import child, children, dumps, loads

WORK = ROOT / '.assembly-work/e73-corner/charge-replay'
PATCH = ROOT / 'hardware/e73-corner-charge-trial.json'
CLI = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
KINDS = ('arc', 'via', 'segment')
WINDOWS = {
    'USB_5V': (86,115,123,151),
    'VBUS': (86,110,119,124),
    'USB_FEED': (334,105,351,117),
    'GND': (106,142,124,149),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def copper(tree):
    return {child(q, 'uuid')[1]:q for kind in KINDS for q in children(tree,kind)}


def patch_board(base, patch):
    assert not patch['candidate_default_selected']
    original = copper(base)
    records = patch['retired']
    assert len(records) == len({item['UUID'] for item in records}) == 68
    for record in records:
        form = original[record['UUID']]
        assert child(form, 'net')[1] == record['net'] in WINDOWS
        assert hashlib.sha256(dumps(form).encode()).hexdigest() == record['sha256']
        base.remove(form)
    seen = set(copper(base))
    for source in patch['added']:
        form = loads(source)
        identifier = child(form,'uuid')[1]
        net = child(form,'net')[1]
        assert identifier not in seen and form[0] in ('segment','via') and net in WINDOWS
        seen.add(identifier)
        x, y, X, Y = WINDOWS[net]
        points = [child(form,key)[1:3] for key in (('at',) if form[0]=='via' else ('start','end'))]
        assert all(x <= float(a) <= X and y <= float(b) <= Y for a,b in points), source
        if form[0]=='via':
            assert child(form,'layers')[1:] == ['F.Cu','B.Cu']
            assert float(child(form,'size')[1]) == .5 and float(child(form,'drill')[1]) == .3
        base.append(form)
    assert len(patch['added']) == 33
    return base


def strict_drc(pcb_path, project):
    config = read(project)
    for key,severity in config['board']['design_settings']['rule_severities'].items():
        if severity=='ignore':
            config['board']['design_settings']['rule_severities'][key] = 'warning'
    project.write_text(json.dumps(config))
    path = WORK/'drc.json'
    with (WORK/'drc.log').open('w') as log:
        subprocess.run([CLI,'pcb','drc','--format','json','--all-track-errors','--refill-zones',
                        '--save-board','--schematic-parity','--severity-all','-o',str(path),str(pcb_path)],
                       check=True,stdout=log,stderr=subprocess.STDOUT)
    drc = read(path)
    assert not drc['unconnected_items'] and not drc['schematic_parity']
    purchase = BASE/'mainboard-purchase.csv'
    with purchase.open() as data:
        fitted = {ref.strip() for row in csv.DictReader(data) for ref in row['References'].split(',')}
    refs = {f.m_Uuid.AsString():f.GetReference() for f in pcb.LoadBoard(str(pcb_path)).GetFootprints()}
    for row in drc['violations']:
        assert row['severity']=='warning' and row['type']=='missing_courtyard',row
        assert all(refs[item['uuid']] not in fitted for item in row['items']),row
    return {'errors':0, 'unconnected':0, 'schematic_parity':0,
            'non_purchased_courtyard_warnings':len(drc['violations'])}


def usb_reference(pcb_path):
    spec = read(ROOT/'hardware/e73-corner-spec.json')
    spec['output_directory'] = str(WORK.relative_to(ROOT))
    spec_path, copper_path = WORK/'spec.json', WORK/'copper.json'
    spec_path.write_text(json.dumps(spec))
    (WORK/'audit').mkdir(exist_ok=True)
    import sys
    with (WORK/'usb.log').open('w') as log:
        subprocess.run([sys.executable,str(ROOT/'scripts/export_e73_corner_geometry.py'),
                        '--pcb',str(pcb_path),'--output',str(copper_path)],check=True,
                       stdout=log,stderr=subprocess.STDOUT)
        subprocess.run(['uv','run','--offline','--python','3.14.7','--with-requirements',
                        str(ROOT/'requirements-audit.txt'),'python',str(ROOT/'scripts/check_e73_corner_usb.py'),
                        '--spec',str(spec_path),'--copper',str(copper_path),'--require-pass'],
                       check=True,stdout=log,stderr=subprocess.STDOUT)
    report = read(WORK/'audit/USB-reference.json')
    assert report['checks_passed'] and report['whole_ground_network_connected']
    return {key:report[key] for key in ('status','whole_ground_network_connected',
                                        'back_pair_minimum_actual_copper_clearance_mm','launches')}


def main():
    patch = read(PATCH)
    assert sha(BOARD)==patch['source_PCB_sha256']
    WORK.mkdir(parents=True,exist_ok=True)
    pcb_path = WORK/BOARD.name
    project_files = sorted(path for path in BASE.iterdir() if path.suffix in
                           ('.kicad_pro','.kicad_sch','.kicad_sym') or
                           path.name in ('fp-lib-table','sym-lib-table'))
    for path in project_files:
        shutil.copyfile(path,WORK/path.name)
    library_path = WORK/'YAECKB.pretty'
    if not library_path.exists():
        library_path.symlink_to(BASE/'YAECKB.pretty',target_is_directory=True)
    base = loads(BOARD.read_text())
    expected = patch_board(loads(BOARD.read_text()),patch)
    pcb_path.write_text(dumps(expected)+'\n')
    drc = strict_drc(pcb_path,pcb_path.with_suffix('.kicad_pro'))
    observed = loads(pcb_path.read_text())
    assert copper(observed)==copper(expected)
    groups = {node[0] for node in base if isinstance(node,list)} - set(KINDS) - {'zone'}
    for key in groups:
        assert sorted(map(dumps,children(observed,key))) == sorted(map(dumps,children(base,key))),key
    # Only zone fill polygons may differ. Rule areas, priority and zone
    # constraints retain their original definitions.
    def zone_definitions(tree):
        return sorted(dumps([v for v in zone if not (isinstance(v,list) and v[0]=='filled_polygon')])
                      for zone in children(tree,'zone'))
    assert zone_definitions(base)==zone_definitions(observed)
    usb = usb_reference(pcb_path)
    board = pcb.LoadBoard(str(pcb_path))
    power_spec_path = ROOT/'hardware/e73-power-repair-spec.json'
    profile_path = ROOT/'mechanical/pcb-fabrication-spec.json'
    harness_path = BASE/'audit/harness-study.json'
    previous_path = BASE/'audit/power-process.json'
    power, profile = read(power_spec_path), read(profile_path)
    fabrication = process_checks(board,pcb_path,power,profile)
    assert fabrication['through_vias']==852
    warning_rows = [r for r in fabrication['annulus_overlaps_SMD_lands']
                    if any(gap<0 for gap in r['same_footprint_drill_to_aperture_mm'].values())]
    assert not warning_rows,warning_rows
    trial_paste_path = BASE/'audit/paste-repair-trial.json'
    case_gaps = {}
    for moved in read(trial_paste_path)['moved_ground_vias']:
        f = next(f for f in board.GetFootprints() if f.GetReference()==moved['ref'])
        point = pcb.VECTOR2I(*(pcb.FromMM(v) for v in moved['to_PCB_mm']))
        case_gaps[moved['ref']] = {}
        for layer in (pcb.B_Mask,pcb.B_Paste):
            gap = pcb.ToMM(min(shape.Distance(point) for shape in layer_shapes(f,layer)))-.15
            assert gap>=.1
            case_gaps[moved['ref']][board.GetLayerName(layer)] = gap

    paths = route_checks(board,power,profile)
    sensitivity = charge_screen(paths,read(harness_path))
    old = read(previous_path)
    checked_paths = ['J4.1 to J5.1','J1.1 to F1.2','F1.1 to U5.13','F1.1 to U1.27']
    comparison = {}
    for key in checked_paths:
        comparison[key] = {'before':old['local_power_paths'][key],'candidate':paths[key]}
        assert paths[key]['trace_only_20C_ohm'] < old['local_power_paths'][key]['trace_only_20C_ohm']
    baseline_r = old['charge_headroom']['modeled_series_at_temperature_ohm']
    trial_r = sensitivity['modeled_series_at_temperature_ohm']
    assert trial_r < .60*baseline_r
    sources = [BOARD,PATCH,Path(__file__),power_spec_path,profile_path,harness_path,previous_path,
               trial_paste_path,BASE/'mainboard-purchase.csv',ROOT/'hardware/e73-corner-spec.json',
               ROOT/'requirements-audit.txt',*project_files,*sorted((BASE/'YAECKB.pretty').glob('*.kicad_mod'))]
    for script in ('check_e73_corner_power.py','check_yeti60_signal_paths.py','kicad_sexpr.py',
                   'export_e73_corner_geometry.py','export_e73_usb_ground.py',
                   'check_e73_corner_usb.py','plan_e73_corner_usb.py'):
        sources.append(ROOT/'scripts'/script)
    report = {
        'status':'combined-charge-routing-and-solder-trial-passed',
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},
        'candidate_PCB_sha256':sha(pcb_path), 'candidate_default_selected':False,
        'replaced_copper_by_net':dict(Counter(r['net'] for r in patch['retired'])),
        'native_DRC':drc, 'filled_USB_reference':usb,
        'through_via_count':fabrication['through_vias'],
        'relocated_drill_to_own_aperture_gaps_mm':case_gaps,
        'path_comparison':comparison, 'charge_headroom':sensitivity,
        'trace_and_wire_drop_reduction_fraction':1-trial_r/baseline_r,
        'physical_verification':False, 'manufacturing_released':False,
    }
    (BASE/'audit/charge-feed-trial.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],drc, f'modeled series {baseline_r:.3f} -> {trial_r:.3f} ohm')


if __name__=='__main__':
    main()
