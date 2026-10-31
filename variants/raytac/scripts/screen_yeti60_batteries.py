#!/usr/bin/env python3
"""Bounded catalog/grid screening; exact chosen-pack BRep verification is separate."""
import json,math,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
fit=json.loads((ROOT/'docs/audit/yeti60-assembly.json').read_text());a=json.loads((ROOT/'mechanical/assembly-spec.json').read_text());plane=json.loads((ROOT/'docs/audit/yeti60-battery-pocket.json').read_text())['underside_plane'];n=plane['normal'];p=plane['point'];catalog=ROOT/'hardware/bom/cell-catalog.json';cells=json.loads(catalog.read_text())['cells']
# Conservative full-pack allocation for screening only. Individual PDF and BRep checks still required.
xmesh,ymesh=np.meshgrid(np.arange(71.,361.,1),np.arange(-194.,-105.,1));results=[]
for c in sorted(cells,key=lambda r:-r['capacity']):
 if c['capacity']<1000:continue
 found=None
 for dx,dy in [(c['L']+10,c['W']+2),(c['W']+2,c['L']+10)]:
  for top in [-4.6,-5.5,-6.0,-8.0]:
   bottom=top-c['T']-.8;floor=bottom-.2
   X=xmesh;Y=ymesh;right=X+dx;front=Y-dy
   outer=p[2]-(n[1]*(front-.75-p[1]))/n[2];wall=(floor-outer)*abs(n[2])-.3
   okay=(right<=357)&(front>=-195)&(wall>=3)&(Y<=-106)
   for e in fit['component_envelopes']:
    b=e['bounds_case_mm']
    if top>b[2]-.5:okay&=~((X-.4<b[3]+.5)&(right+.4>b[0]-.5)&(front-.4<b[4]+.5)&(Y+.4>b[1]-.5))
   # Preserve daughterboard/insert/cable area, not just its four holes.
   okay&=~((X-.75<225.4)&(right+.75>201.2)&(front-.75< -101.3)&(Y+.75> -121.9))
   for xx,yy in a['case']['top_screw_axes']:
    okay&=~((X-.75<xx+5)&(right+.75>xx-5)&(front-.75<yy+5)&(Y+.75>yy-5))
   inds=np.argwhere(okay)
   if len(inds):
    # Prefer the greatest wall margin, then the center of the right compartment.
    costs=[(-wall[i,j],abs(X[i,j]+dx/2-270)) for i,j in inds];k=min(range(len(inds)),key=lambda k:costs[k]);i,j=inds[k]
    found={**c,'pack_size':[dx,dy,c['T']+.8],'bounds':[float(X[i,j]),float(front[i,j]),bottom,float(right[i,j]),float(Y[i,j]),top],'floor':floor,'remaining_wall_after_allowance':float(wall[i,j]),'screening_only':True};break
  if found:break
 if found:results.append(found)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report={'status':'bounded-grid-screening-complete','global_optimum_claimed':False,'catalog_models':len(cells),'screened_capacity_floor_mAh':1000,'candidate_count':len(results),'largest_found':results[0],'fitting_candidates':results,'rules':{'position_grid_mm':1,'rotations_degrees':[0,90],'pack_allowance_L_W_T_mm':[10,2,.8],'top_z_options_mm':[-4.6,-5.5,-6,-8],'pocket_XY_margin_mm':.75,'wall_after_allowance_mm':3,'wall_allowance_mm':.3,'component_clearance_mm':.5,'pack_XY_expansion_mm':.4,'protected_udb_rectangle':[201.2,-121.9,225.4,-101.3]},'limits':['Not an all-market or continuous-position maximum','Catalog dimensions may contain errors: HCP256371 T=25 is preserved, not silently corrected','Full pack and selected bare-cell PDF must be separately qualified'],'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [catalog,ROOT/'docs/audit/yeti60-assembly.json',ROOT/'mechanical/assembly-spec.json',ROOT/'docs/audit/yeti60-battery-pocket.json',Path(__file__).resolve()]}}
(ROOT/'docs/audit/yeti60-cell-screening.json').write_text(json.dumps(report,indent=2)+'\n');print('Screened',len(cells),'catalog models; largest found:',results[0]['model'],results[0]['capacity'],'mAh')
