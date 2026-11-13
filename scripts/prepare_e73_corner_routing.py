#!/usr/bin/env python3
"""Export locked DSN work inputs with an explicit reference-layer constraint.

KiCad Python is required. The 2.1.0 JVM router is the working tool; the 2.5.0
native binary could not serialize this design and is not acceptance evidence.
Board boundaries, pads, fixed tracks/vias, assembly outlines and keepouts are
retained. Refillable GND pours are omitted only from the router work file;
native zone fill and independent ground checks are mandatory after import.
"""
import hashlib
import json
import subprocess
from pathlib import Path
import pcbnew as pcb
from kicad_sexpr import Atom, child, children, dumps, form, loads

ROOT = Path(__file__).resolve().parents[1]


def main():
    spec_path = ROOT / 'hardware/e73-corner-spec.json'
    s = json.loads(spec_path.read_text())
    source = ROOT / s['output_directory'] / 'EC60-nRF52840.kicad_pcb'
    work = ROOT / '.assembly-work/e73-corner'
    work.mkdir(parents=True, exist_ok=True)
    raw = work / 'corner.dsn'
    output = work / 'router-ready.dsn'
    board = pcb.LoadBoard(str(source))
    for t in board.GetTracks():
        t.SetLocked(True)
    assert pcb.ExportSpecctraDSN(board, str(raw))
    tree = loads(raw.read_text().replace('(string_quote ")', '(string_quote __quote__)'))
    structure = child(tree, 'structure')
    for name in ['F.Cu', 'In1.Cu']:
        layer = next(q for q in children(structure, 'layer') if q[1] == name)
        assert child(layer, 'type')[1] == 'signal'
        child(layer, 'type')[1] = Atom('power')
    planes = list(children(structure, 'plane'))
    assert planes and all(p[1] == 'GND' for p in planes)
    for plane in planes:
        structure.remove(plane)
    network = child(tree, 'network')
    default = next(q for q in children(network, 'class') if q[1] == 'kicad_default')
    assert default.count('GND') == 1
    # Let native connectivity decide which nets still need work. The DSN
    # router does not reproduce all custom-pad/plane contacts, so attempting
    # unchanged nets creates hundreds of fictitious repair tasks.
    drc_path = work/'router-native-input-DRC.json'
    subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc',
        '--all-track-errors','--schematic-parity','--refill-zones','--format','json',
        '-o',str(drc_path),str(source)],check=True,capture_output=True)
    drc = json.loads(drc_path.read_text())
    assert not any(q['severity']=='error' for q in drc['violations']), 'Fix native errors before routing'
    assert not drc['schematic_parity']
    owners = {t.m_Uuid.AsString():t.GetNetname() for t in board.GetTracks()}
    owners.update({p.m_Uuid.AsString():p.GetNetname() for f in board.GetFootprints() for p in f.Pads()})
    open_nets = set()
    for q in drc['unconnected_items']:
        names = {owners[i['uuid']] for i in q['items']}
        assert len(names)==1, ('Unconnected endpoint net mismatch',q)
        open_nets.update(names)
    ignored = [n for n in default[2:] if not isinstance(n,list) and (n not in open_nets or n=='GND')]
    for net in ignored:default.remove(net)
    network.append(form('class', 'E73_FIXED_NATIVE', *ignored,
                        form('circuit', form('use_via', 'Via[0-3]_500:300_um')),
                        form('rule', form('width', 200), form('clearance', 200))))
    output.write_text(dumps(tree).replace('(string_quote __quote__)', '(string_quote ")') + '\n')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    report = dict(status='locked-routing-work-input', acceptance=False,
                  route_constraints=['F.Cu and In1.Cu unavailable for new routes; front-side escapes are already fixed', 'Ignore E73_FIXED_NATIVE; independently verify ground and every native net in KiCad'],
                  omitted_refillable_GND_planes=len(planes),native_open_nets=sorted(open_nets),ignored_native_closed_nets=ignored,
                  unchanged=['Native PCB and zones', 'Board boundary', 'Pad copper', 'All existing track/via geometry', 'Assembly outlines', 'Keepouts'],
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in [spec_path, source, drc_path, Path(__file__), ROOT / 'scripts/kicad_sexpr.py']},
                  outputs={str(p.relative_to(ROOT)): sha(p) for p in [raw, output]})
    (work / 'routing-input.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Locked DSN prepared; front/adjacent reference reserved; refillable GND pours omitted only from router input; native refill/verification mandatory')


if __name__ == '__main__':
    main()
