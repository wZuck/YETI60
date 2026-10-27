#!/usr/bin/env python3
"""Require English default / Chinese peers and resolve local Markdown links.

Upstream Git submodules and ignored generated caches retain their own docs.
"""
from pathlib import Path
import re,json
ROOT=Path(__file__).resolve().parents[1]
files=sorted(p for p in ROOT.rglob('*.md') if not set(p.relative_to(ROOT).parts)&{'EC60','felk60','.git','.render-work','.assembly-work','.history','__pycache__'})
errors=[]
for p in files:
    zh=p.name.endswith('.zh-CN.md');peer=p.with_name(p.name.replace('.zh-CN.md','.md') if zh else p.stem+'.zh-CN.md')
    if not peer.exists():errors.append(f'{p.relative_to(ROOT)}: missing {peer.name}')
    if f'({peer.name})' not in p.read_text():errors.append(f'{p.relative_to(ROOT)}: missing peer navigation')
    if not zh:
        body=p.read_text()
        if re.search(r'[\u4e00-\u9fff]',body):errors.append(f'{p.relative_to(ROOT)}: default prose contains untranslated Chinese')
    for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
        target=link.split('#',1)[0].split(' ',1)[0].strip('<>')
        if not target or re.match(r'^[a-z]+:',target) or target.startswith('/'):continue
        if not (p.parent/target).exists():errors.append(f'{p.relative_to(ROOT)}: broken local link {target}')
report={'status':'passed' if not errors else 'failed','policy':'project-owned prose defaults to English with parallel zh-CN; upstream submodules/licenses and machine-readable data retain stable identifiers','markdown_files':len(files),'pairs':len(files)//2,'errors':errors}
(ROOT/'docs/audit/documentation-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(bool(errors))
