#!/usr/bin/env python3
"""Check the published application map and rejection of incomplete settings reads."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_e73_normal_update import CODE_END, NFCPINS, application_only, compare_settings, hex_memory, prepare


def record(address, kind, data):
    payload = bytes([len(data)]) + address.to_bytes(2, "big") + bytes([kind]) + data
    return b":" + (payload + bytes([-sum(payload) & 255])).hex().upper().encode() + b"\n"


def settings_image(first_byte):
    image = [record(0, 4, b"\x00\x0f")]
    for offset in range(0, 0x10000, 32):
        data = bytes([first_byte] + [0xFF] * 31) if offset == 0 else b"\xFF" * 32
        image.append(record(offset, 0, data))
    image.append(record(0, 1, b""))
    return b"".join(image)


class NormalUpdate(unittest.TestCase):
    def test_published_normal_maps_all_app_bytes_and_never_uicr(self):
        folder = ROOT / "hardware/e73-hhkb-corner/firmware"
        source = folder / "releases/normal/yeti60-e73.hex"
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "update.hex"
            report = prepare(folder, output)
            app = hex_memory(output.read_bytes())
            initial = hex_memory(source.read_bytes())
            self.assertEqual(app, {key: val for key, val in initial.items() if key < CODE_END})
            self.assertEqual(bytes(initial[i] for i in range(NFCPINS, NFCPINS + 4)), b"\xFE\xFF\xFF\xFF")
            self.assertFalse(report["device_contacted"])
            with self.assertRaises(FileExistsError):
                prepare(folder, output)

    def test_reject_settings_address_inside_normal_hex(self):
        source = (ROOT / "hardware/e73-hhkb-corner/firmware/releases/normal/yeti60-e73.hex").read_bytes()
        inserted = record(0, 4, b"\x00\x0f") + record(0, 0, b"\xAA")
        tail = source.splitlines(keepends=True)[-3:]
        changed = source[:-sum(map(len, tail))] + inserted + b"".join(tail)
        with self.assertRaisesRegex(ValueError, "outside the application"):
            application_only(changed)

    def test_compare_settings_detects_content_change_and_incomplete_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            before, after = Path(temp) / "before.hex", Path(temp) / "after.hex"
            before.write_bytes(settings_image(0xA5))
            after.write_bytes(before.read_bytes())
            self.assertTrue(compare_settings(before, after)["same_settings"])
            after.write_bytes(settings_image(0xB5))
            self.assertFalse(compare_settings(before, after)["same_settings"])
            after.write_bytes(record(0, 4, b"\x00\x0f") + record(0, 0, b"\xA5") + record(0, 1, b""))
            with self.assertRaisesRegex(ValueError, "exactly the 64 KiB"):
                compare_settings(before, after)


if __name__ == "__main__":
    unittest.main()
