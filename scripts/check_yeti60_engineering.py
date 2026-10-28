#!/usr/bin/env python3
"""Verify engineering deliverables against their current inputs and numeric contracts."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def hashes(mapping):
 for p,h in mapping.items():assert sha(ROOT/p)==h,'Stale engineering source/output: '+p

def main():
 for name in ['yeti60-bom','yeti60-power-budget','yeti60-battery-pocket','yeti60-assembly-drawings']:
  r=read('docs/audit/'+name+'.json');hashes(r['source_sha256']);hashes(r.get('outputs',{}))
 b=read('docs/audit/yeti60-bom.json');assert sum(x['quantity'] for x in b['rows'])==b['fitted_mainboard_parts']==74
 assert b['unpopulated_sites']==['JP1'] and not any('SW2,' in x['references'] for x in b['rows'])
 p=read('docs/audit/yeti60-power-budget.json');assert p['status']=='conditional-sensitivity-model-not-measurement'
 for s in p['scenarios']:
  assert math.isclose(s['runtime_1000mAh_hours'],5*s['runtime_200mAh_hours'])
  assert math.isclose(s['battery_mA']*s['runtime_200mAh_hours'],160)
 assert not p['current_firmware']['deep_sleep_enabled'] and not p['charging']['larger_pack_drop_in_approved']
 g=read('docs/audit/yeti60-battery-pocket.json');assert g['solid_count']==1 and g['case_scale']==[1,1,1];assert g['remaining_wall_after_tolerance_mm']>=3
 assert max(g['pack_case_overlap_mm3']+g['expanded_pack_case_overlap_mm3'])<1e-6 and not g['component_envelope_collisions'];assert g['minimum_pack_to_fastener_envelope_mm']>=.7-1e-6
 assert sha(ROOT/g['output'])==g['output_sha256']
 d=read('docs/audit/yeti60-assembly-drawings.json');assert d['recipe_sha256']==sha(ROOT/'scripts/draw_yeti60_assembly.py');hashes(d['geometry_sources']);hashes(d['outputs']);assert len(d['outputs'])==8
 report={'status':'passed','scope':['74-part mainboard purchase requirements','current-source engineering sheets in separate languages','optional BRep recess and tolerance geometry','conditional power arithmetic with unmeasured assumptions'],'production_approved':False,'check_recipe_sha256':sha(Path(__file__).resolve()),'evidence_sha256':{n:sha(ROOT/'docs/audit'/n) for n in ['yeti60-bom.json','yeti60-power-budget.json','yeti60-battery-pocket.json','yeti60-assembly-drawings.json']},'limits':['Larger battery charging compatibility is explicitly not approved','No physical hardware verification or RF/SI claim']}
 (ROOT/'docs/audit/yeti60-engineering.json').write_text(json.dumps(report,indent=2)+'\n');print('Engineering sources, drawings, purchase quantities and conditional calculations agree')
if __name__=='__main__':main()
