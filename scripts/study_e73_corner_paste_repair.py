#!/usr/bin/env python3
"""Reproduce the ordinary-drill C42/C48 trial without replacing the selected board."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pcbnew as pcb

from check_e73_corner_power import BASE, BOARD, ROOT, layer_shapes, process_checks

WORK = ROOT / '.assembly-work/e73-corner/paste-repair'
CLI = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
BASELINE = 'cbe66a53abd9f4e5674115a2891e27735a093c13d25cfff900507fe63420447e'
MOVES = {
    '93479cbe-e898-4dfd-ae63-fa5383607b43': ('C42', (122.634684,142.577802), (122.12,142.315)),
    'd17868b1-6489-4c01-b95e-c5c196fb1bea': ('C48', (107.454177,147.340215), (107.1368,147.6572)),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def position(point):
    return pcb.VECTOR2I(*(pcb.FromMM(value) for value in point))


def main():
    assert sha(BOARD) == BASELINE, 'Review applicability to the new source PCB'
    WORK.mkdir(parents=True, exist_ok=True)
    inputs = [BOARD, Path(__file__), ROOT/'scripts/check_e73_corner_power.py',
              ROOT/'scripts/check_yeti60_signal_paths.py', ROOT/'scripts/kicad_sexpr.py',
              ROOT/'hardware/e73-power-repair-spec.json', ROOT/'mechanical/pcb-fabrication-spec.json']
    project_files = [path for path in BASE.iterdir()
                     if path.suffix in ('.kicad_pro','.kicad_sch','.kicad_sym')
                     or path.name in ('fp-lib-table','sym-lib-table')]
    inputs.extend(project_files)
    for path in project_files:
        shutil.copyfile(path, WORK/path.name)
    library = BASE/'YAECKB.pretty'
    shutil.copytree(library, WORK/library.name, dirs_exist_ok=True)
    inputs.extend(sorted(library.glob('*.kicad_mod')))

    work_board = WORK/BOARD.name
    candidate = pcb.LoadBoard(str(BOARD))
    initial = {track.m_Uuid.AsString(): track for track in candidate.GetTracks()}
    footprints = {f.GetReference():f for f in candidate.GetFootprints()}
    for identifier, (ref, old, new) in MOVES.items():
        via = initial[identifier]
        assert isinstance(via,pcb.PCB_VIA) and via.GetPosition() == position(old)
        assert via.GetNetname() == 'GND'
        via.SetPosition(position(new))
        via.SetWidth(pcb.FromMM(.5))
        via.SetDrill(pcb.FromMM(.3))
        if ref == 'C42':
            pad = next(p for p in footprints[ref].Pads() if p.GetNumber()=='2')
            assert pad.GetNetname() == 'GND'
            bridge = pcb.PCB_TRACK(candidate)
            bridge.SetUuid(pcb.KIID('da85dd15-5451-4bdf-be7d-e757e41d0b42'))
            bridge.SetStart(pad.GetPosition())
            bridge.SetEnd(via.GetPosition())
            bridge.SetWidth(pcb.FromMM(.25))
            bridge.SetLayer(pcb.B_Cu)
            bridge.SetNetCode(via.GetNetCode())
            candidate.Add(bridge)
    assert pcb.SaveBoard(str(work_board),candidate)
    drc_report = WORK/'drc.json'
    with (WORK/'drc.log').open('w') as log:
        subprocess.run([CLI,'pcb','drc','--format','json','--all-track-errors','--refill-zones',
                        '--save-board','--schematic-parity','--severity-all','-o',str(drc_report),
                        str(work_board)],stdout=log,stderr=subprocess.STDOUT,check=True)
    drc = json.loads(drc_report.read_text())
    errors = {key:sum(row['severity']=='error' for row in drc[key])
              for key in ('violations','unconnected_items','schematic_parity')}
    assert not any(errors.values()), drc_report

    repaired = pcb.LoadBoard(str(work_board))
    profile = json.loads((ROOT/'mechanical/pcb-fabrication-spec.json').read_text())
    process = process_checks(repaired,work_board,None,profile)
    assert process['through_vias'] == 856
    footprints = {footprint.GetReference():footprint for footprint in repaired.GetFootprints()}
    moved = []
    for identifier, (ref, old, new) in MOVES.items():
        target = position(new)
        gaps = {}
        for layer in (pcb.B_Mask,pcb.B_Paste):
            polygons = layer_shapes(footprints[ref],layer)
            assert not any(poly.Contains(target) for poly in polygons)
            measured = pcb.ToMM(min(poly.Distance(target) for poly in polygons))-.15
            assert measured >= .10, (ref, measured)
            gaps[repaired.GetLayerName(layer)] = measured
        moved.append({'via_UUID':identifier,'ref':ref,'from_PCB_mm':old,'to_PCB_mm':new,
                      'drill_mm':.30,'diameter_mm':.50,'nominal_gaps_mm':gaps})
    assert sha(BOARD) == BASELINE
    report = {
        'status':'two-via-trial-passed-native-DRC-and-nominal-aperture-clearance',
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in inputs},
        'candidate_PCB_sha256':sha(work_board), 'native_DRC_errors':errors,
        'moved_ground_vias':moved, 'candidate_default_selected':False,
        'manufacturing_released':False, 'physical_verification':False,
        'limits':['Candidate board is generated under ignored trial output only',
                  'Charging voltage drop is unaffected by these two local edits',
                  'Mask registration, SW1 margin and power delivery still require work'],
    }
    destination = BASE/'audit/paste-repair-trial.json'
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'], moved)


if __name__ == '__main__':
    main()
