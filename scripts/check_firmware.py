#!/usr/bin/env python3
"""Exercise real scanner source with address/undefined-behaviour sanitizers."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "firmware/ec60")
    parser.add_argument("--bounds-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    compiler = shutil.which("clang")
    if not compiler:
        raise SystemExit("clang is required for the sanitizer checks")
    with tempfile.TemporaryDirectory(prefix="yaeckb-scanner-") as directory:
        binary = Path(directory) / "scanner-test"
        command = [compiler, "-std=c11", "-g", "-O1", "-fsanitize=address,undefined",
                   "-fno-sanitize-recover=all", "-fno-omit-frame-pointer",
                   "-I", str(ROOT / "tests/firmware/stubs"), "-I", str(source),
                   f'-DSCANNER_SOURCE="{source / "ec_switch_matrix.c"}"',
                   f'-DMATRIX_SOURCE="{source / "matrix.c"}"',
                   str(ROOT / "tests/firmware/scanner_test.c"), "-o", str(binary)]
        subprocess.run(command, check=True)
        cases = ["row-bounds", "scan-bounds"]
        if not args.bounds_only:
            cases.append("behaviour")
        results = []
        for case in cases:
            result = subprocess.run([str(binary), case], capture_output=True, text=True)
            results.append({"case": case, "exit_code": result.returncode,
                            "output": result.stdout.strip(), "errors": result.stderr.strip()})
        report = {"source": str(source.relative_to(ROOT)), "cases": results,
                          "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                            for p in sorted(source.glob("*.[ch]"))},
                          "limitations": ["mock ADC/GPIO; no timing, noise or physical calibration proof",
                                          "not a QMK target build or BLE firmware test"]}
        encoded = json.dumps(report, indent=2, ensure_ascii=False)
        print(encoded)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded + "\n")
        if any(r["exit_code"] != 0 for r in results):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
