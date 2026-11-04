"""Reject power placement, thermal-via, keepout and local-route regressions."""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import usb_short_power_contract as contract
from kicad_sexpr import child, children, dumps, loads


class PowerFailures(unittest.TestCase):
    def board_fault(self, mutate):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            shutil.copyfile(contract.BASE/'power-layout.json', base/'power-layout.json')
            board = loads((contract.BASE/'EC60-nRF52840.kicad_pcb').read_text())
            mutate(board)
            (base/'EC60-nRF52840.kicad_pcb').write_text(dumps(board)+'\n')
            with patch.object(contract, 'BASE', base), self.assertRaises(AssertionError):
                contract.verify_layout()

    def test_old_U6_position_rejected(self):
        self.board_fault(lambda b: child(next(f for f in children(b,'footprint') if contract.props(f)['Reference']=='U6'),'at').__setitem__(2,145))

    def thermal(self, b):
        return next(v for v in children(b,'via') if child(v,'uuid')[1]=='bd7c6e02-592d-46f4-91c6-9f93a4948ee5')

    def test_small_thermal_drill_rejected(self):
        self.board_fault(lambda b: child(self.thermal(b),'drill').__setitem__(1,.2))

    def test_unexpected_blind_via_rejected(self):
        self.board_fault(lambda b: self.thermal(b).insert(1,'blind'))

    def test_closed_back_thermal_mask_rejected(self):
        self.board_fault(lambda b: child(child(self.thermal(b),'tenting'),'back').__setitem__(1,'yes'))

    def test_removed_inductor_keepout_rejected(self):
        self.board_fault(lambda b: b.remove(next(z for z in children(b,'zone') if child(z,'name')==['name','L1_INTERLAND_NO_COPPER'])))

    def paths(self):
        spec=json.loads((contract.BASE/'power-layout.json').read_text())
        paths=[dict(**r,conservative_track_length_mm=r['max_length_mm']-.1,min_trace_width_mm=r['min_width_mm'],track_layers=['B.Cu'],surface_only=True) for r in spec['local_path_limits']]
        return paths,spec

    def test_long_feedback_rejected(self):
        paths,spec=self.paths();next(p for p in paths if p['to']=='U6.10')['conservative_track_length_mm']=29.183
        with self.assertRaises(AssertionError):contract.verify_paths(paths,spec)

    def test_narrow_switch_node_rejected(self):
        paths,spec=self.paths();paths[0]['min_trace_width_mm']=.127
        with self.assertRaises(AssertionError):contract.verify_paths(paths,spec)

    def test_inner_layer_local_loop_rejected(self):
        paths,spec=self.paths();paths[0]['track_layers']=['B.Cu','In1.Cu'];paths[0]['surface_only']=False
        with self.assertRaises(AssertionError):contract.verify_paths(paths,spec)


if __name__=='__main__':unittest.main()
