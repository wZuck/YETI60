#!/usr/bin/env python3
"""Verify an offline E73 bundle, or verify the bundle and source checkout together."""
import argparse,hashlib,json,re,zipfile
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  self.links.extend(v for k,v in attrs if k in ['href','src'])
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--bundle',type=Path,help='Path to an unpacked delivery directory')
 parser.add_argument('--require-release',action='store_true')
 args=parser.parse_args()
 if not __debug__:
  parser.error('Run Python without optimization so the verification checks are enabled')
 sibling=Path(__file__).resolve().parent
 in_checkout=args.bundle is None and not (sibling/'manifest.json').is_file()
 base=(ROOT/'delivery/YETI60-E73' if in_checkout else args.bundle or sibling).resolve()
 m=json.loads((base/'manifest.json').read_text())
 if in_checkout:
  for name,digest in m['source_sha256'].items():assert sha(ROOT/name)==digest,('Stale source',name)
  assert m['revision']==json.loads((ROOT/'hardware/e73-corner-spec.json').read_text())['revision']
 files={str(p.relative_to(base))for p in base.rglob('*')if p.is_file()and p!=base/'manifest.json'and p.name!='.DS_Store'}
 assert files==set(m['files_sha256']),'Unlisted or missing delivery file'
 for name,digest in m['files_sha256'].items():assert sha(base/name)==digest,('Changed delivery file',name)
 prototype=m['mechanical_first_article']
 assert prototype['revision']=='M05' and prototype['use']=='first-article-dry-fit'
 assert not prototype['physical_verification']
 assert len(set(prototype['shell_STL']))==4 and len(set(prototype['retainer_STL'].values()))==16
 assert len(prototype['harness_lengths'])==len(prototype['assembly_views'])==2
 required=set(prototype['shell_STL']+list(prototype['retainer_STL'].values())+
              prototype['harness_lengths']+prototype['assembly_views'])
 assert required<=files
 case_dir='02-mechanical/service-case-m05/'
 for name in ('BAT-R1','BAT-R2'):assert prototype['retainer_STL'][name]==case_dir+'harness/'+name+'-M05.stl'
 for name in ('bottom-m05','cover-J2','cover-J4'):assert case_dir+name+'-REVIEW.stl' in prototype['shell_STL']
 assert all(path.startswith(case_dir+'harness/wire-lengths-m05') for path in prototype['harness_lengths'])
 render=json.loads((base/'06-validation/assembly-render.json').read_text())
 harness=json.loads((base/'06-validation/m05-harness.json').read_text())
 lengths=harness['trial_variants'][0]['seated_free_lengths_mm']
 assert render['case_revision']==prototype['revision'] and len(lengths)==9
 assert all(abs(value-render['wire_free_lengths_mm'][key])<.000001 for key,value in lengths.items())
 assert render['views']['case-underside']['objects_by_group']['covers']==2
 bench=json.loads((base/'06-validation/bench-power-plan.json').read_text())
 assert bench['pcb_sha256']==m['source_PCB_sha256'] and not bench['physical_verification']
 assert bench['charge_headroom_M05']['model_R_60C_ohm']==harness['charging_path_sensitivity']['model_R_at_temperature_ohm']
 for p in base.rglob('*'):
  if p.suffix=='.html':
   parser=Links();parser.feed(p.read_text());links=parser.links
  elif p.suffix=='.md':links=re.findall(r'\]\(([^)]+)\)',p.read_text())
  else:continue
  for link in links:
   if re.match(r'^[a-z]+:|^#',link):continue
   target=(p.parent/link.split('#')[0]).resolve()
   assert base in target.parents and target.is_file(),('Broken local delivery link',str(p.relative_to(base)),link)
 archive=base/'01-pcb/YETI60-E73-gerbers-REVIEW.zip'
 with zipfile.ZipFile(archive)as z:
  expected={p.name for p in (base/'01-pcb/gerbers').iterdir()
            if p.is_file() and p.name!='.DS_Store'}
  assert len(z.namelist())==len(expected) and set(z.namelist())==expected,'Incomplete or duplicate Gerber archive entries'
  for name in z.namelist():assert z.read(name)==(base/'01-pcb/gerbers'/name).read_bytes(),('Gerber archive mismatch',name)
 cam=json.loads((base/'06-validation/cam-ordinary.json').read_text())
 assert cam['status']=='cam-geometry-matches-native-pcb' and cam['archive_sha256']==sha(archive)
 assert cam['source_sha256']['hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pcb']==m['source_PCB_sha256']
 apertures=json.loads((base/'06-validation/cam-apertures.json').read_text())
 assert apertures['archive_sha256']==cam['archive_sha256'] and apertures['source_PCB_sha256']==m['source_PCB_sha256']
 assert apertures['vias']==cam['through_via_count'] and len(apertures['layers'])==4
 assert all(not layer['nominal_intersections'] and not layer['holes_below_conservative_reserve']
            and layer['min_nominal_gap_mm']>=.229 for layer in apertures['layers'].values())
 assert sha(base/'01-pcb/source/EC60-nRF52840.kicad_pcb')==m['source_PCB_sha256']
 firmware=base/'05-firmware'
 fm=json.loads((firmware/'manifest.json').read_text())
 assert fm['source_PCB_sha256']==m['source_PCB_sha256']
 expected_images={f'releases/{variant}/yeti60-e73.{extension}'
                  for variant in ('normal','calibrator') for extension in ('hex','bin')}
 firmware_prefix='hardware/e73-hhkb-corner/firmware/'
 assert fm['published_outputs'].keys()=={firmware_prefix+image for image in expected_images}
 for image in expected_images:
  assert sha(firmware/image)==fm['published_outputs'][firmware_prefix+image],('Firmware image mismatch',image)
 message='Delivery hashes, M05 files, local links, Gerber archive and firmware/PCB identity passed'
 print(message+(' against the source checkout' if in_checkout else ' in the offline bundle'))
 if args.require_release and (m['pending']or not m['production_approved']):
  print('Delivery remains a review draft:',', '.join(m['pending']));return 2
 return 0
if __name__=='__main__':raise SystemExit(main())
