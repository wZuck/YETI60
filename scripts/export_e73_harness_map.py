#!/usr/bin/env python3
"""Read native connector poses, all fitted bounds and installed mount datums."""
import csv,hashlib,json,math
from pathlib import Path
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/e73-hhkb-corner'
def main():
 path=BASE/'EC60-nRF52840.kicad_pcb';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();before=sha(path);b=p.LoadBoard(str(path));refs={r.strip()for row in csv.DictReader((BASE/'mainboard-purchase.csv').open())for r in row['References'].split(',')};parts={};mounts=[]
 for f in b.GetFootprints():
  ref=f.GetReference()
  if ref in refs:
   bb=f.GetBoundingBox(False,False);parts[ref]={'side':'front'if f.GetLayer()==p.F_Cu else'back','position_PCB_mm':list(p.ToMM(f.GetPosition())),'angle_deg':f.GetOrientationDegrees(),'footprint':str(f.GetFPID().GetLibItemName()),'bbox_PCB_mm':[p.ToMM(v)for v in [bb.GetLeft(),bb.GetTop(),bb.GetRight(),bb.GetBottom()]],'pads':[dict(pin=x.GetNumber(),net=x.GetNetname(),xy_PCB_mm=list(p.ToMM(x.GetPosition())))for x in f.Pads()]}
  if ref.startswith('H')or ref=='REF**':
   for pad in f.Pads():
    if min(p.ToMM(pad.GetDrillSize()))>=2.2:mounts.append(dict(ref=ref,xy_PCB_mm=list(p.ToMM(pad.GetPosition())),drill_mm=list(p.ToMM(pad.GetDrillSize()))))
 assert len(parts)==75 and len(mounts)==29 and sha(path)==before
 target=BASE/'audit/harness-native.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(dict(parts=parts,mounts=mounts,source_PCB_sha256=before,source_sha256={str(f.relative_to(ROOT)):sha(f)for f in [path,BASE/'mainboard-purchase.csv',Path(__file__)]}),indent=2)+'\n');print('75 native body bounds and 29 mounts exported; PCB unchanged')
if __name__=='__main__':main()
