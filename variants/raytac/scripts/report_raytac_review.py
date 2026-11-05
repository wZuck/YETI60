#!/usr/bin/env python3
"""Publish a bounded review only from passing, current-source Raytac evidence."""
import argparse,csv,hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AUD=ROOT/'docs/audit'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())

def candidate_summary(native, cam, assembly, purchase_rows):
 """Keep current-board scalar counts separate from detailed fit dictionaries."""
 fitted_count=sum(int(row['Required']) for row in purchase_rows)
 stock_count=sum(int(row['Planned stock use']) for row in purchase_rows)
 purchase_count=sum(int(row['Net purchase']) for row in purchase_rows)
 assert fitted_count == stock_count + purchase_count == assembly['fitted_mainboard_parts'] == cam['fitted_placements']
 assert native['physical_pin_pairs_checked'] == len(native['physical_pin_pairs'])
 assert all(pair['connected'] for pair in native['physical_pin_pairs'])
 assert set(native['DRC_warnings']) == {'missing_courtyard'}
 assert set(native['ERC_counts']) == {"('warning', 'endpoint_off_grid')"}
 return {'board':'short-USB repair candidate',
         'DRC_errors':native['strict_DRC_errors'], 'opens':native['unconnected_items'],
         'physical_signal_pairs':native['physical_pin_pairs_checked'],
         'DRC_warnings':native['DRC_warnings'], 'ERC_counts':native['ERC_counts'],
         'through_vias':cam['IPC']['via_sites_checked'],
         'CAM_drill_features':cam['drills']['total'],
         'CAM_stencil_apertures':cam['stencil']['apertures'],
         'mainboard_parts':fitted_count,'planned_stock':stock_count,'net_purchase':purchase_count,
         'assembly_conductors':assembly['conductor_count']}

def summary_rows(summary):
 for key in ['DRC_errors','opens','physical_signal_pairs','through_vias','CAM_drill_features',
             'CAM_stencil_apertures','mainboard_parts','planned_stock','net_purchase','assembly_conductors']:
  assert type(summary[key]) is int and summary[key] >= 0, 'Non-scalar review count: '+key
 assert summary['mainboard_parts'] == summary['planned_stock'] + summary['net_purchase']
 pairs=summary['physical_signal_pairs'];warnings=summary['DRC_warnings']['missing_courtyard']
 erc=summary['ERC_counts']["('warning', 'endpoint_off_grid')"]
 fitted_count=summary['mainboard_parts'];stock_count=summary['planned_stock'];purchase_count=summary['net_purchase']
 return [
  ('PCB',f"{summary['DRC_errors']} errors / {summary['opens']} opens; {pairs} signal pairs",f"{summary['DRC_errors']} 错误／{summary['opens']} 断线；{pairs} 对信号连接"),
  ('DRC',f'{warnings} disclosed noncomponent courtyard warnings',f'保留 {warnings} 条非实装图形 courtyard 告警'),
  ('ERC',f'0 errors; {erc} inherited off-grid warnings',f'0 错误；{erc} 条继承离网格告警'),
  ('CAM',f"{summary['CAM_drill_features']} drill/slot features; {summary['through_vias']} via sites; {summary['CAM_stencil_apertures']} stencil apertures",f"{summary['CAM_drill_features']} 处孔槽；{summary['through_vias']} 处过孔；{summary['CAM_stencil_apertures']} 个钢网开口"),
  ('USB / BLE','Current normal/calibrator ARM artifacts and USB500 descriptors checked; simultaneous charge/wired-priority policy host-tested','普通版／校准版 ARM 产物与当前来源及 USB500 描述符一致；同时充电与 USB 优先策略已做主机回归'),
  ('BOM',f'Current candidate: {fitted_count} parts; {stock_count} planned from stock, {purchase_count} net purchases',f'当前候选板 {fitted_count} 件；计划用库存 {stock_count} 件，净补购 {purchase_count} 件'),
  ('Harness',f"Current candidate: {summary['assembly_conductors']} conductors",f"当前候选方案共 {summary['assembly_conductors']} 根导线")]

