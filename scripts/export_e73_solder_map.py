#!/usr/bin/env python3
"""Export actual fitted parts/pads for the E73 soldering guide, read-only."""
import csv,hashlib,json
from pathlib import Path
import pcbnew as p
from export_e73_usb_ground import polygons
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/e73-hhkb-corner'
def main():
 path=BASE/'EC60-nRF52840.kicad_pcb';sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();before=sha(path)
 fitted={r.strip()for row in csv.DictReader((BASE/'mainboard-purchase.csv').open())for r in row['References'].split(',')};assert len(fitted)==75
 b=p.LoadBoard(str(path));outline=p.SHAPE_POLY_SET();assert b.GetBoardPolygonOutlines(outline,False);parts={}
 for f in b.GetFootprints():
  ref=f.GetReference()
  if ref not in fitted|{'J3'}:continue
  bb=f.GetBoundingBox(False,False);layer=p.F_Cu if f.GetLayer()==p.F_Cu else p.B_Cu
  parts[ref]=dict(value=f.GetValue(),side='front'if layer==p.F_Cu else'back',position_mm=list(p.ToMM(f.GetPosition())),orientation_deg=f.GetOrientationDegrees(),bbox=[p.ToMM(v)for v in [bb.GetLeft(),bb.GetTop(),bb.GetRight(),bb.GetBottom()]],pads=[dict(number=pad.GetNumber(),net=pad.GetNetname(),position_mm=list(p.ToMM(pad.GetPosition())),polygons=polygons(pad.GetEffectivePolygon(layer)))for pad in f.Pads()if pad.IsOnLayer(layer)])
 service={'J3':parts.pop('J3')};assert set(parts)==fitted and sha(path)==before
 result=dict(parts=parts,service_pads=service,outline=polygons(outline),source_PCB_sha256=before,physical_verification=False,source_sha256={str(f.relative_to(ROOT)):sha(f)for f in [path,BASE/'mainboard-purchase.csv',Path(__file__),ROOT/'scripts/export_e73_usb_ground.py']})
 target=ROOT/'.assembly-work/e73-corner/solder-map.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2)+'\n');print('75 fitted references and their actual pad nets exported')
if __name__=='__main__':main()
