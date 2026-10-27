#!/usr/bin/env python3
"""Keep attribution while clearing inherited artwork from the new power area."""
from pathlib import Path
import tempfile
import pcbnew as pcb
from kicad_sexpr import loads,dumps,child,children
BASE=Path(__file__).resolve().parents[1]/'hardware/ec60-nrf52840'
path=BASE/'EC60-nRF52840.kicad_pcb'
x=loads(path.read_text())
def reference(fp):return next(v[2] for v in children(fp,'property') if v[1]=='Reference')
x[:]=[v for v in x if not(isinstance(v,list) and v[0]=='footprint' and reference(v)=='G***')]
with tempfile.TemporaryDirectory(prefix='yaeckb-silk-') as folder:
    p=Path(folder)/'board.kicad_pcb';p.write_text(dumps(x)+'\n');board=pcb.LoadBoard(str(p))
for fp in board.GetFootprints():
    layer=pcb.B_Fab if fp.IsFlipped() else pcb.F_Fab
    fp.Reference().SetLayer(layer)
    fp.Value().SetLayer(layer)
    if fp.GetReference()=='REF**':
        fp.Reference().SetLayer(pcb.Dwgs_User)
        fp.SetFPID(pcb.LIB_ID('YAECKB','EC60_BoardOutline'))
        pcb.PCB_IO_KICAD_SEXPR().FootprintSave(str(BASE/'YAECKB.pretty'),fp)
for text,y in (('YAECKB / EC60 by Cipulot',141.5),('NRF-1.0-dev / REAR USB',143)):
    if any(isinstance(t,pcb.PCB_TEXT) and t.GetText()==text for t in board.GetDrawings()):continue
    t=pcb.PCB_TEXT(board);t.SetText(text);t.SetLayer(pcb.B_SilkS);t.SetMirrored(True)
    t.SetPosition(pcb.VECTOR2I(pcb.FromMM(214),pcb.FromMM(y)))
    t.SetTextSize(pcb.VECTOR2I(pcb.FromMM(.8),pcb.FromMM(.8)));t.SetTextThickness(pcb.FromMM(.12));board.Add(t)
pcb.SaveBoard(str(path),board)
print('Retained Cipulot attribution, moved component labels to fabrication layers')
