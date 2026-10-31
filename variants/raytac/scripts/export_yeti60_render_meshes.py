#!/usr/bin/env python3
"""Tessellate unscaled source BReps for the physical assembly renderer.

Run after check_yeti60_assembly.py with requirements-audit.txt. Coordinates
remain millimetres in the source frame; no bevel, shrinkwrap or case resizing.
"""
import hashlib
import json
import math
from pathlib import Path
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from cad_geometry import load, bounds
ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.assembly-work'
REPORT = ROOT / 'docs/audit/yeti60-assembly.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def tessellate(path):
    shape = load(path)
    BRepMesh_IncrementalMesh(shape, .015, False, .08, True).Perform()
    vertices, triangles = [], []
    faces = TopExp_Explorer(shape, TopAbs_FACE)
    while faces.More():
        face = TopoDS.Face(faces.Current()); loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri:
            offset = len(vertices)
            for i in range(1, tri.NbNodes()+1):
                p = tri.Node(i).Transformed(loc.Transformation())
                vertices.append([p.X(), p.Y(), p.Z()])
            for i in range(1, tri.NbTriangles()+1):
                ids = list(tri.Triangle(i).Get())
                if face.Orientation() == TopAbs_REVERSED: ids.reverse()
                triangles.append([offset+j-1 for j in ids])
        faces.Next()
    vb = [min(p[i] for p in vertices) for i in range(3)] + [max(p[i] for p in vertices) for i in range(3)]
    bb = bounds(shape)
    assert max(abs(a-b) for a,b in zip(vb,bb)) < .02, (path,vb,bb)
    return {'vertices_mm':vertices,'triangles':triangles,'brep_bounds_mm':bb,'mesh_bounds_mm':vb}
def main():
    data = json.loads(REPORT.read_text())
    for name,h in data['source_sha256'].items(): assert sha(ROOT/name)==h,name
    meshes = {}
    for name,path in [('bottom',ROOT/data['case_files']['bottom']),('top',ROOT/data['case_files']['top']),('plate',WORK/'plate.step'),('pcb',WORK/'pcb-placed.step')]:
        meshes[name] = tessellate(path)
    harness_path=ROOT/'docs/audit/yeti60-interconnects.json'
    harness=json.loads(harness_path.read_text()); daughter=json.loads((ROOT/'docs/audit/yeti60-daughterboard.json').read_text())
    for source,h in harness['source_sha256'].items(): assert sha(ROOT/source)==h,source
    extras=[]
    for part in harness['render_parts']:
        assert sha(ROOT/part['path'])==part['sha256']
        name='interconnect-'+part['name'];meshes[name]=tessellate(ROOT/part['path']);extras.append({**part,'mesh':name,'group':'interconnect'})
    spec=json.loads((ROOT/'mechanical/assembly-spec.json').read_text())['daughterboard']
    shifts=[spec['source_to_case_x_offset'],spec['source_to_case_y_offset'],spec['pcb_bottom_z']]
    connector=json.loads((ROOT/'docs/audit/yeti60-interconnect-connectors.json').read_text())['headers']['J1']['step']
    components=[('main-sh',connector,[0,0,data['nominal_stack']['pcb_bottom_z']],'header','cream','pcb')]
    components += [('C5-'+name,part,shifts,'daughterboard',{'pcb':'pcb','usb':'metal','sh':'cream','components':'black'}[name],'daughterboard') for name,part in daughter['render_parts'].items()]
    for name,part,offset,category,color,group in components:
        assert sha(ROOT/part['path'])==part['sha256']
        d=tessellate(ROOT/part['path'])
        d['vertices_mm']=[[v[i]+offset[i] for i in range(3)] for v in d['vertices_mm']]
        for field in ['brep_bounds_mm','mesh_bounds_mm']: d[field]=[v+offset[i%3] for i,v in enumerate(d[field])]
        meshes[name]=d;extras.append({'name':name,'mesh':name,'category':category,'color':color,'group':group})
    out = {'interconnect_report_sha256':sha(harness_path),'daughterboard_report_sha256':sha(ROOT/'docs/audit/yeti60-daughterboard.json'),'extra_parts':extras,'export_recipe_sha256':sha(Path(__file__)), 'geometry_helper_sha256':sha(ROOT/'scripts/cad_geometry.py'), 'assembly_report_sha256':sha(REPORT),'geometry_sources':data['source_sha256'],'tessellation_linear_deflection_mm':.015,'tessellation_angular_deflection_rad':.08,'case_scale':[1,1,1],'meshes':meshes}
    (WORK/'render-meshes.json').write_text(json.dumps(out,separators=(',',':')))
    case = [meshes[n] for n in ['top','bottom']]
    bb = [min(m['brep_bounds_mm'][i] for m in case) for i in range(3)] + [max(m['brep_bounds_mm'][i] for m in case) for i in range(3,6)]
    a = math.radians(7)
    points = [(x, y*math.cos(a)-z*math.sin(a), y*math.sin(a)+z*math.cos(a)) for m in case for x,y,z in m['vertices_mm']]
    rb = [min(p[i] for p in points) for i in range(3)] + [max(p[i] for p in points) for i in range(3)]
    proof = {'status':'source-sized-case-geometry-verified','geometry_sources':data['source_sha256'],'case_scale':[1,1,1],'case_modifiers':[], 'linear_mesh_deflection_mm':.015,'max_bounding_deviation_acceptance_mm':.02,'source_frame_case_union_bounds_mm':bb,'source_frame_case_union_size_mm':[bb[i+3]-bb[i] for i in range(3)],'desk_presentation_case_size_mm':[rb[i+3]-rb[i] for i in range(3)],'presentation':'rigid 7 degree rotation about X; original relative shell placement unchanged','not_verified':['actual keycap and dome dimensions','finished resin shrinkage and insert geometry','manufacturing tolerances and physically assembled stack']}
    (ROOT/'docs/audit/yeti60-render-geometry.json').write_text(json.dumps(proof,indent=2)+'\n')

    print('Source-sized case meshes exported; bounding deviations < 0.02 mm')
if __name__ == '__main__': main()
