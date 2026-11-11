"""Read linked ARM HID layouts; retain duplicate local symbols and runtime limits."""
import hashlib
import struct


class Elf32:
    def __init__(self, data):
        self.data = data
        assert data[:6] == b'\x7fELF\x01\x01' and struct.unpack_from('<H', data, 18)[0] == 40
        start = struct.unpack_from('<I', data, 32)[0]
        stride, count = struct.unpack_from('<HH', data, 46)
        self.sections = [struct.unpack_from('<10I', data, start+i*stride) for i in range(count)]
        self.symbols = {}
        for section in self.sections:
            if section[1] != 2:
                continue
            strings = self.sections[section[6]]
            names = data[strings[4]:strings[4]+strings[5]]
            for at in range(section[4], section[4]+section[5], section[9]):
                name, value, size, info, other, index = struct.unpack_from('<IIIBBH', data, at)
                name = names[name:names.find(b'\0', name)].decode(errors='replace')
                if index and index < len(self.sections):
                    self.symbols.setdefault(name, []).append((value, size, index))

    def copies(self, name):
        result = []
        for address, size, index in self.symbols[name]:
            section = self.sections[index]
            assert section[1] != 8, 'Requested symbol has no file-backed bytes: '+name
            offset = section[4]+address-section[3]
            assert section[4] <= offset and offset+size <= section[4]+section[5]
            result.append((self.data[offset:offset+size], offset))
        return result

    def one(self, name):
        copies = self.copies(name)
        assert len(copies) == 1, 'Ambiguous ELF symbol: '+name
        return copies[0]

    def usb_descriptors(self):
        start, _, index = self.symbols['__usb_descriptor_start'][0]
        end, _, end_index = self.symbols['__usb_descriptor_end'][0]
        assert index == end_index and start < end
        section = self.sections[index]
        offset = section[4]+start-section[3]
        data = self.data[offset:offset+end-start]
        result = []
        at = 0
        while at < len(data) and data[at]:
            size = data[at]
            assert size >= 2 and at+size <= len(data), 'Malformed linked USB descriptor'
            result.append((data[at:at+size], offset+at))
            at += size
        assert not any(data[at:]), 'Nonzero bytes after USB descriptor sentinel'
        return result


def input_items(data):
    """Decode short HID items to size actual input fields, not byte-pattern guesses."""
    state = {'page': 0, 'id': 0, 'size': 0, 'count': 0, 'logical_min': 0, 'logical_max': 0}
    stack = []
    local = {}
    items = []
    at = 0
    collections = 0
    while at < len(data):
        prefix = data[at]
        at += 1
        assert prefix != 0xfe, 'Unsupported HID long item'
        size = [0, 1, 2, 4][prefix & 3]
        assert at+size <= len(data), 'Truncated HID item'
        value = int.from_bytes(data[at:at+size], 'little')
        at += size
        kind, tag = (prefix >> 2) & 3, prefix >> 4
        if kind == 1:
            field = {0: 'page', 1: 'logical_min', 2: 'logical_max', 7: 'size', 8: 'id', 9: 'count'}.get(tag)
            if field:
                state[field] = value
                if field == 'id':
                    assert 1 <= value <= 255, 'Invalid HID report ID'
            elif tag == 10:
                stack.append(dict(state))
            elif tag == 11:
                assert stack, 'Unbalanced HID global pop'
                state = stack.pop()
            else:
                assert tag in [3, 4, 5, 6], 'Unknown HID global item'
        elif kind == 2:
            assert tag in [0, 1, 2], 'Unsupported HID local item'
            local[{0: 'usage', 1: 'usage_min', 2: 'usage_max'}[tag]] = value
        elif kind == 0:
            if tag == 8:
                assert state['id'] and state['size'] and state['count'], 'Incomplete HID input item'
                items.append({**state, **local, 'flags': value})
            elif tag == 10:
                collections += 1
            elif tag == 12:
                collections -= 1
                assert collections >= 0, 'Unbalanced HID collection'
            else:
                raise AssertionError('Unexpected output/feature/other HID main item')
            local = {}
        else:
            raise AssertionError('Reserved HID item type')
    assert collections == 0 and not stack, 'Unbalanced HID descriptor'
    return items


