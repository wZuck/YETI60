#!/usr/bin/env python3
"""Check exported single-MCU connectivity against its explicit pin contract."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/ec60-nrf52840'

def main():
    document = ET.parse(BASE / 'netlist.xml').getroot()
    components = document.findall('./components/comp')
    refs = [c.get('ref') for c in components]
    assert len(set(refs)) == len(refs), 'Duplicate reference'
    actual = {(node.get('ref'), node.get('pin')): net.get('name')
              for net in document.findall('./nets/net') for node in net.findall('node')}
    contract = json.loads((BASE / 'components.json').read_text())
    for ref, part in contract.items():
        if ref.startswith('#'): continue  # ERC supply flags are omitted from PCB netlists
        assert ref in refs, f'Missing component: {ref}'
        for pin, expected in part['pins'].items():
            assert actual.get((ref, pin)) == expected, (ref, pin, expected, actual.get((ref, pin)))
    mcus = [c.get('ref') for c in components if any(token in c.findtext('value', '').upper()
            for token in ('STM32', 'NRF52840', 'MDBT50'))]
    assert mcus == ['U1'], f'Expected one nRF52840 module, found {mcus}'
    assert 'USB1' not in refs, 'Rear USB must use daughterboard, not original USB1'
    assert len({actual[('U1', p)] for p in ('37','36','39','38','41')}) == 5
    assert actual[('U1','28')] == actual[('U1','30')] == '+3.3V'
    assert actual[('U1','32')] == 'USB_5V'
    report = {'components': len(refs), 'controller_count': 1, 'pin_contract': 'pass',
              'scope': 'schematic XML connectivity only; PCB routing and interference not certified'}
    (BASE / 'connectivity-check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__': main()
