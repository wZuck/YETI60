#!/usr/bin/env python3
"""Assemble source-bound E73 delivery assets; incomplete gates stay explicit.

No order authorization is issued. Re-run after all current source checks and
firmware publication. The web index works offline, without a build server.
"""
import argparse,hashlib,json,shutil,subprocess,zipfile,re,html,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/e73-hhkb-corner'
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'delivery/YETI60-E73');args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 native=json.loads((BASE/'audit/placement-check.json').read_text());assert native['electrical_routing_complete']
 for name in ['placement-check','USB-reference','corner-fit','harness-study','harness-drawing']:
  report=json.loads((BASE/'audit'/f'{name}.json').read_text())
  for path,digest in report['source_sha256'].items():assert sha(ROOT/path)==digest,('Stale delivery input',path)
  if name=='USB-reference':assert report['checks_passed']
  if name=='harness-study':assert report['status']=='continuous-wire-study-passed-guides-open'and not report['failures']and len(report['variants'])==3
  for path,digest in report.get('outputs',{}).items():assert sha(ROOT/path)==digest,('Stale engineering output',path)
 guide=json.loads((BASE/'audit/solder-guide.json').read_text());assert guide['placed_exactly_once']==75 and guide['calibration_positions']==60
 for section in ['source_sha256','outputs']:
  for path,digest in guide[section].items():assert sha(ROOT/path)==digest,('Stale soldering guide',path)
 subprocess.run(['python3',str(ROOT/'scripts/check_e73_corner_firmware.py')],check=True)
 inputs={'scripts/build_e73_delivery.py':sha(Path(__file__))};mapping={}
 def copy(rel,target):
  source=ROOT/rel;dest=out/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);inputs[rel]=sha(source);mapping[rel]=target
 copy('hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pcb','01-pcb/source/EC60-nRF52840.kicad_pcb')
 for name in ['mainboard-purchase.csv','mainboard-purchase.zh-CN.csv','components.json']:copy('hardware/e73-hhkb-corner/'+name,'03-bom/'+name)
 for rel,target in [('hardware/ec60-nrf52840/LICENSE.EC60','licenses/LICENSE.EC60'),('firmware/LICENSE.GPL-2.0','licenses/LICENSE.GPL-2.0'),('hardware/usb-daughterboard/LICENSE.upstream','licenses/LICENSE.UDB')]:copy(rel,target)
 for name in ['README.md','README.zh-CN.md']:copy(name,'03-bom/materials'+('.zh-CN'if 'zh-CN'in name else '')+'.md')
 for rel,target in [('mechanical/generated/yeti60-top.step','02-mechanical/top.step'),('hardware/e73-hhkb-corner/mechanical/yeti60-e73-corner-bottom-m04.step','02-mechanical/bottom.step'),('hardware/e73-hhkb-corner/mechanical/yeti60-e73-corner-bottom-m04.stl','02-mechanical/bottom.stl'),('mechanical/e73-fit/yeti60-e73-niz-m01.dxf','02-mechanical/steel-plate.dxf'),('mechanical/generated/yeti60-standoff-46.step','02-mechanical/standoff.step'),('mechanical/assembly-spec.json','02-mechanical/assembly-spec.json'),('mechanical/pcb-fabrication-spec.json','01-pcb/process-spec.json')]:copy(rel,target)
 subprocess.run(['uv','run','--python','3.14.7','--with-requirements',str(ROOT/'requirements-audit.txt'),'python',str(ROOT/'scripts/export_e73_delivery_top.py'),'--output',str(out/'02-mechanical/top.stl')],check=True)
 inputs['scripts/export_e73_delivery_top.py']=sha(ROOT/'scripts/export_e73_delivery_top.py')
 for p in sorted((BASE/'firmware').rglob('*')):
  if p.is_file():copy(str(p.relative_to(ROOT)),'05-firmware/'+str(p.relative_to(BASE/'firmware')))
 docs={'docs/build/e73-delivery-start':'START-HERE','docs/build/e73-ordering-printing':'01-pcb/ordering-and-printing','docs/engineering/e73-corner-harness':'04-assembly/harness-routing','docs/engineering/e73-hhkb-corner':'06-validation/corner-review','docs/testing/e73-corner-firmware':'05-firmware/installation','docs/build/key-mechanism':'04-assembly/key-mechanism','docs/engineering/battery-pack-specification':'03-bom/battery-requirements'}
 for source,target in docs.items():
  for suffix in ['.md','.zh-CN.md']:copy(source+suffix,target+suffix)
 for lang in ['', '.zh-CN']:
  for ext in ['png','svg']:copy('docs/engineering/images/key-mechanism'+lang+'.'+ext,'04-assembly/images/key-mechanism'+lang+'.'+ext)
 for lang in ['', '.zh-CN']:
  copy('hardware/e73-hhkb-corner/mechanical/harness-conductors'+lang+'.csv','03-bom/harness-conductors'+lang+'.csv')
  for ext in ['png','svg']:copy('docs/engineering/images/e73-corner-harness'+lang+'.'+ext,'04-assembly/images/e73-corner-harness'+lang+'.'+ext)
 copy('hardware/e73-corner-harness-spec.json','02-mechanical/interconnect-spec.json')
 copy('hardware/e73-corner-j5-repair.json','06-validation/j5-repair.json')
 for p in sorted((ROOT/'docs/assembly/e73-corner').rglob('*')):
  if p.is_file():copy(str(p.relative_to(ROOT)),'04-assembly/'+str(p.relative_to(ROOT/'docs/assembly/e73-corner')))
 for p in sorted((BASE/'audit').glob('*')):
  if p.suffix in ['.json','.png','.svg']:copy(str(p.relative_to(ROOT)),'06-validation/'+p.name)
 # Resolve both Markdown and HTML assets into the offline bundle.
 for rel,target in list(mapping.items()):
  if not target.endswith(('.md','.html')):continue
  def resolve(url):
   if re.match(r'^[a-z]+:|^#',url):return url
   raw,sep,anchor=url.partition('#');source=(ROOT/rel).parent/raw
   try:key=str(source.resolve().relative_to(ROOT))
   except ValueError:return url
   if key in mapping:
    import os
    dest=Path(os.path.relpath(out/mapping[key],(out/target).parent)).as_posix()
   else:dest='https://github.com/wZuck/YETI60/blob/master/'+key
   return dest+('#'+anchor if sep else '')
  p=out/target;text=p.read_text()
  if target.endswith('.md'):text=re.sub(r'\[([^\]]*)\]\(([^)]+)\)',lambda m:'['+m[1]+']('+resolve(m[2])+')',text)
  else:text=re.sub(r'(href|src)="([^"]+)"',lambda m:m[1]+'="'+html.escape(resolve(html.unescape(m[2])),quote=True)+'"',text)
  p.write_text(text)
 for zh in [False,True]:
  suffix='.zh-CN'if zh else '';p=out/('03-bom/materials'+suffix+'.md');text=p.read_text();heading='## 一把键盘需要准备的完整材料'if zh else '## Complete materials for one keyboard';text=text[text.index(heading):];text=text.split('\nConsolidated delivery folder')[0].split('\n集中交付目录')[0];nav='[English](materials.md) | [中文](materials.zh-CN.md)'if zh else 'English | [Chinese](materials.zh-CN.md)';p.write_text(nav+'\n\n'+text)
 cam=out/'01-pcb/gerbers';cam.mkdir(parents=True,exist_ok=True);board=BASE/'EC60-nRF52840.kicad_pcb'
 for kind,extra in [('gerbers',['--check-zones','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts','--subtract-soldermask']),('drill',['--format','excellon','--excellon-units','mm','--excellon-separate-th','--generate-report','--report-path',str(cam/'drill-report.txt')])]:subprocess.run([CLI,'pcb','export',kind,*extra,'-o',str(cam),str(board)],check=True,capture_output=True)
 for p in cam.iterdir():
  if p.is_file()and p.name!='.DS_Store':p.write_text(re.sub(r'20\d\d-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:[.+Z0-9:-]*)','2000-01-01T00:00:00',p.read_text()))
 # Export only fitted procurement references, excluding electrodes, mounts and pogo pads.
 positions=out/'01-pcb/placements.csv'
 subprocess.run([CLI,'pcb','export','pos','--format','csv','--units','mm','--side','both','-o',str(positions),str(board)],check=True,capture_output=True)
 fitted={ref.strip()for row in csv.DictReader((BASE/'mainboard-purchase.csv').open())for ref in row['References'].split(',')}
 rows=list(csv.DictReader(positions.open()));columns=list(rows[0]);rows=[q for q in rows if q['Ref']in fitted];assert len(rows)==len(fitted)==75
 with positions.open('w',newline='')as f:
  writer=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');writer.writeheader();writer.writerows(rows)
 assert {'.gtl','.gbl','.g1','.g2'}<={p.suffix for p in cam.iterdir()},'Missing copper layer'
 assert len(list(cam.glob('*.drl')))>=2
 assert not any(re.search(r'in[12]',p.name,re.I)for p in cam.glob('*.drl')),'Unexpected layer-pair drill'
 with zipfile.ZipFile(out/'01-pcb/YETI60-E73-gerbers-REVIEW.zip','w',compression=zipfile.ZIP_DEFLATED)as z:
  for p in sorted(cam.iterdir()):
   if p.name=='.DS_Store':continue
   info=zipfile.ZipInfo(p.name,(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
 sources={'capabilities':'https://jlcpcb.com/capabilities/Capabilities','stackup':'https://jlcpcb.com/impedance'}
 for zh in [False,True]:
  suffix='.zh-CN'if zh else '';lang='zh-CN'if zh else 'en'
  title='YETI60 / E73 交付目录'if zh else 'YETI60 / E73 delivery'
  status='工程审查版 · 尚未放行下单'if zh else 'ENGINEERING REVIEW · ORDER RELEASE OPEN'
  sections=[('00','从这里开始'if zh else 'Start here','START-HERE'+suffix+'.md','制作顺序'if zh else 'Build sequence'),('01','PCB 下单文件'if zh else 'PCB fabrication','01-pcb/YETI60-E73-gerbers-REVIEW.zip','Gerber ZIP'),('02','外壳及定位板'if zh else 'Case and plate','02-mechanical/bottom.stl','Bottom STL'),('03','材料及库存'if zh else 'Materials and inventory','03-bom/materials'+suffix+'.md','Materials'),('04','焊接与台架装配'if zh else 'Soldering and bench assembly','04-assembly/soldering'+suffix+'.html','PCB / bench guide'),('05','固件与安装'if zh else 'Firmware installation','05-firmware/installation'+suffix+'.md','SWD / calibration'),('06','验收与边界'if zh else 'Validation and limits','06-validation/corner-review'+suffix+'.md','Current review')]
  notes=('主板按普通四层 FR-4、标称 1.6 mm、JLC04161H-7628、ENIG、机械贯通孔、过孔两面盖油审查；不选择盲埋孔、激光孔、树脂塞孔或铜盖帽。板框 285.0 × 94.6 mm；装配 1 块主板，数量按工厂起订量。已有 C5 子板保持不变，无需重做。钢定位板不是 PCB，也不是树脂打印件，使用 304 不锈钢，成品厚度 1.55–1.60 mm。外壳按毫米、100% 比例，工程树脂完全后固化；按装配规格修孔、冷粘嵌件，不将热熔嵌件压入热固性树脂。'if zh else 'Review the mainboard as ordinary 4-layer FR-4, nominal 1.6 mm, JLC04161H-7628, ENIG, mechanical through holes and both-side tented vias. No blind/buried/laser vias, resin fill or copper capping. Board envelope: 285.0 × 94.6 mm; install one mainboard, order quantity subject to the factory minimum. Reuse the existing C5 daughterboard. The plate is machined 304 stainless steel, finished 1.55–1.60 mm; it is neither a PCB nor a resin print. Case files use millimetres at 100% scale; fully post-cure engineering resin, finish bores and cold-bond inserts per the assembly specification.')
  pending=('九根导线的连续几何检查已通过，理线固定件及最终整机装配图仍需同步；电源／电池与制造复核、实物 USB／蓝牙／静电容／温升验收未完成。当前机构指南不是整机装配放行。Gerber ZIP 仅供审查，不能当作已放行订单。'if zh else 'Continuous nine-wire geometry has passed; retainers/guides and final closed-case assembly drawings still require integration. Power/battery and manufacturing review, physical USB/BLE/EC and thermal acceptance remain open. The mechanism guide is not complete assembly release. The Gerber ZIP is for review, not an accepted order.')
  if zh:sections=[(a,b,c,d)for (a,b,c,_),d in zip(sections,['制作顺序','Gerber 压缩包','底壳 STL','完整材料表','焊接／台架教程','SWD／校准教程','当前审查'])]
  rows='\n'.join('| '+n+' | ['+label+']('+url+') |'for n,label,url,_ in sections)
  (out/('README'+suffix+'.md')).write_text(('[English](README.md) | [中文](README.zh-CN.md)\n\n'if zh else 'English | [Chinese](README.zh-CN.md)\n\n')+'# '+title+'\n\n'+('[离线网页入口](index.zh-CN.html)'if zh else '[Offline web entry](index.html)')+'\n\n**'+status+'**\n\n'+notes+'\n\n'+('| 序号 | 入口 |'if zh else '| Step | Entry |')+'\n|---|---|\n'+rows+'\n\n'+pending+'\n\n[Top STL](02-mechanical/top.stl) · [Top STEP](02-mechanical/top.step) · [Bottom STEP](02-mechanical/bottom.step) · [Plate DXF](02-mechanical/steel-plate.dxf) · [BOM CSV](03-bom/mainboard-purchase'+suffix+'.csv) · [Checksums](manifest.json)\n\n[JLC capabilities]('+sources['capabilities']+') · [JLC stack-ups]('+sources['stackup']+')\n')
  cards=''.join('<section><span>'+n+'</span><h2>'+html.escape(label)+'</h2><a href="'+url+'">'+html.escape(link)+' ↗</a></section>'for n,label,url,link in sections)
  page=f'''<!doctype html><html lang="{lang}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>:root{{--paper:#edece5;--ink:#1e2c26;--line:#bbc3b9;--accent:#b84a24}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.65 Georgia,"Noto Serif CJK SC",serif}}main{{max-width:1120px;margin:auto;padding:48px 28px}}header{{border-top:8px solid var(--ink);padding-top:16px;display:flex;justify-content:space-between}}h1{{font-size:clamp(42px,7vw,88px);line-height:1.05;letter-spacing:-.045em;margin:40px 0 25px}}.status{{font:12px/1.5 monospace;letter-spacing:.12em;color:var(--accent)}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:0;margin:36px 0;border-top:1px solid var(--line)}}section{{padding:26px 20px;border-bottom:1px solid var(--line)}}section span{{font:13px monospace;color:var(--accent)}}h2{{font-size:23px;font-weight:400}}a{{color:inherit;text-underline-offset:5px}}a:hover{{color:var(--accent)}}.note{{border-left:4px solid var(--accent);padding:12px 22px;background:#e3e2d8}}img{{width:100%;display:block;margin:36px 0}}footer{{border-top:1px solid var(--ink);padding:20px 0;font:12px monospace}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}main{{padding:25px 18px}}}}@media print{{a{{color:black}}}}</style><main><header><strong>{'YETI60 / 制作手册'if zh else 'YETI60 / FIELD MANUAL'}</strong><a href="index{''if zh else '.zh-CN'}.html">{'English'if zh else '中文'}</a></header><h1>{title}</h1><p class="status">{status}</p><p>{notes}</p><div class="grid">{cards}</div><aside class="note">{pending}</aside><img src="06-validation/corner-layout{suffix}.png" alt="PCB placement"><p><a href="02-mechanical/top.step">{'上壳 STEP'if zh else 'Top STEP'}</a> · <a href="02-mechanical/steel-plate.dxf">{'定位板 DXF'if zh else 'Plate DXF'}</a> · <a href="README{suffix}.md">Markdown</a> · <a href="manifest.json">{'文件清单／SHA-256'if zh else 'Manifest / SHA-256'}</a></p><footer>YETI60 · E73-2G4M08S1C · CORNER-04 · 1 mm = 1 mm</footer></main></html>'''
  (out/('index'+suffix+'.html')).write_text(page)
 subprocess.run(['uv','run','--python','3.14.7','--with','markdown-it-py==4.0.0','python',str(ROOT/'scripts/render_e73_delivery_docs.py'),'--base',str(out)],check=True)
 inputs['scripts/render_e73_delivery_docs.py']=sha(ROOT/'scripts/render_e73_delivery_docs.py')
 manifest=dict(status='draft-delivery-engineering-review-not-order-release',production_approved=False,physical_verification=False,source_PCB_sha256=sha(board),source_sha256=inputs,source_mapping=mapping,pending=['Harness retainers, physical routing and service','Closed-case assembly and current exploded drawing','Power/battery and manufacturing review','Physical acceptance'],files_sha256={str(p.relative_to(out)):sha(p)for p in sorted(out.rglob('*'))if p.is_file()and p!=out/'manifest.json'and p.name!='.DS_Store'})
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Delivery review assets assembled:',out)
if __name__=='__main__':main()
