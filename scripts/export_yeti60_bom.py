#!/usr/bin/env python3
"""Export grouped purchase requirements from the current native schematic contract."""
import csv,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hardware/bom';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(ref):return (re.sub(r'\d','',ref),int(re.search(r'\d+',ref)[0]))
def main():
 net=ROOT/'hardware/ec60-nrf52840/netlist.xml';meta=ROOT/'hardware/ec60-nrf52840/metadata-audit.json';skip=set(json.loads(meta.read_text())['non_purchased_geometry_references']);groups={};omitted=[]
 special={
 'U1':('Ebyte E73-2G4M08S1C','Exact module; supplier order code and certification suffix to confirm','指定模组；订货后缀及认证版本须确认'),
 'U2':('Nexperia 74HC4051PW,118','TSSOP16 HC, not HCT; candidate MPN against native footprint','TSSOP16、HC 系列，不能用 HCT；候选型号须按原生焊盘复核'),
 'U4':('Nexperia 74HC4051PW,118','TSSOP16 HC, not HCT; candidate MPN against native footprint','TSSOP16、HC 系列，不能用 HCT；候选型号须按原生焊盘复核'),
 'U3':('TI OPA350UA','SOIC-8; do not substitute dual OPA2350 or MSOP','SOIC-8；不能替换为双路 OPA2350 或 MSOP 封装'),
 'U5':('TI BQ24074RGTR','VQFN16 RGT; thermal pad soldering and P2 ISET/TMR/ITERM setup required','RGT 封装 VQFN16；须焊接散热焊盘并按 P2 充电电流／计时／终止电流方案设置'),
 'U6':('TI TPS63031DSKR','Fixed 3.3 V DSK; not adjustable TPS63030','DSK 封装固定 3.3 V；不能直接用可调 TPS63030'),
 'U7':('TI TPS22919DCKR','SC70-6; confirm exact reel suffix','SC70-6；确认编带订货后缀'),
 'U8':('TI TPS22919DCKR','SC70-6; confirm exact reel suffix','SC70-6；确认编带订货后缀'),
 'L1':('Wurth 74438336015','1.5 uH MAPI-3015; validate saturation, DCR and regulator loop','1.5 µH、MAPI-3015；确认饱和电流、直流电阻及稳压环路'),
 'D1':('Nexperia PRTR5V0U2X','SOT143; native pinout required','SOT143；须保持原生引脚顺序'),
 'D2':('0603 status LED; vendor MPN unselected','No backlight LEDs; polarity per schematic, Vf/current to confirm','不是背光灯；极性按原理图，正向电压和电流待确认'),
 'J1':('JST SM04B-SRSS-TB(LF)(SN), candidate','1 mm right angle; inherited 1.0T-4P pad/retention geometry must be checked before order','1 mm 卧贴；下单前须复核继承的 1.0T-4P 焊盘及固定脚'),
 'J2':('JST S3B-PH-SM4-TB(LF)(SN)','2 mm side entry, 3 pins; polarity is custom','2 mm 卧贴、三针；本项目线序为自定义'),
 'F1':('1206 resettable fuse, 0.5 A hold','Vendor MPN unselected; rated voltage >= 6 V, trip/derating to confirm','厂商型号待选；耐压不低于 6 V，须确认动作电流及温度降额'),
 'SW1':('Panasonic EVQPUC02K','Reset tactile switch; verify supplier drawing','复位轻触开关；按厂商图纸复核'),
 'SW100':('C&K JS102011SAQN','Power slide switch; underside service access','电源拨动开关；从底部检修孔操作'),
 'JP1':('DNP','Leave open: R16/R17 already set gain 101; do not fit a zero-ohm short','默认不装；R16／R17 已设增益 101，不能短接为零欧姆')}
 for c in ET.parse(net).getroot().findall('./components/comp'):
  ref=c.get('ref');fp=c.findtext('footprint') or ''
  if not fp or ref in skip:omitted.append(ref);continue
  value=c.findtext('value');package=re.sub(r'__[^_]+$','',fp.split(':')[-1]);qty=0 if ref=='JP1' else 1
  if ref in special:mpn,en,zh=special[ref]
  elif ref.startswith('R'):mpn='Vendor MPN unselected';en='0402, 1%, >= 50 mW; 0 ohm links where specified';zh='0402、1%、不低于 50 mW；零欧姆位置须按指定值'
  elif ref.startswith('C'):
   mpn='Vendor MPN unselected';en='220 pF: C0G; others: X7R/X5R, 10% or better, >= 10 V (16 V where specified); validate effective capacitance at DC bias';zh='220 pF 用 C0G；其余用 X7R／X5R、10% 或更优、不低于 10 V（标注 16 V 处按 16 V）；须验证直流偏压下有效容量'
  else:raise AssertionError('Unclassified purchased component '+ref)
  k=(value,package,mpn,en,zh);g=groups.setdefault(k,{'refs':[],'quantity':0});g['refs'].append(ref);g['quantity']+=qty
 rows=[]
 for (v,p,m,en,zh),g in groups.items():rows.append({'references':', '.join(sorted(g['refs'],key=key)),'quantity':g['quantity'],'value':v,'package':p,'candidate_mpn':m,'notes_en':en,'notes_zh':zh})
 rows.sort(key=lambda x:key(x['references'].split(',')[0]));assert sum(x['quantity'] for x in rows)==76
 for zh in [False,True]:
  path=OUT/('mainboard.zh-CN.csv' if zh else 'mainboard.csv')
  with path.open('w',newline='') as f:
   w=csv.writer(f,lineterminator="\n");w.writerow(['位号','数量','设计值','封装','指定或候选型号','要求'] if zh else ['References','Quantity','Design value','Package','Specified or candidate MPN','Requirements'])
   for r in rows:w.writerow([r['references'],r['quantity'],r['value'],r['package'],(r['candidate_mpn'].replace('Vendor MPN unselected','厂商型号待选').replace('0603 status LED; vendor MPN unselected','0603 指示灯，厂商型号待选').replace('1206 resettable fuse, 0.5 A hold','1206 自恢复保险丝，保持电流 0.5 A').replace(', candidate','，候选') if zh else r['candidate_mpn']),r['notes_zh' if zh else 'notes_en']])
 report={'outputs':{str(p.relative_to(ROOT)):sha(p) for p in [OUT/'mainboard.csv',OUT/'mainboard.zh-CN.csv']},'status':'purchase-requirements-exported-not-order-release','fitted_mainboard_parts':76,'unpopulated_sites':['JP1'],'excluded_geometry_and_fixture_references':sorted(omitted),'rows':rows,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [net,meta,ROOT/'mechanical/assembly-spec.json',Path(__file__).resolve()]},'limits':['No stock or price assumptions','Candidate MPNs and passive effective capacitance require supplier qualification','60 mechanical key assemblies are external to the PCB BOM']}
 (ROOT/'docs/audit/yeti60-bom.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print('76 fitted mainboard components; JP1 DNP; virtual electrodes and fixtures excluded')
if __name__=='__main__':main()
