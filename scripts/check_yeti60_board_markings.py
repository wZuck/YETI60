#!/usr/bin/env python3
"""Verify the historical decoration-only change and retain guidance through P2."""
import hashlib,json,subprocess
from pathlib import Path
from kicad_sexpr import loads,child,children,dumps
ROOT=Path(__file__).resolve().parents[1];PCB='hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb';BASE='27894700dd021e40957199dce596f0e5130db60c'
def main():
 old=loads(subprocess.check_output(['git','show',BASE+':'+PCB],cwd=ROOT,text=True));p=ROOT/PCB;new=loads(p.read_text())
 decoration=[x for x in children(old,'gr_text') if str(x[1])=='YETI60 / EC60 by Cipulot'];assert len(decoration)==1
 expected=[x for x in old if x not in decoration]
 historical=loads(subprocess.check_output(['git','show','03c2be3344a0150b3df0afc200a42cd271d601d7:'+PCB],cwd=ROOT,text=True))
 assert historical==expected,'Historical decoration-only commit changed a functional item'
 for kind in ['gr_text','gr_text_box']:
  assert children(new,kind)==children(expected,kind),'Changed functional standalone guidance'
 def refs(tree):return {str(p[2]) for f in children(tree,'footprint') for p in children(f,'property') if p[1]=='Reference'}
 assert refs(expected)<=refs(new),'Removed a footprint reference'
 report={'status':'passed','baseline_commit':BASE,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'removed_nonfunctional_markings':['YETI60 / EC60 by Cipulot'],'retained':'All standalone guidance and existing footprint reference identifiers; electrode/outline/hole geometry checked separately by check_single_nrf_pcb.py','upstream_attribution':'Retained in project documentation','historical_decoration_only_commit':'03c2be3344a0150b3df0afc200a42cd271d601d7','electrical_geometry_unchanged':False,'intentional_power_revision':'P2 changes R40 and adds R55/R56 and local routes; not a decoration-only current PCB'}
 (ROOT/'docs/audit/yeti60-board-markings.json').write_text(json.dumps(report,indent=2)+'\n');print('Historical decoration-only deletion verified; current standalone guidance and existing reference identifiers retained')
if __name__=='__main__':main()
