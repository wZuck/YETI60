#!/usr/bin/env python3
"""Negative evidence tests: reject changed AFE, stale data and false acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import screen_yeti60_interference as layout
import simulate_yeti60_interference as analog
import check_yeti60_acceptance as acceptance
from yeti60_acceptance_gates import design_and_pending_gates,summarize
from yeti60_rf_geometry import matches_controlled_outline
from check_single_nrf_pcb import outline


class EvidenceFaults(unittest.TestCase):
    def test_actual_non_ground_copper_injection_rejected_for_both_options(self):
        for name,folder in [('e73',ROOT),('raytac',ROOT/'variants/raytac')]:
            board=layout.pcb.LoadBoard(str(folder/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'))
            module=next(f for f in board.GetFootprints() if f.GetReference()=='U1')
            _,roi,_=layout.vendor_projection(module,name)
            track=layout.pcb.PCB_TRACK(board)
            track.SetStart(layout.pcb.VECTOR2I(layout.pcb.FromMM(roi[0]+.15),layout.pcb.FromMM(roi[1]+1)))
            track.SetEnd(layout.pcb.VECTOR2I(layout.pcb.FromMM(roi[0]+.55),layout.pcb.FromMM(roi[1]+1)))
            track.SetWidth(layout.pcb.FromMM(.2));track.SetLayer(layout.pcb.F_Cu)
            track.SetNetCode(board.FindNet('ROW_DRV0').GetNetCode());board.Add(track)
            with patch.object(layout.pcb,'LoadBoard',return_value=board):record=layout.screen(folder,name,False)
            self.assertGreater(sum(r['non_GND_union_mm2'] for r in record['layers']),.05)
            self.assertEqual(record['status'],'failed-vendor-keepout' if name=='raytac' else 'risk-copper-in-provisional-antenna-band')

    def test_native_outline_exception_does_not_allow_unrelated_changes(self):
        pcb=layout.pcb;spec=json.loads((ROOT/'mechanical/rf-remediation.json').read_text())
        source=outline(pcb.LoadBoard(str(ROOT/'EC60/PCB/EC60_PCB/EC60.kicad_pcb')))
        for folder in [ROOT,ROOT/'variants/raytac']:
            actual=outline(pcb.LoadBoard(str(folder/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb')))
            self.assertTrue(matches_controlled_outline(source,actual,spec,pcb))
            bad=list(actual);index=next(i for i,v in enumerate(bad) if v in source)
            value=list(bad[index]);value[1]+=1000;bad[index]=tuple(value)
            self.assertFalse(matches_controlled_outline(source,bad,spec,pcb))

    def test_ground_in_vendor_region_fails(self):
        self.assertEqual(layout.classify([0,0,.5,0],True),'failed-vendor-keepout')
        self.assertIn('risk',layout.classify([.5,0,0,0],False))
        self.assertIn('still-required',layout.classify([0,0,0,0],True))

    def test_vendor_projection_follows_native_bottom_placement(self):
        module=layout.pcb.FOOTPRINT(None)
        module.SetLayer(layout.pcb.B_Cu)
        module.SetPosition(layout.pcb.VECTOR2I(layout.pcb.FromMM(356.25),layout.pcb.FromMM(125.25)))
        module.SetOrientationDegrees(90)
        _,roi,formal=layout.vendor_projection(module,'raytac')
        self.assertTrue(formal)
        for a,b in zip(roi,[360.2,120.,364.,130.5]):self.assertAlmostEqual(a,b)
        module.SetPosition(layout.pcb.VECTOR2I(layout.pcb.FromMM(346),layout.pcb.FromMM(117)))
        module.SetOrientationDegrees(0)
        _,roi,formal=layout.vendor_projection(module,'e73')
        self.assertFalse(formal)
        self.assertEqual(roi,[361.,117.,364.,130.])

    def test_native_polygon_intersection(self):
        a=layout.rect([0,0,10,10]);b=layout.rect([5,5,15,15]);a.BooleanIntersection(b)
        self.assertAlmostEqual(a.Area()/1e12,25,places=6)

    def test_feedback_value_change_rejected(self):
        source=ROOT/'hardware/ec60-nrf52840/netlist.xml';analog.check_topology(source)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'net.xml';path.write_text(source.read_text().replace('<value>100k</value>','<value>10k</value>'))
            with self.assertRaises(AssertionError):analog.check_topology(path)

    def test_stale_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'vector.csv';path.write_text('0,1\n');digest=acceptance.sha(path)
            path.write_text('0,999\n')
            with self.assertRaises(AssertionError):acceptance.fresh({'vector.csv':digest},Path(folder))

    def test_false_production_or_physical_pass_rejected(self):
        read=lambda n:json.loads((ROOT/'docs/audit'/n).read_text())
        gates=design_and_pending_gates(read('interference-layout.json'),read('interference-plate.json'),read('USB-signal-paths.json'),
                                     {name:{'status':'passed'} for name in ['e73','raytac']})
        record={'execution_status':'completed',**summarize(gates),'gates':gates,'field_solver_performed':False,
                'variants':{n:{'CAD_checks_passed':True,'firmware_build_and_host_checks_passed':True,
                               'physical_acceptance':'not-run','RF_acceptance':'not-run'} for n in ['e73','raytac']}}
        acceptance.validate(record)
        for key in ['production_approved','physical_test_performed','field_solver_performed']:
            bad=copy.deepcopy(record);bad[key]=True
            with self.assertRaises(AssertionError):acceptance.validate(bad)
        bad=copy.deepcopy(record);bad['variants']['e73']['physical_acceptance']='passed'
        with self.assertRaises(AssertionError):acceptance.validate(bad)

    def test_design_pass_does_not_close_hardware_or_supplier_gates(self):
        gates=[{'id':'layout','scope':'design','state':'passed','description':'layout'},
               {'id':'hardware','scope':'physical','state':'not-run','description':'hardware'},
               {'id':'pack','scope':'supplier','state':'open','description':'pack'}]
        result=summarize(gates)
        self.assertEqual(result['design_review_status'],'passed')
        self.assertTrue(result['ready_for_engineering_first_article'])
        self.assertEqual(result['acceptance_status'],'hold')
        self.assertFalse(result['production_approved'])
        gates[0]['state']='failed'
        self.assertEqual(summarize(gates)['design_review_status'],'hold')


if __name__=='__main__':unittest.main()
