#!/usr/bin/env python3
"""Verify native-saved power geometry and reject manufacturing-relevant faults."""
import copy
import hashlib
import json
from pathlib import Path
from e73_power_repair import expected_footprints, ref, verify
from kicad_sexpr import child, children, loads

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT/'hardware/e73-usb-repair/EC60-nRF52840.kicad_pcb'
    source = ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'
    digest = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    before = digest(path)
    b,old = loads(path.read_text()),loads(source.read_text())
    verify(b,old)
    results = []
    for name in ['EP-size','mask-aperture','model-scale','power-net']:
        mutant = copy.deepcopy(b)
        u5 = next(f for f in children(mutant,'footprint') if ref(f)=='U5')
        if name == 'EP-size':
            ep = next(p for p in children(u5,'pad') if p[1]=='17')
            child(ep,'size')[1] = float(child(ep,'size')[1])+.01
        elif name == 'mask-aperture':
            aperture = next(q for q in children(u5,'fp_rect') if child(q,'layer')[1]=='B.Mask')
            child(aperture,'end')[1] = float(child(aperture,'end')[1])+.01
        elif name == 'model-scale':
            child(child(children(u5,'model')[0],'scale'),'xyz')[1] = 25.4
        else:
            child(next(p for p in children(u5,'pad') if p[1]=='2'),'net')[1] = 'GND'
        try:verify(mutant,old)
        except AssertionError as error:
            assert 'Power footprint/paste/mask/model differs' in str(error),str(error)
        else:raise AssertionError('Accepted power fault: '+name)
        results.append(dict(case=name,rejected=True))
    assert digest(path)==before
    report=dict(status='native-saved-power-geometry-and-fault-checks-passed',
        manufacturing_released=False,physical_verification=False,cases=results,
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in [path,source,Path(__file__),ROOT/'scripts/e73_power_repair.py',ROOT/'hardware/e73-power-repair-spec.json']},
        limits=['Frozen manufacturing geometry only; routing/connectivity and component performance require separate checks'])
    (path.parent/'audit/power-geometry-faults.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'])


if __name__=='__main__':main()
