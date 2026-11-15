#!/usr/bin/env python3
"""Tessellate the unchanged top STEP at millimetre scale and check its STL."""
import argparse,hashlib,json,struct
from pathlib import Path
import numpy as np
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from cad_geometry import load,bounds
from e73_fit_geometry import volume
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();path=args.output.resolve();source=ROOT/'mechanical/generated/yeti60-top.step';shape=load(source)
 mesh=BRepMesh_IncrementalMesh(shape,.05,False,.1,True);mesh.Perform();assert mesh.IsDone();writer=StlAPI_Writer();writer.ASCIIMode=False;assert writer.Write(shape,str(path))
 data=path.read_bytes();count=struct.unpack_from('<I',data,80)[0];assert len(data)==84+count*50
 points=np.array([struct.unpack_from('<9f',data,84+i*50+12)for i in range(count)],dtype=float).reshape(-1,3,3);bb=np.concatenate([points.min(axis=(0,1)),points.max(axis=(0,1))]);native=np.array(bounds(shape));assert np.max(np.abs(bb-native))<.06
 mesh_volume=abs(np.einsum('ij,ij->i',points[:,0],np.cross(points[:,1],points[:,2])).sum()/6);native_volume=volume(shape);assert abs(mesh_volume/native_volume-1)<.01
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();report=dict(status='millimetre-STL-bounds-and-volume-screen-passed',physical_verification=False,shrink_compensated=False,linear_deflection_mm=.05,angular_deflection_radians=.1,triangles=count,STEP_bounds_mm=native.tolist(),STL_bounds_mm=bb.tolist(),STEP_volume_mm3=native_volume,STL_volume_mm3=mesh_volume,output_sha256=sha(path),source_sha256={str(p.relative_to(ROOT)):sha(p)for p in [source,Path(__file__),ROOT/'scripts/cad_geometry.py',ROOT/'scripts/e73_fit_geometry.py']})
 path.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':main()
