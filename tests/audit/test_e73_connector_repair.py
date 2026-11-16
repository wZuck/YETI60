"""Reject changes that would silently violate the ordinary-process repair."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from e73_corner_connector_repair import validate_patch
from kicad_sexpr import loads,dumps,child
class ConnectorRepairTest(unittest.TestCase):
 def setUp(self):self.patch=json.loads((ROOT/'hardware/e73-corner-j5-repair.json').read_text())
 def test_control(self):validate_patch(self.patch)
 def reject(self,mutate):
  patch=copy.deepcopy(self.patch);mutate(patch)
  with self.assertRaises(AssertionError):validate_patch(patch)
 def edit(self,p,kind,mutate):
  index=next(i for i,text in enumerate(p['added'])if loads(text)[0]==kind);q=loads(p['added'][index]);mutate(q);p['added'][index]=dumps(q)
 def test_wrong_header_pose(self):self.reject(lambda p:p.update(final_pose=[335.5,117.5,90]))
 def test_unreviewed_net(self):self.reject(lambda p:self.edit(p,'segment',lambda q:child(q,'net').__setitem__(1,'USB_DM')))
 def test_front_sensing_copper(self):self.reject(lambda p:self.edit(p,'segment',lambda q:child(q,'layer').__setitem__(1,'F.Cu')))
 def test_untented_via(self):self.reject(lambda p:self.edit(p,'via',lambda q:child(child(q,'tenting'),'back').__setitem__(1,'no')))
 def test_small_drill(self):self.reject(lambda p:self.edit(p,'via',lambda q:child(q,'drill').__setitem__(1,.1)))
 def test_outside_region(self):self.reject(lambda p:self.edit(p,'via',lambda q:child(q,'at').__setitem__(1,250)))
if __name__=='__main__':unittest.main()
