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
 for name in ['yeti60-bom','yeti60-power-budget','yeti60-battery-pocket','yeti60-assembly-drawings','yeti60-cell-screening']:
  r=read('docs/audit/'+name+'.json');hashes(r['source_sha256']);hashes(r.get('outputs',{}))
 b=read('docs/audit/yeti60-bom.json');assert sum(x['quantity'] for x in b['rows'])==b['fitted_mainboard_parts']==76
 assert b['unpopulated_sites']==['JP1'] and not any('SW2,' in x['references'] for x in b['rows'])
 p=read('docs/audit/yeti60-power-budget.json');assert p['status']=='conditional-sensitivity-model-not-measurement'
 spec=read('mechanical/assembly-spec.json');assert p['default_capacity_mAh']==spec['battery']['nominal_capacity_mAh']==1600
 for s in p['scenarios']:
  assert math.isclose(s['battery_mA']*s['runtime_default_pack_hours'],1600*.8)
 c=p['charging'];assert not p['current_firmware']['deep_sleep_enabled'] and not c['larger_pack_drop_in_approved']
 assert c['USB_configured_requested_mA']==500 and not c['charging_before_configuration'] and not c['charging_during_suspend']
 assert c['programmed_charge_mA_min_typ_max'][-1]<=spec['battery']['maximum_charge_current_mA']==450
 assert c['termination_mA_min_typ_max'][-1]<=c['cell_charge_endpoint_mA']==32
 assert c['fastcharge_timer_h_min_typ_max'][0]>c['ideal_CC_at_minimum_programmed_current_h']
 assert c['pack_temperature_actual_window_C']==[15,43]
 assert c['hardware_off_defaults']['input_limit_mA']==100 and c['hardware_off_defaults']['charging_enabled']
 screening=read('docs/audit/yeti60-cell-screening.json');assert screening['catalog_models']==651 and screening['largest_found']['model']=='HCP404074' and screening['largest_found']['capacity']==1600
 g=read('docs/audit/yeti60-battery-pocket.json');assert g['solid_count']==1 and g['case_scale']==[1,1,1];assert g['remaining_wall_after_tolerance_mm']>=3
 assert g['minimum_expanded_pack_to_component_mm']>=.5
 assert g['pack_max_envelope_mm']==spec['battery']['full_envelope_including_growth']==[85,43,4.8]
 assert all(math.isclose(a,b,abs_tol=1e-8) for a,b in zip(g['pack_bounds_case_mm'],read('docs/audit/yeti60-assembly.json')['battery_candidates'][0]['bounds_case_mm']))
 assert max(g['pack_case_overlap_mm3']+g['expanded_pack_case_overlap_mm3'])<1e-6 and not g['component_envelope_collisions'];assert g['minimum_pack_to_fastener_envelope_mm']>=.7-1e-6
 assert sha(ROOT/g['output'])==g['output_sha256']
 d=read('docs/audit/yeti60-assembly-drawings.json');assert d['recipe_sha256']==sha(ROOT/'scripts/draw_yeti60_assembly.py');hashes(d['geometry_sources']);hashes(d['outputs']);assert len(d['outputs'])==8
 report={'status':'passed','scope':['76-part mainboard purchase requirements','current-source engineering sheets in separate languages','default 1600 mAh pack, bounded catalog screening, BRep recess and tolerance geometry','conditional power arithmetic with unmeasured assumptions'],'production_approved':False,'check_recipe_sha256':sha(Path(__file__).resolve()),'evidence_sha256':{n:sha(ROOT/'docs/audit'/n) for n in ['yeti60-bom.json','yeti60-power-budget.json','yeti60-battery-pocket.json','yeti60-assembly-drawings.json','yeti60-cell-screening.json']},'limits':['P2 charge design calculated; supplier pack/thermal approval and physical charge-to-termination remain pending','No physical hardware verification or RF/SI claim']}
 (ROOT/'docs/audit/yeti60-engineering.json').write_text(json.dumps(report,indent=2)+'\n');print('Engineering sources, drawings, purchase quantities and conditional calculations agree')
if __name__=='__main__':main()
