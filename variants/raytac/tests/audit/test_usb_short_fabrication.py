"""CAM parity must reject plausible mixed files, moved holes and wrong masks."""
import copy
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import check_usb_short_fabrication as cam
from gerbonara.graphic_objects import Flash
from gerbonara.apertures import CircleAperture


class CAMFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert cam.verify()['status']=='candidate-CAM-native-roundtrip-passed'
        cls.native=cam.read(cam.OUT/'native-map.json')

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)
        for archive in ['yeti60-raytac-candidate-gerbers.zip','yeti60-raytac-candidate-bottom-stencil.zip']:
            with zipfile.ZipFile(cam.OUT/archive) as z:z.extractall(self.work)

    def gerber(self,layer):
        return cam.GerberFile.open(self.work/(cam.NAME+'-'+layer+'.gbr'))

    def test_displaced_thermal_drill_rejected(self):
        p=self.work/(cam.NAME+'-PTH.drl');text=p.read_text()
        match=re.search(r'^X133(?:\.0*)?Y-140\.80*$',text,re.MULTILINE);self.assertIsNotNone(match)
        p.write_text(text[:match.start()]+'X133.1Y-140.8'+text[match.end():])
        with self.assertRaisesRegex(AssertionError,'Missing/moved/drill-size/plating mismatch'):
            cam.check_drills(self.work,self.native)

    def test_incorrect_NPTH_plating_rejected(self):
        p=self.work/(cam.NAME+'-NPTH.drl');text=p.read_text()
        self.assertIn('TF.FileFunction,NonPlated,1,4,NPTH',text)
        p.write_text(text.replace('TF.FileFunction,NonPlated,1,4,NPTH','TF.FileFunction,Plated,1,4,PTH'))
        with self.assertRaisesRegex(AssertionError,'Wrong drill layer span/plating'):
            cam.check_drills(self.work,self.native)

    def test_reversed_copper_files_rejected(self):
        with self.assertRaisesRegex(AssertionError,'Missing/wrong native copper land'):
            cam.check_pads({'F.Cu':self.gerber('B_Cu'),'B.Cu':self.gerber('F_Cu')},self.native)

    def test_moved_power_capacitor_land_rejected(self):
        back=self.gerber('B_Cu')
        p=next(o for o in back.objects if isinstance(o.attrs,dict) and o.attrs.get('.P')==('C40','1'))
        p.x+=.1
        with self.assertRaisesRegex(AssertionError,'Missing/wrong native copper land'):
            cam.check_pads({'F.Cu':self.gerber('F_Cu'),'B.Cu':back},self.native)

    def test_wrong_power_net_rejected(self):
        back=self.gerber('B_Cu')
        p=next(o for o in back.objects if isinstance(o.attrs,dict) and o.attrs.get('.P',())[:2]==('U6','1'))
        p.attrs['.N']=('GND',)
        with self.assertRaisesRegex(AssertionError,'CAM pad net mismatch'):
            cam.check_pads({'F.Cu':self.gerber('F_Cu'),'B.Cu':back},self.native)

    def test_open_profile_rejected(self):
        profile=self.gerber('Edge_Cuts');profile.objects[0].x1+=.05
        with self.assertRaisesRegex(AssertionError,'Open/ambiguous Gerber profile endpoint'):
            cam.check_outline(profile,self.native)

    def test_JP1_extra_paste_rejected(self):
        stencil=self.gerber('B_Paste');extra=copy.deepcopy(stencil.objects[0])
        extra.x,extra.y=self.native['excluded_paste'][0]['center_mm'];stencil.objects.append(extra)
        with self.assertRaisesRegex(AssertionError,'Unexpected paste aperture count'):
            cam.check_stencil(stencil,self.native)

    def test_front_thermal_hole_opening_rejected(self):
        front=self.gerber('F_Mask')
        front.objects.append(Flash(133,-140.8,CircleAperture(.4,unit=cam.MM),unit=cam.MM,attrs={}))
        with self.assertRaisesRegex(AssertionError,'Front thermal via not tented'):
            cam.check_masks(front,self.gerber('B_Mask'))

    def test_covered_back_thermal_hole_rejected(self):
        back=self.gerber('B_Mask')
        back.objects=[o for o in back.objects if not (o.bounding_box(cam.MM)[0][0]<=133<=o.bounding_box(cam.MM)[1][0] and o.bounding_box(cam.MM)[0][1]<=-140.8<=o.bounding_box(cam.MM)[1][1])]
        with self.assertRaisesRegex(AssertionError,'Back thermal hole not fully open'):
            cam.check_masks(self.gerber('F_Mask'),back)

    def test_IPC_aux_origin_offset_rejected(self):
        text=(cam.OUT/'mainboard.ipc').read_text()
        shifted=re.sub(r'X([+-]\d{6})',lambda m:'X'+f'{int(m[1])+1000:+07d}',text)
        self.assertNotEqual(text,shifted);(self.work/'mainboard.ipc').write_text(shifted)
        with patch.object(cam,'OUT',self.work),self.assertRaisesRegex(AssertionError,'IPC origin/pad mismatch'):
            cam.check_ipc(self.native)

    def test_IPC_data_net_swap_rejected(self):
        text=(cam.OUT/'mainboard.ipc').read_text();self.assertIn('USB_DP',text)
        (self.work/'mainboard.ipc').write_text(text.replace('USB_DP','USB_DM'))
        with patch.object(cam,'OUT',self.work),self.assertRaisesRegex(AssertionError,'IPC net mismatch'):
            cam.check_ipc(self.native)

    def test_IPC_via_net_swap_rejected(self):
        netlist=cam.Netlist.open(cam.OUT/'mainboard.ipc')
        via=next(r for r in netlist.test_records if r.is_via and r.net_name!='GND')
        via.net_name='GND'
        with patch.object(cam.Netlist,'open',return_value=netlist),self.assertRaisesRegex(AssertionError,'IPC via net mismatch'):
            cam.check_ipc(self.native)


if __name__=='__main__':unittest.main()
