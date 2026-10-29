#!/usr/bin/env python3
"""Negative evidence tests: reject changed AFE, stale data and false acceptance."""
import copy
from pathlib import Path
import tempfile
import unittest
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import screen_yeti60_interference as layout
import simulate_yeti60_interference as analog
import check_yeti60_acceptance as acceptance


class EvidenceFaults(unittest.TestCase):
    def test_ground_in_vendor_region_fails(self):
        self.assertEqual(layout.classify([0,0,.5,0],True),'failed-vendor-keepout')
        self.assertIn('risk',layout.classify([.5,0,0,0],False))
        self.assertIn('still-required',layout.classify([0,0,0,0],True))

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
        record={'execution_status':'completed','acceptance_status':'hold','production_approved':False,
                'physical_test_performed':False,'field_solver_performed':False,'open_gates':['a','b','c','d'],
                'variants':{n:{'CAD_checks_passed':True,'firmware_build_and_host_checks_passed':True,
                               'physical_acceptance':'not-run','RF_acceptance':'hold'} for n in ['e73','raytac']}}
        acceptance.validate(record)
        for key in ['production_approved','physical_test_performed','field_solver_performed']:
            bad=copy.deepcopy(record);bad[key]=True
            with self.assertRaises(AssertionError):acceptance.validate(bad)
        bad=copy.deepcopy(record);bad['variants']['e73']['physical_acceptance']='passed'
        with self.assertRaises(AssertionError):acceptance.validate(bad)


if __name__=='__main__':unittest.main()
