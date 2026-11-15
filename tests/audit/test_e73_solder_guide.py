#!/usr/bin/env python3
"""Reject missing/duplicate placements, wrong capacitor values and wrong sides."""
import copy,csv,io,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from build_e73_solder_guide import validate
class GuideContracts(unittest.TestCase):
 def setUp(self):
  self.parts=json.loads((ROOT/'.assembly-work/e73-corner/solder-map.json').read_text())['parts'];self.bom={ref.strip():row for row in csv.DictReader(io.StringIO((ROOT/'hardware/e73-hhkb-corner/mainboard-purchase.csv').read_text()))for ref in row['References'].split(',')};self.assigned=list(self.bom)
 def test_control(self):validate(self.parts,self.bom,self.assigned)
 def test_wrong_C10(self):
  self.parts['C10']['value']='100n'
  with self.assertRaisesRegex(AssertionError,'Wrong guide value'):validate(self.parts,self.bom,self.assigned)
 def test_module_wrong_side(self):
  self.parts['U1']['side']='back'
  with self.assertRaisesRegex(AssertionError,'Wrong guide mounting side'):validate(self.parts,self.bom,self.assigned)
 def test_missing(self):
  with self.assertRaises(AssertionError):validate(self.parts,self.bom,self.assigned[1:])
 def test_duplicate(self):
  with self.assertRaises(AssertionError):validate(self.parts,self.bom,self.assigned+['U1'])
 def test_wrong_usb_harness(self):
  next(p for p in self.parts['J4']['pads']if p['number']=='2')['net']='USB_DP'
  with self.assertRaisesRegex(AssertionError,'Wrong harness contract'):validate(self.parts,self.bom,self.assigned)
if __name__=='__main__':unittest.main()
