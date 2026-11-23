#!/usr/bin/env python3
"""Exercise copper routing and land parity against altered Gerber artwork."""

from pathlib import Path
import sys
import unittest
from zipfile import ZipFile

import pcbnew as pcb


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_e73_cam import copper_routing
from check_e73_copper_lands import check_copper_lands


STEM = "EC60-nRF52840"
BOARD = ROOT / "hardware/e73-hhkb-corner" / f"{STEM}.kicad_pcb"
ARCHIVE = ROOT / "delivery/YETI60-E73/01-pcb/YETI60-E73-gerbers-REVIEW.zip"
LAYERS = {
    pcb.F_Cu: "F_Cu.gtl",
    pcb.In1_Cu: "In1_Cu.g1",
    pcb.In2_Cu: "In2_Cu.g2",
    pcb.B_Cu: "B_Cu.gbl",
}
DATA_LAND = "%TO.P,U1,29*%\n%TO.N,USB_DM*%\nX337140000Y-195000000D03*\n"


class E73CamCopper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = pcb.LoadBoard(str(BOARD))
        cls.vias = [track for track in cls.board.GetTracks() if isinstance(track, pcb.PCB_VIA)]
        with ZipFile(ARCHIVE) as bundle:
            cls.artwork = {
                layer: bundle.read(f"{STEM}-{suffix}").decode("ascii")
                for layer, suffix in LAYERS.items()
            }

    def altered_layer(self, layer, old, new):
        artwork = self.artwork.copy()
        self.assertEqual(artwork[layer].count(old), 1)
        artwork[layer] = artwork[layer].replace(old, new)
        return artwork

    def test_delivery_lands_match_native_board(self):
        report = check_copper_lands(self.board, self.artwork)
        self.assertEqual(report["land_flashes_checked_by_layer"], {
            "F.Cu": 266, "In1.Cu": 3, "In2.Cu": 3, "B.Cu": 312,
        })
        self.assertEqual(report["land_flashes_checked"], 584)

    def test_missing_u1_data_land(self):
        missing = DATA_LAND.replace("X337140000Y-195000000D03*\n", "")
        artwork = self.altered_layer(pcb.F_Cu, DATA_LAND, missing)
        with self.assertRaisesRegex(AssertionError, "Copper land flash mismatch"):
            check_copper_lands(self.board, artwork)

    def test_wrong_u1_net_attribute(self):
        wrong_net = DATA_LAND.replace("USB_DM", "USB_DP")
        artwork = self.altered_layer(pcb.F_Cu, DATA_LAND, wrong_net)
        with self.assertRaisesRegex(AssertionError, "Copper land flash mismatch"):
            check_copper_lands(self.board, artwork)

    def test_land_added_on_wrong_side(self):
        wrong_side = "%TD*%\nD23*\n" + DATA_LAND + "M02*"
        artwork = self.altered_layer(pcb.B_Cu, "M02*", wrong_side)
        with self.assertRaisesRegex(AssertionError, "Copper land flash mismatch.*B.Cu"):
            check_copper_lands(self.board, artwork)

    def test_missing_inner_plated_land(self):
        artwork = self.altered_layer(pcb.In1_Cu, "X97012704Y-131809660D03*\n", "")
        with self.assertRaisesRegex(AssertionError, "Copper land flash mismatch.*In1.Cu"):
            check_copper_lands(self.board, artwork)

    def test_delivery_routing_matches_native_board(self):
        counts = [(1041, 11), (958, 94), (790, 139), (1583, 106)]
        for (layer, artwork), (straight, arcs) in zip(self.artwork.items(), counts):
            with self.subTest(layer=self.board.GetLayerName(layer)):
                report = copper_routing(artwork, self.board, layer, self.vias)
                self.assertEqual((report["straight_traces"], report["arc_traces"]), (straight, arcs))
                self.assertEqual(report["via_lands"], 852)

    def test_missing_straight_trace(self):
        artwork = self.altered_layer(pcb.F_Cu, "X330500000Y-190405000D01*\n", "")
        with self.assertRaisesRegex(AssertionError, "Gerber straight trace mismatch"):
            copper_routing(artwork[pcb.F_Cu], self.board, pcb.F_Cu, self.vias)

    def test_wrong_arc_sweep(self):
        arc = "G02*\nX299550359Y-196858282I-1414172J1414229D01*"
        artwork = self.altered_layer(pcb.In1_Cu, arc, arc.replace("G02*", "G03*"))
        with self.assertRaisesRegex(AssertionError, "Gerber arc sweep mismatch"):
            copper_routing(artwork[pcb.In1_Cu], self.board, pcb.In1_Cu, self.vias)

    def test_wrong_via_net(self):
        via = "%TO.N,USB_DM*%\nX337140000Y-196500000D03*"
        artwork = self.altered_layer(pcb.F_Cu, via, via.replace("USB_DM", "USB_DP"))
        with self.assertRaisesRegex(AssertionError, "Gerber via land or net mismatch"):
            copper_routing(artwork[pcb.F_Cu], self.board, pcb.F_Cu, self.vias)


if __name__ == "__main__":
    unittest.main()
