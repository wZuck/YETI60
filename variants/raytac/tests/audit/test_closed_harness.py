"""Regression cases for previously observed closed-case failures."""
import copy,json,sys,unittest,tempfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from check_usb_short_closed_assembly import BASE,ROOT,input_data,build_case,evaluate
import check_usb_short_closed_assembly as closed_geometry
from cad_geometry import load
from usb_short_harness import paths,paired_data,length
class ClosedHarnessFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=json.loads((BASE/'interconnect-spec.json').read_text());cls.assembly,cls.native,cls.exits=input_data(cls.spec);cls.case=load(BASE/'mechanical/yeti60-bottom-short-usb.step')
        result,*_=evaluate(cls.spec,cls.assembly,cls.native,cls.exits,cls.case)
        assert result['USB_geometric_pair_skew_mm']<1
    def test_deep_relief_rejected(self):
        bad=copy.deepcopy(self.spec);bad['case_pocket']['bounds_case_mm'][2]=-6.6
        with tempfile.TemporaryDirectory(prefix='yeti60-bad-case-') as directory:
            with patch.object(closed_geometry,'OUT',Path(directory)):
                with self.assertRaisesRegex(AssertionError,'Outer skin too thin'):
                    build_case(bad,json.loads((ROOT/'mechanical/assembly-spec.raytac.json').read_text()))
    def test_early_power_drop_hits_battery_route(self):
        bad=copy.deepcopy(self.spec)
        # Leave room for the black-wire side shift so this mutant remains
        # tangent and reaches the actual battery-wire collision check.
        bad['power'].update(cross_lower_start_x=220,cross_start_x=230)
        with self.assertRaisesRegex(AssertionError,'Independent harness collision'):
            evaluate(bad,self.assembly,self.native,self.exits,self.case)
    def test_old_drop_column_hits_mount(self):
        bad=copy.deepcopy(self.spec);bad['usb']['drop_x']=200
        with self.assertRaisesRegex(AssertionError,'clearance'):
            evaluate(bad,self.assembly,self.native,self.exits,self.case)
    def test_actual_power_housing_pin_numbers_and_pair_length(self):
        route,centre=paths(self.spec,self.exits);route['usb'].update(paired_data(centre,self.spec)[0])
        self.assertAlmostEqual(route['power']['1'][0]['start'][0],340.5,6)
        self.assertAlmostEqual(route['power']['2'][0]['start'][0],341.5,6)
        self.assertAlmostEqual(route['power']['1'][-1]['end'][1],-122.027723,6)
        self.assertAlmostEqual(route['power']['2'][-1]['end'][1],-125.027723,6)
        self.assertLess(abs(length(route['usb']['2'])-length(route['usb']['3'])),1)
if __name__=='__main__':unittest.main()
