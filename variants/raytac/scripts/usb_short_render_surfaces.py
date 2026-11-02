"""Apply source-coordinate visual copper maps to the candidate PCB mesh."""
import hashlib
import json
import bpy


def apply(root, obj, cx, cy, stack):
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    report = root/'hardware/usb-short-route/audit/assembly-surfaces.json'
    record = json.loads(report.read_text())
    for table in ['source_sha256','outputs']:
        for path,h in record[table].items(): assert sha(root/path)==h,path
    x0,y0,x1,y1 = record['pcb_bounds_XY_mm']
    for side in ['front','back']:
        material = bpy.data.materials.new('Native '+side+' copper visual map / illustrative finish')
        material.use_nodes=True
        nodes=material.node_tree.nodes;shader=nodes.get('Principled BSDF')
        texture=nodes.new('ShaderNodeTexImage')
        texture.image=bpy.data.images.load(str(root/'hardware/usb-short-route/assembly'/('pcb-surface-'+side+'.png')))
        texture.interpolation='Linear'
        material.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color'])
        shader.inputs['Roughness'].default_value=.38
        shader.inputs['Metallic'].default_value=.1
        obj.data.materials.append(material)
    uv=obj.data.uv_layers.new(name='Native board coordinates')
    for loop in obj.data.loops:
        v=obj.data.vertices[loop.vertex_index].co
        x=v.x*1000+cx;y=-(v.y*1000+cy)
        uv.data[loop.index].uv=((x-x0)/(x1-x0),1-(y-y0)/(y1-y0))
    for polygon in obj.data.polygons:
        zs=[obj.data.vertices[i].co.z for i in polygon.vertices]
        if max(abs(z-stack['pcb_top_z']*.001) for z in zs)<1e-6: polygon.material_index=1
        elif max(abs(z-stack['pcb_bottom_z']*.001) for z in zs)<1e-6: polygon.material_index=2
    return sha(report)
