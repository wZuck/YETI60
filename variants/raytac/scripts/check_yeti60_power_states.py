#!/usr/bin/env python3
"""Reconcile actual candidate power nets, reset defaults and limited off-state arithmetic."""
import hashlib,json,math
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/usb-short-route'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify_parts(parts):
    expected={
        'SW100':{'1':'VSYS','2':'REG_EN','3':'GND'},
        'U5':{'1':'BAT_NTC','2':'BAT_CELL','3':'BAT_CELL','4':'CHG_CE_N','5':'CHG_EN2','6':'CHG_EN1','10':'VSYS','11':'VSYS','13':'USB_5V'},
        'U6':{'1':'+3.3V','5':'VSYS','6':'REG_EN','8':'REG_VINA','10':'+3.3V'},
        'U7':{'1':'BAT_CELL','2':'GND','3':'BAT_MEAS_EN','5':'BAT_MEAS_TOP_QOD','6':'BAT_MEAS_TOP'},
        'U8':{'1':'+3.3V','2':'GND','3':'AFE_EN','5':'AFE_3V3_QOD','6':'AFE_3V3'},
        'J2':{'1':'BAT_CELL','2':'GND','3':'BAT_NTC'},
        'R42':{'1':'CHG_EN1','2':'GND'},'R43':{'1':'CHG_EN2','2':'GND'},'R44':{'1':'CHG_CE_N','2':'GND'},
        'R48':{'1':'REG_EN','2':'GND'},'R49':{'1':'BAT_MEAS_EN','2':'GND'},'R50':{'1':'AFE_EN','2':'GND'},
        'R51':{'1':'BAT_MEAS_TOP','2':'BAT_ADC'},'R52':{'1':'BAT_ADC','2':'GND'},
        'R53':{'1':'BAT_MEAS_TOP_QOD','2':'BAT_MEAS_TOP'},'R54':{'1':'AFE_3V3_QOD','2':'AFE_3V3'}}
    for ref,pins in expected.items():
        for pin,net in pins.items():assert parts[ref]['pins'].get(pin)==net,('Power-state pin mismatch',ref,pin,net)
    for ref in ['R42','R43','R44','R48','R49','R50']:assert parts[ref]['value']=='100k',ref
    assert parts['R51']['value']==parts['R52']['value']=='1M/1%'
    assert parts['R53']['value']==parts['R54']['value']=='100'
    assert parts['U5']['value']=='BQ24074RGT' and parts['U6']['value']=='TPS63031DSK'
    assert parts['U7']['value']==parts['U8']['value']=='TPS22919DCK'

def verify_report(report):
    assert report['status']=='power-state-contract-passed-physical-open'
    assert report['physical_verification'] is False and report['whole_board_upper_bound'] is False
    assert report['reset_default'] == {'CE_N':0,'EN1':0,'EN2':0,'USB_input_limit_mA':100,'charge_permission':True}
    assert report['firmware_unconfigured'] == {'CE_N':1,'EN1':0,'EN2':0,'USB_input_limit_mA':100,'charge_permission':False}
    assert report['MCU_reset_equals_USB_bus_reset'] is False
    assert report['suspend_battery_loss_qualified'] is False
    assert abs(report['datasheet_line_item_subtotal_uA']['typical']-4.402)<1e-10
    assert abs(report['datasheet_line_item_subtotal_uA']['sum_of_listed_maxima']-8.2)<1e-10
    assert [(row['assumed_cell_current_uA'],row['mAh_per_30_days']) for row in report['current_sensitivity']]==[(20,14.4),(50,36.0),(100,72.0)]

def main():
    native=json.loads((BASE/'audit/native-check.json').read_text())
    assert native['status']=='native-candidate-checks-passed'
    xml=BASE/'netlist.xml';components=BASE/'components.json'
    for path in [xml,components]:assert native['source_sha256'][str(path.relative_to(ROOT))]==sha(path)
    parts=json.loads(components.read_text());verify_parts(parts)
    exported=ET.parse(xml).getroot()
    nodes={(node.get('ref'),node.get('pin')):net.get('name') for net in exported.findall('./nets/net') for node in net.findall('node')}
    for ref,part in parts.items():
        if ref.startswith('#'):continue
        for pin,net in part['pins'].items():assert nodes[(ref,pin)]==net,('Stale component pin record',ref,pin)
    specs=ROOT/'docs/engineering/power-state-sources.json';source=json.loads(specs.read_text())
    assert source['whole_board_upper_bound'] is False and source['physical_verification'] is False
    runtime=ROOT/'docs/audit/usb-event-policy.json';tested=json.loads(runtime.read_text())
    assert tested['status']=='passed' and not tested['physical_verification'] and len(tested['cases'])==11
    policy=ROOT/'firmware/target/src/usb_policy.c'
    assert tested['source_sha256']['firmware/target/src/usb_policy.c']==sha(policy)
    typical=math.fsum(row['typical_uA'] for row in source['sources'].values())
    listed_max=math.fsum(row['maximum_uA'] for row in source['sources'].values())
    report={'status':'power-state-contract-passed-physical-open','physical_verification':False,'whole_board_upper_bound':False,
        'reset_default':{'CE_N':0,'EN1':0,'EN2':0,'USB_input_limit_mA':100,'charge_permission':True},
        'firmware_unconfigured':{'CE_N':1,'EN1':0,'EN2':0,'USB_input_limit_mA':100,'charge_permission':False},
        'MCU_reset_equals_USB_bus_reset':False,'suspend_battery_loss_qualified':False,
        'datasheet_line_item_subtotal_uA':{'typical':typical,'sum_of_listed_maxima':listed_max,'scope':'Arithmetic sum of different datasheet test conditions, not total or worst-case board current'},
        'current_sensitivity':[{'assumed_cell_current_uA':value,'mAh_per_day':value*24/1000,'mAh_per_30_days':value*24*30/1000} for value in [20,50,100]],
        'not_verified':['GPIO/reset/rail-decay timing and actual current','MCU reboot or pack cutoff while USB host remains suspended','PCM/internal pack consumption and cell self-discharge','Full electrical fault behavior, temperature and USB conformity'],
        'source_sha256':{str(path.relative_to(ROOT)):sha(path) for path in [xml,components,specs,runtime,Path(__file__).resolve(),policy]}}
    verify_report(report)
    (ROOT/'docs/audit/power-states.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Candidate power nets/reset defaults match; off-state reference subtotal:',typical,'uA; listed-maxima sum:',listed_max,'uA; neither is a whole-board bound')
if __name__=='__main__':main()
