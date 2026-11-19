#!/usr/bin/env python3
"""Render checked CORNER-05 geometry and identified visual stand-ins in Cycles."""

import argparse
import json
import math
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Quaternion, Vector

from hashlib import file_digest

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.assembly-work/e73-corner/render'
OUT = ROOT / 'renders/e73-corner-assembly'
CENTER = (214.312707, -153.70968)


def sha(path):
    with path.open('rb') as f:
        return file_digest(f, 'sha256').hexdigest()


def point(coords):
    x, y, z = coords
    return ((x - CENTER[0]) / 1000, (y - CENTER[1]) / 1000, z / 1000)


def material(name, color, roughness=.36, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    return mat


def mesh(name, vertices, faces, mat, parent):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(mat)
    return obj


def box(name, bounds, mat, parent, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=point([(bounds[i] + bounds[i + 3]) / 2 for i in range(3)]))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = [(bounds[i + 3] - bounds[i]) / 1000 for i in range(3)]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.parent = parent
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Visual edge radius', 'BEVEL')
        mod.width = bevel / 1000
        mod.segments = 3
    return obj


def section_surface(name, sections, mat, parent, caps=False):
    n = len(sections[0])
    verts = [point(p) for row in sections for p in row]
    faces = [(i*n+j, i*n+(j+1)%n, (i+1)*n+(j+1)%n, (i+1)*n+j)
             for i in range(len(sections)-1) for j in range(n)]
    if caps:
        faces += [tuple(reversed(range(n))), tuple(range(len(verts)-n, len(verts)))]
    obj = mesh(name, verts, faces, mat, parent)
    return obj


def roundrect(w, h, radius):
    for x, y, angle in [(w/2-radius, h/2-radius, 0), (-w/2+radius, h/2-radius, 90),
                         (-w/2+radius, -h/2+radius, 180), (w/2-radius, -h/2+radius, 270)]:
        for i in range(9):
            a = math.radians(angle + i*90/8)
            yield x+radius*math.cos(a), y+radius*math.sin(a)


def tube(name, points, diameter, mat, parent):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = diameter / 2000
    data.bevel_resolution = 4
    data.use_fill_caps = True
    spline = data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for vertex, xyz in zip(spline.points, points):
        vertex.co = (*point(xyz), 1)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(mat)


def profile(name, x, y, loops, mat, parent, caps=False):
    sections = [[(x + radius*math.cos(i*math.tau/40), y + radius*math.sin(i*math.tau/40), z)
                 for i in range(40)] for radius, z in loops]
    return section_surface(name, sections, mat, parent, caps)


def route_points(path):
    result = []
    for segment in path:
        kind = segment['kind']
        if kind == 'twist':
            sample = segment['points']
        elif kind == 'line':
            sample = [segment['start'], segment['end']]
        else:
            center = Vector(segment['center'])
            arm = Vector(segment['start']) - center
            angle = segment['length'] / segment['radius']
            n = max(4, math.ceil(segment['length'] / .18))
            sample = [center + Quaternion(segment['normal'], angle*i/n) @ arm for i in range(n+1)]
        if result:
            assert math.dist(result[-1], sample[0]) < .0001
        result.extend(sample if not result else sample[1:])
    return result


def import_glb(source, parent, bottom):
    artifact = WORK / source['file']
    assert sha(artifact) == source['sha256']
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(artifact))
    imported = set(bpy.data.objects) - before
    assert any(obj.type == 'MESH' for obj in imported)
    roots = [obj for obj in imported if obj.parent is None]
    for obj in roots:
        obj.parent = parent
        obj.location += Vector((-CENTER[0]/1000, -CENTER[1]/1000, bottom/1000))
    return imported


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    source = json.loads((WORK / 'scene.json').read_text())
    for name, digest in source['source_sha256'].items():
        assert sha(ROOT / name) == digest, name
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 10 if args.preview else 48
    scene.cycles.use_denoising = True
    scene.cycles.adaptive_threshold = .035
    scene.cycles.seed = 60
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = device.type == 'METAL'
        if any(device.use for device in prefs.devices):
            scene.cycles.device = 'GPU'
    except (AttributeError, TypeError, RuntimeError):
        pass
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = -1.65
    scene.world = bpy.data.worlds.new('Studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.69, .76, .84, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .26

    group_names = ['bottom', 'top', 'plate', 'pcb', 'electronics', 'daughterboard', 'retainers',
                   'battery', 'wires', 'plugs', 'gaskets', 'mounts', 'screws', 'inserts',
                   'caps', 'housings', 'domes', 'springs', 'stabilizers', 'feet']
    groups = {}
    for name in group_names:
        groups[name] = bpy.data.objects.new(name, None)
        scene.collection.objects.link(groups[name])
    mats = {
        'resin': material('Satin dark olive resin', (.16,.184,.149), .34),
        'steel': material('304 stainless steel', (.51,.52,.55), .31, .86),
        'mask': material('Forest solder mask', (.021,.15,.073)),
        'black': material('Black polymer', (.027,.032,.029)),
        'ivory': material('Connector resin', (.65,.68,.57)),
        'cap': material('Ivory PBT', (.74,.72,.63), .4),
        'accent': material('Forest PBT', (.033,.13,.083)),
        'ink': material('Legend', (.032,.035,.032)),
        'guide': material('Insulating guide resin', (.22,.34,.30)),
        'film': material('Polyimide film', (.58,.26,.033)),
        'pack': material('Pouch pack illustrative wrap', (.12,.24,.18), .28, .3),
        'brass': material('Brass', (.48,.29,.081), .31, .8),
        'dome': material('Silicone', (.46,.41,.38), .58),
        'red': material('Red insulation', (.54,.026,.021)),
        'white': material('White insulation', (.73,.72,.66)),
        'green': material('Green insulation', (.012,.32,.085)),
        'yellow': material('Yellow insulation', (.62,.39,.012)),
    }
    for name, part in source['meshes'].items():
        mesh(name, [point(v) for v in part['vertices_mm']], part['triangles'],
             mats[part['material']], groups[part['group']])

    assembly = source['assembly']
    stack = assembly['stack']
    plate_lo = stack['plate_bottom_z']
    plate_hi = plate_lo + stack['plate_thickness']
    pcb_hi = plate_lo - stack['pcb_to_plate_gap']
    pcb_lo = pcb_hi - stack['pcb_thickness']
    import_glb(source['native']['pcb'], groups['pcb'], pcb_lo)
    imported = import_glb(source['native']['electronics'], groups['electronics'], pcb_lo)
    assert set(source['native_refs']) - {'J1'} <= {obj.name for obj in imported}
    assert len(source['native_refs']) + len(source['proxy_refs']) == 75
    for ref in source['proxy_refs']:
        part = source['parts'][ref]
        limits = source['wire_spec']['assembly_limits']
        height = limits[ref]
        x, y, X, Y = (source['corner']['module_body_PCB_mm'] if ref == 'U1'
                       else part['bbox_PCB_mm'])
        lo, hi = (pcb_hi, pcb_hi + height) if part['side'] == 'front' else (pcb_lo-height, pcb_lo)
        if ref == 'U1':
            box(ref + ' substrate', [x,-Y,lo,X,-y,lo+.6], mats['mask'], groups['electronics'], .1)
            box(ref + ' shield proxy', [x+.6,-Y+.5,lo+.6,X-3.2,-y-.5,hi],
                mats['steel'], groups['electronics'], .18)
        else:
            box(ref + ' visual envelope', [x,-Y,lo,X,-y,hi], mats['black'], groups['electronics'], .12)

    for family, paths in source['routes'].items():
        for pin, path in paths.items():
            color = source['wire_spec'][family]['colors'][pin]
            tube(f'{family} {pin}', route_points(path), source['wire_spec']['wire']['insulation_od_max'],
                 mats[color], groups['wires'])
    assert len(groups['wires'].children) == 9
    plug_axes = {'J1': (1,0,4), 'J2': (0,1,3), 'J4': (-1,0,4), 'J5': (0,-1,2), 'C5': (0,-1,4)}
    for name, (ax, ay, count) in plug_axes.items():
        x, y, z = source['exits'][name]
        x -= ax*2.5
        y -= ay*2.5
        half_x, half_y = (2.5, (count+1)/2) if ax else ((count+1)/2, 2.5)
        box(name + ' mated plug envelope', [x-half_x,y-half_y,z-1.5,x+half_x,y+half_y,z+1.5],
            mats['ivory'], groups['plugs'], .20)
    battery = assembly['battery']
    x, y, X, Y = battery['bounds_xy']
    z = battery['top_z']
    box('1600 mAh protected pack envelope', [x,y,z-battery['full_envelope_including_growth'][2],X,Y,z],
        mats['pack'], groups['battery'], .48)
    for i, (x, y) in enumerate(source['gaskets']['centers_case_XY_mm'], 1):
        for layer, (lo, hi) in {'lower': (3.19, plate_lo), 'upper': (plate_hi, 6.39)}.items():
            box(f'{layer} gasket {i}', [x-16.5,y-1.5,lo,x+16.5,y+1.5,hi],
                mats['black'], groups['gaskets'], .1)

    def cylinder(name, x, y, r, lo, hi, mat, group):
        profile(name, x, y, [(r,lo), (r,hi)], mats[mat], groups[group], caps=True)

    def ring(name, x, y, outer, inner, lo, hi, mat, group):
        profile(name, x, y, [(outer,lo), (outer,hi), (inner,hi), (inner,lo), (outer,lo)],
                mats[mat], groups[group])

    for m in source['mounts']:
        if m['ref'] in assembly['pcb_fastener']['unused_pcb_mount_refs']:
            continue
        x, y = m['xy_PCB_mm']
        y = -y
        ring('Brass standoff', x, y, 1.75, .8, pcb_hi+.1, plate_lo, 'brass', 'mounts')
        cylinder('M2 stud', x, y, 1, plate_lo, plate_lo+1, 'brass', 'mounts')
        ring('Polyimide disc', x, y, 2.25, .9, pcb_hi, pcb_hi+.1, 'film', 'mounts')
        ring('PEEK washer', x, y, 2, 1.1, pcb_lo-.8, pcb_lo, 'black', 'screws')
        cylinder('M1.6 screw envelope', x, y, .8, pcb_lo-.8, pcb_lo+4.2, 'steel', 'screws')
        cylinder('M1.6 screw head', x, y, 1.6, pcb_lo-1.9, pcb_lo-.8, 'steel', 'screws')
    assert len(groups['mounts'].children) == 28*3
    for x, y in assembly['case']['top_screw_axes']:
        ring('M3 insert', x, y, 2.3, 1.5, 4.79, 7.79, 'brass', 'inserts')
        cylinder('M3 screw', x, y, 1.5, 2.29, 7.29, 'steel', 'screws')
        cylinder('M3 screw head', x, y, 2.8, .7, 2.29, 'steel', 'screws')
        ring('M3 shim', x, y, 2.8, 1.55, 2.29, 2.59, 'steel', 'screws')
    for x, y in assembly['case']['daughterboard_screw_axes']:
        ring('M2 insert', x, y, 1.6, 1, -13.41, -10.91, 'brass', 'inserts')
        cylinder('C5 M2 screw', x, y, 1, -13.0038, -9.0038, 'steel', 'daughterboard')
        cylinder('C5 M2 screw head', x, y, 1.8, -9.0038, -7.8, 'steel', 'daughterboard')
        ring('C5 washer', x, y, 2, 1.05, -9.3038, -9.0038, 'film', 'daughterboard')

    widths = [[1]*15, [1.5]+[1]*12+[1.5], [1.75]+[1]*11+[2.25],
              [2.25]+[1]*10+[1.75,1], [1,1.5,6,1.5,1]]
    labels = ['Esc 1 2 3 4 5 6 7 8 9 0 - = \\ `', 'Tab Q W E R T Y U I O P [ ] Delete',
              "Control A S D F G H J K L ; ' Return", 'Shift Z X C V B N M , . / Shift Fn',
              'Alt ◇ _ ◇ Alt']
    columns = {}
    for row, spans in enumerate(widths):
        row_keys = sorted((key for key in source['keys'] if key['row'] == row),
                          key=lambda key: key['plate_center_case_mm'][0])
        assert len(row_keys) == len(spans) == len(labels[row].split())
        columns.update({key['index']: col for col, key in enumerate(row_keys)})
    for key in source['keys']:
        x, y = key['plate_center_case_mm']
        n = key['index']
        row, col = key['row'], columns[n]
        span = widths[row][col]*19.05-1.2
        tip = 22 - row*.65
        tilt = [-.10,-.05,0,.06,.11][row]
        sections = [[(x+u,y+v,z+v*tilt) for u,v in roundrect(w,h,r)]
                    for w,h,r,z in [(span-.3,17.55,.8,12.3), (span,17.85,1,12.8),
                                    (span-2,16.1,1.5,tip-.5), (span-2.8,15.2,1.7,tip)]]
        for t in [.8,.6,.4,.2,.02]:
            sections.append([(x+t*u,y+t*v,tip-.62*(1-t*t)+t*v*tilt)
                             for u,v in roundrect(span-2.8,15.2,1.7)])
        section_surface(f'Keycap {n}', sections, mats['accent' if n == 0 else 'cap'], groups['caps'], True)
        label = labels[row].split()[col]
        if label != '_':
            font = bpy.data.curves.new('Legend ' + label, 'FONT')
            font.body = label
            font.align_x = 'CENTER'
            font.align_y = 'CENTER'
            font.size = .0025 if len(label)<4 else .0019
            obj = bpy.data.objects.new('Legend ' + label, font)
            scene.collection.objects.link(obj)
            obj.parent = groups['caps']
            obj.location = point((x,y,tip-.50))
            obj.rotation_euler.x = math.atan(tilt)
            obj.data.materials.append(mats['cap' if n == 0 else 'ink'])
        ring(f'NiZ housing {n}', x, y, 6.55, 3.5, plate_lo-2.6, 10.85, 'black', 'housings')
        box(f'NiZ slider {n}', [x-2.4,y-2.4,8.5,x+2.4,y+2.4,13.3],
            mats['ivory'], groups['housings'], .28)
        profile(f'Silicone dome {n}', x, y,
                [(5.1,pcb_hi+.05),(4.7,pcb_hi+.36),(3.7,pcb_hi+1.15),
                 (2.0,pcb_hi+3.65),(1.6,pcb_hi+4.0)],
                mats['dome'], groups['domes'])
        points = [(x+(3.25-2.6*t)*math.cos(t*math.tau*5),
                   y+(3.25-2.6*t)*math.sin(t*math.tau*5), pcb_hi+.1+2.8*t)
                  for t in [i/100 for i in range(101)]]
        tube(f'Conical spring {n}', points, .11, mats['steel'], groups['springs'])
    assert len(groups['domes'].children) == len(groups['springs'].children) == 60

    keys = {key['index']: key for key in source['keys']}
    for stab in source['mechanism']['stabilized_keys']:
        x, y = keys[stab['active_index']]['plate_center_case_mm']
        half = stab['stem_spacing_mm']/2
        tube(stab['name']+' wire', [(x-half,y,plate_lo-.65), (x-half,y-3.8,plate_lo-1.8),
                                    (x+half,y-3.8,plate_lo-1.8), (x+half,y,plate_lo-.65)],
             1.6, mats['steel'], groups['stabilizers'])
        for cx in (x-half, x+half):
            box(stab['name']+' clip', [cx-3.2,y-5.3,plate_lo-2.5,cx+3.2,y+6.5,10.8],
                mats['black'], groups['stabilizers'], .17)
            box(stab['name']+' follower', [cx-1.5,y-1.5,10.8,cx+1.5,y+1.5,13.4],
                mats['ivory'], groups['stabilizers'], .12)
    for i in range(4):
        x = 112 + i*51
        box(f'Foot {i+1}, separate in exploded view', [x-20.9,-233,-7,x+20.9,-227.2,-5],
            mats['black'], groups['feet'], .8)

    floor_material = material('Studio surface', (.31,.29,.235), .7)
    bpy.ops.mesh.primitive_plane_add(size=100, location=(0,0,-.014))
    floor = bpy.context.object
    floor.data.materials.append(floor_material)
    lighting = {}
    for name, loc, power, size in [('Key',(-.28,-.34,.47),28,.44),
                                   ('Fill',(.32,-.25,.35),11,.40),
                                   ('Rim',(.12,.32,.34),25,.36),
                                   ('Underside',(-.11,-.16,-.27),19,.36)]:
        light = bpy.data.lights.new(name, 'AREA')
        light.energy = power
        light.shape = 'DISK'
        light.size = size
        obj = bpy.data.objects.new(name, light)
        scene.collection.objects.link(obj)
        obj.location = loc
        aim(obj, (0,0,.03))
        lighting[name] = obj
    cam = bpy.data.cameras.new('Camera')
    cam.type = 'ORTHO'
    cam.clip_start = .001
    cam.clip_end = 10
    camera = bpy.data.objects.new('Camera', cam)
    scene.collection.objects.link(camera)
    scene.camera = camera
    out = WORK if args.preview else OUT
    out.mkdir(exist_ok=True)
    placements = {
        'assembled': {},
        'exploded': {
            'top': (0,0,.159), 'caps': (0,0,.188), 'housings': (0,0,.133),
            'stabilizers': (0,0,.111), 'plate': (0,0,.110), 'gaskets': (0,.074,.115),
            'domes': (0,0,.087), 'springs': (0,0,.068), 'mounts': (0,0,.050),
            'pcb': (.020,-.020,.035), 'electronics': (.020,-.020,.035),
            'screws': (-.025,-.045,.021), 'inserts': (-.025,-.054,.021),
            'wires': (.064,-.148,.031), 'plugs': (.064,-.148,.031),
            'retainers': (.064,-.148,.031), 'battery': (.087,-.248,.038),
            'daughterboard': (-.001,-.142,.039), 'feet': (-.030,-.073,.008),
        },
        'interior': {},
        'pcb-underside': {'pcb': (0,0,.038), 'electronics': (0,0,.038)},
    }
    proof = {}
    for view, offsets in placements.items():
        visible = set(group_names)
        if view == 'assembled':
            visible.remove('feet')
        if view == 'interior':
            visible -= {'top','plate','pcb','electronics','gaskets','mounts','screws','inserts',
                        'caps','housings','domes','springs','stabilizers','feet'}
        if view == 'pcb-underside':
            visible = {'pcb', 'electronics'}
        for name, parent in groups.items():
            parent.location = offsets.get(name, (0,0,0))
            for child in parent.children_recursive:
                child.hide_render = name not in visible
        scene.render.resolution_x = 1100 if args.preview else 2200
        scene.render.resolution_y = 860 if args.preview else 1650
        direction = Vector({'interior': (.22,-.43,.92), 'pcb-underside': (.15,-.45,-.9)}
                           .get(view, (.36,-.74,.62))).normalized()
        camera.location = direction*.8
        aim(camera, (0,0,0))
        bpy.context.view_layer.update()
        inverse = camera.rotation_euler.to_matrix().transposed()
        objects = [obj for name in visible for obj in groups[name].children_recursive
                   if obj.type in {'MESH','CURVE','FONT'}]
        points = [obj.matrix_world @ Vector(v) for obj in objects for v in obj.bound_box]
        projected = [inverse @ p for p in points]
        lo = [min(v[i] for v in projected) for i in range(3)]
        hi = [max(v[i] for v in projected) for i in range(3)]
        camera.location += camera.rotation_euler.to_matrix() @ Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0))
        cam.ortho_scale = max(hi[0]-lo[0],(hi[1]-lo[1])*scene.render.resolution_x/scene.render.resolution_y)*1.12
        floor.hide_render = view == 'pcb-underside'
        lighting['Underside'].hide_render = view != 'pcb-underside'
        floor.location.z = min(p.z for p in points)-.0006
        bpy.context.view_layer.update()
        uv = [world_to_camera_view(scene,camera,p) for p in points]
        edge_gap = min(min(v.x, v.y, 1-v.x, 1-v.y) for v in uv)
        assert edge_gap > .01, (view,edge_gap)
        target = out / (view + ('-preview' if args.preview else '') + '.png')
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        proof[view] = {'objects_by_group': {name: len(groups[name].children_recursive) for name in sorted(visible)},
                       'minimum_image_border_fraction': edge_gap, 'sha256': sha(target)}

    if not args.preview:
        inputs = dict(source['source_sha256'])
        inputs[str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__))
        for name, digest in inputs.items():
            assert sha(ROOT / name) == digest, name
        report = dict(status='current-source-assembly-views-rendered', physical_verification=False,
                      case_scale=[1,1,1], source_sha256=inputs, native_component_models=source['native_refs'],
                      component_envelope_proxies=source['proxy_refs'], daughter_mesh_sha256=source['daughter_mesh_sha256'],
                      views=proof, outputs={str((OUT/(view+'.png')).relative_to(ROOT)): row['sha256']
                                           for view,row in proof.items()},
                      case_bounds_mm={name:source['meshes'][name]['brep_bounds_mm'] for name in ('top','bottom')},
                      renderer=bpy.app.version_string+' / Cycles', max_samples=scene.cycles.samples)
        (OUT / 'manifest.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
