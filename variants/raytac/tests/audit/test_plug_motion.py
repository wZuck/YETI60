"""Reject endpoint-only service checks and native J2 repair regressions."""
import copy
import shutil
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import usb_short_battery_service as service
from check_usb_short_plug_motion import withdrawal, enlarged, screen
from check_yeti60_assembly import box
from cad_geometry import intersection_volume
from kicad_sexpr import child, children, dumps, loads


class PlugMotionTests(unittest.TestCase):
    def test_current_native_repair_accepted(self):
        service.verify_layout()

    def test_interior_collision_rejected_when_endpoints_clear(self):
        start=[0,0,0,2,2,2]
        header=[0,-2,0,2,4,2]
        _,swept,detached=withdrawal(start,header)
        obstruction=box([.5,3,.5,1.5,4,1.5])
        self.assertEqual(intersection_volume(box(start),obstruction),0)
        self.assertEqual(intersection_volume(box(detached),obstruction),0)
        with self.assertRaisesRegex(AssertionError,'Plug withdrawal obstruction'):
            screen(box(swept),[('intermediate-stop',obstruction)],.15)

    def test_missing_separation_rejected(self):
        with self.assertRaisesRegex(AssertionError,'separation'):
            withdrawal([0,0,0,2,2,2],[0,-2,0,2,4,2],0)

    def test_empty_obstacle_set_rejected(self):
        with self.assertRaisesRegex(AssertionError,'coverage'):
            screen(box([0,0,0,1,1,1]),[],.15)

    def test_pcb_datum_clamps_only_top_of_allowance(self):
        self.assertEqual(enlarged([0,0,-5,2,2,-2],.25,-2),[-.25,-.25,-5.25,2.25,2.25,-2])

    def native_fault(self,mutate,message):
        tree=loads((service.BASE/'EC60-nRF52840.kicad_pcb').read_text())
        mutate(tree)
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            (base/'EC60-nRF52840.kicad_pcb').write_text(dumps(tree)+'\n')
            shutil.copyfile(service.BASE/'battery-service-j2.json',base/'battery-service-j2.json')
            record=json.loads((service.BASE/'battery-service-j2.json').read_text())
            lib=base/record['frozen_FCu_library'];lib.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(service.BASE/record['frozen_FCu_library'],lib)
            with patch.object(service,'BASE',base),self.assertRaisesRegex(AssertionError,message):
                service.verify_layout()

    def test_old_position_rejected(self):
        def mutate(tree):
            footprint=next(f for f in children(tree,'footprint') if any(p[1]=='Reference' and p[2]=='J2' for p in children(f,'property')))
            child(footprint,'at')[1:3]=[152,125]
        self.native_fault(mutate,'J2 service position')

    def test_smaller_new_via_rejected(self):
        def mutate(tree):
            via=next(v for v in children(tree,'via') if child(v,'uuid')[1] in service.via_ids())
            child(via,'drill')[1]=.2
        self.native_fault(mutate,'J2 reconnect')

    def test_control_route_wrong_layer_rejected(self):
        def mutate(tree):
            route=next(s for s in children(tree,'segment') if child(s,'net')[1]=='APLEX_EN_PIN_0' and child(s,'uuid')[1] in {child(i,'uuid')[1] for i in service.new_items()})
            child(route,'layer')[1]='F.Cu'
        self.native_fault(mutate,'J2 reconnect')


if __name__=='__main__':unittest.main()
