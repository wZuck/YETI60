#!/usr/bin/env python3
"""Generate resin insert bores, service access and dimensioned prototype hardware."""
import hashlib,json,sys,re
from pathlib import Path
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
from OCP.gp import gp_Ax2,gp_Pnt,gp_Dir
from cad_geometry import load,bounds
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'mechanical/generated';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cylinder(x,y,z,r,h,direction=1):return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,z),gp_Dir(0,0,direction)),r,h).Shape()
def rounded_box(b,r):
    x,y,z,X,Y,Z=b
    def block(bb):return BRepPrimAPI_MakeBox(gp_Pnt(*bb[:3]),bb[3]-bb[0],bb[4]-bb[1],bb[5]-bb[2]).Shape()
    shape=block([x+r,y,z,X-r,Y,Z])
    for tool in [block([x,y+r,z,X,Y-r,Z])]+[cylinder(cx,cy,z,r,Z-z) for cx in [x+r,X-r] for cy in [y+r,Y-r]]:
        op=BRepAlgoAPI_Fuse(shape,tool);op.Build();assert op.IsDone();shape=op.Shape()
    return shape

def cut(shape,tool):
    op=BRepAlgoAPI_Cut(shape,tool);op.Build();assert op.IsDone();s=op.Shape();assert BRepCheck_Analyzer(s).IsValid();return s

def write(s,name):
    writer=STEPControl_Writer();assert writer.Transfer(s,STEPControl_AsIs)==IFSelect_RetDone
    assert writer.Write(str(OUT/name))==IFSelect_RetDone
    path=OUT/name
    text=re.sub(r"(FILE_NAME\('[^']*',')[^']*",r"\g<1>2000-01-01T00:00:00",path.read_text())
    path.write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n')

def main():
    specpath=ROOT/'mechanical/assembly-spec.json';spec=json.loads(specpath.read_text());c=spec['case']
    sources=[specpath,ROOT/'felk60/felk60_top_hhkb.step',ROOT/'felk60/felk60_bottom.step',Path(__file__).resolve(),ROOT/'scripts/cad_geometry.py']
    top=load(sources[1]);bottom=load(sources[2]);old={'top':bounds(top),'bottom':bounds(bottom)}
    for x,y in c['top_screw_axes']:
        i=c['top_insert'];top=cut(top,cylinder(x,y,i['bore_start_z']-.01,i['bore_diameter']/2,i['bore_depth']+.01))
    for x,y in c['daughterboard_screw_axes']:
        i=c['daughterboard_insert'];bottom=cut(bottom,cylinder(x,y,i['bore_start_z']+.01,i['bore_diameter']/2,i['bore_depth']+.01,-1))
    access=c['service_port'];bottom=cut(bottom,cylinder(*access['center_xy'],-25,access['diameter']/2,21))
    pocketpath=ROOT/'mechanical/battery-pocket-study.json';pocket=json.loads(pocketpath.read_text());sources.append(pocketpath)
    bottom=cut(bottom,rounded_box(pocket['pocket_bounds_case_mm'],pocket['pocket_corner_radius_mm']))
    for name,s in [('top',top),('bottom',bottom)]:
        assert max(abs(a-b) for a,b in zip(old[name],bounds(s)))<1e-5,'Case external envelope changed'
        write(s,'yeti60-'+name+'.step')
    f=spec['pcb_fastener'];body=cylinder(0,0,0,f['body_diameter']/2,f['shoulder_length'])
    op=BRepAlgoAPI_Fuse(body,cylinder(0,0,f['shoulder_length'],1.,f['top_stud_length']));op.Build();assert op.IsDone()
    # Thread envelopes; tapping and external thread callouts govern manufacturing.
    spacer=cut(op.Shape(),cylinder(0,0,-.01,.625,f['bottom_thread_depth']+.01));write(spacer,'yeti60-standoff-46.step')
    report={'status':'generated-valid-solids','source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},'outputs':{str(p.relative_to(ROOT)):sha(p) for p in [OUT/'yeti60-top.step',OUT/'yeti60-bottom.step',OUT/'yeti60-standoff-46.step']},'original_case_bounds':old,'derived_case_bounds':{'top':bounds(top),'bottom':bounds(bottom)},'case_scale':[1,1,1],'changes':['Four bonded M3 insert seats','Four bonded M2 daughterboard insert seats','8 mm underside power-switch service port','Default 1600 mAh single-cell battery recess'],'threads':'CAD uses thread envelopes; manufacturing drawing specifies actual threads','physical_acceptance':False}
    (ROOT/'docs/audit/yeti60-mechanical-design.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Derived case solids valid; original case external bounding coordinates unchanged')
if __name__=='__main__':main()