def linked_hid_layout(data, minimum_ATT_MTU=23):
    elf = Elf32(data)
    maps = elf.copies('zmk_hid_report_desc')
    assert len(maps) == 2, 'Expected separate linked USB and BLE report maps'
    assert maps[0][0] == maps[1][0], 'Linked USB/BLE HID maps differ'
    descriptor = maps[0][0]
    items = input_items(descriptor)
    expected = [
        dict(id=1, page=7, size=1, count=8, flags=2, logical_min=0, logical_max=1, usage_min=0xe0, usage_max=0xe7),
        dict(id=1, page=7, size=8, count=1, flags=3, logical_min=0, logical_max=1),
        dict(id=1, page=7, size=8, count=6, flags=0, logical_min=0, logical_max=255, usage_min=0, usage_max=255),
        dict(id=2, page=12, size=16, count=6, flags=0, logical_min=0, logical_max=4095, usage_min=0, usage_max=4095)]
    assert items == expected, 'Unexpected linked HID input layout'
    bits = {}
    for item in items:
        bits[item['id']] = bits.get(item['id'], 0)+item['size']*item['count']
    assert bits == {1: 64, 2: 96}, 'Linked HID report bit counts differ'
    reports = {}
    for name, report_id, symbol, ref in [('keyboard', 1, 'keyboard_report', 'input'), ('consumer', 2, 'consumer_report', 'consumer_input')]:
        value, _ = elf.one(symbol)
        body_bytes = bits[report_id]//8
        assert len(value) == body_bytes+1 and value[0] == report_id, 'Linked HID object size/ID mismatch: '+name
        report_ref, _ = elf.one(ref)
        assert report_ref == bytes([report_id, 1]), 'Linked BLE Report Reference mismatch: '+name
        reports[name] = dict(report_id=report_id, body_bytes=body_bytes, USB_report_bytes=len(value))
    interfaces = []
    current = None
    for descriptor_bytes, offset in elf.usb_descriptors():
        kind = descriptor_bytes[1]
        if kind == 4:
            current = None
            if descriptor_bytes[5] == 3:
                assert len(descriptor_bytes) == 9 and descriptor_bytes[4] == 1
                assert descriptor_bytes[6:8] == b'\0\0', 'Unexpected USB HID boot subclass/protocol'
                current = {'HID': [], 'endpoints': []}
                interfaces.append(current)
        elif current is not None:
            if kind == 0x21:
                assert len(descriptor_bytes) == 9 and descriptor_bytes[5:7] == b'\x01\x22'
                assert int.from_bytes(descriptor_bytes[7:9], 'little') == 0, 'Unexpected initial HID length placeholder'
                current['HID'].append(descriptor_bytes)
            elif kind == 5:
                assert len(descriptor_bytes) == 7 and descriptor_bytes[2] & 0x80
                assert descriptor_bytes[3] == 3, 'HID endpoint is not interrupt IN'
                current['endpoints'].append({'max_packet_bytes':int.from_bytes(descriptor_bytes[4:6], 'little'), 'interval_ms':descriptor_bytes[6]})
    assert len(interfaces) == 1 and len(interfaces[0]['HID']) == 1 and len(interfaces[0]['endpoints']) == 1
    endpoint = interfaces[0]['endpoints'][0]
    assert endpoint['max_packet_bytes'] == 16 and endpoint['interval_ms'] == 1, 'Unexpected HID endpoint capacity/interval'
    assert max(value['USB_report_bytes'] for value in reports.values()) <= endpoint['max_packet_bytes'], 'HID report exceeds USB endpoint'
    assert minimum_ATT_MTU == 23
    assert max(value['body_bytes'] for value in reports.values()) <= minimum_ATT_MTU-3, 'HID body exceeds minimum ATT notification payload'
    return {'status':'linked-HID-layout-passed', 'report_map_copies':len(maps), 'report_map_bytes':len(maps[0][0]),
            'report_map_sha256':hashlib.sha256(maps[0][0]).hexdigest(), 'reports':reports, 'USB_interrupt_IN':endpoint,
            'USB_boot_subclass_protocol':False, 'BLE_report_refs':{'keyboard':[1,1],'consumer':[2,1]},
            'minimum_ATT_MTU_bytes':minimum_ATT_MTU, 'minimum_ATT_notification_payload_bytes':minimum_ATT_MTU-3,
            'runtime_descriptor_patch_verified':False, 'physical_verification':False}


def verify_summary(report):
    assert report['status'] == 'linked-HID-layout-passed' and report['physical_verification'] is False
    assert report['report_map_copies'] == 2 and report['report_map_bytes'] == 77
    assert report['reports'] == {'keyboard':{'report_id':1,'body_bytes':8,'USB_report_bytes':9}, 'consumer':{'report_id':2,'body_bytes':12,'USB_report_bytes':13}}
    assert report['USB_interrupt_IN'] == {'max_packet_bytes':16,'interval_ms':1}
    assert report['BLE_report_refs'] == {'keyboard':[1,1],'consumer':[2,1]}
    assert report['minimum_ATT_MTU_bytes'] == 23 and report['minimum_ATT_notification_payload_bytes'] == 20
    assert report['USB_boot_subclass_protocol'] is False and report['runtime_descriptor_patch_verified'] is False
