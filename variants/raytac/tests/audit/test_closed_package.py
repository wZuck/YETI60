"""A fresh passed package must reject plausible partial-publication mistakes."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import check_usb_short_assembly_package as package


class PackageFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert package.verify()['status']=='candidate-assembly-package-consistent'

    def rejects(self, relative, mutate):
        original=package.read
        def injected(path):
            data=original(path)
            if path==package.BASE/relative:
                data=copy.deepcopy(data);mutate(data)
            return data
        with patch.object(package,'read',side_effect=injected):
            with self.assertRaises(AssertionError):package.verify()

    def test_previous_seven_wire_harness_rejected(self):
        self.rejects('audit/closed-assembly.json',lambda d:d['nominal']['wires'].pop('power'))

    def test_missing_printed_part_rejected(self):
        self.rejects('audit/guides.json',lambda d:d['parts'].pop())

    def test_foreign_mating_housing_collision_rejected(self):
        self.rejects('audit/assembly.json',lambda d:d['mated_housing_cross_checks'][0].update(minimum_expanded_gap_mm=0))

    def test_previous_J1_data_board_rejected(self):
        self.rejects('assembly/render-manifest.json',lambda d:d['fitted_mainboard_references'].remove('J4'))

    def test_partial_view_from_old_surface_map_rejected(self):
        self.rejects('assembly/render-manifest.json',lambda d:d['outputs']['rear.png'].update(surface_report_sha256='0'*64))

    def test_partial_view_from_old_guides_rejected(self):
        self.rejects('assembly/render-manifest.json',lambda d:d['outputs']['rear.png'].update(guides_report_sha256='0'*64))

    def test_missing_physical_spring_rejected(self):
        self.rejects('assembly/render-manifest.json',lambda d:d['exploded_visible_objects_by_group'].update(springs=59))


if __name__=='__main__':unittest.main()
