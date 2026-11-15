#!/usr/bin/env python3
"""Verify bundle bytes, current inputs, local links and factory archive contents."""
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
 parser=argparse.ArgumentParser();parser.add_argument('--require-release',action='store_true');args=parser.parse_args();base=ROOT/'delivery/YETI60-E73';m=json.loads((base/'manifest.json').read_text())
 for name,digest in m['source_sha256'].items():assert sha(ROOT/name)==digest,('Stale source',name)
 files={str(p.relative_to(base))for p in base.rglob('*')if p.is_file()and p!=base/'manifest.json'}
 assert files==set(m['files_sha256']),'Unlisted or missing delivery file'
 for name,digest in m['files_sha256'].items():assert sha(base/name)==digest,('Changed delivery file',name)
 for p in base.rglob('*'):
  if p.suffix=='.html':
   parser=Links();parser.feed(p.read_text());links=parser.links
  elif p.suffix=='.md':links=re.findall(r'\]\(([^)]+)\)',p.read_text())
  else:continue
  for link in links:
   if re.match(r'^[a-z]+:|^#',link):continue
   assert (p.parent/link.split('#')[0]).is_file(),('Broken local delivery link',str(p.relative_to(base)),link)
 with zipfile.ZipFile(base/'01-pcb/YETI60-E73-gerbers-REVIEW.zip')as z:
  for name in z.namelist():assert z.read(name)==(base/'01-pcb/gerbers'/name).read_bytes(),('Gerber archive mismatch',name)
 assert (base/'05-firmware/manifest.json').is_file()
 fm=json.loads((base/'05-firmware/manifest.json').read_text());assert fm['source_PCB_sha256']==m['source_PCB_sha256']
 print('Delivery hashes, current sources, local links, Gerber archive and firmware/PCB identity passed')
 if args.require_release and (m['pending']or not m['production_approved']):
  print('Delivery remains a review draft:',', '.join(m['pending']));return 2
 return 0
if __name__=='__main__':raise SystemExit(main())
