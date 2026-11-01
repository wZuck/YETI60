#!/usr/bin/env python3
"""Real DXF faults must be caught without touching native design inputs."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import ezdxf
import check_yeti60_deskeys_plate as c

class PlateContract(unittest.TestCase):
 def setUp(self):self.s=ezdxf.readfile(c.SOURCE);self.t=ezdxf.readfile(c.TARGET);self.spec=json.loads(c.SPEC.read_text())
 def test_selected_geometry(self):self.assertEqual(c.verify(self.s,self.t,self.spec)['key_centers_preserved'],60)
 def test_mount_shift(self):
  e=next(iter(self.t.modelspace().query('CIRCLE')));e.dxf.center=(e.dxf.center.x+.05,e.dxf.center.y,0)
  with self.assertRaises(AssertionError):c.verify(self.s,self.t,self.spec)
 def test_stock_undersized_hole(self):
  for a,b in zip(self.s.modelspace().query('LWPOLYLINE'),self.t.modelspace().query('LWPOLYLINE')):
   if c.kind(a)=='normal':b.set_points(a.get_points('xyseb'),format='xyseb');break
  with self.assertRaises(AssertionError):c.verify(self.s,self.t,self.spec)
 def test_side_stabilizer_position(self):
  for a,b in zip(self.s.modelspace().query('LWPOLYLINE'),self.t.modelspace().query('LWPOLYLINE')):
   if c.kind(a)=='spacebar-side':b.translate(.1,0,0);break
  with self.assertRaises(AssertionError):c.verify(self.s,self.t,self.spec)

if __name__=='__main__':unittest.main()
