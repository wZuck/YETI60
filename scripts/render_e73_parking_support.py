#!/usr/bin/env python3
"""Render both M05 parking supports at their checked case locations."""

import json
from pathlib import Path
import struct

import bpy

from render_e73_corner_assembly import ROOT, aim, material, mesh, point, sha


BASE = ROOT/'hardware/e73-hhkb-corner'
AUDIT = BASE/'audit'
SUPPORT = BASE/'mechanical/service-case-m05/parking-support'


def add_body(path, mat, offset=(0, 0, 0)):
    content = path.read_bytes()
    vertices = []
    for face in struct.iter_unpack('<12fH', content[84:]):
        for i in (3, 6, 9):
            vertices.append(point(tuple(a+b for a,b in zip(face[i:i+3], offset))))
    faces = [(i,i+1,i+2) for i in range(0,len(vertices),3)]
    assert len(faces)==struct.unpack_from('<I',content,80)[0]
    mesh(path.stem,vertices,faces,mat,None)


def main():
    source = AUDIT/'m05-parking-support.json'
    record = json.loads(source.read_text())
    for sec in ('source_sha256','outputs'):
        for path,digest in record[sec].items():
            assert sha(ROOT/path)==digest, path
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = -1.65
    scene.world = bpy.data.worlds.new('Bench studio')
    scene.world.use_nodes = True
    world = scene.world.node_tree.nodes['Background']
    world.inputs['Color'].default_value = (.55,.61,.68,1)
    world.inputs['Strength'].default_value = .35
    mats = {'case':material('Resin',(.19,.22,.17),.4),
            'carrier':material('Carrier',(.13,.27,.36),.38),
            'rod-shelf':material('Rod shelf',(.50,.25,.09),.4)}
    bottom = BASE/'mechanical/service-case-m05/bottom-m05-REVIEW.stl'
    add_body(bottom,mats['case'])
    for port in record['ports']:
        for name, data in port['media'].items():
            add_body(SUPPORT/(port['ref']+'-'+name+'.stl'),mats[name],data['STL_origin_in_case_mm'])
    bpy.ops.object.camera_add(location=(.02,.27,-.43))
    cam = bpy.context.object
    scene.camera = cam
    aim(cam,(0,.002,-.021))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = .390
    for location, power, size in [((-.16,.01,-.28),10,.30),((.21,.14,-.20),8,.19),((.01,-.20,-.13),5,.22)]:
        bpy.ops.object.light_add(type='AREA',location=location)
        lamp = bpy.context.object
        lamp.data.energy = power
        lamp.data.size = size
        aim(lamp,(0,0,-.012))
    scene.render.resolution_x=1600
    scene.render.resolution_y=810
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    target = AUDIT/'m05-parking-support.png'
    scene.render.filepath=str(target)
    bpy.ops.render.render(write_still=True)
    inputs = [source,bottom,Path(__file__),ROOT/'scripts/render_e73_corner_assembly.py']
    (AUDIT/'m05-parking-support-render.json').write_text(json.dumps({
        'status':'checked-M05-parking-parts-rendered',
        'physical_verification':False,
        'source_sha256':dict(record['outputs'],**{str(p.relative_to(ROOT)):sha(p)for p in inputs}),
        'outputs':{str(target.relative_to(ROOT)):sha(target)},
    },indent=2)+'\n')


if __name__=='__main__':
    main()
