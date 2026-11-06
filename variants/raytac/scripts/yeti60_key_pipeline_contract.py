"""Bounded acceptance contract for pinned matrix/keymap/HID host evidence."""
def verify(report,build,build_sha256):
    assert report['status']=='passed' and report['physical_verification'] is False
    assert report['upstream_revision']==build['dependencies']['zmk']
    assert report['target_build_manifest_sha256']==build_sha256
    assert set(report['compiled_variants'])==set(build['variants'])=={'normal','calibrator'}
    for name,record in build['variants'].items():
        assert report['compiled_variants'][name]=={key:record[key] for key in ['configuration_sha256','devicetree_sha256']}
    assert report['compiled_maps']['normal']==report['compiled_maps']['calibrator']
    assert len(set(report['compiled_maps']['normal']))==60
    assert report['compiled_bindings']['normal']==report['compiled_bindings']['calibrator']
    cfg=report['resolved_HID_configuration']
    assert cfg['CONFIG_ZMK_HID_REPORT_TYPE_HKRO']=='y' and cfg['CONFIG_ZMK_HID_REPORT_TYPE_NKRO']=='n'
    assert cfg['CONFIG_ZMK_HID_KEYBOARD_REPORT_SIZE']=='6' and cfg['CONFIG_ZMK_KSCAN_EVENT_QUEUE_SIZE']=='128'
    cases={case['case']:case for case in report['positive_cases']}
    assert len(cases)==len(report['positive_cases'])==6
    assert {name:item['checked'] for name,item in cases.items()}=={'base':60,'fn':59,'layer-release-order':2,'rollover':7,'unused':15,'all-release':60}
    assert cases['base']['report_submissions']==118
    assert cases['fn']['profile_commands']==5 and cases['fn']['tap_dance_boundary_presses']==1
    assert cases['unused']['position_events']==cases['unused']['report_submissions']==0
    assert cases['all-release']['position_events']==120
    assert {case['case'] for case in report['rejected_mutants']}=={'wrong-transform','drop-layer-snapshot','release-on-current-layer','omit-HID-release'}
    assert all(case['exit_code']!=0 for case in report['rejected_mutants'])
    assert len(report['not_verified'])>=3
