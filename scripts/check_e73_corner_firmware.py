#!/usr/bin/env python3
"""Check published corner images against this PCB and the host-suite evidence."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/e73-hhkb-corner'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 folder=BASE/'firmware';manifest=json.loads((folder/'manifest.json').read_text())
 assert manifest['status']=='candidate-normal-calibrator-built-host-suite-passed'
 assert not manifest['manufacturing_released'] and not manifest['physical_verification']
 assert sha(BASE/'EC60-nRF52840.kicad_pcb')==manifest['source_PCB_sha256']
 assert sha(BASE/'audit/placement-check.json')==manifest['native_evidence_sha256']
 for group in ['source_sha256','published_outputs','evidence']:
  for name,digest in manifest[group].items():assert sha(ROOT/name)==digest,('Stale candidate firmware',name)
 build=json.loads((folder/'yeti60-target-build.json').read_text())
 target=json.loads((folder/'yeti60-target-check.json').read_text())
 suite=json.loads((folder/'firmware-suite.json').read_text())
 assert build['status']=='built' and target['status']==suite['status']=='passed'
 assert target['build_manifest_sha256']==sha(folder/'yeti60-target-build.json')
 for name,digest in suite['evidence_sha256'].items():assert sha(folder/Path(name).name)==digest,('Changed suite evidence',name)
 assert set(build['variants'])=={'normal','calibrator'}
 assert len({v['calibration_version']for v in build['variants'].values()})==1
 for variant,data in build['variants'].items():
  assert data['E73_configuration']=={'LF_clock':'internal-RC','REG1':'LDO','REG0_DCDC':False,'NFC_pins':'GPIO','HEX_NFCPINS_UICR':0xfffffffe}
  for extension in ['hex','bin']:
   name=f'firmware/releases/{variant}/yeti60-e73.{extension}'
   assert sha(folder/'releases'/variant/Path(name).name)==data['outputs'][name]
 print('Corner PCB identity, normal/calibrator images and host-suite evidence verified; physical acceptance remains open')
if __name__=='__main__':main()
