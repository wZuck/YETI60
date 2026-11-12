#!/usr/bin/env python3
"""Real DXF faults must be caught without touching native design inputs."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import ezdxf
import check_yeti60_plate_mount as c

class PlateContract(unittest.TestCase):
 def setUp(self):self.s=ezdxf.readfile(c.SOURCE);self.t=ezdxf.readfile(c.TARGET);self.spec=json.loads(c.SPEC.read_text())
 def test_selected_geometry(self):self.assertEqual(c.verify(self.s,self.t,self.spec)['installed_mount_sets'],28)
 def test_mount_shift(self):
  e=next(iter(self.t.modelspace().query('CIRCLE')));e.dxf.center=(e.dxf.center.x+.05,e.dxf.center.y,0)
  with self.assertRaises(AssertionError):c.verify(self.s,self.t,self.spec)
 def test_wrong_normal_cutout(self):
  e=list(self.t.modelspace().query('LWPOLYLINE'))[1];e.scale(1.0001,1,1)
  with self.assertRaises(AssertionError):c.verify(self.s,self.t,self.spec)
 def test_stabilizer_position(self):
  e=list(self.t.modelspace().query('LWPOLYLINE'))[58];e.translate(.1,0,0)
  with self.assertRaises(AssertionError):c.verify(self.s,self.t,self.spec)
 def test_reintroduced_H26_mount(self):
  x,y=self.spec['unused_mount_center_case_mm'];self.t.modelspace().add_circle((-x,-y),.812)
  with self.assertRaises(AssertionError):c.verify(self.s,self.t,self.spec)

if __name__=='__main__':unittest.main()
