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
    analog=read(AUD/'analog-waveform.json');hashes(analog['source_sha256']);hashes(analog['outputs'])
    assert analog['status']=='model-regression-passed-physical-open' and not analog['physical_verification']
    assert {x['case'] for x in analog['order_mutants_rejected']}=={'rise-before-release','fall-before-clamp'}
    assert all(x['exit_code']!=0 for x in analog['order_mutants_rejected']) and len(analog['sensitivities'])==36
    assert analog['illustrative_correct_delta_ADC_codes']>32 and analog['illustrative_wrong_rise_delta_ADC_codes']==0
    assert not analog['ADC_API_latency_qualified'] and not analog['key_capacitance_measured'] and not analog['opamp_dynamic_model']
    assert not analog['AFE_saturation_qualified']
    assert analog['diagnostic_counter']['clock_hz']==32768 and analog['diagnostic_counter']['one_tick_quantization_guard']
    assert not analog['diagnostic_counter']['hardware_sample_timestamp'] and not analog['diagnostic_counter']['absolute_time_accuracy_qualified']
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
    gpio_modes=read(AUD/'gpio-mode-policy.json');hashes(gpio_modes['source_sha256'])
    assert gpio_modes['status']=='passed' and not gpio_modes['physical_verification']
    assert gpio_modes['upstream_revision']==target['dependencies']['zephyr']
    assert gpio_modes['GPIO_constants_checked_against_pinned_headers'] and gpio_modes['nominal_scan_samples']==150
    assert len(gpio_modes['positive_cases'])==5 and len(gpio_modes['rejected_mutants'])==4
    assert all(x['exit_code']!=0 for x in gpio_modes['rejected_mutants'])
    scan_control=read(AUD/'scan-control.json');hashes(scan_control['source_sha256'])
    assert scan_control['status']=='passed' and not scan_control['physical_verification']
    assert scan_control['upstream_revision']==target['dependencies']['zephyr']
    assert scan_control['ZMK_revision']==target['dependencies']['zmk']
    assert scan_control['active_keys_checked']==60 and scan_control['inactive_positions_rejected']==15
    assert scan_control['event_queue_capacity']==128 and scan_control['undrained_burst_events_checked']==120
    assert len(scan_control['positive_cases'])==15 and len(scan_control['rejected_mutants'])==17
    assert scan_control['calibration_record_bytes']==308 and scan_control['legacy_record_bytes_rejected']==304
    assert all(x['exit_code']!=0 for x in scan_control['rejected_mutants'])
    from yeti60_scan_control_contract import verify as verify_scan_control
    verify_scan_control(scan_control,target,sha(AUD/'yeti60-target-build.json'))
    from yeti60_key_pipeline_contract import verify as verify_key_pipeline
    pipeline=read(AUD/'key-pipeline.json');hashes(pipeline['source_sha256'])
    verify_key_pipeline(pipeline,target,sha(AUD/'yeti60-target-build.json'))
    calibration=read(AUD/'calibration.json');hashes(calibration['source_sha256'])
    assert calibration['status']=='passed' and not calibration['physical_verification']
    storage=calibration['storage_integrity']
    assert storage['record_bytes']==308 and storage['independent_zlib_records']==512
    assert storage['single_bit_flips_rejected']==2464 and storage['byte_inversions_rejected']==308
    assert storage['sliding_32_bit_bursts_rejected']==2433 and not storage['physical_power_cut_tested']
    assert len(storage['rejected_mutants'])==3 and all(c['exit_code']!=0 for c in storage['rejected_mutants'])
    from yeti60_nvs_contract import verify as verify_nvs
    nvs=read(AUD/'nvs-powercut.json');hashes(nvs['source_sha256'])
    verify_nvs(nvs,target,sha(AUD/'yeti60-target-build.json'))
    usb_events=read(AUD/'usb-event-policy.json');hashes(usb_events['source_sha256'])
    assert usb_events['status']=='passed' and not usb_events['physical_verification']
    assert usb_events['upstream_revision']=='0862fc0f8c864834007986efcaf52f292ea6d37d'
    assert len(usb_events['cases'])==11 and usb_events['synchronous_disable_before_upstream_notification']
    assert usb_events['configuration_zero_rejected'] and usb_events['GPIO_fault_latched'] and usb_events['unintended_external_ILIM_mode_rejected']
    recovery=read(AUD/'firmware-recovery.json');hashes(recovery['source_sha256'])
    assert recovery['status']=='passed' and not recovery['physical_verification']
    assert recovery['upstream_revision']==target['dependencies']['zmk']
    assert len(recovery['CMake_mutation_cases'])==10
    assert target_check['recovery_binding']['clears']=='selected BLE profile only'
    assert not target_check['recovery_binding']['calibration_settings_erase_binding']
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
    candidate=ROOT/'hardware/usb-short-route'
    short=read(candidate/'audit/native-check.json');assert short['status']=='native-candidate-checks-passed'
    assert short['strict_DRC_errors']==short['unconnected_items']==short['schematic_parity_items']==0
    assert short['physical_pin_pairs_checked']==len(short['physical_pin_pairs'])==411
    assert all(pair['connected'] for pair in short['physical_pin_pairs'])
    hashes(short['source_sha256']);assert short['audit_script_sha256']==sha(ROOT/'scripts/check_usb_short_route.py')
    local=read(candidate/'audit/geometry-check.json');assert local['status']=='local-header-fit-and-reference-passed';hashes(local['source_sha256'])
    assert all(local['USB_reference_screen'][side]['nearest_adjacent_GND_coverage_fraction']>.999 for side in ['positive','negative'])
    firmware=read(candidate/'firmware/manifest.json');hashes(firmware['source_sha256']);hashes(firmware['published_outputs']);hashes(firmware['evidence'])
    candidate_pipeline=read(candidate/'firmware/key-pipeline.json');hashes(candidate_pipeline['source_sha256'])
    verify_key_pipeline(candidate_pipeline,read(candidate/'firmware/build.json'),sha(candidate/'firmware/build.json'))
    assert firmware['native_acceptance_sha256']==sha(candidate/'audit/native-check.json')
    assert firmware['local_geometry_acceptance_sha256']==sha(candidate/'audit/geometry-check.json')
    assert not short['manufacturing_released'] and not local['manufacturing_released'] and not firmware['physical_verification']
    from check_usb_short_assembly_package import verify as verify_assembly_package
    package=verify_assembly_package()
    from study_usb_short_tolerances import verify_evidence as verify_tolerance_evidence
    tolerance=read(candidate/'audit/tolerance-diagnostic.json');hashes(tolerance['source_sha256'])
    verify_tolerance_evidence(tolerance,read(ROOT/'mechanical/assembly-spec.raytac.json'),read(ROOT/'mechanical/pcb-fabrication-spec.json'))
    exported=read(candidate/'audit/fabrication-export.json');hashes(exported['source_sha256']);hashes(exported['outputs'])
    cam=read(candidate/'audit/fabrication-check.json');hashes(cam['source_sha256'])
    assert cam['status']=='candidate-CAM-native-roundtrip-passed'
    assert not cam['manufacturing_released'] and not cam['physical_verification'] and not cam['production_approved']
    assert cam['fitted_placements']==75 and cam['copper_lands']['fitted_lands_checked']==289
    assert cam['drills']['total']==846 and cam['drills']['slots']==2
    assert cam['IPC']['all_test_records_checked']==cam['IPC']['parsed_records']==1444
    assert cam['IPC']['via_sites_checked']==813 and cam['IPC']['all_pad_sites_checked']==631
    assert cam['stencil']['omitted_DNP']==['JP1'] and cam['stencil']['apertures']==297
    return {'status':'passed','shared_links':shared_links,'controller_count':1,
            'summary_board':'Current short-USB Raytac candidate',
            'physical_pin_pairs':short['physical_pin_pairs_checked'],
            'retained_reference':{'physical_pin_pairs':len(cad['physical_pin_pairs']),
                                  'scope':'Canonical long-route reference, not the current first-board package'},
            'matched_mount_holes':28,'assembly_condition':'C04 plate and switch bounded design fit passed; full keyboard/physical acceptance remains open','firmware_condition':'normal/calibrator ARM targets built, USB500 descriptor verified; hardware enumeration/BLE/calibration untested','production_approved':False,'open_requirements':config['open_requirements'],'USB_repair_candidate':{'native_and_local_geometry':'passed','firmware':'rebuilt-and-host-checked','manufacturing_released':False,'complete_harness_and_assembly_integration':'installed-geometry-and-publication-checked','assembly_package':package['status'],'combined_tolerance_qualified':False,'tolerance_diagnostic':tolerance['status'],'service_mating_path_and_physical_acceptance':'open'}}
def main():
    try: report=verify()
    except (AssertionError,KeyError,FileNotFoundError,ValueError) as error:
        location=traceback.extract_tb(error.__traceback__)[-1]
        report={'status':'failed','error':str(error) or location.line,'check_location':f'{Path(location.filename).name}:{location.lineno}','production_approved':False}
    (AUD/'integration.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))
    raise SystemExit(report['status']!='passed')
if __name__=='__main__':main()
