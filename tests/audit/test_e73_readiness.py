#!/usr/bin/env python3
"""Reject release in the presence of measured E73 layout and service defects."""
import copy,json,sys,unittest,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from review_e73_readiness import gates
from study_e73_service import withdrawal
class Readiness(unittest.TestCase):
 def inputs(self):
  read=lambda n:json.loads((ROOT/'docs/audit'/n).read_text())
  return [json.loads((ROOT/'hardware/ec60-nrf52840/audit-current.json').read_text()),read('yeti60-target-check.json'),read('usb-event-policy.json'),read('interference-layout.json')['variants']['e73'],read('USB-signal-paths.json')['variants']['e73'],read('yeti60-assembly.json'),read('e73-service-motion.json'),read('outcome.json'),read('firmware-suite.json')]
 def states(self,data):return {x['id']:x['state'] for x in gates(*data)}
 def test_cli_retains_design_hold(self):
  run=subprocess.run([sys.executable,str(ROOT/'scripts/review_e73_readiness.py'),'--require-design'],cwd=ROOT,capture_output=True,text=True)
  self.assertEqual(run.returncode,2,run.stdout+run.stderr)
  result=json.loads((ROOT/'docs/audit/e73-readiness.json').read_text());self.assertEqual(result['status'],'hold')
 def test_current_obstructions_are_not_accepted(self):
  states=self.states(self.inputs())
  for key in ['USB-protection-branches','NiZ-plate-mounted-stabilizers','battery-plug-service']:self.assertEqual(states[key],'failed')
 def test_incomplete_storage_suite_blocks_firmware(self):
  data=self.inputs();data[8]['NVS_cut_trials']=0;self.assertEqual(self.states(data)['scanner-calibration-storage-models'],'failed')
 def test_ground_disconnection_blocks_native_acceptance(self):
  data=self.inputs();data[0]['failed_ground_pairs']=1;self.assertEqual(self.states(data)['native-PCB'],'failed')
 def test_non_ground_antenna_copper_blocks_projection(self):
  data=self.inputs();data[3]['layers'][0]['non_GND_union_mm2']=.2;self.assertEqual(self.states(data)['antenna-projection'],'failed')
 def test_bad_USB_event_evidence_blocks_policy(self):
  data=self.inputs();data[2]['configuration_zero_rejected']=False;self.assertEqual(self.states(data)['USB-event-charging-policy'],'failed')
 def test_correct_thickness_alone_does_not_qualify_mounts(self):
  data=self.inputs();data[5]['nominal_stack']['plate_thickness_mm']=1.6;self.assertEqual(self.states(data)['NiZ-plate-mounted-stabilizers'],'failed')
 def test_physical_checks_never_inherit_CAD_success(self):
  states=self.states(self.inputs());self.assertEqual(states['physical-functional-RF-thermal-mechanical'],'not-run');self.assertEqual(states['closed-harness-and-power-layout'],'open')
 def test_absent_protection_evidence_is_not_a_zero_length_stub(self):
  data=self.inputs();data[4]['positive']['ESD_branch_to_main_path_mm']=None;self.assertEqual(self.states(data)['USB-protection-branches'],'failed')
 def test_coarse_plate_dimensions_do_not_qualify_unported_geometry(self):
  data=self.inputs();data[5]['nominal_stack']['plate_thickness_mm']=1.6;data[5]['mounting_hole_matches']=data[5]['mounting_hole_matches'][:28];self.assertEqual(self.states(data)['NiZ-plate-mounted-stabilizers'],'failed')
 def test_missing_ground_pairs_blocks_native_acceptance(self):
  data=self.inputs();data[0]['ground_pin_pairs']=[];self.assertEqual(self.states(data)['native-PCB'],'failed')
 def test_continuous_withdrawal_spans_intermediate_positions(self):
  travel,swept,detached=withdrawal([0,0,-3,4,5,-2],[0,-2,-3,4,2,-2])
  self.assertEqual(travel,2.5);self.assertEqual(swept,[0,0,-3,4,7.5,-2]);self.assertEqual(detached,[0,2.5,-3,4,7.5,-2])
 def test_insufficient_separation_rejected(self):
  with self.assertRaises(AssertionError):withdrawal([0,0,-3,4,5,-2],[0,-2,-3,4,2,-2],.1)
if __name__=='__main__':unittest.main()
