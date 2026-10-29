#!/usr/bin/env python3
"""Export current PCB datums for conditional mechanical checks (KiCad Python)."""
import json,hashlib,math
from pathlib import Path
import pcbnew as pcb
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/ec60-nrf52840';path=BASE/'EC60-nRF52840.kicad_pcb';b=pcb.LoadBoard(str(path));virtual=set(json.loads((BASE/'metadata-audit.json').read_text())['non_purchased_geometry_references'])|{'REF**'}
def xy(p):return [pcb.ToMM(p.x),pcb.ToMM(p.y)]
parts=[];holes=[]
for f in b.GetFootprints():
    ref=f.GetReference()
    if ref.startswith('H') or ref=='REF**':
        for p in f.Pads():
            if p.GetDrillSize().x>0:holes.append({'ref':ref,'center_pcb_mm':xy(p.GetPosition()),'drill_mm':xy(p.GetDrillSize())})
    if ref in virtual:continue
    bb=f.GetBoundingBox(False,False)
    # These generic bounds are deliberately conditional, not BOM qualification.
    height=3.1 if ref=='U1' else (5.5 if ref=='J2' else (3.5 if ref=='SW100' else 3.0))
    physical=None
    if ref=='U1':
        angle=math.radians(f.GetOrientationDegrees());ox,oy=xy(f.GetPosition())
        # Vendor origin: X=0..18, Y=-13..0. Back-side placement mirrors Y.
        # Expand each edge by 0.1 mm to conservatively cover body tolerance.
        pts=[[ox+math.cos(angle)*x-math.sin(angle)*y,oy-math.sin(angle)*x-math.cos(angle)*y]
             for x in [-.1,18.1] for y in [-13.1,.1]]
        physical=[min(v[0] for v in pts),min(v[1] for v in pts),max(v[0] for v in pts),max(v[1] for v in pts)]
    if ref=='J2':
        pts=[]
        for item in f.GraphicalItems():
            if item.GetClass()=='PCB_SHAPE' and item.GetLayer()==pcb.B_Fab and abs(pcb.ToMM(item.GetWidth())-.1)<1e-6:pts.extend([xy(item.GetStart()),xy(item.GetEnd())])
        physical=[min(v[0] for v in pts),min(v[1] for v in pts),max(v[0] for v in pts),max(v[1] for v in pts)]
    parts.append({'physical_body_bbox_pcb_mm':physical,'ref':ref,'value':f.GetValue(),'back':f.IsFlipped(),'position_pcb_mm':xy(f.GetPosition()),'angle_deg':f.GetOrientationDegrees(),'xy_courtyard_and_graphics_bbox_pcb_mm':[pcb.ToMM(bb.GetLeft()),pcb.ToMM(bb.GetTop()),pcb.ToMM(bb.GetRight()),pcb.ToMM(bb.GetBottom())],'height_envelope_mm':height,'height_basis':'Ebyte module specification: 3.0 mm nominal plus 0.1 mm tolerance' if ref=='U1' else ('JST PH SMT side-entry drawing; verify final part and mating wire envelope' if ref=='J2' else 'provisional conservative render/clearance envelope; final MPN height unqualified')})
report={'source':str(path.relative_to(ROOT)),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pcb_thickness_mm':pcb.ToMM(b.GetDesignSettings().GetBoardThickness()),'parts':parts,'mount_holes':holes,'limits':['Bounding rectangles include native footprint courtyard/graphics but exclude text; they are conservative XY approximations','U1 module height and J2 header height/body outline are sourced; remaining component envelopes and mating wires remain conditional']}
(ROOT/'docs/audit/yeti60-pcb-mechanical-metadata.json').write_text(json.dumps(report,indent=2)+'\n');print(len(parts),'component envelopes,',len(holes),'mounting holes')
