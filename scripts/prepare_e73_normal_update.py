#!/usr/bin/env python3
"""Prepare a SETTINGS-preserving E73 update without contacting the device."""

import argparse
import hashlib
import json
from pathlib import Path


CODE_END = 0xF0000
SETTINGS_END = 0x100000
FIRMWARE_PREFIX = "hardware/e73-hhkb-corner/firmware/"
NFCPINS = 0x1000120C
UICR_TRAILER = [b":020000041000EA", b":04120C00FEFFFFFFE3", b":00000001FF"]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def hex_memory(payload):
    """Decode standard Intel HEX data and reject ambiguous or truncated images."""
    high = 0
    ended = False
    memory = {}
    for number, line in enumerate(payload.splitlines(), 1):
        if ended or not line.startswith(b":"):
            raise ValueError(f"Invalid or trailing HEX record on line {number}")
        record = bytes.fromhex(line[1:].decode("ascii"))
        if len(record) < 5 or len(record) != record[0] + 5 or sum(record) % 256:
            raise ValueError(f"Invalid HEX length or checksum on line {number}")
        count, address, kind = record[0], int.from_bytes(record[1:3], "big"), record[3]
        data = record[4:-1]
        if kind == 0:
            if address + count > 0x10000:
                raise ValueError(f"HEX record crosses its address window on line {number}")
            for i, byte in enumerate(data, high + address):
                if i in memory:
                    raise ValueError(f"Duplicate HEX address 0x{i:08X}")
                memory[i] = byte
        elif kind in (2, 4) and address == 0 and count == 2:
            high = int.from_bytes(data, "big") << (4 if kind == 2 else 16)
        elif kind == 1 and address == 0 and count == 0:
            ended = True
        elif kind not in (3, 5) or address != 0 or count != 4:
            raise ValueError(f"Unsupported HEX record on line {number}")
    if not ended or not memory:
        raise ValueError("HEX data or EOF is missing")
    return memory


def application_only(full_hex):
    lines = full_hex.splitlines()
    if lines[-3:] != UICR_TRAILER:
        raise ValueError("Unexpected E73 UICR record or HEX trailer")
    application = b"\n".join(lines[:-3] + [UICR_TRAILER[-1]]) + b"\n"
    app_data = hex_memory(application)
    if min(app_data) != 0 or max(app_data) >= CODE_END:
        raise ValueError("Update contains bytes outside the application partition")
    expected = dict(app_data)
    expected.update(enumerate(bytes.fromhex("FEFFFFFF"), NFCPINS))
    if hex_memory(full_hex) != expected:
        raise ValueError("The complete image differs by more than UICR.NFCPINS")
    return application


def prepare(firmware_dir, output):
    manifest = json.loads((firmware_dir / "manifest.json").read_text())
    image = "releases/normal/yeti60-e73.hex"
    full_hex = (firmware_dir / image).read_bytes()
    if digest(full_hex) != manifest["published_outputs"][FIRMWARE_PREFIX + image]:
        raise ValueError("Normal E73 HEX does not match the published firmware manifest")
    evidence_path = "yeti60-target-check.json"
    evidence = (firmware_dir / evidence_path).read_bytes()
    if digest(evidence) != manifest["evidence"][FIRMWARE_PREFIX + evidence_path]:
        raise ValueError("Linked target check does not match the published firmware manifest")
    calibration_version = json.loads(evidence)["calibration_contract_version"]
    update = application_only(full_hex)
    with output.open("xb") as stream:
        stream.write(update)
    return {
        "update_hex": str(output),
        "sha256": digest(update),
        "calibration_contract_version": calibration_version,
        "settings_start_hex": "0xF0000",
        "settings_size_bytes": SETTINGS_END - CODE_END,
        "device_contacted": False,
    }


def settings_data(path):
    memory = hex_memory(path.read_bytes())
    if len(memory) != SETTINGS_END - CODE_END or min(memory) != CODE_END or max(memory) != SETTINGS_END - 1:
        raise ValueError(f"{path} must contain exactly the 64 KiB E73 settings partition")
    return bytes(memory[address] for address in range(CODE_END, SETTINGS_END))


def compare_settings(before, after):
    first, second = settings_data(before), settings_data(after)
    return {
        "same_settings": first == second,
        "settings_size_bytes": len(first),
        "settings_blank_before": all(byte == 0xFF for byte in first),
        "sha256_before": digest(first),
        "sha256_after": digest(second),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare", help="Write a new application-only normal HEX")
    prepare_parser.add_argument("output", type=Path)
    prepare_parser.add_argument("--firmware-dir", type=Path, default=Path(__file__).resolve().parent)
    check_parser = commands.add_parser("check-settings", help="Check that a backup is complete and nonblank")
    check_parser.add_argument("backup", type=Path)
    compare_parser = commands.add_parser("compare-settings", help="Compare before and after readback HEX files")
    compare_parser.add_argument("before", type=Path)
    compare_parser.add_argument("after", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.firmware_dir, args.output)
        elif args.command == "check-settings":
            data = settings_data(args.backup)
            result = {"settings_size_bytes": len(data),
                      "settings_blank": all(byte == 0xFF for byte in data), "sha256": digest(data)}
        else:
            result = compare_settings(args.before, args.after)
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))
    return 0 if result.get("same_settings", True) and not result.get("settings_blank", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
