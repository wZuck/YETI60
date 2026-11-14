#!/usr/bin/env python3
"""Reject a real reference-plane cut in an isolated native PCB copy.

Run with KiCad Python after the current actual-copper USB screen passes. This
checks geometry, not an electromagnetic model or physical USB performance.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import pcbnew as pcb

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/e73-hhkb-corner'
WORK=ROOT/'.assembly-work/e73-corner/usb-faults'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources=[BASE/'EC60-nRF52840.kicad_pcb',ROOT/'hardware/e73-corner-spec.json',
             ROOT/'scripts/check_e73_corner_usb.py',ROOT/'scripts/export_e73_corner_geometry.py',Path(__file__)]
    original={str(p.relative_to(ROOT)):sha(p)for p in sources}
    report=json.loads((BASE/'audit/USB-reference.json').read_text())
    assert report['checks_passed'] and report['whole_ground_network_connected'],'Current control must pass first'
    for name,digest in report['source_sha256'].items():assert sha(ROOT/name)==digest,('Stale USB control',name)
    WORK.mkdir(parents=True,exist_ok=True);(WORK/'audit').mkdir(exist_ok=True)
    for suffix in ['.kicad_pcb','.kicad_pro']:shutil.copyfile(BASE/('EC60-nRF52840'+suffix),WORK/('EC60-nRF52840'+suffix))
    spec=json.loads((ROOT/'hardware/e73-corner-spec.json').read_text())
    spec['output_directory']=str(WORK.relative_to(ROOT));fixture_spec=WORK/'fixture-spec.json'
    fixture_spec.write_text(json.dumps(spec,indent=2)+'\n')
    path=WORK/'EC60-nRF52840.kicad_pcb';board=pcb.LoadBoard(str(path))
    # Outside the existing track keepout, but close enough that the new
    # non-ground clearance cuts into the B-layer pair's In2 reference copper.
    trace=pcb.PCB_TRACK(board);trace.SetLayer(pcb.In2_Cu)
    trace.SetNet(board.GetNetsByName()['PGOOD_N']);trace.SetWidth(pcb.FromMM(.127))
    trace.SetStart(pcb.VECTOR2I(pcb.FromMM(353.35),pcb.FromMM(135)))
    trace.SetEnd(pcb.VECTOR2I(pcb.FromMM(353.35),pcb.FromMM(136)));board.Add(trace)
    pcb.ZONE_FILLER(board).Fill(board.Zones());pcb.SaveBoard(str(path),board)
    copper=WORK/'copper.json'
    subprocess.run([sys.executable,str(ROOT/'scripts/export_e73_corner_geometry.py'),'--pcb',str(path),'--output',str(copper)],check=True,capture_output=True)
    command=['uv','run','--python','3.14.7','--with-requirements',str(ROOT/'requirements-audit.txt'),'python',
             str(ROOT/'scripts/check_e73_corner_usb.py'),'--require-pass','--spec',str(fixture_spec),'--copper',str(copper)]
    result=subprocess.run(command,text=True,capture_output=True);(WORK/'check.log').write_text(result.stdout+result.stderr)
    failed=json.loads((WORK/'audit/USB-reference.json').read_text())
    assert result.returncode==2 and not failed['reference_passed'],(result.returncode,result.stdout,result.stderr)
    assert all(sha(ROOT/name)==digest for name,digest in original.items()),'Fault fixture edited source'
    output=dict(status='native-USB-reference-mutation-rejected',physical_verification=False,manufacturing_released=False,
                source_unchanged=True,control_passed=True,negative_case='actual In2 copper added outside track keepout, GND refilled',
                rejected_reference_cut=True,exit_code=result.returncode,
                uncovered_reference_mm2=sum(q['uncovered_connected_reference_mm2']for q in failed['segments']),
                source_sha256=original,limits=['Geometry regression only; no impedance, eye, RF or physical USB qualification'])
    (BASE/'audit/USB-reference-faults.json').write_text(json.dumps(output,indent=2)+'\n');print(output['status'])


if __name__=='__main__':main()
