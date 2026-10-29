#!/usr/bin/env python3
"""Reject accidental reintroduction of a process the user cannot order."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('fabrication',ROOT/'scripts/check_yeti60_fabrication.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class OrdinaryProcess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        audit.main()

    def rejects(self, change):
        board = audit.pcb.LoadBoard(str(audit.BOARD))
        change(board)
        with patch.object(audit.pcb, 'LoadBoard', return_value=board):
            with self.assertRaises(AssertionError):
                audit.main()

    def test_reject_blind_via(self):
        def change(board):
            via = next(v for v in board.GetTracks() if v.GetClass() == 'PCB_VIA')
            via.SetViaType(audit.pcb.VIATYPE_MICROVIA)
            via.SetLayerPair(audit.pcb.In2_Cu,audit.pcb.B_Cu)
        self.rejects(change)

    def test_reject_special_small_drill(self):
        self.rejects(lambda b:next(v for v in b.GetTracks() if v.GetClass() == 'PCB_VIA').SetDrill(audit.pcb.FromMM(.2)))

    def test_reject_module_via_in_pad(self):
        def change(board):
            module = next(f for f in board.GetFootprints() if f.GetReference() == 'U1')
            pad = next(p for p in module.Pads() if p.GetNumber() == '39')
            via = audit.pcb.PCB_VIA(board)
            via.SetPosition(pad.GetPosition());via.SetWidth(audit.pcb.FromMM(.5))
            via.SetDrill(audit.pcb.FromMM(.3));via.SetViaType(audit.pcb.VIATYPE_THROUGH)
            via.SetLayerPair(audit.pcb.F_Cu,audit.pcb.B_Cu);via.SetNetCode(pad.GetNetCode())
            board.Add(via)
        self.rejects(change)


if __name__ == '__main__':
    unittest.main(verbosity=2)
