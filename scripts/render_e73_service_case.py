#!/usr/bin/env python3
"""Render M05 from the checked print meshes in its open underside pose."""

import json
import struct
from pathlib import Path

import bpy
from render_e73_corner_assembly import ROOT, aim, material, mesh, point, sha


BASE = ROOT/'hardware/e73-hhkb-corner'
AUDIT = BASE/'audit'


def add_print_mesh(path, mat, drop_mm=0):
    data = path.read_bytes()
    count = struct.unpack_from('<I', data, 80)[0]
    vertices = [
        point((x, y, z-drop_mm))
        for facet in struct.iter_unpack('<12fH', data[84:])
        for x, y, z in zip(facet[3:12:3], facet[4:12:3], facet[5:12:3])
    ]
    faces = [(i, i+1, i+2) for i in range(0, len(vertices), 3)]
    assert len(faces) == count
    return mesh(path.stem, vertices, faces, mat, None)


def main():
    report = AUDIT/'service-case-m05.json'
    checked = json.loads(report.read_text())
    for path, digest in checked['outputs'].items():
        assert sha(ROOT/path) == digest
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.cycles.seed = 60
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = -1.65
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.55,.61,.68,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35

    resin = material('Satin resin', (.19,.22,.17), .40)
    covers = material('Satin cover resin', (.32,.36,.27), .40)
    for path in checked['outputs']:
        if not path.endswith('.stl'):
            continue
        cap = Path(path).name.startswith('cover-')
        add_print_mesh(ROOT/path, covers if cap else resin, 35 if cap else 0)
    bpy.ops.object.camera_add(location=(.02,.26,-.44))
    scene.camera = bpy.context.object
    aim(scene.camera, (0,.002,-.020))
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = .395

    for position, watts, width in [
        ((-.16,.01,-.28), 10, .30), ((.21,.14,-.20), 8, .19), ((.01,-.20,-.13), 5, .22),
    ]:
        bpy.ops.object.light_add(type='AREA', location=position)
        lamp = bpy.context.object
        lamp.data.energy = watts
        lamp.data.size = width
        aim(lamp, (0,0,-.012))
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 810
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    target = AUDIT/'m05-access-exploded.png'
    scene.render.filepath = str(target)
    bpy.ops.render.render(write_still=True)
    sources = [report, Path(__file__), ROOT/'scripts/render_e73_corner_assembly.py']
    (AUDIT/'service-case-m05-render.json').write_text(json.dumps({
        'status':'checked-M05-meshes-rendered',
        'source_sha256':dict(checked['outputs'], **{str(p.relative_to(ROOT)):sha(p) for p in sources}),
        'outputs':{str(target.relative_to(ROOT)):sha(target)},
        'cover_explosion_mm':35,
        'physical_verification':False,
    }, indent=2)+'\n')


if __name__ == '__main__':
    main()
