#!/usr/bin/env python3
"""Compare decoration cleanup against a fixed electrical baseline, never against HEAD."""
import hashlib,json,subprocess
from pathlib import Path
from kicad_sexpr import loads,child,children,dumps
ROOT=Path(__file__).resolve().parents[1];PCB='hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb';BASE='27894700dd021e40957199dce596f0e5130db60c'
def main():
 old=loads(subprocess.check_output(['git','show',BASE+':'+PCB],cwd=ROOT,text=True));p=ROOT/PCB;new=loads(p.read_text())
 decoration=[x for x in children(old,'gr_text') if str(x[1])=='YETI60 / EC60 by Cipulot'];assert len(decoration)==1
 expected=[x for x in old if x not in decoration];assert new==expected,'Cleanup changed a functional or non-decoration item'
 report={'status':'passed','baseline_commit':BASE,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'removed_nonfunctional_markings':['YETI60 / EC60 by Cipulot'],'retained':'Every other native item, including all copper, mask, footprints, pads, holes, outline, numbers and fabrication/assembly text','upstream_attribution':'Retained in project documentation','electrical_geometry_unchanged':True}
 (ROOT/'docs/audit/yeti60-board-markings.json').write_text(json.dumps(report,indent=2)+'\n');print('Decoration-only deletion verified; every other native item is identical')
if __name__=='__main__':main()
