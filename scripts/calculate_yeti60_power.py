#!/usr/bin/env python3
"""Explicit sensitivity scenarios; does not invent measured average board current."""
import csv,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 scanner=ROOT/'firmware/target/src/scanner.c';s=scanner.read_text();conf=(ROOT/'firmware/target/config/yeti60.conf').read_text()
 assert 'CONFIG_ZMK_SLEEP=n' in conf and '.acquisition_us = 40' in s and 'k_sleep(K_MSEC(4))' in s
 # 75 samples; explicit timing excludes GPIO/driver, conversion-start, scheduler and BLE overhead.
 busy=15*3+75*(10+5);acq=75*40;conv_budget=75*2;frame=busy+acq+conv_budget+4000
 scenarios=[]
 for name,op,mc,eta,vb,charger,pcm in [('lower-demand',5.2,3,.90,3.7,.0043,.010),('planning',5.2,6,.85,3.7,.0043,.010),('stress',7.5,10,.80,3.3,.0065,.020)]:
  # R44 (/CE high) and R50 (AFE_EN high); R48 is separately on VSYS.
  pull=2*3.3/100000*1000;switch=.008;mux=.016;misc=.1
  rail=op+mc+pull+switch+mux+misc;reg_enable=vb/100000*1000
  ibat=3.3*rail/(vb*eta)+reg_enable+charger+pcm
  scenarios.append({'scenario':name,'opamp_mA':op,'mcu_average_mA_ASSUMED':mc,'efficiency_ASSUMED':eta,'battery_voltage_V_ASSUMED':vb,'rail_3v3_mA':rail,'battery_mA':ibat,'battery_power_mW':vb*ibat,'usable_capacity_factor_ASSUMED':.8,'runtime_200mAh_hours':200*.8/ibat,'runtime_1000mAh_hours':1000*.8/ibat})
 for zh in [False,True]:
  p=ROOT/'hardware/bom'/('power-scenarios.zh-CN.csv' if zh else 'power-scenarios.csv')
  with p.open('w',newline='') as f:
   w=csv.writer(f,lineterminator='\n');w.writerow(['情景','假设主控平均电流_mA','假设效率','假设电池电压_V','3.3V电流_mA','电池电流_mA','200mAh条件续航_h','1000mAh条件续航_h'] if zh else ['Scenario','Assumed MCU average mA','Assumed efficiency','Assumed battery V','3.3V current mA','Battery current mA','Conditional 200mAh hours','Conditional 1000mAh hours'])
   for r in scenarios:w.writerow([({'lower-demand':'较低负载','planning':'规划值','stress':'压力情景'}[r['scenario']] if zh else r['scenario']),r['mcu_average_mA_ASSUMED'],r['efficiency_ASSUMED'],r['battery_voltage_V_ASSUMED'],round(r['rail_3v3_mA'],3),round(r['battery_mA'],3),round(r['runtime_200mAh_hours'],2),round(r['runtime_1000mAh_hours'],2)])
 report={'outputs':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'hardware/bom/power-scenarios.csv',ROOT/'hardware/bom/power-scenarios.zh-CN.csv']},'status':'conditional-sensitivity-model-not-measurement','source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [scanner,ROOT/'firmware/yeti60/core.c',ROOT/'firmware/target/config/yeti60.conf',ROOT/'firmware/target/boards/yeti/yeti60/yeti60.dts',ROOT/'docs/engineering/sources.json',ROOT/'hardware/ec60-nrf52840/netlist.xml',Path(__file__).resolve()]},'equations':{'rail_mA':'I_OPA + I_MCU_average + 2*3.3/100k*1000 + 0.008 + 0.016 + 0.100','battery_mA':'3.3*I_rail/(V_bat*eta) + V_bat/100k*1000 + I_charger + I_PCM','runtime_hours':'capacity_mAh * usable_factor / I_battery','energy_equivalent':'runtime = (V_bat*capacity_Ah*usable_factor) / (P_rail/eta + V_bat*I_bias)'},'scenarios':scenarios,'timing_us':{'busy_wait_per_frame':busy,'acquisition_per_frame':acq,'conversion_budget_per_frame':conv_budget,'frame_without_gpio_driver_overhead':frame,'note':'2us per conversion is an engineering timing budget, not a measured duration. ADC blocking can allow CPU sleep; do not treat all acquisition time as CPU busy.'},'current_firmware':{'AFE_on_between_frames':True,'deep_sleep_enabled':False,'battery_reporting':False,'REG1_DCDC_enabled_by_custom_board':False,'LED':'No status LED drive in current adapter; assumed off'},'not_claimed':['Guaranteed current or runtime range','Measured BLE duty cycle, connection interval, SAADC/CPU occupancy','End-to-end efficiency or battery capacity acceptance','USB calibration firmware power equal to normal BLE mode'],'charging':{'ISET_resistor_ohm':8870,'nominal_K_ISET_Aohm':890,'nominal_programmed_charge_mA':890/8870*1000,'USB_input_cap_mA':100,'default_fastcharge_timer_h_min_typ_max':[4,5,6],'TMR':'pin14 no-connect, internal timer','larger_pack_drop_in_approved':False,'reason':'1000mAh at <=100mA requires >=10h before CV/system load; finite timer and dynamic scaling require a separate charger revision and qualification'}}
 (ROOT/'docs/audit/yeti60-power-budget.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(scenarios,indent=2))
if __name__=='__main__':main()
