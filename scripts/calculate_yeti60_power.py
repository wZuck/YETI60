#!/usr/bin/env python3
"""Explicit sensitivity scenarios; does not invent measured average board current."""
import csv,hashlib,json,re
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 scanner=ROOT/'firmware/target/src/scanner.c';s=scanner.read_text();conf=(ROOT/'firmware/target/config/yeti60.conf').read_text()
 assert 'CONFIG_USB_MAX_POWER=250' in conf
 parts={c.get('ref'):c.findtext('value') for c in ET.parse(ROOT/'hardware/ec60-nrf52840/netlist.xml').getroot().findall('./components/comp')}
 assert [parts[r] for r in ['R40','R55','R56']]==['2.21k/1%','69.8k/1%','1.82k/1%']
 nodes={(n.get('ref'),n.get('pin')):net.get('name') for net in ET.parse(ROOT/'hardware/ec60-nrf52840/netlist.xml').getroot().findall('./nets/net') for n in net.findall('node')}
 for ref,signal in [('R42','CHG_EN1'),('R43','CHG_EN2'),('R44','CHG_CE_N')]:
  assert parts[ref]=='100k' and nodes[(ref,'1')]==signal and nodes[(ref,'2')]=='GND','Hardware-off pull-down contract changed'
 assert [nodes[('SW100',pin)] for pin in ['1','2','3']]==['VSYS','REG_EN','GND']
 spec=json.loads((ROOT/'mechanical/assembly-spec.json').read_text());capacity=spec['battery']['nominal_capacity_mAh'];assert capacity==1600
 assert 'CONFIG_ZMK_SLEEP=n' in conf and '.acquisition_us = 40' in s and 'k_sleep(K_MSEC(4))' in s
 # 75 samples; explicit timing excludes GPIO/driver, conversion-start, scheduler and BLE overhead.
 busy=15*3+75*(10+5);acq=75*40;conv_budget=75*2;frame=busy+acq+conv_budget+4000
 scenarios=[]
 for name,op,mc,eta,vb,charger,pcm in [('lower-demand',5.2,3,.90,3.7,.0043,.010),('planning',5.2,6,.85,3.7,.0043,.010),('stress',7.5,10,.80,3.3,.0065,.020)]:
  # R44 (/CE high) and R50 (AFE_EN high); R48 is separately on VSYS.
  pull=2*3.3/100000*1000;switch=.008;mux=.016;misc=.1
  rail=op+mc+pull+switch+mux+misc;reg_enable=vb/100000*1000
  ibat=3.3*rail/(vb*eta)+reg_enable+charger+pcm
  scenarios.append({'scenario':name,'opamp_mA':op,'mcu_average_mA_ASSUMED':mc,'efficiency_ASSUMED':eta,'battery_voltage_V_ASSUMED':vb,'rail_3v3_mA':rail,'battery_mA':ibat,'battery_power_mW':vb*ibat,'usable_capacity_factor_ASSUMED':.8,'runtime_default_pack_hours':capacity*.8/ibat})
 for zh in [False,True]:
  p=ROOT/'hardware/bom'/('power-scenarios.zh-CN.csv' if zh else 'power-scenarios.csv')
  with p.open('w',newline='') as f:
   w=csv.writer(f,lineterminator='\n');w.writerow(['情景','假设主控平均电流_mA','假设效率','假设电池电压_V','3.3V电流_mA','电池电流_mA','1600mAh条件续航_h'] if zh else ['Scenario','Assumed MCU average mA','Assumed efficiency','Assumed battery V','3.3V current mA','Battery current mA','Conditional 1600mAh hours'])
   for r in scenarios:w.writerow([({'lower-demand':'较低负载','planning':'规划值','stress':'压力情景'}[r['scenario']] if zh else r['scenario']),r['mcu_average_mA_ASSUMED'],r['efficiency_ASSUMED'],r['battery_voltage_V_ASSUMED'],round(r['rail_3v3_mA'],3),round(r['battery_mA'],3),round(r['runtime_default_pack_hours'],2)])
 report={'outputs':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'hardware/bom/power-scenarios.csv',ROOT/'hardware/bom/power-scenarios.zh-CN.csv']},'status':'conditional-sensitivity-model-not-measurement','source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [scanner,ROOT/'firmware/yeti60/core.c',ROOT/'firmware/target/config/yeti60.conf',ROOT/'firmware/target/boards/yeti/yeti60/yeti60.dts',ROOT/'docs/engineering/sources.json',ROOT/'mechanical/assembly-spec.json',ROOT/'firmware/target/src/scanner.c',ROOT/'hardware/ec60-nrf52840/netlist.xml',Path(__file__).resolve()]},'equations':{'rail_mA':'I_OPA + I_MCU_average + 2*3.3/100k*1000 + 0.008 + 0.016 + 0.100','battery_mA':'3.3*I_rail/(V_bat*eta) + V_bat/100k*1000 + I_charger + I_PCM','runtime_hours':'capacity_mAh * usable_factor / I_battery','energy_equivalent':'runtime = (V_bat*capacity_Ah*usable_factor) / (P_rail/eta + V_bat*I_bias)'},'scenarios':scenarios,'timing_us':{'busy_wait_per_frame':busy,'acquisition_per_frame':acq,'conversion_budget_per_frame':conv_budget,'frame_without_gpio_driver_overhead':frame,'note':'2us per conversion is an engineering timing budget, not a measured duration. ADC blocking can allow CPU sleep; do not treat all acquisition time as CPU busy.'},'current_firmware':{'AFE_on_between_frames':True,'deep_sleep_enabled':False,'battery_reporting':False,'REG1_DCDC_enabled_by_custom_board':False,'LED':'No status LED drive in current adapter; assumed off'},'not_claimed':['Guaranteed current or runtime range','Measured BLE duty cycle, connection interval, SAADC/CPU occupancy','End-to-end efficiency or battery capacity acceptance','USB calibration firmware power equal to normal BLE mode'], 'default_capacity_mAh':capacity,'charging':{
  'ISET_resistor_ohm':2210,'TMR_resistor_ohm':69800,'ITERM_resistor_ohm':1820,'resistor_tolerance_fraction':.01,
  'programmed_charge_mA_min_typ_max':[797/(2210*1.01)*1000,890/2210*1000,975/(2210*.99)*1000],
  'termination_mA_min_typ_max':[.0225*1820*.99/(2210*1.01)*1000,.03*1820/2210*1000,.0375*1820*1.01/(2210*.99)*1000],
  'fastcharge_timer_h_min_typ_max':[10*69.8*.99*36/3600,10*69.8*48/3600,10*69.8*1.01*60/3600],
  'USB_configured_requested_mA':500,'USB500_input_limit_mA_min_typ_max':[450,475,500],
  'preconfiguration_input_limit_mA':100,'charging_before_configuration':False,'charging_during_suspend':False,
  'control_policy_scope':'Powered target firmware; hardware-off defaults are separate',
  'hardware_off_defaults':{'EN1':0,'EN2':0,'CE_N':0,'input_limit_mA':100,'charging_enabled':True,'full_charge_time_verified':False},
  'system_input_reserve_mA_ASSUMED':40,'minimum_input_available_after_assumed_reserve_mA':450-40,
  'ideal_CC_at_minimum_programmed_current_h':capacity/(797/(2210*1.01)*1000),
  'CV_budget_before_minimum_timer_h':10*69.8*.99*36/3600-capacity/(797/(2210*1.01)*1000),
  'guaranteed_full_charge_time':False,'larger_pack_drop_in_approved':False,'design_revision':'P2 default 1600 mAh, revised PCB and firmware required',
  'cell_charge_endpoint_mA':.02*capacity,'pack_temperature_actual_window_C':spec['battery']['thermal_protection_actual_window_C'],
  'acceptance':['Supplier-signed pack drawing and corrected current/temperature limits','Verify full charge to termination before timer under USB load and temperature limits','Independent factory pack thermal interruption, not just voltage/current protection']}}
 assert max(report['charging']['programmed_charge_mA_min_typ_max'])<=spec['battery']['maximum_charge_current_mA']
 assert max(report['charging']['termination_mA_min_typ_max'])<=report['charging']['cell_charge_endpoint_mA']
 assert 18<69.8*.99 and 69.8*1.01<72
 (ROOT/'docs/audit/yeti60-power-budget.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(scenarios,indent=2))
if __name__=='__main__':main()
