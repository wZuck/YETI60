#!/usr/bin/env python3
"""Reject unsafe or contradictory power-state pin/report claims."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from check_yeti60_power_states import verify_parts,verify_report
class PowerStates(unittest.TestCase):
 def setUp(self):
  self.parts=json.loads((ROOT/'hardware/usb-short-route/components.json').read_text())
  self.report=json.loads((ROOT/'docs/audit/power-states.json').read_text())
  verify_parts(self.parts);verify_report(self.report)
 def test_charger_reset_pull_cannot_be_reversed(self):
  self.parts['R44']['pins']['2']='+3.3V'
  with self.assertRaises(AssertionError):verify_parts(self.parts)
 def test_measuring_divider_cannot_bypass_switch(self):
  self.parts['R51']['pins']['1']='BAT_CELL'
  with self.assertRaises(AssertionError):verify_parts(self.parts)
 def test_power_switch_cannot_disrupt_charger_supply(self):
  self.parts['SW100']['pins']['2']='USB_5V'
  with self.assertRaises(AssertionError):verify_parts(self.parts)
 def test_reset_is_not_a_software_inhibit(self):
  self.report['reset_default']['charge_permission']=False
  with self.assertRaises(AssertionError):verify_report(self.report)
 def test_subtotal_cannot_be_a_whole_board_bound(self):
  self.report['whole_board_upper_bound']=True
  with self.assertRaises(AssertionError):verify_report(self.report)
 def test_unmeasured_suspend_failure_cannot_be_accepted(self):
  self.report['suspend_battery_loss_qualified']=True
  with self.assertRaises(AssertionError):verify_report(self.report)
if __name__=='__main__':unittest.main()
