#!/usr/bin/env python3
"""Source-derived FELK60/PCB/plate assembly study with illustrative switches/caps.

Uses the SAME provisional transforms as check_yeti60_assembly.py. Requires OCP,
VTK, Pillow and ffmpeg. The renders are not a qualified production assembly.
"""
import json,math,hashlib,subprocess,sys
from pathlib import Path
import vtk
from PIL import Image,ImageDraw,ImageFont
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_FACE,TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from check_case_assembly import load
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/yeti60-assembly';WORK=ROOT/'.assembly-work';OUT.mkdir(parents=True,exist_ok=True)
REPORT=ROOT/'docs/audit/yeti60-assembly.json';data=json.loads(REPORT.read_text())
for name,h in data['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name

def mesh(shape):
    BRepMesh_IncrementalMesh(shape,.12,False,.3,True).Perform();points=vtk.vtkPoints();cells=vtk.vtkCellArray();faces=TopExp_Explorer(shape,TopAbs_FACE)
    while faces.More():
        f=TopoDS.Face(faces.Current());loc=TopLoc_Location();tri=(getattr(BRep_Tool,'Triangulation_s',None) or BRep_Tool.Triangulation)(f,loc)
        if tri:
            offset=points.GetNumberOfPoints()
            for i in range(1,tri.NbNodes()+1):
                p=tri.Node(i).Transformed(loc.Transformation());points.InsertNextPoint(p.X(),p.Y(),p.Z())
            for i in range(1,tri.NbTriangles()+1):
                ids=list(tri.Triangle(i).Get())
                if f.Orientation()==TopAbs_REVERSED:ids.reverse()
                cells.InsertNextCell(3)
                for j in ids:cells.InsertCellPoint(offset+j-1)
        faces.Next()
    poly=vtk.vtkPolyData();poly.SetPoints(points);poly.SetPolys(cells);normal=vtk.vtkPolyDataNormals();normal.SetInputData(poly);normal.SetFeatureAngle(45);normal.Update();return normal.GetOutput()

def actor(poly,color,metal=0,rough=.45):
    m=vtk.vtkPolyDataMapper();m.SetInputData(poly);a=vtk.vtkActor();a.SetMapper(m);p=a.GetProperty();p.SetColor(*color);p.SetInterpolationToPBR();p.SetMetallic(metal);p.SetRoughness(rough);return a

def cube(bounds,color):
    x=vtk.vtkCubeSource();x.SetBounds(*bounds);x.Update();return actor(x.GetOutput(),color)

def cap(x,y,width,top,color):
    w=width*19.05-1.2;h=17.85;z=12.3
    pts=vtk.vtkPoints()
    for X,Y,Z in [(-w/2,-h/2,z),(w/2,-h/2,z),(w/2,h/2,z),(-w/2,h/2,z),(-w/2+1.4,-h/2+1.2,top),(w/2-1.4,-h/2+1.2,top),(w/2-1.4,h/2-1.2,top),(-w/2+1.4,h/2-1.2,top)]:pts.InsertNextPoint(x+X,y+Y,Z)
    cells=vtk.vtkCellArray()
    for q in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
        cells.InsertNextCell(4)
        for v in q:cells.InsertCellPoint(v)
    poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(cells);norm=vtk.vtkPolyDataNormals();norm.SetInputData(poly);norm.Update();return actor(norm.GetOutput(),color,rough=.36)

ren=vtk.vtkRenderer();ren.SetBackground(.034,.059,.078);ren.SetBackground2(.075,.11,.13);ren.GradientBackgroundOn()
window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetMultiSamples(8);window.SetSize(2400,1500);window.AddRenderer(ren)
groups={name:vtk.vtkAssembly() for name in ['bottom','pcb','plate','switches','top','caps','battery']}
world=vtk.vtkAssembly()
for g in groups.values():world.AddPart(g)
# Case CAD uses a level PCB plane; its underside has the original 7-degree
# wedge. Rotate the entire scene for a level supporting desk plane.
tr=vtk.vtkTransform();tr.PostMultiply();tr.Translate(-214.312704,151.20966,0);tr.RotateX(7);world.SetUserTransform(tr);ren.AddActor(world)
objects={}
for name,path,color,metal in [('bottom',ROOT/'felk60/felk60_bottom.step',(.42,.50,.53),0),('top',ROOT/'felk60/felk60_top_hhkb.step',(.64,.70,.70),0),('plate',WORK/'plate.step',(.46,.50,.50),.75),('pcb',WORK/'pcb-placed.step',(.045,.22,.16),0)]:
    a=actor(mesh(load(path)),color,metal);groups[name].AddPart(a);objects[name]=a
# Illustrative backside component envelopes, located by the current PCB.
for part in data['component_envelopes']:
    bb=part['bounds_case_mm'];ref=part['ref'];color=(.06,.08,.09) if ref.startswith('U') else (.45,.47,.43)
    if ref.startswith('J'):color=(.84,.83,.75)
    groups['pcb'].AddPart(cube((bb[0],bb[3],bb[1],bb[4],bb[2],bb[5]),color))
# PCB geometry is source-derived; copper surface artwork is omitted.
rows={}
for k in data['active_key_positions']:rows.setdefault(round(k['y'],3),[]).append(k)
legends=[['Esc','1','2','3','4','5','6','7','8','9','0','-','=','\\','`'],['Tab','Q','W','E','R','T','Y','U','I','O','P','[',']','Back'],['Ctrl','A','S','D','F','G','H','J','K','L',';',"'",'Enter'],['Shift','Z','X','C','V','B','N','M',',','.','/','Shift','Fn'],['Alt','Meta','YETI60','Meta','Alt']]
widths=[[1]*15,[1.5]+[1]*12+[1.5],[1.75]+[1]*11+[2.25],[2.25]+[1]*10+[1.75,1],[1,1.5,6,1.5,1]]
for row,(y,keys) in enumerate(sorted(rows.items(),reverse=True)):
    keys.sort(key=lambda k:k['x']);assert len(keys)==len(legends[row]),(row,len(keys))
    for col,k in enumerate(keys):
        x,y=k['x'],k['y'];top=22-row*.65
        housing=cube((x-6.9,x+6.9,y-6.6,y+6.6,data['nominal_stack']['pcb_top_z']+1.,10.9),(.16,.19,.18));groups['switches'].AddPart(housing)
        stem=cube((x-1.5,x+1.5,y-1.5,y+1.5,10.9,13.4),(.16,.21,.18));groups['switches'].AddPart(stem)
        color=(.78,.80,.75)
        if legends[row][col] in ['Esc','YETI60']:color=(.16,.34,.27)
        c=cap(x,y,widths[row][col],top,color);groups['caps'].AddPart(c)
        label=vtk.vtkVectorText();label.SetText(legends[row][col]);label.Update();a=actor(label.GetOutput(),(.12,.15,.14) if color[0]>.5 else (.85,.89,.80));bb=label.GetOutput().GetBounds();scale=2.0 if len(legends[row][col])<4 else 1.65;a.SetScale(scale,scale,scale);a.SetPosition(x-(bb[1]+bb[0])*scale/2,y-(bb[3]+bb[2])*scale/2,top+.03);groups['caps'].AddPart(a)
if data['battery_candidates']:
    bb=data['battery_candidates'][0]['bounds_case_mm'];battery=cube((bb[0],bb[3],bb[1],bb[4],bb[2],bb[5]),(.25,.73,.48));battery.GetProperty().SetOpacity(.8);groups['battery'].AddPart(battery)
groups['battery'].SetVisibility(False)
# Supporting desk, after transforming the actual bottom-case mesh.
transformed=vtk.vtkTransformPolyDataFilter();transformed.SetInputData(objects['bottom'].GetMapper().GetInput());transformed.SetTransform(tr);transformed.Update();floor_z=transformed.GetOutput().GetBounds()[4]-.15
floor=vtk.vtkPlaneSource();floor.SetOrigin(-2500,-2500,floor_z);floor.SetPoint1(2500,-2500,floor_z);floor.SetPoint2(-2500,2500,floor_z);floor.Update();ren.AddActor(actor(floor.GetOutput(),(.006,.011,.016),rough=.82))
for pos,intensity in [((-180,-160,340),1.0),((240,100,240),.7),((-240,170,170),.5)]:
    light=vtk.vtkLight();light.SetPosition(*pos);light.SetFocalPoint(0,0,0);light.SetIntensity(intensity);light.SetLightTypeToSceneLight();ren.AddLight(light)
steps=vtk.vtkRenderStepsPass();ao=vtk.vtkSSAOPass();ao.SetDelegatePass(steps);ao.SetRadius(4);ao.SetBias(.04);ao.SetKernelSize(64);ao.BlurOn();ren.SetPass(ao)
camera=ren.GetActiveCamera();camera.SetViewUp(0,0,1);camera.SetPosition(330,-420,330);camera.SetFocalPoint(0,0,3);camera.SetViewAngle(29)

def capture(path,title,subtitle,w=2400,h=1500):
    window.SetSize(w,h);ren.ResetCameraClippingRange();window.Render();f=vtk.vtkWindowToImageFilter();f.SetInput(window);f.SetInputBufferTypeToRGB();f.ReadFrontBufferOff();f.Update();png=vtk.vtkPNGWriter();png.SetFileName(str(WORK/'scene.png'));png.SetInputConnection(f.GetOutputPort());png.Write()
    raw=Image.open(WORK/'scene.png').convert('RGB');canvas=Image.new('RGB',(w,h+220),(9,16,21));canvas.paste(raw,(0,130));d=ImageDraw.Draw(canvas);fp='/System/Library/Fonts/Helvetica.ttc';d.text((75,32),'YETI60  /  '+title,font=ImageFont.truetype(fp,43),fill=(225,238,232));d.text((78,92),subtitle,font=ImageFont.truetype(fp,23),fill=(144,173,166));d.text((78,h+155),'Source-derived case / PCB / 1.2 mm plate; provisional Z stack. Switches, keycaps and component bodies illustrative.',font=ImageFont.truetype(fp,21),fill=(149,174,169));canvas.save(path)

capture(OUT/'assembled.png','ASSEMBLY STUDY','FELK60 HHKB case / one nRF52840 / illustrative resin and keycaps')
# Explode source-coordinate groups without changing the fit-check geometry.
for name,z in [('pcb',20),('plate',45),('switches',45),('top',68),('caps',96)]:groups[name].SetPosition(0,0,z)
camera.SetPosition(340,-450,330);camera.SetFocalPoint(0,0,48)
capture(OUT/'exploded.png','EXPLODED VIEW','Original shell geometry and current PCB; switch/dome stack still requires physical qualification')
for g in groups.values():g.SetPosition(0,0,0)
groups['caps'].SetVisibility(False);groups['switches'].SetVisibility(False);groups['top'].SetVisibility(False);groups['plate'].SetVisibility(False);groups['pcb'].SetVisibility(False);groups['battery'].SetVisibility(True);camera.SetPosition(210,-260,350);camera.SetFocalPoint(0,0,-3)
capture(OUT/'battery-space.png','BATTERY SPACE STUDY','Green volume is a conditional space envelope, not a selected battery')
window.Finalize()
for name,h in data['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
files={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in OUT.glob('*.png')}
manifest={'recipe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'project':'YETI60','assembly_report_sha256':hashlib.sha256(REPORT.read_bytes()).hexdigest(),'geometry_sources':data['source_sha256'],'provisional_stack':data['nominal_stack'],'source_derived':['FELK60 top and bottom STEP','current PCB finished-thickness envelope (surface copper artwork omitted)','audited HHKB plate DXF extruded 1.2mm'],'illustrative':['switches, stems and keycaps','resin color/material and key legends','backside component body envelopes','battery candidate volume; no pack selected'],'outputs':files,'production_approved':False}
(OUT/'render-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('YETI60 assembly renders complete')