def verify_publication(report, documents, summary):
 """Read back both language tables against current CAD/CAM/BOM evidence."""
 assert report['current_candidate_summary'] == summary, 'Stale candidate summary'
 for key in ['DRC_errors','opens','physical_signal_pairs','DRC_warnings','ERC_counts','through_vias',
             'mainboard_parts','planned_stock','net_purchase']:
  assert report[key] == summary[key], 'Wrong top-level candidate count: '+key
 assert report['physical_verification'] is False and report['production_approved'] is False
 assert report['manufacturing_order_released'] is False
 rows=summary_rows(summary)
 for zh,text in documents.items():
  for tag,en,cn in rows:
   label='线束' if zh and tag=='Harness' else tag
   assert f'| {label} | {cn if zh else en} |' in text, 'Wrong review table: '+tag
  assert "{'status':" not in text, 'Detailed dictionary leaked into prose'

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--sync-downloads',action='store_true');args=parser.parse_args()
 files=['outcome.json','integration.json','schematic-current.json','yeti60-target-check.json','yeti60-firmware-simulation.json','yeti60-ordinary-process.json','C5-protection.json','USB-signal-paths.json','interference-layout.json','complete-exploded.json','yeti60-assembly.json','yeti60-inventory.json','plate-mount.json','key-mechanism-drawing.json','yeti60-materials.json','calibration.json','yeti60-power-budget.json','prototype-research.json']
 files.extend(['firmware-recovery.json','usb-event-policy.json','analog-waveform.json','gpio-mode-policy.json','scan-control.json','nvs-powercut.json'])
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
        'Retained reference explosion includes seven wires; current candidate assembly supplies nine wires and C04 gasket strips. Use the candidate assembly entry for the current build',
        'NiZ ordinary housings/sliders and separate Cherry plate-mounted stabilizers selected; 1.6 mm plate, 28 mounts and H26 unused; 60 sensing centers and exterior preserved; actual wire/clip/stroke fit awaits a first article',
        'Second review corrected stale 29-fastener inventory/acceptance prose and 1.2 mm render descriptions in both languages; negative tests now reject their return',
        'Current RF status distinguishes passing minimum antenna-copper clearance from unqualified USB signal integrity and enclosed RF; historical reviews remain labeled snapshots',
        'Broken tracked Raytac third_party/zmk link repaired to the pinned repository submodule; all tracked shared links now checked and missing-source fault injected']
 paths=evidence['USB-signal-paths.json']['variants']['raytac']
 usb_review={'positive_trace_mm':paths['positive']['actual_trace_centerline_mm'],'negative_trace_mm':paths['negative']['actual_trace_centerline_mm'],'positive_vias':paths['positive']['via_count'],'negative_vias':paths['negative']['via_count'],'geometric_contact_path_difference_mm':paths['geometric_path_difference_mm'],'scope':'Mainboard only; excludes C5, harness, connectors and module internals; not propagation delay, impedance or an eye result','acceptance':'open; qualify complete return/coupling and full-speed USB with the final harness before manufacturing release'}
 report={'review_scope':'Current Raytac native CAD, built firmware, host tests, assembly and deliverable provenance; E73 excluded','review_timestamp_UTC':datetime.now(timezone.utc).isoformat(),'status':'software-and-CAD-consistency-reviewed','audit_stages_passed':count,'DRC_errors':sum(cad['drc_errors_by_type'].values()),'opens':cad['unconnected_items'],'physical_signal_pairs':len(cad['physical_pin_pairs']),'DRC_warnings':cad['warnings_by_type'],'ERC_counts':erc,'through_vias':ordinary['through_vias'],'mainboard_parts':75,'planned_stock':inventory['planned_stock_parts'],'net_purchase':inventory['net_purchase_parts'],'fixed_findings':notes,'physical_verification':False,'manufacturing_order_released':False,'production_approved':False,'open_requirements':evidence['outcome.json']['open_requirements'],'evidence_sha256':{n:sha(AUD/n) for n in files},'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb',ROOT/'mechanical/rf-remediation.json',ROOT/'renders/yeti60-assembly/render-manifest.json']}}
 report['USB_route_review']=usb_review
 report['functional_acceptance_passed']=False
 report['firmware_artifacts_verified']=True
 candidate=ROOT/'hardware/usb-short-route'
 short=read(candidate/'audit/native-check.json');local=read(candidate/'audit/geometry-check.json');built=read(candidate/'firmware/manifest.json')
 purchase_file=candidate/'mainboard-purchase.csv'
 with purchase_file.open(newline='') as stream:purchase_rows=list(csv.DictReader(stream))
 fitted=sum(int(r['Required']) for r in purchase_rows);stock=sum(int(r['Planned stock use']) for r in purchase_rows);buy=sum(int(r['Net purchase']) for r in purchase_rows)
 assert (fitted,stock,buy)==(75,8,67)
 report['source_sha256'][str(purchase_file.relative_to(ROOT))]=sha(purchase_file)
 report['retained_reference_inventory']={'planned_stock':inventory['planned_stock_parts'],'net_purchase':inventory['net_purchase_parts'],'source':'docs/audit/yeti60-inventory.json'}
 report.update(mainboard_parts=fitted,planned_stock=stock,net_purchase=buy)
 report['review_scope']='Canonical Raytac plus isolated short-USB repair candidate; E73 excluded; canonical images/order archive do not describe candidate cables'
 report['USB_repair_candidate']={'native_checks':short['status'],'physical_pin_pairs_checked':short['physical_pin_pairs_checked'],'USB_contact_path_mm_per_leg':short['USB_positive_contact_path_mm'],'USB_data_vias_per_leg':0,'adjacent_GND_centerline_coverage':{k:local['USB_reference_screen'][k]['nearest_adjacent_GND_coverage_fraction'] for k in ['positive','negative']},'firmware_artifacts_verified':True,'firmware_status':built['status'],'fitted_parts':fitted,'planned_stock':stock,'net_purchase':buy,'complete_cable_geometry_and_assembly_illustrations':'installed-geometry-and-publication-checked','service_mating_path_and_physical_acceptance':'open','manufacturing_released':False,'physical_verification':False,'evidence_sha256':{str(v.relative_to(ROOT)):sha(v) for v in [candidate/'audit/native-check.json',candidate/'audit/geometry-check.json',candidate/'firmware/manifest.json',candidate/'audit/assembly-package.json']}}
 report['USB_repair_candidate']['firmware_recovery']={'entry':'docs/testing/firmware-recovery.md','status':evidence['firmware-recovery.json']['status'],'calibration_version':read(candidate/'firmware/target-check.json')['calibration_contract_version'],'gesture':'Fn + double-tap Backspace within 400 ms; selected BLE profile only','physical_verification':False}
 report['USB_repair_candidate']['USB_event_policy']={'entry':'docs/testing/usb-event-policy.md','status':evidence['usb-event-policy.json']['status'],'native_scenarios':len(evidence['usb-event-policy.json']['cases']),'callback_linkage':read(candidate/'firmware/target-check.json')['variants']['normal']['USB_callback_linkage'],'physical_verification':False}
 report['USB_repair_candidate']['analog_scan_review']={'entry':'docs/testing/analog-waveform.md','status':evidence['analog-waveform.json']['status'],'physical_verification':False,'ADC_API_latency_qualified':False,'capacitance_delay_cases':len(evidence['analog-waveform.json']['sensitivities'])}
 report['USB_repair_candidate']['GPIO_mode_policy']={'entry':'docs/testing/gpio-mode-policy.md','candidate_evidence':'hardware/usb-short-route/firmware/gpio-mode-policy.json','status':evidence['gpio-mode-policy.json']['status'],'positive_cases':len(evidence['gpio-mode-policy.json']['positive_cases']),'rejected_mutants':len(evidence['gpio-mode-policy.json']['rejected_mutants']),'physical_verification':False}
 report['USB_repair_candidate']['passive_specifications']='hardware/usb-short-route/PASSIVES.md'
 report['USB_repair_candidate']['inactive_position_and_idle']={'entry':'docs/testing/scan-control.md',**evidence['scan-control.json']['inactive_idle'],'compiled_active_masks':evidence['scan-control.json']['compiled_matrix_active_masks'],'physical_verification':False}
 report['USB_repair_candidate']['idle_short_tap']={'entry':'docs/testing/scan-control.md',**evidence['scan-control.json']['idle_short_tap'],'physical_verification':False}


 report['USB_repair_candidate']['calibration_storage']={'entry':'docs/testing/calibration-storage.md',**evidence['calibration.json']['storage_integrity']}
 report['USB_repair_candidate']['NVS_recovery_model']={'entry':'docs/testing/nvs-powercut.md','candidate_evidence':'hardware/usb-short-route/firmware/nvs-powercut.json','status':evidence['nvs-powercut.json']['status'],'modeled_cut_trials':evidence['nvs-powercut.json']['total_cut_trials'],'rejected_mutants':len(evidence['nvs-powercut.json']['rejected_mutants']),'physical_verification':False}

 report['USB_repair_candidate']['scanner_control']={'entry':'docs/testing/scan-control.md','candidate_evidence':'hardware/usb-short-route/firmware/scan-control.json','status':evidence['scan-control.json']['status'],'positive_cases':len(evidence['scan-control.json']['positive_cases']),'rejected_mutants':len(evidence['scan-control.json']['rejected_mutants']),'event_queue_capacity':128,'undrained_burst_events_checked':120,'physical_verification':False}
 report['USB_repair_candidate']['power_layout_rework_open']=short.get('power_layout_rework_open',True)
 report['USB_repair_candidate']['conservative_local_power_paths']=short.get('conservative_local_power_paths',[])
 cam=read(candidate/'audit/fabrication-check.json');exported=read(candidate/'audit/fabrication-export.json')
 for path,digest in exported['outputs'].items():assert sha(ROOT/path)==digest,('Stale candidate CAM output',path)
 report['USB_repair_candidate']['fabrication_files']={'status':cam['status'],'entry':'hardware/usb-short-route/FIRST-ARTICLE.md','all_IPC_records_checked':cam['IPC']['all_test_records_checked'],'supplier_DFM_and_physical_acceptance':'open','manufacturing_released':False,'evidence_sha256':sha(candidate/'audit/fabrication-check.json')}
 report['bare_board_order_ready_scope']='Previous canonical long-USB research; candidate CAM file availability is reported separately'
 report['USB_repair_candidate']['selected_F1']=read(candidate/'parts-qualification.json')['F1']
 service=read(candidate/'audit/vertical-motion.json')
 for path,expected in service['source_sha256'].items():
  assert sha(ROOT/path)==expected,('Stale service-path diagnostic',path)
 report['USB_repair_candidate']['service_diagnostic']={'status':service['status'],'service_path_qualified':False,'report':'hardware/usb-short-route/audit/vertical-motion.json'}
 tolerance=read(candidate/'audit/tolerance-diagnostic.json')
 from study_usb_short_tolerances import verify_evidence as verify_tolerance_evidence
 verify_tolerance_evidence(tolerance,read(ROOT/'mechanical/assembly-spec.raytac.json'),read(ROOT/'mechanical/pcb-fabrication-spec.json'))
 for path,expected in tolerance['source_sha256'].items():assert sha(ROOT/path)==expected,('Stale tolerance diagnostic',path)
 report['USB_repair_candidate']['tolerance_diagnostic']={'entry':'hardware/usb-short-route/TOLERANCES.md','scope':'Pre-C04 baseline, not current repaired geometry','status':tolerance['status'],'combined_tolerance_qualified':False,'directional_budgets':tolerance['directional_budgets']}
 fit_evidence=read(candidate/'audit/tolerance-fit.json')
 for path,expected in fit_evidence['source_sha256'].items():assert sha(ROOT/path)==expected,('Stale bounded fit',path)
 report['USB_repair_candidate']['current_bounded_plate_switch_fit']={'entry':'hardware/usb-short-route/MECHANICAL-FIT.md','status':fit_evidence['status'],'interfaces':fit_evidence['interfaces'],'physical_verification':False,'complete_keyboard_tolerance_qualified':False}
 report['USB_repair_candidate']['evidence_sha256']['hardware/usb-short-route/audit/tolerance-fit.json']=sha(candidate/'audit/tolerance-fit.json')
 report['USB_repair_candidate']['evidence_sha256']['hardware/usb-short-route/audit/tolerance-diagnostic.json']=sha(candidate/'audit/tolerance-diagnostic.json')
 report['USB_repair_candidate']['evidence_sha256']['hardware/usb-short-route/audit/vertical-motion.json']=sha(candidate/'audit/vertical-motion.json')
 report['tracked_shared_links']=evidence['integration.json']['shared_links']
 report['bare_board_order_ready']=evidence['prototype-research.json']['bare_board_order_ready']
 report['new_open_design_findings']=evidence['prototype-research.json']['blocking_design_findings']
 assembly_package=read(candidate/'audit/assembly-package.json')
 summary=candidate_summary(short,cam,assembly_package,purchase_rows)
 reference_keys=['DRC_errors','opens','physical_signal_pairs','DRC_warnings','ERC_counts','through_vias']
 report['retained_reference']={key:report[key] for key in reference_keys}
 report['retained_reference']['USB_route_review']=report.pop('USB_route_review')
 report.update({key:summary[key] for key in reference_keys})
 report['current_candidate_summary']=summary
 report['review_scope']='Current short-USB Raytac candidate; retained canonical long-route evidence explicitly labeled; E73 excluded'
 for item in [candidate/'audit/native-check.json',candidate/'audit/fabrication-check.json',candidate/'audit/assembly-package.json']:
  report['source_sha256'][str(item.relative_to(ROOT))]=sha(item)
 documents={}
 for zh in [False,True]:
  suffix='.zh-CN' if zh else '';peer='raytac-review.md' if zh else 'raytac-review.zh-CN.md'
  head=f'[English]({peer}) | 简体中文' if zh else f'English | [Chinese]({peer})'
  title='Raytac 本轮审查结论' if zh else 'Raytac review conclusions'
  body=(f'**已记录的 {count} 个软件／CAD 审查阶段全部通过；尚未放行生产或证明实物工作。** 本轮只覆盖 Raytac，不把旧双方案报告当作本版验收。' if zh else f'**All {count} recorded software/CAD audit stages passed. Manufacturing and physical operation are not approved.** This review covers Raytac only, not the old dual-option report.')
  rows=summary_rows(summary)
  lines=[head,'','# '+title,'',body,'',('下表数值均对应当前短 USB 候选板；旧参考板数据单独标注。' if zh else 'The table describes the current short-USB candidate; retained reference-board figures are labeled separately.'),'','| 范围 | 结果 |' if zh else '| Area | Result |','|---|---|']+[f"| {'线束' if zh and tag=='Harness' else tag} | {cn if zh else en} |" for tag,en,cn in rows]
  lines+=['',('**当前首板采用[短 USB 修补候选包](../../hardware/usb-short-route/FIRST-ARTICLE.zh-CN.md)。** 旧长布线压缩包保留为暂停的参考；不能把旧七线图用于当前九线装配。电池保护包仍待供方确认；完整 USB 链路、模拟稳定性及实物验收仍待首板。见[含电池的开台流程](../../OPEN-BENCH.zh-CN.md)。' if zh else '**Use the [short-USB repair candidate package](../../hardware/usb-short-route/FIRST-ARTICLE.md) for the current first board.** The old long-route archive remains a held reference; its seven-wire illustrations do not describe the current nine-wire assembly. Pack confirmation, complete USB-link/analog stability and physical acceptance remain open. See the [battery-inclusive open-bench flow](../../OPEN-BENCH.md).')]
  lines+=['',('扫描故障处理见[专项说明](../testing/scan-control.zh-CN.md)：初始化不可用明确拒绝命令，故障关闭并释放按键；15 个场景和 17 个错误版本验证，128 项事件队列覆盖 120 事件突发。实际主机送达仍待验收。' if zh else 'See [scanner fault handling](../testing/scan-control.md): unavailable initialization rejects commands, faults shut down and release tracked keys; fifteen scenarios and seventeen mutants, with a 128-entry queue checked against a 120-event burst. Physical host delivery remains open.')]
  lines+=['',('新增 [NVS 中断恢复模型](../testing/nvs-powercut.zh-CN.md)：14,795 次指定写入／垃圾回收／再次恢复中断通过，两个错误顺序／漏搬版本被拒绝；实际 NVMC、蓝牙绑定和欠压验收仍待首板。NVS 模型本身不改变固件标识。' if zh else 'The [NVS recovery model](../testing/nvs-powercut.md) passes 14,795 selected write/GC/recovery interruptions and rejects two ordering/live-copy mutants. Actual NVMC, Bluetooth-bond and brownout acceptance remain first-board work. The NVS model itself does not change firmware identifiers.')]
  lines+=['',('空闲短按已修补：有效位置的首次待确认边沿恢复快速扫描，保留两帧消抖；模型中的 50 ms 持按从漏报变为一次按下／松开，后续单帧尖峰不误报，见[专项证据](../testing/scan-control.zh-CN.md)。升级采用配套固件并重新校准；真实首键延迟及噪声功耗仍待实测。' if zh else 'Idle short-tap correction: the first pending active edge restores fast scanning while retaining two-frame debounce. A modeled 50 ms hold now produces one press/release and a later single-frame spike produces no extra event; see [evidence](../testing/scan-control.md). Upgrade with matched images and recalibrate; actual first-key latency and noise-related power remain unmeasured.')]
  lines+=['','## 修补与图像复核' if zh else '## Repairs and image inspection','']
  repaired=(['C5 的真实保护通道和接地核对后，删除主板重复 D1 与长 USB 支线，保留 C5 必装的 D1／U1／F1。','共享模拟／放电总线标签统一；新导出网表与保存的引脚合同一致。','材料、库存、焊接步骤、实装坐标与编号图同步为 75 件。','保留的参考爆炸图展示七线；当前候选方案展示九线和 C04 垫片。制作时采用候选装配入口。','已改用 NiZ 普通轴座滑块及独立 Cherry 钢板卫星轴；新板 1.6 mm、28 个安装点，H26 不装；保留 60 个感应中心和外形，实际钢丝、卡扣及全行程须首件确认。','再次审查修正库存／验收页的旧 29 套五金及渲染说明中的旧 1.2 mm 板厚；中英文均增加错误注入检查，防止回退。','现行射频状态明确区分：最小天线铜区检查通过，USB 信号完整性及关壳射频仍待验收；历史审查保留为已标注的快照。'] if zh else notes)
  if zh:repaired.append('修复 Raytac 的 third_party/zmk 失效软链接，使其指向仓库固定版本子模块；新增全部受控软链接检查和缺失来源负向测试。')
  lines+=['- '+v for v in repaired]
  lines+=['','## 功能核对与测试边界' if zh else '## Functional coverage and test boundaries','']
  coverage=[
   ('60-key scan / 60 键扫描', '[Geometry/map](yeti60-key-geometry.json); host core tests all 75 matrix positions, hysteresis, debounce and ADC frame abort. Real EC waveforms remain unmeasured.', '[几何及映射](yeti60-key-geometry.json)覆盖 60 键；主机核心覆盖 75 个矩阵位置、迟滞、消抖及 ADC 故障整帧撤销。真实静电容波形未测。'),
   ('Calibration / 校准', '[Guard tests](calibration.json); inspect the target release/press/save flow, 128-frame capture, saturation/overlap rejection and persistent thresholds. First-article capture and flash retention remain open.', '[保护区间测试](calibration.json)及目标代码核对覆盖松键／持按／保存、128 帧采样、饱和／重叠拒绝和阈值持久化；真实采样与刷写保留设置仍待验收。'),
   ('USB priority / USB 优先', '[Actual adapter host regression](yeti60-firmware-simulation.json) covers configured charging plus USB preference, retained BLE preference, suspend/resume/reset/detach and failure retries. USB/BLE interfaces are mocks.', '[实际适配层主机回归](yeti60-firmware-simulation.json)覆盖配置后充电并优先 USB、历史 BLE 偏好、挂起／恢复／复位／拔线和失败重试；USB／BLE 接口为模拟。'),
   ('Power / 供电', '[Current/timer arithmetic](yeti60-power-budget.json), enable-net and adapter review agree with BQ24074 input modes. Off-state USB100 charging differs from firmware-controlled charging. Actual thermal/current behavior remains open.', '[电流和定时计算](yeti60-power-budget.json)、控制网络与适配层符合 BQ24074 输入模式；关机自主 USB100 慢充与固件运行时策略不同。实际温度／电流仍待验收。'),
   ('Firmware / 固件', '[Existing normal/calibrator ARM artifacts](yeti60-target-check.json) rechecked against current source hashes, flash ranges and linked USB500 descriptors. Normal and calibrator images are rebuilt after firmware changes; these checks do not execute the targets.', '[已有普通版／校准版 ARM 产物](yeti60-target-check.json)再次核对当前来源哈希、刷写范围和已链接 USB500 描述符；固件修改后重建普通版与校准版；这些检查不代表执行过目标固件。'),
   ('Assembly / 装配', '[Current candidate assembly](../../hardware/usb-short-route/ASSEMBLY.md) checks nine conductors, C04 plate, 28 mounts / H26 omission, 1.6 mm plate and image provenance. Actual NiZ skirts/clips, 6U bends, preload and local stiffness remain open.', '[当前候选装配](../../hardware/usb-short-route/ASSEMBLY.zh-CN.md)覆盖九根线、C04 定位板、28 套五金／H26 留空、1.6 mm 板厚及图像来源；NiZ 下裙边／卡扣、6U 弯形、预压和局部刚度待实物验收。'),
  ]
  lines+=['| 功能 | 本轮证据与尚未证明的部分 |' if zh else '| Function | Evidence and remaining boundary |','|---|---|']
  for label,en,cn in coverage:
   label=label.split(' / ')[1 if zh else 0]
   lines.append(f'| {label} | {cn if zh else en} |')
  lines.append('')
  lines.append('通用阻容与状态灯已改为[按规格采购](../../hardware/usb-short-route/PASSIVES.zh-CN.md)，七处电源电容同步改成 0805 焊盘，并保留库存备注。完整电源区域已重布，反馈／C46 保守路径缩短为 3.555／4.681 mm；[位置与普通散热通孔说明](../../hardware/usb-short-route/POWER-LAYOUT.zh-CN.md)记录设计检查与实测边界。' if zh else 'Generic passives and the LED now use [purchasing specifications](../../hardware/usb-short-route/PASSIVES.md); seven power capacitors have matching 0805 lands and stock credits remain. The complete power stage is relocated; feedback/C46 conservative paths are 3.555/4.681 mm. [Positions and ordinary thermal vias](../../hardware/usb-short-route/POWER-LAYOUT.md) document the design checks and physical boundaries.')
  lines+=['','## 独立的 USB 修补候选板' if zh else '## Isolated USB repair candidate','']
  lines.append(('上述原目录的 PCB、库存与七根线装配图仍对应原布线。新[修补候选板](../../hardware/usb-short-route/README.zh-CN.md)另行通过严格原生检查及 411 组实际连接检查；两路接触路径均为 5.286396 mm，无数据过孔，相邻层地铜中心线投影覆盖率均为 100%。新插座／胶壳局部公差检查及两版固件重建、主机模拟、校准测试通过。候选板仍装 75 件，计划用库存 8 件、补购 67 件，共九根导线。[九线关壳、16 件理线件及完整装配插图](../../hardware/usb-short-route/ASSEMBLY.zh-CN.md)已通过联合几何与来源一致性检查；检修插接路径及实物验收仍待完成，不能据此放行原制板压缩包。下节长线路数值继续用于说明原目录的限制。' if zh else 'The canonical PCB, inventory and seven-wire assembly images above still describe the previous routing. The separate [repair candidate](../../hardware/usb-short-route/README.md) passed strict native checks and 411 physical pin-pair checks. Both contact paths are 5.286396 mm, with zero data vias and 100% adjacent-ground centerline coverage. Local header/housing tolerance checks, both rebuilt targets, host simulation and calibration tests passed. The candidate fits 75 parts, credits 8 stock parts and requires 67 purchases, with nine conductors total. [Nine-wire enclosure routes, 16 guides and complete assembly illustrations](../../hardware/usb-short-route/ASSEMBLY.md) passed combined installed-geometry and provenance checks; service/mating access and physical acceptance remain open. This does not release the canonical fabrication archive. The long-route values below continue to document the canonical routing limitation.'))
  lines.append('当前候选板的[首板制造包及无外壳流程](../../hardware/usb-short-route/FIRST-ARTICLE.zh-CN.md)已经提供；独立回读覆盖 846 处孔槽、289 个实装铜焊盘、75 件贴装、297 个钢网开口及全部 1,444 条 IPC 记录。已排除 JP1 锡膏并统一电测原点。板厂 DFM 在生产前，实物验收在首板制造后；不放行原布线压缩包。' if zh else 'The candidate [first-article fabrication package and case-free procedure](../../hardware/usb-short-route/FIRST-ARTICLE.md) are available. Independent readback covers 846 drill/slot features, 289 fitted copper lands, 75 placements, 297 stencil apertures and all 1,444 IPC records. JP1 paste is omitted and the test-netlist origin is normalized. Supplier DFM precedes fabrication; physical acceptance follows the first board. The previous routing archive remains held.')
  lines.append('候选板 F1 已选为 [Littelfuse 0466001.NRHF 一次性快断及修订焊盘](../../hardware/usb-short-route/F1-SELECTION.zh-CN.md)。新增[连续垂直扫掠](../../hardware/usb-short-route/SERVICE-PATH.zh-CN.md)确认内部避空已消除标称刚体运动中的翼板阻挡，并修订后部理线夹公差通道；USB／电池插头退出、线束变形和完整公差仍未验收，不能据此批准关壳装配。' if zh else 'Candidate F1 is now the [Littelfuse 0466001.NRHF one-time fuse with revised lands](../../hardware/usb-short-route/F1-SELECTION.md). A new [continuous vertical sweep](../../hardware/usb-short-route/SERVICE-PATH.md) confirms that an internal relief removes the nominal rigid-body wing obstruction and revised rear clips provide a screened PCB corridor. USB/battery unmating, wire deformation and combined tolerances remain unqualified; enclosed service is not approved.')
  lines.append('原定位耳及开关底部问题已通过 [C04 定位板、底壳凹槽和八条垫片](../../hardware/usb-short-route/MECHANICAL-FIT.zh-CN.md)修补。在规定的成品尺寸与安装误差内，定位板静态／连续取出和开关底部包络通过；定位板至少约剩 0.188 mm 空气余量。原诊断保留为修补前基线。整键盘公差、泡棉性能、带线检修和实物验收仍待完成。' if zh else 'The previous locating-ear and switch-floor issues are repaired by the [C04 plate, lower-shell pocket and eight gasket strips](../../hardware/usb-short-route/MECHANICAL-FIT.md). Static/continuous plate and switch-floor envelopes pass under the stated finished-part and installation limits; the plate retains approximately 0.188 mm air reserve. The previous diagnostic remains a pre-repair baseline. Full-keyboard tolerances, foam behavior, connected service and physical acceptance remain open.')
  lines.append('模拟引脚已改为[断开数字缓冲的高阻模式，并清理初始化失败](../testing/gpio-mode-policy.zh-CN.md)。实际回调及初始化函数的五个正向场景通过，四个错误变体被拒绝；候选包独立重复测试。实际寄存器、漏电、瞬态及供电故障仍需首板测量。' if zh else 'Analog pins now use [high impedance with digital buffers disconnected, plus startup-error cleanup](../testing/gpio-mode-policy.md). Five positive cases execute actual callback/init sources and reject four mutants; the candidate bundle repeats the tests independently. Actual registers, leakage, transients and physical power faults require the first board.')
  lines.append('静电容扫描修补[释放／充电和钳位／下降沿顺序](../testing/analog-waveform.zh-CN.md)。两个反向变体被实际核心回归拒绝；36 组无源 RC 敏感性计算不替代真实 NiZ 电容、运放动态或采样时刻验收。校准版新增 32768 Hz RTC 粗略耗时诊断，显示频率并计入一格量化余量，不当作精确采样时刻。' if zh else 'EC scanning repairs [release/charge and clamp/falling-edge order](../testing/analog-waveform.md). Actual-core regressions reject both reversed variants. Thirty-six passive RC sensitivity cases do not qualify real NiZ capacitance, op-amp dynamics or sample timing. The calibrator adds coarse 32768 Hz RTC timing estimates with the clock and one-tick guard reported, not precise sample timestamps.')
  lines.append('固件审查补齐[当前蓝牙槽位恢复与 v3 校准失效规则](../testing/firmware-recovery.zh-CN.md)。两版 ARM 构建的解析设备树已核对 Fn＋双击 Backspace，仅清除当前槽位；实际 CMake 指纹变动和固定版本 ZMK 手势实现经过主机测试。真实配对、模拟时序和充电切换仍需首板验证。' if zh else 'Firmware review adds [selected-profile recovery and calibration v3 invalidation](../testing/firmware-recovery.md). Resolved device trees in both ARM builds verify Fn + double-tap Backspace clears only the selected slot. Actual CMake fingerprint mutations and pinned ZMK gesture code are host-tested. Real pairing, analog timing and charging transitions still require the first board.')
  lines.append('USB 审查修补[回调式禁充与主机取消配置](../testing/usb-event-policy.zh-CN.md)：固定版本 ZMK 原始 USB 回调经过 11 个主机场景测试，两版 ARM 的实际调用目标已核对。实测回调延迟、挂起电流和电池支撑仍未验收。' if zh else 'USB review repairs [callback-driven charger disable and host deconfiguration](../testing/usb-event-policy.md). Eleven host scenarios compile the unmodified pinned ZMK USB callback; both ARM call targets are checked. Physical callback latency, suspend current and battery-backed transitions remain open.')
  lines+=['','## 旧参考板 USB 布线的具体限制' if zh else '## USB routing limitation of the retained reference board','']
  lines.append((f"旧参考板 D+／D− 实际线段中心线分别约 **{usb_review['positive_trace_mm']:.3f}／{usb_review['negative_trace_mm']:.3f} mm**，经过 **{usb_review['positive_vias']}／{usb_review['negative_vias']} 个过孔**。含焊盘接入等桥接的几何接触路径差为 **{usb_review['geometric_contact_path_difference_mm']:.3f} mm**；它不是传播延迟差。这里未包含 C5、线束、连接器内部和模组内部。保护导通及 DRC 通过不能证明差分阻抗、回流连续性、共模或 USB 眼图通过；发布制造前需审查完整链路，并在最终线束下实测。" if zh else f"Retained reference-board D+ / D− actual trace centerlines are approximately **{usb_review['positive_trace_mm']:.3f} / {usb_review['negative_trace_mm']:.3f} mm**, through **{usb_review['positive_vias']} / {usb_review['negative_vias']} vias**. The pad-access/contact-bridge geometric path difference is **{usb_review['geometric_contact_path_difference_mm']:.3f} mm**, not propagation-delay skew. C5, harness, connector and module internals are excluded. Protected connectivity and DRC do not establish differential impedance, continuous return, common-mode behavior or a passing USB eye. Review the complete link and measure it with the final harness before manufacturing release."))
  lines+=['',('[充电器原厂资料](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [稳压器原厂资料](https://www.ti.com/lit/ds/symlink/tps63031.pdf)。数据手册复核不能代替本板波形和温升实测。' if zh else '[Charger primary datasheet](https://www.ti.com/lit/ds/symlink/bq24074.pdf) · [Regulator primary datasheet](https://www.ti.com/lit/ds/symlink/tps63031.pdf). Datasheet review does not replace board waveform or thermal measurements.')]
  lines+=['','## 仍需实物或供应商证据' if zh else '## Supplier and physical work still open','']
  pending=(['通用阻容／LED 按采购规格选购，不要求逐颗指定品牌；关键电容偏压下的有效容量及保险丝实际温度降额仍须符合要求。布局修补已通过设计检查，稳定性、纹波和瞬态仍需首板实测。','定制电池完整包络、供方签图、允许充电电压／电流及独立温度断充。','真实轴座、胶碗、弹簧、稳定机构、树脂公差与线束装配样件。','实际 USB 枚举／眼图、边充边输入、BLE、逐键校准、温升／续航及关壳后的干扰测试。','C5 上游默认 DRC 仍有制造审查项；本轮保护通道通过不等于 C5 已取得制造或 ESD 认证。'] if zh else ['Generic passives/LEDs are purchased by specification without mandatory individual brands. Effective capacitance under bias and actual fuse thermal derating still require compliance; layout rework passes design checks; stability, ripple and transients still require first-board measurements.','Supplier-signed complete pack envelope, charge limits and independent thermal interruption.','Actual housings/domes/springs/stabilizers, resin tolerances and harness/mechanical samples.','Physical USB enumeration/eye, concurrent charge/input, BLE, per-key calibration, thermal/runtime and enclosed interference tests.','Upstream C5 default DRC review items remain; protected-channel verification is not C5 manufacturing or ESD certification.'])
  lines+=['- '+v for v in pending]
  lines+=['',('[制作总入口](../../BUILD.zh-CN.md) · [完整爆炸图与元件对照](../engineering/exploded.zh-CN.md) · [首件验收流程](../testing/README.zh-CN.md) · [机器审查与来源哈希](raytac-review.json)' if zh else '[Build entry](../../BUILD.md) · [complete explosion and part index](../engineering/exploded.md) · [first-article acceptance](../testing/README.md) · [machine evidence/hashes](raytac-review.json)'),'']
  documents[zh]='\n'.join(lines)
 verify_publication(report,documents,summary)
 (AUD/'raytac-review.json').write_text(json.dumps(report,indent=2)+'\n')
 for zh,text in documents.items():
  (AUD/('raytac-review'+('.zh-CN' if zh else '')+'.md')).write_text(text)
 if args.sync_downloads:
  repo=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True).strip());dest=repo/'hardware/raytac';dest.mkdir(exist_ok=True)
  mirror={}
  for rel in ['hardware/usb-short-route/EC60-nRF52840.kicad_pcb','hardware/usb-short-route/fabrication/yeti60-raytac-candidate-gerbers.zip','hardware/usb-short-route/fabrication/yeti60-raytac-candidate-bottom-stencil.zip']:
   source=ROOT/rel;target=dest/source.name;shutil.copyfile(source,target);assert sha(source)==sha(target);mirror[str(target.relative_to(repo))]={'canonical_source':str(source.relative_to(repo)),'sha256':sha(target)}
  legacy=dest/'yeti60-raytac-p2-dfm-review.zip'
  if legacy.exists():
   assert sha(legacy)==sha(ROOT/'hardware/fabrication'/legacy.name),'Preserve an unexpectedly modified legacy download'
   legacy.unlink()
  (dest/'manifest.json').write_text(json.dumps({'status':'verified-current-Raytac-candidate-download-copies','manufacturing_order_released':False,'canonical_entry':'variants/raytac/hardware/usb-short-route/FIRST-ARTICLE.md','files':mirror,'removed_superseded_download':'yeti60-raytac-p2-dfm-review.zip; previous canonical reference retained under variants/raytac/hardware/fabrication'},indent=2)+'\n')
  for zh in [False,True]:
   suffix='.zh-CN' if zh else '';peer='README.md' if zh else 'README.zh-CN.md'
   text=(f'[English]({peer}) | 简体中文\n\n# Raytac 当前候选板下载\n\n本目录只提供当前修补候选板的原生 PCB、主板 Gerber／钻孔包及背面钢网副本，均与[首板入口](../../variants/raytac/hardware/usb-short-route/FIRST-ARTICLE.zh-CN.md)来源一致；用[哈希清单](manifest.json)确认版本。旧布线的重复下载包已移除，历史参考仍保留在方案目录中。\n\n从[首板入口](../../variants/raytac/hardware/usb-short-route/FIRST-ARTICLE.zh-CN.md)查阅 JLC 参数、备料、接线和无外壳验证。编辑工程或查看模型／封装库时使用方案目录的完整工程，不把本目录的单个 PCB 副本当作完整工程。生产前仍需板厂 DFM；实物验收和生产批准尚未完成。\n' if zh else f'English | [Chinese]({peer})\n\n# Current Raytac candidate downloads\n\nThis directory mirrors the current repair candidate PCB, mainboard Gerber/drill ZIP and bottom-stencil ZIP from the [first-article entry](../../variants/raytac/hardware/usb-short-route/FIRST-ARTICLE.md). Identify the files with the [hash manifest](manifest.json). The duplicate download for the previous routing is removed; historical reference files remain in the variant directory.\n\nUse the [first-article entry](../../variants/raytac/hardware/usb-short-route/FIRST-ARTICLE.md) for JLC selections, materials, wiring and case-free validation. Use the complete variant project for editing, models and footprint libraries; the individual PCB copy here is not a complete project. Supplier DFM precedes production; physical acceptance and production approval remain open.\n')
   (dest/('README'+suffix+'.md')).write_text(text)
 print('Raytac review generated from',count,'passing audit stages; manufacturing/physical acceptance remains open')
if __name__=='__main__':main()
