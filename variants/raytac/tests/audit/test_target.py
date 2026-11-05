#!/usr/bin/env python3
"""A linked USB100 descriptor must not pass the P2 500 mA power contract."""
import importlib.util,unittest,sys,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('target',ROOT/'scripts/check_yeti60_target.py');target=importlib.util.module_from_spec(spec);spec.loader.exec_module(target)
class LinkedUsbPower(unittest.TestCase):
 def test_reject_USB_initialization_without_callback_wrapper(self):
  for variant in ['normal','calibrator']:
   with self.subTest(variant=variant):
    elf=(ROOT/'firmware/releases'/variant/'yeti60-raytac.elf').read_bytes()
    self.assertTrue(target.usb_callback_linkage(elf)['ZMK_init_calls_wrapper'])
    shoff=struct.unpack_from('<I',elf,32)[0];stride,count=struct.unpack_from('<HH',elf,46)
    sections=[struct.unpack_from('<IIIIIIIIII',elf,shoff+i*stride) for i in range(count)]
    modified=bytearray(elf);changed=False
    for section in sections:
     if section[1]!=2:continue
     strings=sections[section[6]];names=elf[strings[4]:strings[4]+strings[5]]
     for at in range(section[4],section[4]+section[5],section[9]):
      name,value,size,info,other,index=struct.unpack_from('<IIIBBH',elf,at)
      if names[name:names.find(b'\0',name)]!=b'zmk_usb_init':continue
      code=sections[index];offset=code[4]+(value&~1)-code[3]
      modified[offset:offset+size]=b'\x00\xbf'*(size//2)+b'\x00'*(size%2)
      changed=True
    self.assertTrue(changed)
    with self.assertRaisesRegex(AssertionError,'bypasses charger callback wrapper'):
     target.usb_callback_linkage(modified)
 def test_reject_descriptor_requesting_only_100mA(self):
  for variant in ['normal','calibrator']:
   with self.subTest(variant=variant):
    elf=(ROOT/'firmware/releases'/variant/'yeti60-raytac.elf').read_bytes()
    self.assertEqual(target.usb_configuration_power(elf),500)
    needle=b'\x09\x02\x00\x00\x00\x01\x00\xe0\xfa'
    self.assertEqual(elf.count(needle),1)
    modified=elf.replace(needle,needle[:-1]+b'\x32')
    with self.assertRaisesRegex(AssertionError,'descriptor must request 500'):
     target.usb_configuration_power(modified)
if __name__=='__main__':unittest.main(verbosity=2)
