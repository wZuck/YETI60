"""Adversarial checks for the USB candidate's native connectivity/geometry evidence."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import pcbnew as pcb
from kicad_sexpr import loads,dumps,children,child
from check_usb_short_route import BASE,geometry,connected_groups
class USBRepairFaults(unittest.TestCase):
    def setUp(self):
        self.path=BASE/'EC60-nRF52840.kicad_pcb'
    def test_current_pair_reaches_correct_module_pads(self):
        group=connected_groups(pcb.LoadBoard(str(self.path)))
        self.assertEqual(group['J4','2'],group['U1','34']);self.assertEqual(group['J4','3'],group['U1','35']);self.assertNotEqual(group['J4','2'],group['U1','35'])
    def test_data_lane_cut_is_detected(self):
        tree=loads(self.path.read_text())
        for n in list(children(tree,'segment')):
            if child(n,'net')[1]=='USB_DP':tree.remove(n)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'cut.kicad_pcb';path.write_text(dumps(tree)+'\n');g=connected_groups(pcb.LoadBoard(str(path)))
        self.assertNotEqual(g['J4','3'],g['U1','35'])
    def test_sensing_electrode_movement_is_detected(self):
        b=pcb.LoadBoard(str(self.path));before=geometry(b);f=next(f for f in b.GetFootprints() if f.GetReference()=='SW17');p=f.GetPosition();f.SetPosition(pcb.VECTOR2I(p.x+pcb.FromMM(.05),p.y));self.assertNotEqual(before,geometry(b))
    def test_mount_hole_movement_is_detected(self):
        b=pcb.LoadBoard(str(self.path));before=geometry(b);f=next(f for f in b.GetFootprints() if f.GetReference()=='H23');p=f.GetPosition();f.SetPosition(pcb.VECTOR2I(p.x,p.y+pcb.FromMM(.05)));self.assertNotEqual(before,geometry(b))
if __name__=='__main__':unittest.main()
