#!/usr/bin/env python3
"""Compare generated source with scratch regeneration; never overwrite edits."""
from pathlib import Path
import tempfile

import build_ble_interface as generator


def main():
    if not __debug__:
        raise SystemExit("Run without -O")
    actual = generator.DEST
    with tempfile.TemporaryDirectory(prefix="yaeckb-interface-regenerate-") as folder:
        generator.DEST = Path(folder)
        generator.build()
        mismatches = [p.name for p in generator.DEST.iterdir()
                      if not (actual / p.name).is_file() or p.read_bytes() != (actual / p.name).read_bytes()]
        if mismatches:
            raise ValueError(f"Generated interface differs from its generator: {mismatches}")
    print("Interface source matches scratch regeneration; existing files were not overwritten")


if __name__ == "__main__":
    main()
