#!/usr/bin/env python3
"""Ensure engineering checks reject contradictions, not merely missing files."""
import copy,importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('engineering',ROOT/'scripts/check_yeti60_engineering.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
class EngineeringEvidence(unittest.TestCase):
 @classmethod
 def setUpClass(cls):audit.main()
 def reject(self,path,change):
  original=audit.read
  def altered(candidate):
   data=original(candidate)
   if candidate==path:data=copy.deepcopy(data);change(data)
   return data
  with patch.object(audit,'read',side_effect=altered):
   with self.assertRaises(AssertionError):audit.main()
 def test_reject_unqualified_large_pack_approval(self):
  self.reject('docs/audit/yeti60-power-budget.json',lambda d:d['charging'].update(larger_pack_drop_in_approved=True))
 def test_reject_excess_charge_current(self):
  self.reject('docs/audit/yeti60-power-budget.json',lambda d:d['charging'].update(programmed_charge_mA_min_typ_max=[357,403,451]))
 def test_reject_excess_termination_current(self):
  self.reject('docs/audit/yeti60-power-budget.json',lambda d:d['charging'].update(termination_mA_min_typ_max=[18,25,33]))
 def test_reject_thin_recess_wall(self):
  self.reject('docs/audit/yeti60-battery-pocket.json',lambda d:d.update(remaining_wall_after_tolerance_mm=2.9))
 def test_reject_changed_assembly_image(self):
  original=audit.sha;p=ROOT/'docs/engineering/images/assembly.png'
  with patch.object(audit,'sha',side_effect=lambda q:'0'*64 if q==p else original(q)):
   with self.assertRaisesRegex(AssertionError,'Stale engineering'):audit.main()
if __name__=='__main__':unittest.main(verbosity=2)
