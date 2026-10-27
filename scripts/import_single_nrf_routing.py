#!/usr/bin/env python3
"""Import a local Specctra routing result; fill zones and save a review PCB."""
from pathlib import Path
import sys
import tempfile
import json
import pcbnew as pcb
from kicad_sexpr import Atom as A, loads, dumps, child, children
from configure_single_nrf_rules import nrf_nets
BASE = Path(__file__).resolve().parents[1] / 'hardware/ec60-nrf52840'
NAME = 'EC60-nRF52840'
original_path = BASE / (NAME + '.unrouted.kicad_pcb')
original = loads(original_path.read_text())
retained = [v for v in original if isinstance(v,list) and v[0] in ('segment','arc','via')]
session = loads(Path(sys.argv[1]).read_text().replace('(string_quote ")',''))
for net in children(child(child(session,'routes'),'network_out'),'net'):
    net[:] = [v for v in net if not (isinstance(v,list) and v and v[0] in ('wire','via')
              and child(v,'type') and child(v,'type')[1]=='protect')]
child(child(child(session,'routes'),'parser'),'string_quote')
board = pcb.LoadBoard(str(original_path))
with tempfile.TemporaryDirectory(prefix='yaeckb-route-import-') as folder:
    only_new=Path(folder)/'new.ses'
    only_new.write_text(dumps(session)+'\n')
    assert pcb.ImportSpecctraSES(board, str(only_new)), 'Specctra import failed'
    # The router exports protected arcs as coarse chords. Restore the exact
    # retained KiCad arcs/segments/vias instead of importing those approximations.
    temp=Path(folder)/'new.kicad_pcb'
    pcb.SaveBoard(str(temp),board)
    merged=loads(temp.read_text())
    fine_nets=set(nrf_nets())
    for item in merged:
        if isinstance(item,list) and item[0] in ('segment','arc'):
            width=child(item,'width')
            minimum=.127 if str(child(item,'net')[1]) in fine_nets else .2
            if float(width[1])<minimum:width[1]=minimum
    merged.extend(retained)
    temp.write_text(dumps(merged)+'\n')
    board=pcb.LoadBoard(str(temp))
contract_path=BASE/'pcb-placement-contract.json'
if contract_path.exists():
    for fp in board.GetFootprints():
        expected=json.loads(contract_path.read_text()).get(fp.GetReference())
        if expected:
            if fp.IsFlipped()!=expected['flipped']:fp.Flip(fp.GetPosition(),False)
            fp.SetOrientationDegrees(expected['angle'])
            fp.SetPosition(pcb.VECTOR2I(*expected['position_nm']))
board.BuildConnectivity()
filler = pcb.ZONE_FILLER(board)
filler.Fill(board.Zones())
out = BASE / (NAME + '.kicad_pcb')
pcb.SaveBoard(str(out), board)
print(out)
