#!/usr/bin/env python3
"""Reject broken linked USB power/callback and HID format contracts."""
import importlib.util,unittest,sys,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('target',ROOT/'scripts/check_yeti60_target.py');target=importlib.util.module_from_spec(spec);spec.loader.exec_module(target)
from yeti60_hid_contract import Elf32,input_items,linked_hid_layout,verify_summary

class LinkedHidLayout(unittest.TestCase):
 def images(self):
  for variant in ['normal','calibrator']:
   yield variant,(ROOT/'firmware/releases'/variant/'yeti60-e73.elf').read_bytes()

 def mutate_maps(self,elf,old,new,all_copies=True):
  data=bytearray(elf);maps=Elf32(elf).copies('zmk_hid_report_desc')
  for body,offset in maps if all_copies else maps[:1]:
   self.assertEqual(body.count(old),1)
   at=offset+body.index(old);data[at:at+len(old)]=new
  return data

 def test_linked_layout_in_both_images(self):
  for variant,elf in self.images():
   with self.subTest(variant=variant):verify_summary(linked_hid_layout(elf))

 def test_reject_different_USB_BLE_maps(self):
  for variant,elf in self.images():
   with self.subTest(variant=variant),self.assertRaisesRegex(AssertionError,'maps differ'):
    linked_hid_layout(self.mutate_maps(elf,b'\x75\x08\x95\x06',b'\x75\x08\x95\x05',False))

 def test_reject_wrong_key_count_in_both_maps(self):
  for variant,elf in self.images():
   with self.subTest(variant=variant),self.assertRaisesRegex(AssertionError,'input layout'):
    linked_hid_layout(self.mutate_maps(elf,b'\x75\x08\x95\x06',b'\x75\x08\x95\x05'))

 def test_reject_smaller_USB_endpoint(self):
  for variant,elf in self.images():
   data=bytearray(elf);changed=0;hid=False
   for descriptor,offset in Elf32(elf).usb_descriptors():
    if descriptor[1]==4:hid=descriptor[5]==3
    if descriptor[1]==5 and hid:data[offset+4:offset+6]=b'\x08\0';changed+=1
   self.assertEqual(changed,1)
   with self.subTest(variant=variant),self.assertRaisesRegex(AssertionError,'endpoint capacity'):
    linked_hid_layout(data)

 def test_reject_wrong_BLE_reference(self):
  for variant,elf in self.images():
   data=bytearray(elf);_,offset=Elf32(elf).one('consumer_input');data[offset]=3
   with self.subTest(variant=variant),self.assertRaisesRegex(AssertionError,'Report Reference'):
    linked_hid_layout(data)

 def test_reject_wrong_linked_keyboard_report_ID(self):
  for variant,elf in self.images():
   data=bytearray(elf);_,offset=Elf32(elf).one('keyboard_report');data[offset]=2
   with self.subTest(variant=variant),self.assertRaisesRegex(AssertionError,'object size/ID'):
    linked_hid_layout(data)

 def test_reject_zero_report_ID(self):
  for variant,elf in self.images():
   with self.subTest(variant=variant),self.assertRaisesRegex(AssertionError,'Invalid HID report ID'):
    linked_hid_layout(self.mutate_maps(elf,b'\x85\x01',b'\x85\x00'))

 def test_reject_wrong_input_report_type(self):
  for variant,elf in self.images():
   with self.subTest(variant=variant),self.assertRaisesRegex(AssertionError,'Unexpected output'):
    linked_hid_layout(self.mutate_maps(elf,b'\x81\x02',b'\x91\x02'))

 def test_reject_wrong_modifier_usage_range(self):
  for variant,elf in self.images():
   with self.subTest(variant=variant),self.assertRaisesRegex(AssertionError,'input layout'):
    linked_hid_layout(self.mutate_maps(elf,b'\x29\xe7',b'\x29\xe6'))

 def test_reject_truncated_and_unbalanced_items(self):
  for variant,elf in self.images():
   descriptor=Elf32(elf).copies('zmk_hid_report_desc')[0][0]
   with self.subTest(variant=variant),self.assertRaisesRegex(AssertionError,'Unbalanced'):
    input_items(descriptor[:-1])
   with self.subTest(variant=variant),self.assertRaisesRegex(AssertionError,'Truncated'):
    input_items(b'\x75')

class LinkedUsbPower(unittest.TestCase):
 def test_reject_USB_initialization_without_callback_wrapper(self):
  for variant in ['normal','calibrator']:
   with self.subTest(variant=variant):
    elf=(ROOT/'firmware/releases'/variant/'yeti60-e73.elf').read_bytes()
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
