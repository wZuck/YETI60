#!/usr/bin/env python3
"""Run portable calibration acceptance under ASan/UBSan."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    sources=[ROOT/'firmware/yeti60/calibration.c',ROOT/'firmware/yeti60/calibration.h',
             ROOT/'tests/yeti60/calibration.c',Path(__file__)]
    with tempfile.TemporaryDirectory(prefix='yeti60-calibration-') as directory:
        executable=Path(directory)/'calibration'
        subprocess.run([shutil.which('clang'),'-std=c11','-Wall','-Wextra','-Werror','-O1','-g',
                        '-fsanitize=address,undefined','-fno-sanitize-recover=all',
                        '-I',str(ROOT/'firmware/yeti60'),str(sources[0]),str(sources[2]),'-o',str(executable)],check=True)
        run=subprocess.run([str(executable)],capture_output=True,text=True,check=True)
    report={'status':'passed','execution':'native host ASan/UBSan; no physical calibration performed',
            'output':run.stdout.splitlines(),'minimum_samples':64,'capture_samples':128,
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'physical_verification':False}
    (ROOT/'docs/audit/calibration.json').write_text(json.dumps(report,indent=2)+'\n')
    print(run.stdout,end='')


if __name__=='__main__':main()
