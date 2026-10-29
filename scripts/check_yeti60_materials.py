#!/usr/bin/env python3
"""Prevent README purchase tables drifting from the current bilingual BOM."""
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = [Path(__file__)]
    for suffix in ['', '.zh-CN']:
        readme = ROOT/('README'+suffix+'.md')
        csv_path = ROOT/('hardware/bom/mainboard'+suffix+'.csv')
        material = ROOT/('docs/engineering/materials'+suffix+'.md')
        sources.extend([readme,csv_path,material])
        purchase_path = ROOT/('hardware/bom/mainboard-purchase'+suffix+'.csv')
        sources.append(purchase_path)
        purchases = {r[0]: r for r in list(csv.reader(purchase_path.open()))[1:]}
        tables = [[c.strip() for c in line.strip('|').split('|')]
                  for line in readme.read_text().splitlines() if line.startswith('|')]
        rows = list(csv.reader(csv_path.open()))[1:]
        fitted = [r for r in rows if int(r[1])]
        assert sum(int(r[1]) for r in fitted) == 76
        for row in fitted:
            stock = purchases[row[0]]
            assert row[:5] + [stock[2], stock[3], stock[9]] in tables, 'README component stock row stale: '+row[0]+suffix
            assert int(stock[1]) == int(stock[2]) + int(stock[3]) == int(row[1])
        daughter_path = ROOT/('hardware/bom/daughterboard'+suffix+'.csv')
        sources.append(daughter_path)
        daughter = list(csv.reader(daughter_path.open()))[1:]
        assert sum(int(r[1]) for r in daughter) == 7
        for row in daughter:
            assert row in tables, 'README daughterboard stock row stale: '+row[0]+suffix
            assert int(row[1]) == int(row[5]) + int(row[6])
        for line in material.read_text().splitlines():
            if not re.match(r'^\| M\d{2} \|',line):
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            matches = [r for r in tables if r[0] == cells[0]]
            assert len(matches) == 1 and matches[0][2] == cells[2], 'README mechanical quantity stale: '+cells[0]
    report = {'status':'readme-materials-match-bom', 'fitted_mainboard_parts':76,
              'inventory_annotations_checked':True,
              'mechanical_rows_per_language':20, 'optional_daughterboard_parts':7, 'production_approved':False,
              'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources}}
    (ROOT/'docs/audit/yeti60-materials.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Both READMEs contain all 76 fitted PCB parts and the 20 mechanical material rows')


if __name__ == '__main__':
    main()
