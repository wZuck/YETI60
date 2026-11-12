#!/usr/bin/env python3
"""Fault injection against the actual E73 USB repair, using KiCad Python."""
import importlib.util
import json
import concurrent.futures
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_e73_usb_repair as check
from kicad_sexpr import child, dumps, loads


class NativeRepairFaults(unittest.TestCase):
    def board(self):
        return pcb.LoadBoard(str(check.BASE / (check.NAME + '.kicad_pcb')))

    def pad(self, board, ref, number):
        return next(p for f in board.GetFootprints() if f.GetReference() == ref
                    for p in f.Pads() if p.GetNumber() == number)

    def test_positive_complete_netlist_and_native_pairs(self):
        check.netlist_contract(check.SOURCE / 'netlist.xml', check.BASE / 'netlist.xml')
        result = check.connectivity(self.board(), check.BASE / 'netlist.xml')
        self.assertGreater(result['signal_power_pairs'], 250)
        self.assertGreater(result['ground_pairs'], 140)
        check.usb_paths(self.board())

    def test_deleted_power_hierarchy_is_rejected(self):
        tree = ET.parse(check.BASE / 'netlist.xml')
        components = tree.find('components')
        components.remove(next(c for c in components if c.get('ref') == 'U6'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'missing-power.xml'
            tree.write(path)
            with self.assertRaises(AssertionError):
                check.netlist_contract(check.SOURCE / 'netlist.xml', path)

    def test_USB_data_swap_is_rejected(self):
        board = self.board()
        a, b = self.pad(board, 'J4', '2'), self.pad(board, 'J4', '3')
        na, nb = a.GetNet(), b.GetNet()
        a.SetNet(nb)
        b.SetNet(na)
        with self.assertRaises(AssertionError):
            check.connectivity(board, check.BASE / 'netlist.xml')

    def test_USB_positive_trace_cut_is_rejected(self):
        # Make a real damaged board file. PCB.Remove() invalidates some SWIG
        # wrappers in this KiCad build; it must not count as detecting a fault.
        tree = loads((check.BASE / (check.NAME + '.kicad_pcb')).read_text())
        removed = [n for n in tree if isinstance(n, list) and n[0] in ['segment', 'arc', 'via'] and child(n, 'net')[1] == 'USB_DP']
        self.assertTrue(removed)
        for item in removed:
            tree.remove(item)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cut-positive.kicad_pcb'
            path.write_text(dumps(tree) + '\n')
            board = pcb.LoadBoard(str(path))
            with self.assertRaises(AssertionError):
                check.connectivity(board, check.BASE / 'netlist.xml')
            with self.assertRaises(AssertionError):
                check.usb_paths(board)

    def test_E73_land_displacement_is_rejected(self):
        board = self.board()
        pad = self.pad(board, 'U1', '43')
        pad.SetPosition(pad.GetPosition() + pcb.VECTOR2I(pcb.FromMM(.05), 0))
        with self.assertRaises(AssertionError):
            check.preserved_geometry(board, pcb.LoadBoard(str(check.SOURCE / (check.NAME + '.kicad_pcb'))))

    def test_retained_control_copper_net_change_is_rejected(self):
        board = self.board()
        retired=set(json.loads((ROOT/'hardware/e73-usb-repair-spec.json').read_text())['removed_RESET_B_item_UUIDs'])
        original=pcb.LoadBoard(str(check.SOURCE/(check.NAME+'.kicad_pcb')))
        retained={check.uid(t)for t in original.GetTracks()}-retired
        track = next(t for t in board.GetTracks() if t.GetNetname() == 'RESET_N' and check.uid(t)in retained)
        track.SetNet(self.pad(board, 'J4', '1').GetNet())
        with self.assertRaises(AssertionError):
            check.preserved_geometry(board, pcb.LoadBoard(str(check.SOURCE / (check.NAME + '.kicad_pcb'))))

    def test_new_via_in_module_land_is_rejected(self):
        board = self.board()
        via = pcb.PCB_VIA(board)
        via.SetViaType(pcb.VIATYPE_THROUGH)
        via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
        via.SetWidth(pcb.FromMM(.5))
        via.SetDrill(pcb.FromMM(.3))
        via.SetPosition(self.pad(board, 'U1', '29').GetPosition())
        via.SetNet(self.pad(board, 'U1', '29').GetNet())
        board.Add(via)
        with self.assertRaises(AssertionError):
            check.preserved_geometry(board, pcb.LoadBoard(str(check.SOURCE / (check.NAME + '.kicad_pcb'))))

    def test_existing_power_only_J1_cannot_reconnect_data(self):
        board = self.board()
        self.pad(board, 'J1', '2').SetNet(self.pad(board, 'J4', '2').GetNet())
        with self.assertRaises(AssertionError):
            check.connectivity(board, check.BASE / 'netlist.xml')

    def test_C5_unprotected_IO_or_missing_ground_is_rejected(self):
        spec = importlib.util.spec_from_file_location('e73_test_C5', ROOT / 'variants/raytac/scripts/check_yeti60_c5_protection.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = ROOT / 'hardware/usb-daughterboard/upstream/UDB.kicad_pcb'
        for pins in [('1', '4'), ('3',)]:
            board = pcb.LoadBoard(str(source))
            for number in pins:
                self.pad(board, 'U1', number).SetNetCode(0)
            with self.assertRaises(AssertionError):
                module.verify(board)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--case':
        result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([NativeRepairFaults(sys.argv[2])]))
        raise SystemExit(0 if result.wasSuccessful() else 1)
    # KiCad 10's SWIG/wx runtime can lose registered wrapper types after
    # repeated board teardown. Isolate real native mutations by process;
    # assertion failures and runtime errors both fail the parent run.
    cases = unittest.defaultTestLoader.getTestCaseNames(NativeRepairFaults)
    def run_case(name):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--case', name], capture_output=True, text=True)
        return name, result.returncode, result.stdout + result.stderr
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run_case, cases))
    for name, code, output in results:
        print(name, 'PASS' if code == 0 else 'FAIL')
        if code:
            print(output[-6000:])
    successful = all(code == 0 for _, code, _ in results)
    inputs = [Path(__file__), ROOT / 'scripts/check_e73_usb_repair.py',
              check.BASE / (check.NAME + '.kicad_pcb'), check.BASE / 'netlist.xml',
              check.SOURCE / (check.NAME + '.kicad_pcb'), check.SOURCE / 'netlist.xml',
              ROOT / 'hardware/usb-daughterboard/upstream/UDB.kicad_pcb',
              ROOT / 'variants/raytac/scripts/check_yeti60_c5_protection.py',
              ROOT / 'scripts/check_yeti60_signal_paths.py', ROOT / 'scripts/check_schematic_current.py']
    report = {'status': 'passed' if successful else 'failed',
              'test_methods': len(cases), 'failed_methods': [name for name, code, _ in results if code],
              'process_isolation': True,
              'physical_verification': False,
              'source_sha256': {str(p.relative_to(ROOT)): check.sha(p) for p in inputs}}
    (check.BASE / 'audit/fault-tests.json').write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if successful else 1)
