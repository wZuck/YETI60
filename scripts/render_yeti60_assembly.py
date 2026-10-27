#!/usr/bin/env python3
"""Cycles studio renders from dimension-checked FELK60 BRep tessellations.

Run export_yeti60_render_meshes.py first with the CAD runtime, then run this
script with requirements-render.txt. Source units are millimetres, converted
uniformly to metres. Case meshes receive no geometry modifiers or resizing.
Keycaps/switches and materials remain illustrative pending actual part data.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'renders/yeti60-assembly'; OUT.mkdir(exist_ok=True)
WORK = ROOT/'.assembly-work'
REPORT = ROOT/'docs/audit/yeti60-assembly.json'
MESH = WORK/'render-meshes.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
data = json.loads(REPORT.read_text()); meshdata = json.loads(MESH.read_text())
assert sha(REPORT) == meshdata['assembly_report_sha256']
for name,h in data['source_sha256'].items(): assert sha(ROOT/name)==h,name
parser=argparse.ArgumentParser(); parser.add_argument('--preview',action='store_true'); parser.add_argument('--view',choices=['assembled','rear','exploded','battery-space']); args=parser.parse_args()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene; scene.render.engine='CYCLES'
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
scene.cycles.samples=48 if args.preview else 256
scene.cycles.use_denoising=True; scene.cycles.adaptive_threshold=.04 if args.preview else .012
scene.cycles.seed=60
scene.cycles.max_bounces=10; scene.cycles.transmission_bounces=6
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='METAL'; prefs.get_devices()
    for device in prefs.devices: device.use=device.type=='METAL'
    if any(d.use for d in prefs.devices): scene.cycles.device='GPU'
except Exception: pass
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
scene.render.resolution_percentage=100; scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'; scene.view_settings.exposure=-2.5
world=bpy.data.worlds.new('Studio'); world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.70,.76,.85,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.18; scene.world=world

def material(name,color,rough=.35,metal=0,subsurface=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    n=m.node_tree.nodes; p=n.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
    p.inputs['Subsurface Weight'].default_value=subsurface
    # Fine molded/plastic surface, in real metre units; no visible print bands.
    if not metal:
        tex=n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=8500; tex.inputs['Detail'].default_value=2
        bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.11; bump.inputs['Distance'].default_value=.000012
        m.node_tree.links.new(tex.outputs['Fac'],bump.inputs['Height']); m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m
case_mat=material('Satin warm gray resin — illustrative finish',(.47,.49,.46),.29,subsurface=.025)
cap_mat=material('Ivory PBT',(.72,.69,.60),.39)
accent_mat=material('Deep forest PBT',(.025,.075,.055),.38)
ink=material('Dark pad print',(.045,.048,.040),.48)
light_ink=material('Ivory pad print',(.7,.73,.65),.48)
pcb_mat=material('Green soldermask',(.022,.105,.058),.31)
steel=material('Stainless steel plate',(.52,.54,.56),.3,metal=1)
black=material('Switch housing',(.025,.03,.027),.38)
metalmat=material('Component metal',(.5,.51,.48),.32,metal=.8)
cream=material('Connector plastic',(.63,.62,.52),.4)
battery_mat=material('Unselected space envelope',(.04,.31,.17),.28,metal=.3)
desk_mat=material('Warm studio backdrop',(.34,.32,.28),.65)
groups={}
for name in ['bottom','top','plate','pcb','caps','switches','battery']:
    o=bpy.data.objects.new(name,None); scene.collection.objects.link(o); groups[name]=o
root=bpy.data.objects.new('Rigid 7 degree presentation transform',None); scene.collection.objects.link(root)
for o in groups.values(): o.parent=root
root.rotation_euler[0]=math.radians(7)
# Only a rigid translation/rotation and the uniform mm-to-m unit conversion.
CX,CY=214.312707,-153.70968
def point(p): return ((p[0]-CX)*.001,(p[1]-CY)*.001,p[2]*.001)
def object_mesh(name,vertices,faces,mat,group,smooth=True):
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(vertices,[],faces); mesh.update()
    obj=bpy.data.objects.new(name,mesh); scene.collection.objects.link(obj); obj.data.materials.append(mat); obj.parent=groups[group]
    for f in mesh.polygons: f.use_smooth=smooth
    return obj
for name,mat in [('bottom',case_mat),('top',case_mat),('plate',steel),('pcb',pcb_mat)]:
    d=meshdata['meshes'][name]; object_mesh(name+' / unmodified source CAD',[point(v) for v in d['vertices_mm']],d['triangles'],mat,name)

def box(name,bb,mat,group,bevel=0):
    x0,y0,z0,x1,y1,z1=bb
    bpy.ops.mesh.primitive_cube_add(size=1,location=point(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2)))
    o=bpy.context.object; o.name=name; o.dimensions=((x1-x0)*.001,(y1-y0)*.001,(z1-z0)*.001); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(mat); o.parent=groups[group]
    if bevel:
        mod=o.modifiers.new('Illustrative component edge radius','BEVEL'); mod.width=bevel*.001; mod.segments=3
    return o
for p in data['component_envelopes']:
    mat=cream if p['ref'].startswith('J') else black if p['ref'].startswith('U') else metalmat
    box(p['ref']+' / height envelope',p['bounds_case_mm'],mat,'pcb',.12)

def rounded(w,h,r,n=8):
    out=[]
    for cx,cy,angle in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
        for k in range(n+1):
            a=math.radians(angle+90*k/n); out.append((cx+r*math.cos(a),cy+r*math.sin(a)))
    return out

def cap(x,y,width,top,row,mat):
    w=width*19.05-1.2; h=17.85; slope=[-.10,-.05,0,.06,.11][row]; verts=[]; faces=[]
    # Rounded lower edge, tapered walls, rolled upper edge, concave finger dish.
    specs=[(w-.3,h-.3,.75,12.3),(w,h,.9,12.55),(w-.35,h-.35,1.0,13.1),(w-2.0,h-1.7,1.4,top-.6),(w-2.5,h-2.2,1.6,top-.18),(w-3.0,h-2.7,1.7,top)]
    for ww,hh,r,z in specs:
        for xx,yy in rounded(ww,hh,r): verts.append(point((x+xx,y+yy,z+yy*slope)))
    n=len(rounded(1,1,.1))
    for a in range(len(specs)-1):
        for j in range(n): faces.append((a*n+j,a*n+(j+1)%n,(a+1)*n+(j+1)%n,(a+1)*n+j))
    outer=rounded(w-3.0,h-2.7,1.7)
    for scale in [.8,.6,.4,.2,.02]:
        start=len(verts)-n
        for xx,yy in outer:
            X,Y=xx*scale,yy*scale
            # Cylindrical scoop maintains the long spacebar profile.
            z=top-.62*(1-scale*scale)+Y*slope
            verts.append(point((x+X,y+Y,z)))
        new=len(verts)-n
        for j in range(n): faces.append((start+j,start+(j+1)%n,new+(j+1)%n,new+j))
    faces.append(tuple(range(len(verts)-n,len(verts)))); faces.append(tuple(reversed(range(n))))
    return object_mesh('Illustrative sculpted keycap',verts,faces,mat,'caps')
rows={}
for k in data['active_key_positions']: rows.setdefault(round(k['y'],3),[]).append(k)
legends=[['Esc','1','2','3','4','5','6','7','8','9','0','-','=','\\','`'],['Tab','Q','W','E','R','T','Y','U','I','O','P','[',']','Delete'],['Control','A','S','D','F','G','H','J','K','L',';',"'",'Return'],['Shift','Z','X','C','V','B','N','M',',','.','/','Shift','Fn'],['Alt','◇','','◇','Alt']]
widths=[[1]*15,[1.5]+[1]*12+[1.5],[1.75]+[1]*11+[2.25],[2.25]+[1]*10+[1.75,1],[1,1.5,6,1.5,1]]
for row,(y,keys) in enumerate(sorted(rows.items(),reverse=True)):
    keys.sort(key=lambda k:k['x']); assert len(keys)==len(widths[row])
    for col,k in enumerate(keys):
        x,y=k['x'],k['y']; top=22-row*.65
        box('Illustrative Topre housing',(x-6.9,y-6.6,data['nominal_stack']['pcb_top_z']+1,x+6.9,y+6.6,10.9),black,'switches',.3)
        box('Illustrative Topre stem',(x-1.5,y-1.5,10.9,x+1.5,y+1.5,13.4),cream,'switches',.2)
        accent=row==0 and col==0
        cap(x,y,widths[row][col],top,row,accent_mat if accent else cap_mat)
        text=legends[row][col]
        if text:
            curve=bpy.data.curves.new('Pad printed legend','FONT'); curve.body=text; curve.align_x='CENTER'; curve.align_y='CENTER'; curve.size=.0026 if len(text)<4 else .002; curve.resolution_u=12; curve.extrude=.000001
            o=bpy.data.objects.new('Legend '+text,curve); scene.collection.objects.link(o); o.location=point((x,y,top-.54)); o.rotation_euler[0]=math.atan([-.10,-.05,0,.06,.11][row]); o.data.materials.append(light_ink if accent else ink); o.parent=groups['caps']
if data['battery_candidates']: box('Maximum space only / no battery selected',data['battery_candidates'][0]['bounds_case_mm'],battery_mat,'battery',.5)
groups['battery'].hide_render=True
bpy.context.view_layer.update()
verts=[root.matrix_world @ (groups['bottom'].matrix_local @ Vector(point(v))) for v in meshdata['meshes']['bottom']['vertices_mm']]
floor_z=min(v.z for v in verts)-.0001
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,floor_z)); floor=bpy.context.object; floor.name='Studio table'; floor.data.materials.append(desk_mat)
def aim(o,target): o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def light(name,location,power,size,size_y,color):
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='RECTANGLE'; d.size=size; d.size_y=size_y; d.color=color
    o=bpy.data.objects.new(name,d); scene.collection.objects.link(o); o.location=location; aim(o,(0,0,0))
light('Large softbox key',(-.30,-.20,.55),25,.55,.4,(1,.91,.79))
light('Cool fill',(.36,-.04,.38),12,.38,.35,(.8,.88,1))
light('Rear strip',(-.05,.35,.40),28,.55,.12,(1,.97,.9))
d=bpy.data.cameras.new('Product camera'); camera=bpy.data.objects.new('Product camera',d); scene.collection.objects.link(camera); scene.camera=camera; d.lens=68; d.clip_start=.001; d.clip_end=100

def capture(name,position,target,lens=68):
    # Empty objects do not propagate hide_render to their children.
    for group in groups.values():
        for child in group.children_recursive: child.hide_render=group.hide_render
    camera.location=position; aim(camera,target); d.lens=lens
    scene.render.resolution_x=1200 if args.preview else 2600; scene.render.resolution_y=800 if args.preview else 1734
    scene.render.filepath=str(WORK/(name+'-preview.png') if args.preview else OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
views=['assembled','rear','exploded','battery-space'] if not args.view else [args.view]
for view in views:
    for g in groups.values(): g.location=(0,0,0); g.hide_render=False
    groups['battery'].hide_render=True
    if view=='assembled': capture(view,(.37,-.49,.36),(0,0,.012))
    elif view=='rear': capture(view,(-.44,.56,.32),(0,0,.009),68)
    elif view=='exploded':
        for name,z in [('pcb',.020),('plate',.045),('switches',.045),('top',.068),('caps',.096)]: groups[name].location.z=z
        capture(view,(.43,-.59,.42),(0,0,.055),65)
    else:
        for name in ['top','plate','switches','caps','pcb']: groups[name].hide_render=True
        groups['battery'].hide_render=False; capture(view,(.23,-.29,.47),(0,0,-.006),65)
if not args.preview:
    for name,h in data['source_sha256'].items(): assert sha(ROOT/name)==h,name
    manifest={'project':'YETI60','renderer':'Blender '+bpy.app.version_string+' / Cycles','samples':scene.cycles.samples,'recipe_sha256':sha(Path(__file__)),'mesh_export_recipe_sha256':sha(ROOT/'scripts/export_yeti60_render_meshes.py'),'assembly_report_sha256':sha(REPORT),'geometry_sources':data['source_sha256'],'case_scale':[1,1,1],'units':'source mm converted uniformly to m by 0.001; rigid 7 degree presentation rotation','tessellation_linear_deflection_mm':meshdata['tessellation_linear_deflection_mm'],'source_case_bounds_mm':{name:{'brep':meshdata['meshes'][name]['brep_bounds_mm'],'mesh':meshdata['meshes'][name]['mesh_bounds_mm']} for name in ['top','bottom']},'case_geometry_modifiers':[],'illustrative':['sculpted keycaps, legends, switch housings and stems','resin/PBT finish and colours','backside component envelopes','unselected battery maximum space envelope'],'provisional_stack':data['nominal_stack'],'outputs':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in OUT.glob('*.png')},'production_approved':False}
    (OUT/'render-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('YETI60 physical studio renders complete')
