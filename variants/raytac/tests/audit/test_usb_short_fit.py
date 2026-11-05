"""Reject original tight parts and excessive tolerances with actual CAD."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import ezdxf

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import check_usb_short_closed_assembly as closed
from check_usb_short_fit import BASE,ROOT,read,plate_envelope,switch_envelope,screen,gasket_coverage
from cad_geometry import load


class BoundedFitFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fit=read(BASE/'mechanical-fit-spec.json');cls.assembly=read(BASE/'audit/assembly.json')
        cls.spec=read(ROOT/'mechanical/assembly-spec.raytac.json');cls.fab=read(ROOT/'mechanical/pcb-fabrication-spec.json')
        cls.doc=ezdxf.readfile(ROOT/cls.fit['plate']['output']);cls.bottom=load(BASE/'mechanical/yeti60-bottom-short-usb.step');cls.top=load(ROOT/'mechanical/generated/yeti60-top.step')
        cls.part=next(p for p in cls.assembly['component_envelopes'] if p['ref']=='SW100')
        screen(cls.bottom,plate_envelope(cls.doc,cls.fit,cls.assembly['nominal_stack']),cls.fit,'positive-control-plate')
        screen(cls.bottom,switch_envelope(cls.part,cls.fit,cls.spec,cls.fab)[0],cls.fit,'positive-control-switch')

    def test_original_plate_has_inadequate_allowance(self):
        original=ezdxf.readfile(ROOT/self.fit['plate']['source'])
        for label,case in [('bottom',self.bottom),('top',self.top)]:
            with self.subTest(label=label),self.assertRaisesRegex(AssertionError,'Bounded fit reserve exhausted'):
                screen(case,plate_envelope(original,self.fit,self.assembly['nominal_stack']),self.fit,label)

    def test_original_switch_floor_rejected(self):
        with self.assertRaisesRegex(AssertionError,'Bounded fit reserve exhausted'):
            screen(load(ROOT/'mechanical/generated/yeti60-bottom.step'),switch_envelope(self.part,self.fit,self.spec,self.fab)[0],self.fit,'original-floor')

    def test_excess_profile_error_rejected(self):
        bad=copy.deepcopy(self.fit);bad['plate']['maximum_profile_point_error_XY_radial_mm']=.4
        with self.assertRaisesRegex(AssertionError,'Bounded fit reserve exhausted'):
            screen(self.bottom,plate_envelope(self.doc,bad,self.assembly['nominal_stack']),bad,'oversize-profile')

    def test_excess_switch_height_rejected(self):
        bad=copy.deepcopy(self.fit);bad['switch']['maximum_installed_height_below_local_PCB_mm']=4.3
        with self.assertRaisesRegex(AssertionError,'Bounded fit reserve exhausted'):
            screen(self.bottom,switch_envelope(self.part,bad,self.spec,self.fab)[0],bad,'tall-switch')

    def test_gasket_outside_bearing_rejected(self):
        bad=copy.deepcopy(self.fit);bad['gaskets']['centers_case_XY_mm'][0][0]+=20
        with self.assertRaisesRegex(AssertionError,'Gasket leaves'):
            gasket_coverage(self.doc,bad,{'lower':self.bottom,'upper':self.top})

    def test_floor_relief_cannot_thin_external_skin(self):
        bad=copy.deepcopy(self.fit);bad['switch_floor_relief']['bounds_case_mm'][2]=-18.4
        with tempfile.TemporaryDirectory(prefix='yeti60-bad-floor-') as directory:
            with patch.object(closed,'OUT',Path(directory)):
                with self.assertRaisesRegex(AssertionError,'Outer skin too thin'):
                    closed.build_case(read(BASE/'interconnect-spec.json'),self.spec,bad)


if __name__=='__main__':unittest.main()
