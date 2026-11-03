"""Reject the old fuse, a moved fuse and the old nominal-1206 land pattern."""
import sys,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import usb_short_fuse_contract as contract
from kicad_sexpr import loads,dumps,children,child


class FuseFailures(unittest.TestCase):
    def setUp(self):
        contract.verify_fuse()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        for name in ['EC60-nRF52840.kicad_pcb','EC60-nRF52840.kicad_sch','parts-qualification.json']:
            shutil.copyfile(contract.BASE/name,self.base/name)
        shutil.copytree(contract.BASE/'YAECKB.pretty',self.base/'YAECKB.pretty')

    def reject_board(self,mutate):
        path=self.base/'EC60-nRF52840.kicad_pcb';tree=loads(path.read_text())
        f=next(f for f in children(tree,'footprint') if contract.properties(f)['Reference']=='F1')
        mutate(f);path.write_text(dumps(tree)+'\n')
        with patch.object(contract,'BASE',self.base):
            with self.assertRaises(AssertionError):contract.verify_fuse()

    def test_old_land_size_rejected(self):
        self.reject_board(lambda f:child(children(f,'pad')[0],'size').__setitem__(slice(1,None),[1.25,1.75]))

    def test_old_500mA_part_rejected(self):
        self.reject_board(lambda f:next(p for p in children(f,'property') if p[1]=='Value').__setitem__(2,'500mA'))

    def test_moved_fuse_rejected(self):
        self.reject_board(lambda f:child(f,'at').__setitem__(1,88.659827))

    def test_old_resettable_symbol_rejected(self):
        path=self.base/'EC60-nRF52840.kicad_sch';tree=loads(path.read_text())
        f=next(f for f in children(tree,'symbol') if contract.properties(f).get('Reference')=='F1')
        child(f,'lib_id')[1]='YAECKB:Polyfuse';path.write_text(dumps(tree)+'\n')
        with patch.object(contract,'BASE',self.base):
            with self.assertRaises(AssertionError):contract.verify_fuse()


if __name__=='__main__':unittest.main()
