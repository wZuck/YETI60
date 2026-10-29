#!/usr/bin/env python3
"""Create a reproducible DFM review archive, never an order authorization."""
import csv
import hashlib
import io
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / 'hardware/ec60-nrf52840'
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
OUT = ROOT / 'hardware/fabrication'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    board = HW / 'EC60-nRF52840.kicad_pcb'
    before = sha(board)
    bom = json.loads((ROOT / 'docs/audit/yeti60-bom.json').read_text())
    purchased = {r.strip() for row in bom['rows'] if row['quantity']
                 for r in row['references'].split(',')}
    assert len(purchased) == 76
    OUT.mkdir(exist_ok=True)
    sources = [board, ROOT/'hardware/bom/mainboard.csv',
               ROOT/'hardware/bom/mainboard.zh-CN.csv',
               ROOT/'mechanical/pcb-fabrication-spec.json', HW/'fabrication-notes.md', HW/'fabrication-notes.zh-CN.md',
               ROOT/'docs/engineering/fabrication-review.md',
               ROOT/'docs/engineering/fabrication-review.zh-CN.md', Path(__file__)]
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    with tempfile.TemporaryDirectory(prefix='yeti60-dfm-') as directory:
        work = Path(directory)
        def run(*args):
            subprocess.run([CLI, 'pcb', 'export', *args, str(board)],
                           check=True, capture_output=True, text=True)
        run('gerbers', '--check-zones', '--layers', 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts,F.Fab,B.Fab',
            '--subtract-soldermask', '-o', str(work))
        run('drill', '--format', 'excellon', '--excellon-units', 'mm',
            '--excellon-separate-th', '--generate-report',
            '--report-path', str(work/'drill-report.txt'), '-o', str(work))
        run('ipcd356', '-o', str(work/'yeti60.ipc'))
        run('pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
            '-o', str(work/'positions-raw.csv'))
        raw = list(csv.DictReader((work/'positions-raw.csv').open()))
        assert raw and 'Ref' in raw[0]
        rows = [r for r in raw if r['Ref'] in purchased]
        assert {r['Ref'] for r in rows} == purchased
        with (work/'positions.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=raw[0], lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)
        (work/'positions-raw.csv').unlink()
        for source in sources[1:-1]:
            (work/source.name).write_bytes(source.read_bytes())
        # Normalize generation dates only; leave coordinates and process data intact.
        for path in work.iterdir():
            if path.suffix in ['.gbr', '.gbrjob', '.drl', '.txt', '.ipc'] or path.suffix.startswith('.g'):
                text = path.read_text()
                text = re.sub(r'20\d\d-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:[.+Z0-9:-]*)',
                              '2000-01-01T00:00:00', text)
                path.write_text(text)
        drills = {p.name:p.read_text() for p in work.glob('*.drl')}
        blind = {n:t for n,t in drills.items() if 'in2' in n.lower() or 'in2' in t.lower()}
        assert not blind, 'Ordinary process must not generate layer-pair drills: '+str(list(blind))
        blind_name=None;hits=[]
        assert any('NPTH' in n for n in drills) and any('PTH' in n and 'NPTH' not in n for n in drills)
        files = {p.name:sha(p) for p in sorted(work.iterdir()) if p.is_file()}
        manifest = {'purpose':'DFM and assembly review only; not manufacturing release',
                    'source_sha256':source_hashes, 'files_sha256':files,
                    'copper_layers':['F.Cu','In1.Cu','In2.Cu','B.Cu'],
                    'blind_drill_file':blind_name, 'blind_drill_hits':len(hits),
                    'placement_parts':len(rows), 'DNP':['JP1'],
                    'placement_frame':'KiCad absolute origin, mm; bottom X not negated; assembler must verify first article orientation',
                    'required_process':'JLC ordinary four-layer JLC04161H-7628, nominal order 1.6 mm; mechanical through holes only; no blind/buried, resin-filled or copper-capped process required',
                    'production_approved':False}
        (work/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        target = OUT/'yeti60-p2-dfm-review.zip'
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(work.iterdir()):
                info = zipfile.ZipInfo(path.name, (2000,1,1,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
    assert sha(board) == before
    report = {**manifest, 'status':'review-package-generated-not-order-release',
              'outputs':{str(target.relative_to(ROOT)):sha(target)}}
    (ROOT/'docs/audit/yeti60-fabrication.json').write_text(json.dumps(report, indent=2)+'\n')
    print('DFM review archive: four copper layers, zero blind holes, 76 placements; supplier approval pending')


if __name__ == '__main__':
    main()
