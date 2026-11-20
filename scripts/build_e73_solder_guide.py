#!/usr/bin/env python3
"""Generate bilingual soldering/bench guides from all 75 actual fitted parts."""
import csv,hashlib,html,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/e73-hhkb-corner';OUT=ROOT/'docs/assembly/e73-corner'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(parts,bom,assigned):
 assert set(parts)==set(bom) and len(parts)==75
 assert len(assigned)==len(set(assigned))==75 and set(assigned)==set(bom)
 for ref,f in parts.items():
  assert f['value']==bom[ref]['Design value'],('Wrong guide value',ref)
  assert f['side']==('front'if ref=='U1'else'back'),('Wrong guide mounting side',ref)
 for ref,expected in {'J4':{'1':'USB_FEED','2':'USB_DM','3':'USB_DP','4':'GND'},'J5':{'1':'USB_FEED','2':'GND'},'J1':{'1':'VBUS','4':'GND'},'J2':{'1':'BAT_CELL','2':'GND','3':'BAT_NTC'}}.items():
  pins={p['number']:p['net']for p in parts[ref]['pads']}
  assert all(pins[n]==net for n,net in expected.items()),('Wrong harness contract',ref)

def main():
 data_path=ROOT/'.assembly-work/e73-corner/solder-map.json';data=json.loads(data_path.read_text());content=OUT/'steps.json';cfg=json.loads(content.read_text())
 for name,digest in data['source_sha256'].items():assert sha(ROOT/name)==digest,('Stale solder map',name)
 bom={ref.strip():row for row in csv.DictReader((BASE/'mainboard-purchase.csv').open())for ref in row['References'].split(',')};assert set(bom)==set(data['parts'])and len(bom)==75
 groups={'power':{'U5','U6','F1','L1','C30'}|{f'C{i}'for i in range(40,47)}|{f'R{i}'for i in range(40,49)}|{'R55','R56'},'gates':{'U7','U8','C47','C48'}|{f'R{i}'for i in range(49,55)},'reset':{'R26','R32','SW1','D2'},'local':{'C31','C32'},'connectors':{'J1','J2','J4','J5','SW100'},'module':{'U1'}}
 used=set().union(*groups.values());assert used<=set(bom);groups['analog']=set(bom)-used;groups['none']=set()
 assigned=[r for step in cfg['steps']for r in groups[step['group']]];validate(data['parts'],bom,assigned)
 assert {p['number']:p['net']for p in data['service_pads']['J3']['pads']}=={'1':'+3.3V','2':'SWDIO','3':'GND','4':'SWDCLK','5':'RESET_N','6':'GND'}
 image_dir=OUT/'images';image_dir.mkdir(parents=True,exist_ok=True);outputs={}
 allpts=[p for poly in data['outline']for p in poly['outer']];lo=min(p[0]for p in allpts);hi=max(p[0]for p in allpts);y0=min(p[1]for p in allpts);y1=max(p[1]for p in allpts)
 def diagram(step,zh):
  selected=set(groups[step['group']]);selected|=({'C45','F1','J1','J4','SW100'}if step['id']=='08'else{'J3'}if step['id']=='10'else set());front=step['group']=='module';project=lambda p:(p[0]if front else lo+hi-p[0],p[1]);parts={**data['parts'],**data['service_pads']};tags=[]
  def path(records):
   chunks=[]
   for p in records:
    for ring in [p['outer'],*p['holes']]:chunks.append('M'+' L'.join(f'{x:.6f},{y:.6f}'for x,y in map(project,ring))+' Z')
   return ' '.join(chunks)
  title=('正面，直接观察'if front else'背面，已水平镜像为实际底视')if zh else('Front, viewed directly'if front else'Back, mirrored to the physical underside')
  tags.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{lo-4} {y0-8} {hi-lo+8} {y1-y0+13}" role="img"><title>{title}</title><rect x="{lo-4}" y="{y0-8}" width="{hi-lo+8}" height="{y1-y0+13}" fill="#f7f6f0"/><text x="{lo}" y="{y0-3}" font-family="sans-serif" font-size="3">{title} · {step["id"]}</text><path d="{path(data["outline"])}" fill="#e0e8dc" stroke="#40574b" stroke-width=".25" fill-rule="evenodd"/>')
  label_boxes=[]
  for ref,f in parts.items():
   if (f['side']=='front')!=front:continue
   color='#a95626'if ref in selected else'#9da89e';tags.append(f'<g id="{ref}"><title>{html.escape(ref+" / "+f["value"]+" / "+f["side"])}</title>')
   for pad in f['pads']:
    tags.append(f'<path d="{path(pad["polygons"])}" fill="{color}" fill-rule="evenodd"/>')
    if ref in selected and pad['number']=='1':
     x,y=project(pad['position_mm']);tags.append(f'<circle cx="{x}" cy="{y}" r=".3" fill="#d92525"/>')
   if ref in selected:
    x,y=project(f['position_mm']);w=len(ref)*.9
    for dx,dy in [(0,-1.8),(0,3),(0,-4),(0,5),(-3,-3),(3,4),(0,-6),(0,7)]:
     rect=(x+dx-w/2,y+dy-1.5,x+dx+w/2,y+dy+.3)
     if not any(rect[0]<q[2]+.3 and rect[2]>q[0]-.3 and rect[1]<q[3]+.3 and rect[3]>q[1]-.3 for q in label_boxes):break
    label_boxes.append(rect);tags.append(f'<path d="M{x},{y} L{x+dx},{y+dy}" stroke="#657469" stroke-width=".12"/><text x="{x+dx}" y="{y+dy}" text-anchor="middle" font-family="sans-serif" font-size="1.5" stroke="#fff" stroke-width=".25" paint-order="stroke" fill="#17291e">{ref}</text>')
   tags.append('</g>')
  tags.append('</svg>');p=image_dir/('step-'+step['id']+('.zh-CN'if zh else'')+'.svg');text='\n'.join(tags)+'\n';p.write_text(text);outputs[str(p.relative_to(ROOT))]=sha(p);images=['images/'+p.name]
  for region,(left,right)in enumerate([(70,170),(170,270),(270,360)]):
   refs=[r for r in selected if r in parts and left<=parts[r]['position_mm'][0]<right]
   if not refs:continue
   points=[project((x,y))for r in refs for x in [parts[r]['bbox'][0],parts[r]['bbox'][2]]for y in [parts[r]['bbox'][1],parts[r]['bbox'][3]]];x=min(q[0]for q in points)-8;y=min(q[1]for q in points)-8;w=max(q[0]for q in points)-x+8;h=max(q[1]for q in points)-y+8
   import re
   zoom=p.with_name(p.stem+'-detail-'+str(region)+'.svg');zoom.write_text(re.sub(r'viewBox="[^"]+"',f'viewBox="{x} {y} {w} {h}"',text,count=1));outputs[str(zoom.relative_to(ROOT))]=sha(zoom);images.append('images/'+zoom.name)
  return images
 for zh in [False,True]:
  lang='zh-CN'if zh else'en';suffix='.zh-CN'if zh else'';title='从裸板焊接到台架测试'if zh else'Bare PCB to bench bring-up';nav='[English](soldering.md) | [中文](soldering.zh-CN.md)'if zh else'English | [Chinese](soldering.zh-CN.md)';intro='本指南覆盖 75 件实装元件，尚无样机验证。关壳前请核实线束装拆条件。温升、实物安全及无线验收待样机确认。'if zh else'This guide covers all 75 fitted parts. No physical unit has validated it. Verify harness access before closure. Physical thermal, safety and RF acceptance require a prototype.';md=[nav,'','# '+title,'',intro,''];articles=[]
  for step in cfg['steps']:
   refs=sorted(groups[step['group']]);heading=step['zh'if zh else'en'];body=step['body_zh'if zh else'body_en'];images=diagram(step,zh);image=images[0];md+=['## '+step['id']+' · '+heading,'',body,'',f'![{heading}]({image})',''];md.extend(f'![{heading}]({detail})\n'for detail in images[1:]);rows=[]
   if refs:
    md+=['| 位号 | 数值 | 封装 | 安装面 |'if zh else'| Reference | Value | Package | Side |','|---|---|---|---|']
    for ref in refs:
     b=bom[ref];f=data['parts'][ref];side=('正面'if f['side']=='front'else'背面')if zh else f['side'];vals=[ref,b['Design value'],b['Package'],side];md.append('| '+' | '.join(vals)+' |');rows.append('<tr>'+''.join('<td>'+html.escape(v)+'</td>'for v in vals)+'</tr>')
    md.append('')
   table='<table><thead><tr>'+''.join('<th>'+x+'</th>'for x in (['位号','数值','封装','安装面']if zh else['Reference','Value','Package','Side']))+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table>'if rows else''
   def image_html(name):
    import re
    dims=[float(v)for v in re.search(r'viewBox="([^"]+)"',(OUT/name).read_text()).group(1).split()];height=round(1200*dims[3]/dims[2])
    return '<a href="'+name+'"><img src="'+name+'" width="1200" height="'+str(height)+'" alt="'+heading+'"></a>'
   overviewhtml=image_html(image)
   detailhtml=''.join(image_html(d)for d in images[1:])
   articles.append(f'<section id="step-{step["id"]}"><h2>{step["id"]} / {heading}</h2><p>{html.escape(body)}</p>{overviewhtml}<div class="details">{detailhtml}</div>{table}</section>')
  sources=[('TI BQ24074','https://www.ti.com/lit/ds/symlink/bq24074.pdf'),('TI TPS63031','https://www.ti.com/lit/ds/symlink/tps63031.pdf'),('SEGGER J-Link Commander','https://kb.segger.com/J-Link_Commander')]
  md+=['## '+('关联说明与资料'if zh else'Related instructions and sources'),'','[NiZ / plate](../../build/key-mechanism'+suffix+'.md) · [Firmware](../../testing/e73-corner-firmware'+suffix+'.md)','',*('['+n+']('+u+')'for n,u in sources),''];p=OUT/('soldering'+suffix+'.md');p.write_text('\n'.join(md));outputs[str(p.relative_to(ROOT))]=sha(p)
  navhtml=''.join('<a href="#step-'+s['id']+'">'+s['id']+' '+s['zh'if zh else'en']+'</a>'for s in cfg['steps']);page=f'''<!doctype html><html lang="{lang}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} / YETI60</title><style>body{{margin:0;background:#eeede6;color:#203128;font:17px/1.7 Georgia,"Noto Serif CJK SC",serif}}main{{max-width:1160px;margin:auto;padding:40px 24px}}header{{border-top:7px solid #203128;padding-top:15px;display:flex;justify-content:space-between}}h1{{font-size:clamp(32px,5vw,64px);line-height:1.15}}h2{{font-size:28px;line-height:1.3}}a{{color:inherit;text-underline-offset:4px}}.intro{{border-left:4px solid #ae4828;padding:12px 20px}}nav{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:30px 0}}section{{border-top:1px solid #aeb8ab;padding:22px 0 45px}}img{{width:100%;height:auto;display:block;background:white;margin:18px 0}}.details{{display:flex;gap:20px;flex-wrap:wrap}}.details a{{flex:1 1 400px;max-width:700px}}table{{border-collapse:collapse;width:100%;font:13px/1.5 monospace}}td,th{{text-align:left;padding:9px;border-bottom:1px solid #ccd0c5;overflow-wrap:anywhere}}@media(max-width:700px){{nav{{grid-template-columns:1fr}}main{{padding:24px 15px}}table{{font-size:10px}}}}@media print{{nav{{display:none}}section{{break-inside:avoid}}}}</style><main><header><strong>YETI60 / E73 / CORNER-07</strong><a href="soldering{''if zh else'.zh-CN'}.html">{'English'if zh else'中文'}</a></header><h1>{title}</h1><p class="intro">{intro}</p><nav>{navhtml}</nav>{''.join(articles)}<p><a href="../../build/key-mechanism{suffix}.md">{'NiZ／定位板装配'if zh else'NiZ / plate assembly'}</a> · <a href="../../testing/e73-corner-firmware{suffix}.md">{'固件与刷写'if zh else'Firmware installation'}</a></p><footer>{' · '.join('<a href="'+u+'">'+n+'</a>'for n,u in sources)}</footer></main></html>''';p=OUT/('soldering'+suffix+'.html');p.write_text(page);outputs[str(p.relative_to(ROOT))]=sha(p)
 keys_path=ROOT/'docs/audit/yeti60-key-geometry.json';keys=json.loads(keys_path.read_text())['matches'];assert len(keys)==60 and len({(k['row'],k['col'])for k in keys})==60
 p=OUT/'calibration-keys.csv'
 with p.open('w',newline='')as f:
  writer=csv.writer(f,lineterminator='\n');writer.writerow(['Index','Row','Column','Electrode','Plate_X_mm','Plate_Y_mm'])
  for key in keys:writer.writerow([key['index'],key['row'],key['col'],key['electrode'],*key['plate_center_case_mm']])
 outputs[str(p.relative_to(ROOT))]=sha(p)
 for zh in [False,True]:
  title='校准坐标：正面观察，标签为行／列'if zh else'Calibration coordinates: front view, labels are row/column'
  svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="70 100 290 101"><rect x="70" y="100" width="290" height="101" fill="#f7f6f0"/><text x="74" y="105" font-family="sans-serif" font-size="3">{title}</text>']
  for key in keys:
   x,y=key['plate_center_case_mm'];y=-y;svg.append(f'<g><title>{key["electrode"]} / {key["row"]},{key["col"]}</title><circle cx="{x}" cy="{y}" r="6.2" fill="#dbe5d8" stroke="#657a68" stroke-width=".2"/><text x="{x}" y="{y+.8}" text-anchor="middle" font-family="monospace" font-size="2.5">{key["row"]},{key["col"]}</text></g>')
  svg.append('</svg>');p=image_dir/('calibration'+('.zh-CN'if zh else'')+'.svg');p.write_text('\n'.join(svg)+'\n');outputs[str(p.relative_to(ROOT))]=sha(p)
 subprocess.run([sys.executable,str(ROOT/'tests/audit/test_e73_solder_guide.py')],check=True)
 report=dict(status='native-map-soldering-guide-generated-physical-open',physical_verification=False,placed_exactly_once=75,regression_tests=6,calibration_positions=60,stage_references={s['id']:sorted(groups[s['group']])for s in cfg['steps']},source_sha256={str(p.relative_to(ROOT)):sha(p)for p in [data_path,content,keys_path,ROOT/'tests/audit/test_e73_solder_guide.py',BASE/'EC60-nRF52840.kicad_pcb',BASE/'mainboard-purchase.csv',Path(__file__)]},outputs=outputs,limits=['No physical solder, power, battery or radio acceptance','Physical harness insertion and withdrawal remain open'])
 (BASE/'audit/solder-guide.json').write_text(json.dumps(report,indent=2)+'\n');print('75 parts assigned exactly once; bilingual diagrams, Markdown and HTML generated')
if __name__=='__main__':main()
