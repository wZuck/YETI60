#!/usr/bin/env python3
"""Run portable calibration acceptance under ASan/UBSan."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import random
import struct
import zlib

ROOT=Path(__file__).resolve().parents[1]


def main():
    sources=[ROOT/'firmware/yeti60/calibration.c',ROOT/'firmware/yeti60/calibration.h',
             ROOT/'tests/yeti60/calibration.c',Path(__file__)]
    sources.append(ROOT/'firmware/yeti60/board_pins.h')
    with tempfile.TemporaryDirectory(prefix='yeti60-calibration-') as directory:
        directory=Path(directory);executable=directory/'calibration'
        payload=struct.pack('<I75H75H',0x12345678,*([1000]*75),*([1500]*75))
        reference=zlib.crc32(payload)
        def build(target,source):
            subprocess.run([shutil.which('clang'),'-std=c11','-Wall','-Wextra','-Werror','-O1','-g',
                        '-fsanitize=address,undefined','-fno-sanitize-recover=all',
                        '-DEXPECTED_RECORD_CRC='+hex(reference)+'u',
                        '-I',str(ROOT/'firmware/yeti60'),str(source),str(sources[2]),'-o',str(target)],check=True)
        build(executable,sources[0])
        run=subprocess.run([str(executable)],capture_output=True,text=True,check=True)
        rng=random.Random(0x59455449);encoded=[];expected=[]
        for _ in range(256):
            version=rng.getrandbits(32);low=[rng.randrange(0,4095) for _ in range(75)]
            high=[rng.randrange(n+1,4096) for n in low]
            data=struct.pack('<I75H75H',version,*low,*high);crc=zlib.crc32(data)
            encoded.append(data+struct.pack('<I',crc));expected.append(f'{crc:08x} 1')
            # Correct checksum never excuses an out-of-range threshold.
            high[0]=4096;data=struct.pack('<I75H75H',version,*low,*high);crc=zlib.crc32(data)
            encoded.append(data+struct.pack('<I',crc));expected.append(f'{crc:08x} 0')
        compared=subprocess.run([str(executable),'--records'],input=b''.join(encoded),capture_output=True,check=True)
        assert compared.stdout.decode().splitlines()==expected,'Independent zlib CRC/range comparison failed'
        original=sources[0].read_text();negative=[]
        for name,text in [
            ('omit-CRC-check',original.replace('value->crc32 != yeti_calibration_checksum(value)','false')),
            ('omit-ADC-range',original.replace(' || value->high[r][c] > 4095','')),
            ('wrong-CRC-polynomial',original.replace('0xedb88320u','0x82f63b78u'))]:
            assert text!=original,name
            mutant=directory/(name+'.c');mutant.write_text(text);binary=directory/name;build(binary,mutant)
            result=subprocess.run([str(binary)],capture_output=True,text=True)
            assert result.returncode!=0 and 'Assertion' in result.stderr,(name,result.stdout,result.stderr)
            negative.append(dict(case=name,exit_code=result.returncode,output=result.stderr.strip()[-600:]))
    report={'status':'passed','execution':'native host ASan/UBSan; no physical calibration performed',
            'output':run.stdout.splitlines(),'minimum_samples':64,'capture_samples':128,
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'physical_verification':False}
    report['storage_integrity']={'record_bytes':308,'legacy_record_bytes':304,'CRC':'CRC-32/ISO-HDLC; version/low/high little-endian fields; excludes CRC field','golden_record_crc32':hex(reference),'independent_zlib_records':512,'single_bit_flips_rejected':2464,'byte_inversions_rejected':308,'sliding_32_bit_bursts_rejected':2433,'rejected_mutants':negative,'physical_power_cut_tested':False}
    (ROOT/'docs/audit/calibration.json').write_text(json.dumps(report,indent=2)+'\n')
    print(run.stdout,end='')


if __name__=='__main__':main()
