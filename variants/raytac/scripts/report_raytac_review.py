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
 files=['outcome.json','integration.json','schematic-current.json','yeti60-target-check.json','yeti60-firmware-simulation.json','yeti60-ordinary-process.json','C5-protection.json','USB-signal-paths.json','interference-layout.json','complete-exploded.json','yeti60-assembly.json','yeti60-inventory.json','plate-mount.json','key-mechanism-drawing.json','yeti60-materials.json','calibration.json','yeti60-power-budget.json','prototype-research.json']
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
        'NiZ ordinary housings/sliders and separate Cherry plate-mounted stabilizers selected; 1.6 mm plate, 28 mounts and H26 unused; 60 sensing centers and exterior preserved; actual wire/clip/stroke fit awaits a first article',
        'Second review corrected stale 29-fastener inventory/acceptance prose and 1.2 mm render descriptions in both languages; negative tests now reject their return',
        'Current RF status distinguishes passing minimum antenna-copper clearance from unqualified USB signal integrity and enclosed RF; historical reviews remain labeled snapshots',
        'Broken tracked Raytac third_party/zmk link repaired to the pinned repository submodule; all tracked shared links now checked and missing-source fault injected']
 paths=evidence['USB-signal-paths.json']['variants']['raytac']
 usb_review={'positive_trace_mm':paths['positive']['actual_trace_centerline_mm'],'negative_trace_mm':paths['negative']['actual_trace_centerline_mm'],'positive_vias':paths['positive']['via_count'],'negative_vias':paths['negative']['via_count'],'geometric_contact_path_difference_mm':paths['geometric_path_difference_mm'],'scope':'Mainboard only; excludes C5, harness, connectors and module internals; not propagation delay, impedance or an eye result','acceptance':'open; qualify complete return/coupling and full-speed USB with the final harness before manufacturing release'}
 report={'review_scope':'Current Raytac native CAD, built firmware, host tests, assembly and deliverable provenance; E73 excluded','review_timestamp_UTC':datetime.now(timezone.utc).isoformat(),'status':'software-and-CAD-consistency-reviewed','audit_stages_passed':count,'DRC_errors':sum(cad['drc_errors_by_type'].values()),'opens':cad['unconnected_items'],'physical_signal_pairs':len(cad['physical_pin_pairs']),'DRC_warnings':cad['warnings_by_type'],'ERC_counts':erc,'through_vias':ordinary['through_vias'],'mainboard_parts':75,'planned_stock':inventory['planned_stock_parts'],'net_purchase':inventory['net_purchase_parts'],'fixed_findings':notes,'physical_verification':False,'manufacturing_order_released':False,'production_approved':False,'open_requirements':evidence['outcome.json']['open_requirements'],'evidence_sha256':{n:sha(AUD/n) for n in files},'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb',ROOT/'mechanical/rf-remediation.json',ROOT/'renders/yeti60-assembly/render-manifest.json']}}
 report['USB_route_review']=usb_review
 report['functional_acceptance_passed']=False
 report['firmware_rebuilt_this_mechanical_review']=False
 candidate=ROOT/'hardware/usb-short-route'
 short=read(candidate/'audit/native-check.json');local=read(candidate/'audit/geometry-check.json');built=read(candidate/'firmware/manifest.json')
 report['review_scope']='Canonical Raytac plus isolated short-USB repair candidate; E73 excluded; canonical images/order archive do not describe candidate cables'
 report['USB_repair_candidate']={'native_checks':short['status'],'physical_pin_pairs_checked':short['physical_pin_pairs_checked'],'USB_contact_path_mm_per_leg':short['USB_positive_contact_path_mm'],'USB_data_vias_per_leg':0,'adjacent_GND_centerline_coverage':{k:local['USB_reference_screen'][k]['nearest_adjacent_GND_coverage_fraction'] for k in ['positive','negative']},'firmware_rebuilt':True,'firmware_status':built['status'],'fitted_parts':75,'planned_stock':8,'net_purchase':67,'complete_cable_geometry_and_assembly_illustrations':'open','manufacturing_released':False,'physical_verification':False,'evidence_sha256':{str(v.relative_to(ROOT)):sha(v) for v in [candidate/'audit/native-check.json',candidate/'audit/geometry-check.json',candidate/'firmware/manifest.json']}}
 report['tracked_shared_links']=evidence['integration.json']['shared_links']
 report['bare_board_order_ready']=evidence['prototype-research.json']['bare_board_order_ready']
 report['new_open_design_findings']=evidence['prototype-research.json']['blocking_design_findings']
 (AUD/'raytac-review.json').write_text(json.dumps(report,indent=2)+'\n')
 for zh in [False,True]:
  suffix='.zh-CN' if zh else '';peer='raytac-review.md' if zh else 'raytac-review.zh-CN.md'
  head=f'[English]({peer}) | 简体中文' if zh else f'English | [Chinese]({peer})'
  title='Raytac 本轮审查结论' if zh else 'Raytac review conclusions'
  body=(f'**{count} 个软件／CAD 审查阶段全部通过；尚未放行生产或证明实物工作。** 本轮只覆盖 Raytac，不把旧双方案报告当作本版验收。' if zh else f'**All {count} implemented software/CAD audit stages passed. Manufacturing and physical operation are not approved.** This review covers Raytac only, not the old dual-option report.')
  rows=[['PCB',f"0 errors / 0 opens; {len(cad['physical_pin_pairs'])} signal pairs",f"0 错误／0 断线；{len(cad['physical_pin_pairs'])} 对信号连接"],['DRC',f"102 disclosed noncomponent courtyard warnings",'保留 102 条非实装图形 courtyard 告警'],['ERC',f"0 errors; {erc.get('warning',0)} inherited off-grid warnings",f"0 错误；{erc.get('warning',0)} 条继承离网格告警"],['JLC',f"{ordinary['through_vias']} ordinary through vias; >=0.50/0.30 mm land/drill",f"{ordinary['through_vias']} 个普通机械通孔，盘／孔不小于 0.50／0.30 mm"],['USB / BLE','Normal/calibrator ARM builds and USB500 descriptors checked; simultaneous charge/wired-priority policy host-tested','普通版／校准版 ARM 构建及 USB500 描述符通过；同时充电与 USB 优先策略已做主机回归'],['RF','All four layers clear in vendor minimum antenna projection; physical RF open','厂商最小天线投影内四层铜均清空；实际射频待测'],['BOM','75 parts; 10 planned from stock, 65 net purchases','主板 75 件；计划用库存 10 件，净补购 65 件']]
  lines=[head,'','# '+title,'',body,'','| 范围 | 结果 |' if zh else '| Area | Result |','|---|---|']+[f'| {tag} | {cn if zh else en} |' for tag,en,cn in rows]
  lines+=['',('**新增首样阻塞项：长 USB 线路配对／回流须修补，保护电池包尚未获确认；逐网确认 C47 电池滤波的名义 RC 时序通过，C48 是模拟电源去耦。新增研究检查通过只证明分析可复现，不代表问题已修复。** 请先看[含电池的无外壳流程](../../OPEN-BENCH.zh-CN.md)和[详细研究](../engineering/prototype-qualification.zh-CN.md)。' if zh else '**New prototype blockers: repair long USB pairing/reference routing and qualify battery protection. Actual nets confirm that C47 battery-filter settling passes nominally; C48 is AFE rail decoupling. Passing research stages establishes reproducible analysis, not repaired hardware.** See the [open-bench guide including a battery](../../OPEN-BENCH.md) and [detailed findings](../engineering/prototype-qualification.md).')]
  lines+=['','## 修补与图像复核' if zh else '## Repairs and image inspection','']
  repaired=(['C5 的真实保护通道和接地核对后，删除主板重复 D1 与长 USB 支线，保留 C5 必装的 D1／U1／F1。','共享模拟／放电总线标签统一；新导出网表与保存的引脚合同一致。','材料、库存、焊接步骤、实装坐标与编号图同步为 75 件。','完整三维爆炸图展示电池、七根线、电子元件及机械层；脚垫／胶棉托盘加入桌面高度和画面边界校验。','已改用 NiZ 普通轴座滑块及独立 Cherry 钢板卫星轴；新板 1.6 mm、28 个安装点，H26 不装；保留 60 个感应中心和外形，实际钢丝、卡扣及全行程须首件确认。','再次审查修正库存／验收页的旧 29 套五金及渲染说明中的旧 1.2 mm 板厚；中英文均增加错误注入检查，防止回退。','现行射频状态明确区分：最小天线铜区检查通过，USB 信号完整性及关壳射频仍待验收；历史审查保留为已标注的快照。'] if zh else notes)
  if zh:repaired.append('修复 Raytac 的 third_party/zmk 失效软链接，使其指向仓库固定版本子模块；新增全部受控软链接检查和缺失来源负向测试。')
  lines+=['- '+v for v in repaired]
  lines+=['','## 功能核对与测试边界' if zh else '## Functional coverage and test boundaries','']
  coverage=[
   ('60-key scan / 60 键扫描', '[Geometry/map](yeti60-key-geometry.json); host core tests all 75 matrix positions, hysteresis, debounce and ADC frame abort. Real EC waveforms remain unmeasured.', '[几何及映射](yeti60-key-geometry.json)覆盖 60 键；主机核心覆盖 75 个矩阵位置、迟滞、消抖及 ADC 故障整帧撤销。真实静电容波形未测。'),
   ('Calibration / 校准', '[Guard tests](calibration.json); inspect the target release/press/save flow, 128-frame capture, saturation/overlap rejection and persistent thresholds. First-article capture and flash retention remain open.', '[保护区间测试](calibration.json)及目标代码核对覆盖松键／持按／保存、128 帧采样、饱和／重叠拒绝和阈值持久化；真实采样与刷写保留设置仍待验收。'),
   ('USB priority / USB 优先', '[Actual adapter host regression](yeti60-firmware-simulation.json) covers configured charging plus USB preference, retained BLE preference, suspend/resume/reset/detach and failure retries. USB/BLE interfaces are mocks.', '[实际适配层主机回归](yeti60-firmware-simulation.json)覆盖配置后充电并优先 USB、历史 BLE 偏好、挂起／恢复／复位／拔线和失败重试；USB／BLE 接口为模拟。'),
   ('Power / 供电', '[Current/timer arithmetic](yeti60-power-budget.json), enable-net and adapter review agree with BQ24074 input modes. Off-state USB100 charging differs from firmware-controlled charging. Actual thermal/current behavior remains open.', '[电流和定时计算](yeti60-power-budget.json)、控制网络与适配层符合 BQ24074 输入模式；关机自主 USB100 慢充与固件运行时策略不同。实际温度／电流仍待验收。'),
   ('Firmware / 固件', '[Existing normal/calibrator ARM artifacts](yeti60-target-check.json) rechecked against current source hashes, flash ranges and linked USB500 descriptors. No firmware source changed or rebuild was required in this mechanical review; this is not target execution.', '[已有普通版／校准版 ARM 产物](yeti60-target-check.json)再次核对当前来源哈希、刷写范围和已链接 USB500 描述符；本次机械审查未改固件源码、未重新构建，不代表执行过目标固件。'),
   ('Assembly / 装配', '[Native fit](yeti60-assembly.json), [plate](plate-mount.json), 28 mounts / H26 omission, 1.6 mm plate, seven conductors and image provenance checked. Actual NiZ skirts/clips, 6U bends, preload and local stiffness remain open.', '[原生装配](yeti60-assembly.json)、[新钢板](plate-mount.json)、28 套五金／H26 留空、1.6 mm 板厚、七根线及图像来源已核对；NiZ 下裙边／卡扣、6U 弯形、预压和局部刚度待实物验收.'),
  ]
  lines+=['| 功能 | 本轮证据与尚未证明的部分 |' if zh else '| Function | Evidence and remaining boundary |','|---|---|']
  for label,en,cn in coverage:
   label=label.split(' / ')[1 if zh else 0]
   lines.append(f'| {label} | {cn if zh else en} |')
  lines+=['','## 独立的 USB 修补候选板' if zh else '## Isolated USB repair candidate','']
  lines.append(('上述原目录的 PCB、库存与七根线装配图仍对应原布线。新[修补候选板](../../hardware/usb-short-route/README.zh-CN.md)另行通过严格原生检查及 411 组实际连接检查；两路接触路径均为 5.286396 mm，无数据过孔，相邻层地铜中心线投影覆盖率均为 100%。新插座／胶壳局部公差检查及两版固件重建、主机模拟、校准测试通过。候选板仍装 75 件，计划用库存 8 件、补购 67 件，共九根导线。完整关壳线束、理线件、装配图和实物验收尚未完成，不能据此放行原制板压缩包。下节长线路数值继续用于说明原目录的限制。' if zh else 'The canonical PCB, inventory and seven-wire assembly images above still describe the previous routing. The separate [repair candidate](../../hardware/usb-short-route/README.md) passed strict native checks and 411 physical pin-pair checks. Both contact paths are 5.286396 mm, with zero data vias and 100% adjacent-ground centerline coverage. Local header/housing tolerance checks, both rebuilt targets, host simulation and calibration tests passed. The candidate fits 75 parts, credits 8 stock parts and requires 67 purchases, with nine conductors total. Complete enclosed cables, guides, assembly illustrations and physical acceptance remain open. This does not release the canonical fabrication archive. The long-route values below continue to document the canonical routing limitation.'))
  lines+=['','## USB 布线的具体限制' if zh else '## Specific USB routing limitation','']
  lines.append((f"主板 D+／D− 实际线段中心线分别约 **{usb_review['positive_trace_mm']:.3f}／{usb_review['negative_trace_mm']:.3f} mm**，经过 **{usb_review['positive_vias']}／{usb_review['negative_vias']} 个过孔**。含焊盘接入等桥接的几何接触路径差为 **{usb_review['geometric_contact_path_difference_mm']:.3f} mm**；它不是传播延迟差。这里未包含 C5、线束、连接器内部和模组内部。保护导通及 DRC 通过不能证明差分阻抗、回流连续性、共模或 USB 眼图通过；发布制造前需审查完整链路，并在最终线束下实测。" if zh else f"Mainboard D+ / D− actual trace centerlines are approximately **{usb_review['positive_trace_mm']:.3f} / {usb_review['negative_trace_mm']:.3f} mm**, through **{usb_review['positive_vias']} / {usb_review['negative_vias']} vias**. The pad-access/contact-bridge geometric path difference is **{usb_review['geometric_contact_path_difference_mm']:.3f} mm**, not propagation-delay skew. C5, harness, connector and module internals are excluded. Protected connectivity and DRC do not establish differential impedance, continuous return, common-mode behavior or a passing USB eye. Review the complete link and measure it with the final harness before manufacturing release."))
  lines+=['',('[充电器原厂资料](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [稳压器原厂资料](https://www.ti.com/lit/ds/symlink/tps63031.pdf)。数据手册复核不能代替本板波形和温升实测。' if zh else '[Charger primary datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [Regulator primary datasheet](https://www.ti.com/lit/ds/symlink/tps63031.pdf). Datasheet review does not replace board waveform or thermal measurements.')]
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
