#!/usr/bin/env python3
"""Prepare CORNER-04 CAD meshes and native KiCad visual layers for Blender."""

import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

from check_yeti60_assembly import build_plate, write_step
from export_yeti60_render_meshes import tessellate

ROOT = Path(__file__).resolve().parents[1]
BOARD_DIR = ROOT / 'hardware/e73-hhkb-corner'
WORK = ROOT / '.assembly-work/e73-corner/render'
CLI = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
MODELS = os.environ.get('KICAD10_3DMODEL_DIR', '/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels')


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text())


def verify(report, sections):
    for section in sections:
        for path, digest in report[section].items():
            assert sha(ROOT / path) == digest, ('Stale scene input', path)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    scene_path = WORK / 'scene.json'
    scene_path.unlink(missing_ok=True)
    board = BOARD_DIR / 'EC60-nRF52840.kicad_pcb'
    native_path = BOARD_DIR / 'audit/harness-native.json'
    native = read(native_path)
    assert native['source_PCB_sha256'] == sha(board)
    assembly_path = ROOT / 'mechanical/assembly-spec.json'
    fit_path = ROOT / 'mechanical/e73-fit-spec.json'
    mechanism_path = ROOT / 'mechanical/yeti60-key-mechanism.e73.json'
    key_path = ROOT / 'docs/audit/yeti60-key-geometry.json'
    harness_path = BOARD_DIR / 'audit/harness-study.json'
    retention_path = BOARD_DIR / 'audit/retention-prints.json'
    retention_study_path = BOARD_DIR / 'audit/retention-study.json'
    daughter_path = ROOT / 'docs/audit/yeti60-daughterboard.json'
    harness = read(harness_path)
    retention = read(retention_path)
    daughter = read(daughter_path)
    assert not harness['failures'] and not read(retention_study_path)['failures']
    for report in (harness, retention, read(retention_study_path)):
        verify(report, ['source_sha256', 'outputs'])
    assembly = read(assembly_path)
    stack = assembly['stack']
    sources = [board, native_path, assembly_path, fit_path, mechanism_path, key_path,
               harness_path, retention_path, retention_study_path, daughter_path, Path(__file__),
               ROOT / 'scripts/export_yeti60_render_meshes.py', ROOT / 'scripts/cad_geometry.py',
               ROOT / 'scripts/check_yeti60_assembly.py', ROOT / 'scripts/e73_corner_harness_paths.py',
               ROOT / assembly['geometry']['plate'], ROOT / 'hardware/e73-corner-harness-spec.json',
               ROOT / 'hardware/e73-corner-spec.json', ROOT / 'scripts/interconnect_geometry.py']
    source_hashes = {str(path.relative_to(ROOT)): sha(path) for path in sources}
    meshes = {}

    def add(name, path, group, material, offset=(0, 0, 0), tracked=True):
        if tracked:
            source_hashes[str(path.relative_to(ROOT))] = sha(path)
        mesh = tessellate(path)
        mesh['vertices_mm'] = [[value + offset[i] for i, value in enumerate(vertex)]
                               for vertex in mesh['vertices_mm']]
        meshes[name] = dict(mesh, group=group, material=material)

    for half in ('top', 'bottom'):
        add(half, ROOT / assembly['geometry'][half], half, 'resin')
    plate, keys = build_plate(stack['plate_bottom_z'], stack['plate_thickness'])
    plate_path = WORK / 'steel-plate.step'
    write_step(plate, plate_path)
    add('Steel plate', plate_path, 'plate', 'steel', tracked=False)
    key_geometry = read(key_path)['matches']
    assert len(keys) == len(key_geometry) == 60
    by_electrode = {item['electrode']: item for item in key_geometry}
    assert len(by_electrode) == 60
    for key in keys:
        assert any(abs(key['x'] - item['plate_center_case_mm'][0]) < .001
                   and abs(key['y'] - item['plate_center_case_mm'][1]) < .001
                   for item in key_geometry), key

    d = assembly['daughterboard']
    c5_offset = (d['source_to_case_x_offset'], d['source_to_case_y_offset'], d['pcb_bottom_z'])
    for name, record in daughter['render_parts'].items():
        path = ROOT / record['path']
        assert sha(path) == record['sha256'], path
        add('C5 ' + name, path, 'daughterboard',
            {'pcb': 'mask', 'usb': 'steel', 'sh': 'ivory', 'components': 'black'}[name],
            c5_offset, tracked=False)

    j1_report = ROOT / 'docs/audit/yeti60-interconnect-connectors.json'
    j1 = read(j1_report)['headers']['J1']
    j1_native = native['parts']['J1']
    assert j1_native['position_PCB_mm'] == j1['board_position_pcb_mm']
    assert j1_native['angle_deg'] == j1['board_angle_deg']
    footprint = BOARD_DIR / 'YAECKB.pretty' / (j1_native['footprint'] + '.kicad_mod')
    assert sha(footprint) == j1['native_sha256']
    source_hashes[str(footprint.relative_to(ROOT))] = sha(footprint)
    source_hashes[str(j1_report.relative_to(ROOT))] = sha(j1_report)
    path = ROOT / j1['step']['path']
    assert sha(path) == j1['step']['sha256']
    pcb_bottom = stack['plate_bottom_z'] - stack['pcb_to_plate_gap'] - stack['pcb_thickness']
    add('J1', path, 'electronics', 'ivory', (0, 0, pcb_bottom), tracked=False)

    for part in retention['rigid_parts'] + retention['film_blanks']:
        name = part['name']
        rigid = 'local_STL' in part
        path = BOARD_DIR / 'mechanical/retention/assembly-reference' / (name + '.step')
        assert sha(path) == retention['outputs'][str(path.relative_to(ROOT))]
        add(name, path, 'retainers', 'guide' if rigid else 'film')
    assert sum(part['group'] == 'retainers' for part in meshes.values()) == 33

    refs = sorted(set(native['parts']) - {'U1', 'J1'})
    resolved_board = WORK / 'EC60-render-only.kicad_pcb'

    def resolve_model(match):
        model = (Path(MODELS) / match[2] if match[1] == 'KICAD6_3DMODEL_DIR'
                 else BOARD_DIR / match[2])
        if model.suffix == '.wrl':
            model = model.with_suffix('.step')
        return '(model "' + model.as_posix() + '"' if model.is_file() else match[0]

    resolved_board.write_text(re.sub(r'\(model "\$\{(KICAD6_3DMODEL_DIR|KIPRJMOD)\}/([^"]+)"',
                                     resolve_model, board.read_text()))
    native_artifacts = {}
    for name, options in [
        ('pcb', ['--board-only', '--include-tracks', '--include-pads', '--include-zones',
                 '--include-silkscreen', '--include-soldermask']),
        ('electronics', ['--no-board-body', '--component-filter', ','.join(refs)]),
    ]:
        target = WORK / (name + '.glb')
        log = WORK / (name + '-export.log')
        with log.open('w') as output:
            subprocess.run([CLI, 'pcb', 'export', 'glb', '-f', '--user-origin', '0x0mm',
                            *options, '-o', str(target),
                            str(board if name == 'pcb' else resolved_board)], stdout=output,
                           stderr=subprocess.STDOUT, check=True)
        native_artifacts[name] = {'file': target.name, 'sha256': sha(target)}
    raw = (WORK / 'electronics.glb').read_bytes()
    doc = json.loads(raw[20:20 + struct.unpack_from('<I', raw, 12)[0]])
    names = {node.get('name') for node in doc['nodes']}
    native_refs = sorted((set(refs) & names) | {'J1'})
    proxy_refs = sorted(set(native['parts']) - set(native_refs))
    print('Native component models:', len(native_refs), 'Envelope stand-ins:', proxy_refs, flush=True)

    wire_spec = read(ROOT / 'hardware/e73-corner-harness-spec.json')
    nominal = harness['variants'][0]
    assert nominal['pcb_bottom_shift_mm'] == 0
    assert sum(map(len, nominal['routes'].values())) == 9
    scene = dict(source_sha256=source_hashes, native=native_artifacts,
                 native_refs=native_refs, proxy_refs=proxy_refs, parts=native['parts'],
                 meshes=meshes, keys=key_geometry, mounts=native['mounts'],
                 assembly=assembly, mechanism=read(mechanism_path), gaskets=read(fit_path)['gaskets'],
                 corner=read(ROOT / 'hardware/e73-corner-spec.json'), wire_spec=wire_spec,
                 routes=nominal['routes'], exits=harness['connector_exits_case_mm'],
                 daughter_mesh_sha256={name: item['sha256'] for name, item in daughter['render_parts'].items()})
    verify(scene, ['source_sha256'])
    scene_path.write_text(json.dumps(scene, separators=(',', ':')))


if __name__ == '__main__':
    main()
