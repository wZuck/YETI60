#!/usr/bin/env python3
"""Check freshly exported schematic connectivity, saved contracts and native ERC."""
import hashlib,json,os,subprocess,tempfile
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]; BASE=ROOT/'hardware/ec60-nrf52840'
CLI=os.environ.get('KICAD_CLI','/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
def signature(path):
    doc=ET.parse(path).getroot()
    components={c.get('ref'):(c.findtext('value'),c.findtext('footprint')) for c in doc.findall('./components/comp')}
    nets={n.get('name'):sorted((v.get('ref'),v.get('pin')) for v in n.findall('node')) for n in doc.findall('./nets/net')}
    return components,nets

def main():
    sch=BASE/'EC60-nRF52840.kicad_sch'
    with tempfile.TemporaryDirectory(prefix='yeti60-schematic-') as folder:
        fresh=Path(folder)/'netlist.xml'
        subprocess.run([CLI,'sch','export','netlist','--format','kicadxml','-o',str(fresh),str(sch)],check=True,capture_output=True)
        actual,nets=signature(fresh)
        assert (actual,nets)==signature(BASE/'netlist.xml'),'Saved netlist differs from current schematic; export it again and review contracts'
    contract=json.loads((BASE/'components.json').read_text())
    expected={ref:(part['value'],part['footprint']) for ref,part in contract.items() if not ref.startswith('#')}
    assert all(actual.get(ref)==value for ref,value in expected.items()),'Schematic component values/footprints differ from partial redesign contract'
    frozen=json.loads((BASE/'frozen-footprints.json').read_text())
    assert all(frozen[ref]['id']==value[1] for ref,value in actual.items()),'Schematic footprint differs from frozen library contract'
    subprocess.run([CLI,'sch','erc','--format','json','--severity-all','-o',str(BASE/'ERC.json'),str(sch)],check=True,capture_output=True)
    erc=json.loads((BASE/'ERC.json').read_text()); counts=Counter(v['severity'] for sheet in erc['sheets'] for v in sheet['violations'])
    report={'status':'passed' if not counts['error'] else 'failed','fresh_netlist_matches_saved':True,'component_values_and_footprints_match':True,'components':len(actual),'redesign_value_contract_components':len(expected),'erc_counts':dict(counts),'erc_ignored_checks':erc.get('ignored_checks'),'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*BASE.glob('*.kicad_sch'),BASE/'components.json',BASE/'netlist.xml',BASE/'YAECKB.kicad_sym']}}
    (ROOT/'docs/audit/schematic-current.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['status']=='passed','ERC errors remain'
    print('Fresh schematic, saved netlist and component contracts agree;',dict(counts))
if __name__=='__main__':main()
