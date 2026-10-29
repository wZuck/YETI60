#!/usr/bin/env python3
"""A linked USB100 descriptor must not pass the P2 500 mA power contract."""
import importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('target',ROOT/'scripts/check_yeti60_target.py');target=importlib.util.module_from_spec(spec);spec.loader.exec_module(target)
class LinkedUsbPower(unittest.TestCase):
 def test_reject_missing_or_protected_nfc_configuration(self):
  for image in [{},{0x1000120c:0xff},{0x1000120c:0x00}]:
   with self.subTest(image=image),self.assertRaisesRegex(AssertionError,'release both NFC pins'):
    target.verify_nfc_gpio(image)
  target.verify_nfc_gpio({0x1000120c:0xfe})
 def test_reject_descriptor_requesting_only_100mA(self):
  for variant in ['normal','calibrator']:
   with self.subTest(variant=variant):
    elf=(ROOT/'firmware/releases'/variant/'yeti60-e73.elf').read_bytes()
    self.assertEqual(target.usb_configuration_power(elf),500)
    needle=b'\x09\x02\x00\x00\x00\x01\x00\xe0\xfa'
    self.assertEqual(elf.count(needle),1)
    modified=elf.replace(needle,needle[:-1]+b'\x32')
    with self.assertRaisesRegex(AssertionError,'descriptor must request 500'):
     target.usb_configuration_power(modified)
if __name__=='__main__':unittest.main(verbosity=2)
