#!/usr/bin/env python3
"""Reject stale or contradictory CAD, firmware, assembly and image evidence."""
import hashlib,json,subprocess,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; HW=ROOT/'hardware/ec60-nrf52840'; AUD=ROOT/'docs/audit'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def hashes(items,base=ROOT):
    for name,expected in items.items():
        assert sha(base/name)==expected,'Stale source: '+name

def verify_shared_links(paths):
    result={}
    for path in paths:
        assert path.is_symlink() and path.exists(), 'Broken tracked shared link: '+str(path)
        result[str(path.relative_to(ROOT))]=str(path.readlink())
    return result

def tracked_shared_links():
    entries=subprocess.check_output(['git','ls-files','--stage','-z'],cwd=ROOT).decode().split('\0')
    return [ROOT/entry.split('\t',1)[1] for entry in entries if entry.startswith('120000 ')]

def verify():
    shared_links=verify_shared_links(tracked_shared_links())
    config=read(ROOT/'design-constraints.json')
    assert config['fabrication']['process']=='ordinary-four-layer-FR4' and not config['fabrication']['HDI_allowed']
    ordinary=read(AUD/'yeti60-ordinary-process.json');assert ordinary['blind_buried_vias']==0 and not ordinary['module_via_in_pad'];hashes(ordinary['source_sha256'])
    fabrication=read(AUD/'yeti60-fabrication.json');assert fabrication['blind_drill_hits']==0 and fabrication['placement_parts']==75;hashes(fabrication['source_sha256']);hashes(fabrication['outputs'])
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
    assert len(fit['mounting_hole_matches'])==28 and len(meta['mount_holes'])==29
    assert fit['unused_pcb_mount_refs']==['H26'] and 'H26' not in {h['pcb_ref'] for h in fit['mounting_hole_matches']}
    assert fit['selected_fasteners']['installed_quantity']==28
    assert fit['nominal_stack']['plate_thickness_mm']==1.6
    assert abs(fit['nominal_stack']['compressed_top_gasket_mm']-.5838)<1e-6
    assert fit['gasket_stock_mm']=={'bottom':2.0,'top':1.2}
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
            assert m['mechanism_source_sha256']==sha(ROOT/'mechanical/yeti60-key-mechanism.json')
            hashes(m['geometry_sources']); assert m['assembly_report_sha256']==sha(AUD/'yeti60-assembly.json')
            assert m['mesh_export_recipe_sha256']==sha(ROOT/'scripts/export_yeti60_render_meshes.py')
            assert m['case_scale']==[1,1,1] and not m['case_geometry_modifiers']
            assert m['interconnect_report_sha256']==sha(AUD/'yeti60-interconnects.json')
            assert m['daughterboard_report_sha256']==sha(AUD/'yeti60-daughterboard.json')
            assert set(m['outputs'])=={'assembled.png','rear.png','exploded.png','battery-space.png'}
        for name,item in m['outputs'].items():
            assert sha(base/name)==item['sha256'],'Changed render asset: '+name
            if folder=='yeti60-assembly':
                for key in ['recipe_sha256','assembly_report_sha256','mesh_export_recipe_sha256','interconnect_report_sha256','daughterboard_report_sha256','mechanism_source_sha256']:
                    assert item[key]==m[key],name+' was not rendered from current inputs'
    plot=read(ROOT/'renders/yeti60-firmware/plot-manifest.json'); assert plot['trace_sha256']==sim['trace_sha256']; assert plot['recipe_sha256']==sha(ROOT/'scripts/plot_yeti60_simulation.py'); hashes(plot['outputs'],ROOT/'renders/yeti60-firmware')
    materials=read(AUD/'yeti60-materials.json');assert materials['fitted_mainboard_parts']==75;hashes(materials['source_sha256'])
    inventory=read(AUD/'yeti60-inventory.json');hashes(inventory['source_sha256']);hashes(inventory['outputs'])
    assert inventory['required_mainboard_parts']==inventory['planned_stock_parts']+inventory['net_purchase_parts']==75
    assert inventory['in_transit_credited']==inventory['optional_c5_parts_credited']==0
    assert not inventory['physical_remaining_count_confirmed'] and not inventory['production_approved']
    key_geometry=read(AUD/'yeti60-key-geometry.json');hashes(key_geometry['source_sha256'])
    assert key_geometry['status']=='plate-copper-firmware-mapping-passed' and len(key_geometry['matches'])==60
    mechanism=read(AUD/'plate-mount.json');hashes(mechanism['source_sha256'])
    assert mechanism['status']=='drawing-based-plate-mount-contract-passed'
    assert mechanism['key_centers_preserved']==60 and mechanism['mount_centers_preserved']==28
    assert mechanism['spacebar_side_spacing_mm']==95.25 and mechanism['PCB_mount_holes_added']==0
    mechanism_drawing=read(AUD/'key-mechanism-drawing.json')
    hashes(mechanism_drawing['source_sha256']);hashes(mechanism_drawing['outputs'])
    assert len(mechanism_drawing['outputs'])==4
    guide=read(AUD/'yeti60-build-guide.json');hashes(guide['source_sha256']);hashes(guide['outputs'])
    guide_check=read(AUD/'yeti60-build-guide-check.json')
    assert guide_check['status']=='passed' and guide_check['guide_manifest_sha256']==sha(AUD/'yeti60-build-guide.json')
    assert guide_check['verification_recipe_sha256']==sha(ROOT/'scripts/check_yeti60_build_guide.py')
    engineering=read(AUD/'yeti60-engineering.json');assert engineering['status']=='passed';hashes(engineering['evidence_sha256'],AUD)
    target=read(AUD/'yeti60-target-build.json');assert target['status']=='built';hashes(target['source_sha256'])
    for variant in target['variants'].values():hashes(variant['outputs'])
    target_check=read(AUD/'yeti60-target-check.json');assert target_check['status']=='passed' and target_check['build_manifest_sha256']==sha(AUD/'yeti60-target-build.json')
    assert all(v['USB_configuration_mA']==500 for v in target_check['variants'].values())
    complete=read(AUD/'complete-exploded.json');hashes(complete['source_sha256']);hashes(complete['outputs'])
    assert complete['mainboard_parts']==75 and complete['USB_wires']==4 and complete['battery_wires']==3
    assert complete['mount_sets']==28 and complete['active_keys']==60
    protection=read(AUD/'C5-protection.json');assert protection['status']=='protected-I/O-coverage-passed';hashes(protection['source_sha256'])
    rendered=read(ROOT/'renders/yeti60-assembly/render-manifest.json')
    assert len(rendered['fitted_mainboard_references'])==75 and rendered['fitted_BOM_sha256']==sha(AUD/'yeti60-bom.json')
    assert all(rendered['exploded_visible_objects_by_group'].values())
    assert rendered['exploded_visible_objects_by_group']['electronics']==75
    assert rendered['exploded_visible_objects_by_group']['stabilizers']==15
    assert set(rendered['exploded_frame_checks'])=={'feet','electronics','battery','interconnect'}
    assert all(v['in_frame'] and v['above_desk'] for v in rendered['exploded_frame_checks'].values())
    assert read(AUD/'documentation-check.json')['status']=='passed'
    research=read(AUD/'prototype-research.json');hashes(research['source_sha256']);hashes(research['outputs'])
    assert research['native_recipe_sha256']==sha(ROOT/'scripts/export_yeti60_usb_reference.py')
    assert not research['bare_board_order_ready'] and not research['production_approved'] and not research['physical_verification']
    assert research['mechanical']['installed_mounts']==28 and research['mechanical']['unused_mounts']==['H26']
    return {'status':'passed','shared_links':shared_links,'controller_count':1,'physical_pin_pairs':len(cad['physical_pin_pairs']),'matched_mount_holes':28,'assembly_condition':'provisional stack only','firmware_condition':'normal/calibrator ARM targets built, USB500 descriptor verified; hardware enumeration/BLE/calibration untested','production_approved':False,'open_requirements':config['open_requirements']}
def main():
    try: report=verify()
    except (AssertionError,KeyError,FileNotFoundError,ValueError) as error:
        location=traceback.extract_tb(error.__traceback__)[-1]
        report={'status':'failed','error':str(error) or location.line,'check_location':f'{Path(location.filename).name}:{location.lineno}','production_approved':False}
    (AUD/'integration.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))
    raise SystemExit(report['status']!='passed')
if __name__=='__main__':main()
