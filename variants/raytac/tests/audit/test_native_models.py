#!/usr/bin/env python3
"""Reject restored legacy models and broken thermal-mask/stencil geometry."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from kicad_sexpr import loads,children,child
from usb_short_model_contract import validate_native
from usb_short_charger_contract import verify_footprint
BASE=ROOT/'hardware/usb-short-route'
class NativeModels(unittest.TestCase):
 def setUp(self):
  self.tree=loads((BASE/'EC60-nRF52840.kicad_pcb').read_text());self.spec=json.loads((BASE/'models/model-sources.json').read_text())
 def footprint(self,ref):return next(f for f in children(self.tree,'footprint') if any(p[1]=='Reference' and p[2]==ref for p in children(f,'property')))
 def test_current_source_closure(self):validate_native(self.tree,self.spec)
 def test_duplicate_IC_rejected(self):
  f=self.footprint('U2');f.append(copy.deepcopy(child(f,'model')))
  with self.assertRaises(AssertionError):validate_native(self.tree,self.spec)
 def test_missing_connector_model_rejected(self):
  child(self.footprint('J2'),'model')[1]='${KICAD6_3DMODEL_DIR}/private.step'
  with self.assertRaises(AssertionError):validate_native(self.tree,self.spec)
 def test_short_inductor_model_rejected(self):
  m=child(self.footprint('L1'),'model');m[1]=m[1].replace('3020','3015')
  with self.assertRaises(AssertionError):validate_native(self.tree,self.spec)
 def test_wrong_connector_offset_rejected(self):
  child(child(self.footprint('J2'),'model'),'offset')[1][2]='1.4'
  with self.assertRaises(AssertionError):validate_native(self.tree,self.spec)
 def test_thermal_windows(self):
  for ref in ['U5','U6']:self.assertGreater(verify_footprint(self.footprint(ref),ref)['paste_coverage_ratio'],.5)
 def test_old_EP_size_rejected(self):
  f=self.footprint('U5');p=next(p for p in children(f,'pad') if p[1]=='17');child(p,'size')[1:]=['1.6','1.6']
  with self.assertRaises(AssertionError):verify_footprint(f,'U5')
 def test_mask_island_removed_rejected(self):
  f=self.footprint('U6');f.remove(next(r for r in children(f,'fp_rect') if child(r,'layer')[1]=='B.Mask'))
  with self.assertRaises(AssertionError):verify_footprint(f,'U6')
 def test_paste_over_cap_rejected(self):
  f=self.footprint('U5');p=next(p for p in children(f,'pad') if not p[1]);child(p,'at')[1:3]=['-.35','0']
  with self.assertRaises(AssertionError):verify_footprint(f,'U5')
 def test_pin1_markers_in_both_current_ICs(self):
  from cad_geometry import load
  from check_usb_short_models import pin1_marker
  w=ROOT/'.assembly-work/usb-short-models';native=json.loads((w/'native-inputs.json').read_text())
  for ref in ['U2','U4']:self.assertTrue(pin1_marker(load(w/'parts'/(ref+'.step')),native['parts'][ref])['quadrant_matches'])
 def test_half_turn_can_land_but_pin1_is_rejected(self):
  import math
  from cad_geometry import load
  from check_usb_short_models import pin1_marker,landing
  from OCP.gp import gp_Trsf,gp_Ax1,gp_Pnt,gp_Dir
  from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
  w=ROOT/'.assembly-work/usb-short-models';native=json.loads((w/'native-inputs.json').read_text())
  for ref in ['U2','U4']:
   part=native['parts'][ref];x,y=part['position_pcb_mm'];t=gp_Trsf();t.SetRotation(gp_Ax1(gp_Pnt(x,-y,0),gp_Dir(0,0,1)),math.pi)
   wrong=BRepBuilderAPI_Transform(load(w/'parts'/(ref+'.step')),t,True).Shape()
   self.assertEqual(landing(wrong,part['pads'],16)['matched_lands'],16)
   with self.assertRaisesRegex(AssertionError,'wrong quadrant'):pin1_marker(wrong,part)
if __name__=='__main__':unittest.main()
