"""Reject the measured wing trap and inadequate rear-clip motion clearance."""
import copy
import json
import sys
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from check_usb_short_vertical_motion import BASE,ROOT,planar_sweep,case_check,rear_clip_screen
from cad_geometry import load
from usb_short_guides import build
from check_usb_short_closed_assembly import build_case
import check_usb_short_closed_assembly as closed_geometry


class VerticalMotionFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=json.loads((BASE/'interconnect-spec.json').read_text())
        cls.closed=json.loads((BASE/'audit/closed-assembly.json').read_text())
        cls.pcb=planar_sweep(load(ROOT/'.assembly-work/pcb-placed.step'),22)
        cls.case=load(BASE/'mechanical/yeti60-bottom-short-usb.step')
        case_check(cls.case,[('PCB',cls.pcb)])

    def guides(self,spec):
        parts,films=build(spec,self.case,self.closed['nominal']['routes'],self.closed['connector_exits_case_mm'])
        return [(p['name'],p['shape']) for p in parts+films if p['name'].startswith('USB-R')]

    def test_original_captured_wing_rejected(self):
        with self.assertRaisesRegex(AssertionError,'Rigid extraction hits bottom'):
            case_check(load(ROOT/'mechanical/generated/yeti60-bottom.step'),[('PCB',self.pcb)])

    def test_old_rear_clips_rejected(self):
        rear_clip_screen(self.spec,self.pcb,self.guides(self.spec))
        old=copy.deepcopy(self.spec)
        old['usb']['rear_y']=-101
        old['guides']['USB_rear_front_half_width']=2.7
        with self.assertRaisesRegex(AssertionError,'Rear clip blocks PCB tolerance corridor'):
            rear_clip_screen(old,self.pcb,self.guides(old))

    def test_overtrimmed_clip_wall_rejected(self):
        bad=copy.deepcopy(self.spec);bad['guides']['USB_rear_front_half_width']=2.1
        with self.assertRaisesRegex(AssertionError,'Rear clip front wall too thin'):
            self.guides(bad)

    def test_service_notch_cannot_erode_plate_bearing(self):
        bad=copy.deepcopy(self.spec)
        bad['case_service_relief']['bounds_case_mm'][0]=350
        bad['case_service_relief']['bounds_case_mm'][4]=-96
        self.reject_case(bad,'guarded plate bearing')

    def test_service_notch_cannot_thin_exterior_skin(self):
        bad=copy.deepcopy(self.spec);bad['case_service_relief']['bounds_case_mm'][2]=-5.6
        self.reject_case(bad,'Outer skin too thin')

    def reject_case(self,spec,message):
        # A broken guard must never let a fault-injection case overwrite the
        # published STEP/STL. Keep even an unexpected successful build local.
        with tempfile.TemporaryDirectory(prefix='yeti60-bad-case-') as directory:
            with patch.object(closed_geometry,'OUT',Path(directory)):
                with self.assertRaisesRegex(AssertionError,message):
                    build_case(spec,json.loads((ROOT/'mechanical/assembly-spec.raytac.json').read_text()))


if __name__=='__main__':unittest.main()
