"""Check repaired geometry and reject the actual unmodified E73 interfaces."""
import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import ezdxf
from cad_geometry import load
from check_yeti60_assembly import distance
from build_e73_fit_candidate import ROOT, SPEC, AUD, inset_plate, hashes
from e73_fit_geometry import (internal_contract, plate_envelope, switch_envelope,
                              screen, gasket_coverage)

def read(p):return json.loads(p.read_text())

class E73FitCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit=read(SPEC);cls.report=read(AUD);hashes(cls.report['source_sha256']);hashes(cls.report['outputs'])
        cls.assembly=read(ROOT/'docs/audit/yeti60-assembly.json')
        cls.spec=read(ROOT/'mechanical/assembly-spec.json');cls.fabrication=read(ROOT/'mechanical/pcb-fabrication-spec.json')
        cls.bottom=load(ROOT/cls.fit['bottom_output']);cls.original=load(ROOT/'mechanical/generated/yeti60-bottom.step')
        cls.top=load(ROOT/'mechanical/generated/yeti60-top.step')
        cls.part=next(p for p in cls.assembly['component_envelopes'] if p['ref']=='SW100')
    def doc(self):return ezdxf.readfile(ROOT/self.fit['plate']['output'])
    def test_repaired_plate_both_shells(self):
        env=plate_envelope(self.doc(),self.fit,self.assembly['nominal_stack'])
        for name,case in [('upper',self.top),('lower',self.bottom)]:
            with self.subTest(name=name):self.assertGreaterEqual(screen(case,env,self.fit,name)['remaining_air_gap_mm'],.15)
    def test_repaired_switch_floor(self):
        env,_=switch_envelope(self.part,self.fit,self.spec,self.fabrication)
        self.assertGreaterEqual(screen(self.bottom,env,self.fit,'switch')['remaining_air_gap_mm'],.15)
    def test_old_plate_fails_even_with_repaired_floor(self):
        original=ezdxf.readfile(ROOT/self.fit['plate']['source'])
        env=plate_envelope(original,self.fit,self.assembly['nominal_stack'])
        for case in (self.top,self.bottom):
            with self.assertRaisesRegex(AssertionError,'Bounded fit reserve exhausted'):screen(case,env,self.fit,'old plate')
    def test_old_floor_fails_bounded_switch(self):
        env,_=switch_envelope(self.part,self.fit,self.spec,self.fabrication)
        with self.assertRaisesRegex(AssertionError,'Bounded fit reserve exhausted'):screen(self.original,env,self.fit,'old floor')
    def test_interiors_and_mount_entities_preserved(self):
        baseline=ezdxf.readfile(ROOT/self.fit['plate']['source'])
        self.assertEqual(internal_contract(baseline),internal_contract(self.doc()))
        self.assertEqual(len(self.doc().modelspace().query('CIRCLE')),28)
    def test_large_inset_rejected(self):
        fit=copy.deepcopy(self.fit);fit['plate']['outer_perimeter_inset_mm']=2
        with self.assertRaises(AssertionError):inset_plate(ezdxf.readfile(ROOT/fit['plate']['source']),fit)
    def test_outward_growth_rejected(self):
        fit=copy.deepcopy(self.fit);fit['plate']['outer_perimeter_inset_mm']=-.1
        with self.assertRaises(AssertionError):inset_plate(ezdxf.readfile(ROOT/fit['plate']['source']),fit)
    def test_gaskets_supported_with_allowances(self):
        self.assertEqual(len(gasket_coverage(self.doc(),self.fit,{'lower':self.bottom,'upper':self.top})),8)
    def test_shifted_gasket_rejected(self):
        fit=copy.deepcopy(self.fit);fit['gaskets']['centers_case_XY_mm'][0][0]+=30
        with self.assertRaises(AssertionError):gasket_coverage(self.doc(),fit,{'lower':self.bottom,'upper':self.top})
    def test_larger_installed_switch_rejected(self):
        fit=copy.deepcopy(self.fit);fit['switch']['maximum_installed_height_below_local_PCB_mm']=6
        env,_=switch_envelope(self.part,fit,self.spec,self.fabrication)
        with self.assertRaisesRegex(AssertionError,'Bounded fit reserve exhausted'):screen(self.bottom,env,fit,'oversize switch')

if __name__=='__main__':unittest.main()
