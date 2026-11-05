"""Verify source/compiled-matrix and bounded scanner host-test evidence."""
def verify(report, build, build_sha256):
    assert report['status']=='passed' and not report['physical_verification']
    assert report['upstream_revision']==build['dependencies']['zephyr']
    assert report['ZMK_revision']==build['dependencies']['zmk']
    assert report['target_build_manifest_sha256']==build_sha256
    normal=build['variants']['normal']
    assert report['resolved_configuration_sha256']==normal['configuration_sha256']
    assert report['resolved_devicetree_sha256']==normal['devicetree_sha256']
    options=normal['calibration_scan_configuration']
    assert report['scan_configuration']==options
    assert options=={'CONFIG_YETI60_ACTIVE_SCAN_MS':'4','CONFIG_YETI60_IDLE_SCAN_MS':'30','CONFIG_YETI60_IDLE_AFTER_MS':'30000','CONFIG_YETI60_AFE_IDLE_GATING':'y'}
    assert report['active_keys_checked']==60 and report['inactive_positions_rejected']==15
    positions=[tuple(p) for p in report['compiled_matrix_positions']]
    assert len(set(positions))==len(positions)==60 and all(0<=r<5 and 0<=c<15 for r,c in positions)
    assert set(report['compiled_variant_maps'])==set(build['variants'])=={'normal','calibrator'}
    for name,info in report['compiled_variant_maps'].items():
        record=build['variants'][name]
        assert info['devicetree_sha256']==record['devicetree_sha256']
        assert info['configuration_sha256']==record['configuration_sha256']
        assert [tuple(p) for p in info['positions']]==positions
        assert record['calibration_version']==normal['calibration_version']
        assert record['calibration_scan_configuration']==options
    masks=[0]*5
    for row,col in positions:masks[row]|=1<<col
    assert masks==report['compiled_matrix_active_masks']==[0x7fff,0x3fff,0x2fff,0x6ffd,0x0646]
    assert report['event_queue_capacity']==128 and report['undrained_burst_events_checked']==120
    assert report['calibration_record_bytes']==308 and report['legacy_record_bytes_rejected']==304
    assert len(report['positive_cases'])==15 and len(report['rejected_mutants'])==17
    assert all(c['exit_code']!=0 for c in report['rejected_mutants'])
    idle=report['inactive_idle']
    assert idle['unused_fullscale_positions']==15 and idle['post_capture_frames']==7511
    assert idle['ADC_reads']==7511*75==563325
    assert idle['idle_sleeps']==3 and idle['active_sleeps']==7508
    assert idle['presses']==idle['releases']==60
    assert idle['modeled_sleep_ms']==4*7508+30*3==30122
    tap=report['idle_short_tap']
    assert tap['short_tap_ms']==50 and tap['presses']==tap['releases']==1
    assert tap['press_delay_ms']==29 and tap['release_delay_ms']==7
    assert tap['single_frame_spikes']==1 and tap['idle_sleeps']==1 and tap['active_sleeps']==7519
    assert tap['ADC_reads']==7520*75==564000
    mutants={item['case']:item for item in report['rejected_mutants']}
    missed=mutants['omit-pending-wake']['observed'];assert missed['presses']==missed['releases']==0
    noisy=mutants['bypass-debounce']['observed'];assert noisy['presses']==noisy['releases']==2
