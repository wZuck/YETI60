#!/usr/bin/env python3
import sys,unittest
from pathlib import Path
import pcbnew as pcb
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from check_yeti60_c5_protection import verify,SOURCE
class Protection(unittest.TestCase):
 def test_native_channels(self):self.assertEqual(len(verify(pcb.LoadBoard(str(SOURCE)))),4)
 def test_optional_NC_pads_do_not_count_as_protection(self):
  b=pcb.LoadBoard(str(SOURCE));fp=next(f for f in b.GetFootprints() if f.GetReference()=='U1')
  for p in fp.Pads():
   if p.GetNumber() in ['1','4']:p.SetPosition(p.GetPosition()+pcb.VECTOR2I(pcb.FromMM(50),pcb.FromMM(50)))
  with self.assertRaises(AssertionError):verify(b)
 def test_ground_must_be_ground(self):
  b=pcb.LoadBoard(str(SOURCE));fp=next(f for f in b.GetFootprints() if f.GetReference()=='U1');pads={p.GetNumber():p for p in fp.Pads()};pads['3'].SetNet(pads['1'].GetNet())
  with self.assertRaises(AssertionError):verify(b)
if __name__=='__main__':unittest.main()
