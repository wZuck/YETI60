#!/usr/bin/env python3
"""Match each actual plate opening to sensing copper nets and target matrix."""
import hashlib
import json
import re
from pathlib import Path
import numpy as np
from matplotlib.path import Path as PolygonPath

ROOT = Path(__file__).resolve().parents[1]
DTS = ROOT / 'firmware/target/boards/yeti/yeti60/yeti60.dts'
SCANNER = ROOT / 'firmware/target/src/scanner.c'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identify(native, plate):
    # Numerical geometric witness only; this does not model EC sensitivity.
    grid = np.arange(-3, 3.001, .15)
    x, y = np.meshgrid(grid, grid)
    disk = np.column_stack((x.ravel(), y.ravel()))
    disk = disk[(disk*disk).sum(axis=1) < 9]
    result = []
    for index, key in enumerate(plate):
        center = np.array([key['x'], -key['y']])
        nets, sources = {}, {}
        for ref, electrode in native['electrodes'].items():
            if np.linalg.norm(center-electrode['at']) > 11:
                continue
            for pad in electrode['pads']:
                net = pad['net']
                if not re.fullmatch(r'(ROW[0-4]|COL(?:[0-9]|1[0-4]))', net):
                    continue
                count = sum(PolygonPath(poly).contains_points(center+disk).sum() for poly in pad['polygons'])
                if count:
                    nets[net] = nets.get(net, 0) + int(count)
                    sources.setdefault(net, set()).add(ref)
        rows = [n for n, count in nets.items() if n.startswith('ROW') and count*.15**2 > 1]
        cols = [n for n, count in nets.items() if n.startswith('COL') and count*.15**2 > 1]
        assert len(rows) == len(cols) == 1, f'Ambiguous/missing copper at plate key {index}: {nets}'
        refs = sorted(sources[rows[0]] & sources[cols[0]])
        assert len(refs) == 1
        result.append({'index': index, 'plate_center_case_mm': [key['x'], key['y']],
                       'row': int(rows[0][3:]), 'col': int(cols[0][3:]), 'electrode': refs[0],
                       'copper_witness_area_mm2': {n: round(nets[n]*.15**2, 4) for n in rows+cols}})
    assert len(result) == 60 and len({(r['row'],r['col']) for r in result}) == 60
    return result


def verify(matches, dts, scanner):
    region = re.search(r'map\s*=\s*<([\s\S]*?)>;', dts).group(1)
    mapped = [tuple(map(int,p)) for p in re.findall(r'RC\((\d+),(\d+)\)', region)]
    expected = [(r['row'],r['col']) for r in matches]
    assert mapped == expected, 'Firmware transform differs from actual plate/copper positions'
    block = re.search(r'active\[5\]\s*=\s*\{([^}]+)', scanner).group(1)
    masks = [int(n.strip(), 0) for n in block.split(',') if n.strip()]
    expected_masks = [sum(1<<c for r,c in expected if r == row) for row in range(5)]
    assert masks == expected_masks, 'Calibration active mask differs from actual plate/copper positions'
    return masks


def main():
    mapping = ROOT / '.assembly-work/build-map.json'
    native = json.loads(mapping.read_text())
    assert native['pcb_sha256'] == sha(ROOT/native['pcb_source'])
    fitpath = ROOT / 'docs/audit/yeti60-assembly.json'
    fit = json.loads(fitpath.read_text())
    matches = identify(native, fit['active_key_positions'])
    masks = verify(matches, DTS.read_text(), SCANNER.read_text())
    sources = [ROOT/native['pcb_source'], ROOT/'mechanical/felk60_plate_hhkb.audited.dxf',
               fitpath, DTS, SCANNER, ROOT/'scripts/export_yeti60_build_map.py', Path(__file__).resolve()]
    report = {'status':'plate-copper-firmware-mapping-passed', 'physical_verification':False,
              'sampling_disk_radius_mm':3, 'sampling_grid_mm':.15, 'minimum_net_witness_area_mm2':1,
              'active_masks_hex':[hex(m) for m in masks], 'matches':matches,
              'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},
              'limits':['Copper-coverage geometry, not capacitance/signal simulation','Actual springs, domes, travel and calibration require hardware']}
    (ROOT/'docs/audit/yeti60-key-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print('60 plate positions match native ROW/COL copper, target transform and calibration mask')


if __name__=='__main__':
    main()
