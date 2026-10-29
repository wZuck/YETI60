#!/usr/bin/env python3
"""Reject stale or contradictory CAD, firmware, assembly and image evidence."""
import hashlib,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; HW=ROOT/'hardware/ec60-nrf52840'; AUD=ROOT/'docs/audit'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def hashes(items,base=ROOT):
    for name,expected in items.items():
        assert sha(base/name)==expected,'Stale source: '+name

def verify():
    config=read(ROOT/'design-constraints.json')
    assert config['fabrication']['process']=='ordinary-four-layer-FR4' and not config['fabrication']['HDI_allowed']
    ordinary=read(AUD/'yeti60-ordinary-process.json');assert ordinary['blind_buried_vias']==0 and not ordinary['module_via_in_pad'];hashes(ordinary['source_sha256'])
    fabrication=read(AUD/'yeti60-fabrication.json');assert fabrication['blind_drill_hits']==0 and fabrication['placement_parts']==76;hashes(fabrication['source_sha256']);hashes(fabrication['outputs'])
    assert config['mcu_count']==1 and config['wireless_controller']=='nRF52840' and not config['stm32_allowed']
    assert config['external_usb_c']['connector_path']=='rear-daughterboard-to-J1'
    parts=read(HW/'components.json')
    assert parts['J1']['pins']=={'1':'VBUS','2':'D-','3':'D+','4':'GND'}
    assert parts['J2']['pins']=={'1':'BAT_CELL','2':'GND','3':'BAT_NTC'}
    schematic=read(AUD/'schematic-current.json'); assert schematic['status']=='passed'; hashes(schematic['source_sha256'])
    cad=read(HW/'audit-current.json'); assert cad['status']=='cad-checks-passed'; hashes(cad['source_sha256'],HW)
    assert cad['mcu_count']==1 and not cad['failed_pin_pairs'] and not cad['failed_critical_paths']
    pcb=read(HW/'pcb-contract-check.json'); assert pcb['netlist_parity']=='pass' and pcb['copper_layers']==4
    regression=read(HW/'connectivity-changes.json'); assert not regression['regressed_pairs']; hashes(regression['source_sha256'])
    electrical=read(AUD/'yeti60-electrical.json'); assert sha(HW/'EC60-nRF52840.kicad_pcb')==electrical['source_sha256']
    sim=read(AUD/'yeti60-firmware-simulation.json'); assert sim['status']=='passed'; hashes(sim['source_sha256']); assert sha(ROOT/sim['trace_file'])==sim['trace_sha256']
    plate=read(AUD/'plate.json'); assert plate['status']=='passed'; hashes(plate['source_sha256'])
    meta=read(AUD/'yeti60-pcb-mechanical-metadata.json'); assert sha(ROOT/meta['source'])==meta['source_sha256']
    fit=read(AUD/'yeti60-assembly.json'); hashes(fit['source_sha256']); hashes(fit['verification_recipe_sha256'])
    assert sha(AUD/'yeti60-pcb-mechanical-metadata.json')==fit['mechanical_metadata_sha256']
    assert not fit['colliding_envelopes'] and max(fit['pcb_case_overlap_mm3']+fit['plate_case_overlap_mm3'])<1e-5
    assert len(fit['mounting_hole_matches'])==len(meta['mount_holes'])==29
    assert abs(fit['finished_board_envelope_thickness_mm']-meta['pcb_thickness_mm'])<1e-6
    assert all(max(c['case_overlap_mm3'])<1e-5 for c in fit['battery_candidates'])
    harness=read(AUD/'yeti60-interconnects.json');assert harness['status']=='controlled-route-geometry-passed' and not harness['production_approved'];hashes(harness['source_sha256']);hashes(harness['published_guide_sha256'])
    assert len(harness['wires']['usb'])==4 and len(harness['wires']['battery'])==3
    assert not harness['case_modification_required'] and harness['minimum_expanded_harness_to_harness_gap_mm']>=.15
    geometry=read(AUD/'yeti60-render-geometry.json'); hashes(geometry['geometry_sources']); assert geometry['case_scale']==[1,1,1] and not geometry['case_modifiers']
    for folder,recipe in [('ec60-nrf52840','render_single_nrf.py'),('yeti60-assembly','render_yeti60_assembly.py')]:
        base=ROOT/'renders'/folder; m=read(base/'render-manifest.json'); assert sha(ROOT/'scripts'/recipe)==m['recipe_sha256'],folder+' recipe changed; regenerate renders'
        if folder=='ec60-nrf52840': assert sha(ROOT/m['source'])==m['source_sha256']
        else:
            hashes(m['geometry_sources']); assert m['assembly_report_sha256']==sha(AUD/'yeti60-assembly.json')
            assert m['mesh_export_recipe_sha256']==sha(ROOT/'scripts/export_yeti60_render_meshes.py')
            assert m['case_scale']==[1,1,1] and not m['case_geometry_modifiers']
            assert m['interconnect_report_sha256']==sha(AUD/'yeti60-interconnects.json')
            assert m['daughterboard_report_sha256']==sha(AUD/'yeti60-daughterboard.json')
            assert set(m['outputs'])=={'assembled.png','rear.png','exploded.png','battery-space.png'}
        for name,item in m['outputs'].items():
            assert sha(base/name)==item['sha256'],'Changed render asset: '+name
            if folder=='yeti60-assembly':
                for key in ['recipe_sha256','assembly_report_sha256','mesh_export_recipe_sha256','interconnect_report_sha256','daughterboard_report_sha256']:
                    assert item[key]==m[key],name+' was not rendered from current inputs'
    plot=read(ROOT/'renders/yeti60-firmware/plot-manifest.json'); assert plot['trace_sha256']==sim['trace_sha256']; assert plot['recipe_sha256']==sha(ROOT/'scripts/plot_yeti60_simulation.py'); hashes(plot['outputs'],ROOT/'renders/yeti60-firmware')
    materials=read(AUD/'yeti60-materials.json');assert materials['fitted_mainboard_parts']==76;hashes(materials['source_sha256'])
    engineering=read(AUD/'yeti60-engineering.json');assert engineering['status']=='passed';hashes(engineering['evidence_sha256'],AUD)
    target=read(AUD/'yeti60-target-build.json');assert target['status']=='built';hashes(target['source_sha256'])
    for variant in target['variants'].values():hashes(variant['outputs'])
    target_check=read(AUD/'yeti60-target-check.json');assert target_check['status']=='passed' and target_check['build_manifest_sha256']==sha(AUD/'yeti60-target-build.json')
    assert all(v['USB_configuration_mA']==500 for v in target_check['variants'].values())
    assert read(AUD/'documentation-check.json')['status']=='passed'
    return {'status':'passed','controller_count':1,'physical_pin_pairs':len(cad['physical_pin_pairs']),'matched_mount_holes':29,'assembly_condition':'provisional stack only','firmware_condition':'normal/calibrator ARM targets built, USB500 descriptor verified; hardware enumeration/BLE/calibration untested','production_approved':False,'open_requirements':config['open_requirements']}
def main():
    try: report=verify()
    except (AssertionError,KeyError,FileNotFoundError,ValueError) as error:
        location=traceback.extract_tb(error.__traceback__)[-1]
        report={'status':'failed','error':str(error) or location.line,'check_location':f'{Path(location.filename).name}:{location.lineno}','production_approved':False}
    (AUD/'integration.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))
    raise SystemExit(report['status']!='passed')
if __name__=='__main__':main()
