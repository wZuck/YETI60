#!/usr/bin/env python3
"""Native regressions for mid-track contacts, branches and curved geometry."""
import math
from pathlib import Path
import sys
import tempfile
import unittest
import pcbnew as pcb

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import check_yeti60_signal_paths as paths


class SignalPaths(unittest.TestCase):
    def test_midpoint_branch_is_split_without_charging_whole_primitive(self):
        board=pcb.BOARD();board.SetCopperLayerCount(4)
        nets={}
        for name in ['D+','D-','USB_DP','USB_DM']:
            net=pcb.NETINFO_ITEM(board,name);board.Add(net);nets[name]=net
        def vec(x,y):return pcb.VECTOR2I(pcb.FromMM(x),pcb.FromMM(y))
        parts={}
        def pad(ref,number,net,x,y):
            if ref not in parts:
                fp=pcb.FOOTPRINT(board);fp.SetReference(ref);board.Add(fp);parts[ref]=fp
            p=pcb.PAD(parts[ref]);p.SetNumber(number);p.SetAttribute(pcb.PAD_ATTRIB_SMD)
            p.SetShape(pcb.PAD_SHAPE_RECT);p.SetSize(vec(.4,.4));p.SetPosition(vec(x,y))
            layers=pcb.LSET();layers.AddLayer(pcb.B_Cu);p.SetLayerSet(layers);p.SetNet(nets[net]);parts[ref].Add(p)
        def track(net,a,b):
            t=pcb.PCB_TRACK(board);t.SetStart(vec(*a));t.SetEnd(vec(*b));t.SetWidth(pcb.FromMM(.2));t.SetLayer(pcb.B_Cu);t.SetNet(nets[net]);board.Add(t)
        for positive,y in [(False,0),(True,5)]:
            front,back=('D+','USB_DP') if positive else ('D-','USB_DM')
            resistor='R31' if positive else 'R30'
            pad('J1','3' if positive else '2',front,0,y)
            pad(resistor,'1',front,10,y);pad(resistor,'2',back,11,y)
            pad('U1','31' if positive else '29',back,20,y)
            pad('D1','2' if positive else '3',front,5,y+2)
            track(front,(0,y),(10,y));track(front,(5,y),(5,y+2));track(back,(11,y),(20,y))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.kicad_pcb';pcb.SaveBoard(str(path),board)
            record=paths.extract(path)
        for name in ['positive','negative']:
            self.assertAlmostEqual(record[name]['actual_trace_centerline_mm'],19,places=6)
            self.assertAlmostEqual(record[name]['geometric_centerline_path_mm'],20,places=6)
            self.assertAlmostEqual(record[name]['ESD_branch_to_main_path_mm'],2,places=6)
            self.assertEqual(record[name]['via_count'],0)
        self.assertAlmostEqual(record['geometric_path_difference_mm'],0,places=6)

    def test_arc_tessellation_preserves_quarter_circle_length(self):
        board=pcb.BOARD();arc=pcb.PCB_ARC(board);point=lambda x,y:pcb.VECTOR2I(pcb.FromMM(x),pcb.FromMM(y))
        arc.SetStart(point(1,0));arc.SetMid(point(math.sqrt(.5),math.sqrt(.5)));arc.SetEnd(point(0,1))
        points=paths.centerline(arc)
        self.assertLess(abs(sum(math.dist(a,b) for a,b in zip(points,points[1:]))-math.pi/2),.002)

    def test_crossing_contact_is_not_only_an_endpoint_projection(self):
        result=paths.contacts((0,0),(10,0),(5,-3),(5,3))
        self.assertTrue(any(abs(a-.5)<1e-9 and abs(b-.5)<1e-9 for a,b in result))


if __name__=='__main__':unittest.main()
