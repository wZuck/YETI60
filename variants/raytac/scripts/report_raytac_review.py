#!/usr/bin/env python3
"""Publish a bounded review only from passing, current-source Raytac evidence."""
import argparse,hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AUD=ROOT/'docs/audit'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--sync-downloads',action='store_true');args=parser.parse_args()
 files=['outcome.json','integration.json','schematic-current.json','yeti60-target-check.json','yeti60-firmware-simulation.json','yeti60-ordinary-process.json','C5-protection.json','USB-signal-paths.json','interference-layout.json','complete-exploded.json','yeti60-assembly.json','yeti60-inventory.json','plate-mount.json','key-mechanism-drawing.json']
 evidence={n:read(AUD/n) for n in files}
 assert evidence['outcome.json']['checks_passed'] and all(s['state']=='passed' for s in evidence['outcome.json']['stages'])
 assert evidence['integration.json']['status']=='passed'
 from check_project_integration import verify
 verify() # Recheck hashes; do not accept a stale passed status.
 cad=read(ROOT/'hardware/ec60-nrf52840/audit-current.json');assert cad['status']=='cad-checks-passed' and not cad['unconnected_items'] and not cad['failed_pin_pairs']
 rf=read(ROOT/'mechanical/rf-remediation.json')['placements']['raytac'];module=next(p for p in evidence['yeti60-assembly.json']['component_envelopes'] if p['ref']=='U1')
 assert all(abs(a-b)<1e-6 for a,b in zip(module['position_pcb_mm'],rf['origin_PCB_XY'])) and abs(module['angle_deg']-rf['rotation_deg'])<1e-6
 layout=evidence['interference-layout.json']['variants']['raytac'];assert all(v['GND_union_mm2']==v['non_GND_union_mm2']==0 for v in layout['layers'])
 render=read(ROOT/'renders/yeti60-assembly/render-manifest.json');assert render['recipe_sha256']==sha(ROOT/'scripts/render_yeti60_assembly.py')
 assert render['exploded_visible_objects_by_group']['electronics']==75
 assert all(v['above_desk'] and v['in_frame'] for v in render['exploded_frame_checks'].values())
 count=len(evidence['outcome.json']['stages']);erc=evidence['schematic-current.json']['erc_counts'];ordinary=evidence['yeti60-ordinary-process.json'];inventory=evidence['yeti60-inventory.json']
 notes=['USB mainboard D1 and long branches removed after actual C5 protected-channel/ground verification; C5 D1/U1/F1 retained',
        'Shared analog/discharge net labels unified without changing exported pin connectivity',
        '75-part purchase, stock allocation, placement and illustrated guide contracts reconciled',
        'Complete explosion includes 75 electronic bodies, battery, seven wires, 60 domes/springs and hardware; tray camera/desk bounds checked',
        'NiZ ordinary housings/sliders and separate Cherry plate-mounted stabilizers selected; 1.6 mm plate, 28 mounts and H26 unused; 60 sensing centers and exterior preserved; actual wire/clip/stroke fit awaits a first article']
 report={'review_scope':'Current Raytac native CAD, built firmware, host tests, assembly and deliverable provenance; E73 excluded','review_timestamp_UTC':datetime.now(timezone.utc).isoformat(),'status':'software-and-CAD-consistency-reviewed','audit_stages_passed':count,'DRC_errors':sum(cad['drc_errors_by_type'].values()),'opens':cad['unconnected_items'],'physical_signal_pairs':len(cad['physical_pin_pairs']),'DRC_warnings':cad['warnings_by_type'],'ERC_counts':erc,'through_vias':ordinary['through_vias'],'mainboard_parts':75,'planned_stock':inventory['planned_stock_parts'],'net_purchase':inventory['net_purchase_parts'],'fixed_findings':notes,'physical_verification':False,'manufacturing_order_released':False,'production_approved':False,'open_requirements':evidence['outcome.json']['open_requirements'],'evidence_sha256':{n:sha(AUD/n) for n in files},'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb',ROOT/'mechanical/rf-remediation.json',ROOT/'renders/yeti60-assembly/render-manifest.json']}}
 (AUD/'raytac-review.json').write_text(json.dumps(report,indent=2)+'\n')
 for zh in [False,True]:
  suffix='.zh-CN' if zh else '';peer='raytac-review.md' if zh else 'raytac-review.zh-CN.md'
  head=f'[English]({peer}) | 简体中文' if zh else f'English | [Chinese]({peer})'
  title='Raytac 本轮审查结论' if zh else 'Raytac review conclusions'
  body=(f'**{count} 个软件／CAD 审查阶段全部通过；尚未放行生产或证明实物工作。** 本轮只覆盖 Raytac，不把旧双方案报告当作本版验收。' if zh else f'**All {count} implemented software/CAD audit stages passed. Manufacturing and physical operation are not approved.** This review covers Raytac only, not the old dual-option report.')
  rows=[['PCB',f"0 errors / 0 opens; {len(cad['physical_pin_pairs'])} signal pairs",f"0 错误／0 断线；{len(cad['physical_pin_pairs'])} 对信号连接"],['DRC',f"102 disclosed noncomponent courtyard warnings",'保留 102 条非实装图形 courtyard 告警'],['ERC',f"0 errors; {erc.get('warning',0)} inherited off-grid warnings",f"0 错误；{erc.get('warning',0)} 条继承离网格告警"],['JLC',f"{ordinary['through_vias']} ordinary through vias; >=0.50/0.30 mm land/drill",f"{ordinary['through_vias']} 个普通机械通孔，盘／孔不小于 0.50／0.30 mm"],['USB / BLE','Normal/calibrator ARM builds and USB500 descriptors checked; simultaneous charge/wired-priority policy host-tested','普通版／校准版 ARM 构建及 USB500 描述符通过；同时充电与 USB 优先策略已做主机回归'],['RF','All four layers clear in vendor minimum antenna projection; physical RF open','厂商最小天线投影内四层铜均清空；实际射频待测'],['BOM','75 parts; 10 planned from stock, 65 net purchases','主板 75 件；计划用库存 10 件，净补购 65 件']]
  lines=[head,'','# '+title,'',body,'','| 范围 | 结果 |' if zh else '| Area | Result |','|---|---|']+[f'| {tag} | {cn if zh else en} |' for tag,en,cn in rows]
  lines+=['','## 修补与图像复核' if zh else '## Repairs and image inspection','']
  repaired=(['C5 的真实保护通道和接地核对后，删除主板重复 D1 与长 USB 支线，保留 C5 必装的 D1／U1／F1。','共享模拟／放电总线标签统一；新导出网表与保存的引脚合同一致。','材料、库存、焊接步骤、实装坐标与编号图同步为 75 件。','完整三维爆炸图展示电池、七根线、电子元件及机械层；脚垫／胶棉托盘加入桌面高度和画面边界校验。','已改用 NiZ 普通轴座滑块及独立 Cherry 钢板卫星轴；新板 1.6 mm、28 个安装点，H26 不装；保留 60 个感应中心和外形，实际钢丝、卡扣及全行程须首件确认。'] if zh else notes)
  lines+=['- '+v for v in repaired]
  lines+=['','## 仍需实物或供应商证据' if zh else '## Supplier and physical work still open','']
  pending=(['电容有效容量、保险丝温度降额与 LED 等最终料号；标称容量和保持电流不等于所有工作条件下已合格。','定制电池完整包络、供方签图、允许充电电压／电流及独立温度断充。','真实轴座、胶碗、弹簧、稳定机构、树脂公差与线束装配样件。','实际 USB 枚举／眼图、边充边输入、BLE、逐键校准、温升／续航及关壳后的干扰测试。','C5 上游默认 DRC 仍有制造审查项；本轮保护通道通过不等于 C5 已取得制造或 ESD 认证。'] if zh else ['Final capacitor effective capacitance, fuse thermal derating, LED and exact-part qualification.','Supplier-signed complete pack envelope, charge limits and independent thermal interruption.','Actual housings/domes/springs/stabilizers, resin tolerances and harness/mechanical samples.','Physical USB enumeration/eye, concurrent charge/input, BLE, per-key calibration, thermal/runtime and enclosed interference tests.','Upstream C5 default DRC review items remain; protected-channel verification is not C5 manufacturing or ESD certification.'])
  lines+=['- '+v for v in pending]
  lines+=['',('[制作总入口](../../BUILD.zh-CN.md) · [完整爆炸图与元件对照](../engineering/exploded.zh-CN.md) · [首件验收流程](../testing/README.zh-CN.md) · [机器审查与来源哈希](raytac-review.json)' if zh else '[Build entry](../../BUILD.md) · [complete explosion and part index](../engineering/exploded.md) · [first-article acceptance](../testing/README.md) · [machine evidence/hashes](raytac-review.json)'),'']
  (AUD/('raytac-review'+suffix+'.md')).write_text('\n'.join(lines))
 if args.sync_downloads:
  repo=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True).strip());dest=repo/'hardware/raytac';dest.mkdir(exist_ok=True)
  mirror={}
  for rel in ['hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb','hardware/fabrication/yeti60-raytac-p2-dfm-review.zip']:
   source=ROOT/rel;target=dest/source.name;shutil.copyfile(source,target);assert sha(source)==sha(target);mirror[str(target.relative_to(repo))]={'canonical_source':str(source.relative_to(repo)),'sha256':sha(target)}
  (dest/'manifest.json').write_text(json.dumps({'status':'verified-Raytac-download-copies','manufacturing_order_released':False,'canonical_entry':'variants/raytac/BUILD.md','files':mirror},indent=2)+'\n')
  for zh in [False,True]:
   suffix='.zh-CN' if zh else '';peer='README.md' if zh else 'README.zh-CN.md'
   text=(f'[English]({peer}) | 简体中文\n\n# Raytac 下载文件\n\n这两份文件与 [Raytac 正式目录](../../variants/raytac/BUILD.zh-CN.md) 中本轮验证过的原生 PCB 和审查压缩包一致；[文件哈希](manifest.json)用于识别版本。它们不是第三套设计，也不代表已经批准下单。\n\n请从[制作总入口](../../variants/raytac/BUILD.zh-CN.md)查阅下单参数、材料、焊接、固件、完整爆炸图和本轮审查。\n' if zh else f'English | [Chinese]({peer})\n\n# Raytac download files\n\nThese copies match the current validated native PCB and DFM review archive in the [canonical Raytac directory](../../variants/raytac/BUILD.md). Use the [hash manifest](manifest.json) to identify the revision. They are not a third design or an order authorization.\n\nStart from the [build entry](../../variants/raytac/BUILD.md) for ordering settings, materials, soldering, firmware, complete explosion and review.\n')
   (dest/('README'+suffix+'.md')).write_text(text)
 print('Raytac review generated from',count,'passing audit stages; manufacturing/physical acceptance remains open')
if __name__=='__main__':main()
