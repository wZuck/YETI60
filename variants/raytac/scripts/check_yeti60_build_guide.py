#!/usr/bin/env python3
"""Reject stale/missing step images and incomplete placement instructions."""
import csv
import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path = ROOT/'docs/audit/yeti60-build-guide.json'
    report = json.loads(path.read_text())
    assert report['status'] == 'source-linked-illustrated-prototype-guide'
    assert not report['production_approved']
    for mapping in ['source_sha256', 'geometry_sources', 'outputs']:
        for name, digest in report[mapping].items():
            assert sha(ROOT/name) == digest, 'Stale build-guide source/output: '+name
    assert sha(ROOT/'.assembly-work/build-map.json') == report['native_map_sha256']
    assert report['steps_per_language'] == 28 and report['mounting_holes'] == 29
    assert len(report['underside_foot_pocket_centers_case_mm']) == 4
    with (ROOT/'hardware/bom/mainboard.csv').open() as source:
        refs = {r for row in csv.DictReader(source) if int(row['Quantity']) for r in row['References'].split(', ')}
    assert set(report['fitted_mainboard_references_placed_once']) == refs and len(refs) == 76
    assert len(set(report['active_electrodes'])) == 60
    for language in ['en', 'zh-CN']:
        records = [s for s in report['steps'] if s['language'] == language]
        assert [s['id'] for s in records] == [f'{i:02}' for i in range(1, 29)]
        placed = [r for s in records for r in s['references']]
        assert len(placed) == len(set(placed)) == 76 and set(placed) == refs
        assert [s['id'] for s in records if s['optional']] == ['12', '13']
        doc = ROOT/('docs/assembly/build-guide.zh-CN.md' if language=='zh-CN' else 'docs/assembly/build-guide.md')
        for step in records:
            image = ROOT/step['image']
            assert f'images/{image.name}' in doc.read_text()
            with image.open('rb') as stream:
                header = stream.read(24)
            assert header[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', header[16:24]) == (2400,1500)
            assert ET.parse(image.with_suffix('.svg')).getroot().tag.endswith('svg')
    assert len([n for n in report['outputs'] if n.endswith(('.png','.svg'))]) == 112
    result = {'status':'passed', 'steps_per_language':28, 'illustrations_per_language':28,
              'mainboard_placement_references':76, 'guide_manifest_sha256':sha(path),
              'verification_recipe_sha256':sha(Path(__file__)), 'physical_verification':False}
    (ROOT/'docs/audit/yeti60-build-guide-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print('28 steps x 2 languages; all 112 PNG/SVG files and all 76 mainboard placement references current')


if __name__=='__main__':
    main()
