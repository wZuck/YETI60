"""Shared bounded NVS recovery evidence checks; no physical acceptance claim."""
def verify(report, build, build_sha256):
    assert report['status']=='passed' and not report['physical_verification']
    assert report['upstream_revision']==build['dependencies']['zephyr']
    assert report['target_build_manifest_sha256']==build_sha256
    normal=build['variants']['normal']
    assert report['resolved_configuration_sha256']==normal['configuration_sha256']
    assert report['resolved_devicetree_sha256']==normal['devicetree_sha256']
    profile=report['profile']
    assert profile['calibration_version']==normal['calibration_version']
    assert (profile['partition_offset'],profile['partition_bytes'],profile['sector_bytes'],profile['sectors'],profile['NVS_bytes'],profile['write_bytes'])==(0xf0000,0x10000,4096,8,32768,4)
    assert not profile['global_NVS_CRC']
    cases={case['scenario']:case for case in report['cases']}
    assert len(report['cases'])==len(cases)==5
    assert set(cases)=={'first-save','rewrite','legacy-replacement','garbage-collection','recovery-cut'}
    for name,case in cases.items():
        assert case['trials']==case['program_or_erase_units']*6+1
        assert case['old']+case['new']+case['uncalibrated']==case['trials']
        if name in ['first-save','legacy-replacement']:
            assert case['old']==0 and case['new'] and case['uncalibrated']
        else:
            assert case['old'] and not case['uncalibrated']
        if name in ['garbage-collection','recovery-cut']:
            assert case['dirty_erases']>0 and case['erase_calls']>0
    assert cases['recovery-cut']['new']==0
    assert cases['rewrite']['new'] and cases['garbage-collection']['new']
    assert report['total_cut_trials']==sum(c['trials'] for c in cases.values())==14795
    assert report['opaque_unrelated_sentinel_preserved'] and report['post_recovery_resave_verified']
    assert len(report['rejected_mutants'])==2 and all(c['exit_code']!=0 for c in report['rejected_mutants'])
