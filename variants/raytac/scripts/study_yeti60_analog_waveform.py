#!/usr/bin/env python3
"""Production GPIO trace -> actual-netlist passive RC model and order regressions."""
import csv,hashlib,io,json,re,shutil,subprocess,tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
ROOT=Path(__file__).resolve().parents[1]
AUD=ROOT/'docs/audit';DOC=ROOT/'docs/testing';IMAGE=DOC/'images'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def numeric(text):
    match=re.fullmatch(r'([0-9.]+)([kMunp]?)(?:/.*)?',text)
    assert match,text
    return float(match[1])*{'':1,'k':1e3,'M':1e6,'u':1e-6,'n':1e-9,'p':1e-12}[match[2]]
def topology(path):
    root=ET.parse(path).getroot();values={c.get('ref'):c.findtext('value') for c in root.findall('components/comp')};nets={}
    for net in root.findall('nets/net'):
        for node in net.findall('node'):nets[node.get('ref'),node.get('pin')]=net.get('name')
    def pair(ref):return {v for (r,p),v in nets.items() if r==ref}
    assert pair('C10')=={'APLEX_OUT_PIN_0','GND'}
    assert pair('R6')=={'ROW0','ROW_DRV0'} and pair('R8')=={'COL0','GND'}
    assert nets['U2','3']==nets['U3','3']=='APLEX_OUT_PIN_0' and nets['U2','13']=='COL0'
    assert nets['U3','6']=='ADC' and nets['U3','2']==nets['R16','2']==nets['R17','1']
    assert pair('R16')=={'ADC',nets['U3','2']} and pair('R17')=={'GND',nets['U3','2']}
    assert values['U3']=='OPA350' and values['U2']=='74HC4051'
    assert pair('JP1')=={'ADC',nets['U3','2']}
    return dict(hold_F=numeric(values['C10']),row_ohm=numeric(values['R6']),column_ohm=numeric(values['R8']),feedback_ohm=numeric(values['R16']),gain_ground_ohm=numeric(values['R17']))
def pwl(events,pin,on,initial,start,end):
    points=[(0,initial)];previous=initial
    for event in events:
        if int(event['pin'])!=pin or event['event'] not in on:continue
        t=float(event['time_us'])-start
        if not 0<t<end:continue
        value=on[event['event']]
        if value==previous:continue
        points.extend([(t,previous),(t+0.01,value)]);previous=value
    points.append((end,previous))
    return ' '.join(f'{t:.6f}u {v:.12g}' for t,v in points)
def main():
    spice=shutil.which('ngspice');clang=shutil.which('clang');assert spice and clang,'ngspice and host Clang are required'
    version=subprocess.check_output([spice,'--version'],text=True).splitlines()[1].strip()
    inputs=DOC/'analog-waveform-inputs.json';cfg=json.loads(inputs.read_text())
    assert cfg['gpio_call_us_assumption']==0.5 and cfg['gpio_rise_fall_ns_assumption']==10
    netlist=ROOT/'hardware/usb-short-route/netlist.xml';electrical=topology(netlist)
    reference=ROOT/'hardware/ec60-nrf52840/netlist.xml'
    assert topology(reference)==electrical,'Reference and candidate analog circuits differ'
    target_check=ROOT/'docs/audit/yeti60-target-check.json';target=json.loads(target_check.read_text())
    assert target['status']=='passed' and all(v['diagnostic_clock_hz']==32768 for v in target['variants'].values())
    scanner=ROOT/'firmware/target/src/scanner.c';text=scanner.read_text();timing={}
    assert '.gain = ADC_GAIN_1_6' in text and '.reference = ADC_REF_INTERNAL' in text and '.resolution = 12' in text
    pins=(ROOT/'firmware/yeti60/board_pins.h').read_text()
    row_pin=int(re.search(r'#define PIN_ROW_DRV0 (\d+)',pins).group(1))
    clamp_pin=int(re.search(r'#define PIN_APLEX_OUT_PIN_0 (\d+)',pins).group(1))
    for name in ['debounce_frames','afe_settle_us','mux_settle_us','discharge_us','charge_us','acquisition_us']:
        found=re.search(r'\.'+name+r'\s*=\s*(\d+)',text);assert found,name;timing[name]=int(found.group(1))
    core=(ROOT/'firmware/yeti60/core.c').read_text()
    rise='io(s, PIN_APLEX_OUT_PIN_0, Y_OD_RELEASE);\n      io(s, yeti_rows[r], Y_HIGH);'
    fall='io(s, PIN_APLEX_OUT_PIN_0, Y_OD_LOW);\n      io(s, yeti_rows[r], Y_LOW);'
    assert core.count(rise)==core.count(fall)==1
    mutants={'correct':core,'rise-before-release':core.replace(rise,'io(s, yeti_rows[r], Y_HIGH);\n      io(s, PIN_APLEX_OUT_PIN_0, Y_OD_RELEASE);'),'fall-before-clamp':core.replace(fall,'io(s, yeti_rows[r], Y_LOW);\n      io(s, PIN_APLEX_OUT_PIN_0, Y_OD_LOW);')}
    curves={};samples=[];rejected=[];gain=1+electrical['feedback_ohm']/electrical['gain_ground_ohm']
    with tempfile.TemporaryDirectory(prefix='yeti60-waveform-') as folder:
        temp=Path(folder);(temp/'timing.h').write_text('#define TEST_CONFIG {'+','.join('.'+k+'='+str(v) for k,v in timing.items())+'}\n')
        binaries={}
        flags=[clang,'-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(ROOT/'firmware/yeti60')]
        for name,source in mutants.items():
            file=temp/(name+'.c');file.write_text(source);binary=temp/name
            subprocess.run(flags+['-I',str(temp),str(file),str(ROOT/'tests/yeti60/waveform.c'),'-o',str(binary)],check=True);binaries[name]=binary
            if name!='correct':
                reject=temp/(name+'-reject')
                subprocess.run(flags+[str(file),str(ROOT/'tests/yeti60/sim.c'),'-o',str(reject)],check=True)
                result=subprocess.run([str(reject)],text=True,capture_output=True)
                assert result.returncode!=0 and 'Assertion' in result.stderr,(name,result.stderr)
                rejected.append(dict(case=name,exit_code=result.returncode,output=result.stderr.strip()[-600:]))
        def simulate(name,key_pf,latency):
            result=subprocess.run([str(binaries[name]),str(latency)],text=True,capture_output=True,check=True)
            events=list(csv.DictReader(io.StringIO(result.stdout)))
            row=next(float(e['time_us']) for e in events if e['event']=='HIGH' and int(e['pin'])==row_pin)
            acquire=next(float(e['time_us']) for e in events if e['event']=='ACQUIRE')
            sample=next(float(e['time_us']) for e in events if e['event']=='SAMPLE')
            start=row-15;end=sample-start+2
            row_pwl=pwl(events,row_pin,{'LOW':0,'HIGH':cfg['row_drive_V_assumption']},0,start,end)
            clamp_pwl=pwl(events,clamp_pin,{'CLAMP':1,'RELEASE':0},1,start,end)
            circuit=f'''YETI60 selected-column RC sensitivity, {name}
Vrow drive 0 PWL({row_pwl})
Rrow drive row {electrical['row_ohm']+cfg['row_extra_driver_ohm_assumption']}
Ckey row col {key_pf}p
Rcolumn col 0 {electrical['column_ohm']}
Ccolumn col 0 {cfg['column_parasitic_pF_assumption']+4*cfg['other_four_key_capacitance_pF_each_assumption']}p
Rmux col sense {cfg['mux_on_ohm_assumption']}
C10 sense 0 {electrical['hold_F']}
Cparasitic sense 0 {cfg['bus_parasitic_pF_assumption']}p
Vclamp clamp 0 PWL({clamp_pwl})
Sdischarge sense 0 clamp 0 clamp_model
.model clamp_model SW(Ron={cfg['gpio_clamp_on_ohm_assumption']} Roff={cfg['gpio_clamp_off_ohm_assumption']} Vt=0.5 Vh=0)
* Ideal algebraic gain/rail proxy, NOT an OPA350 dynamic/stability model.
Bproxy proxy 0 V=min(max({gain}*v(sense),0),{cfg['row_drive_V_assumption']-cfg['amplifier_high_rail_headroom_V_assumption']})
.tran 0.01u {end:.6f}u 0 0.01u
.control
set wr_singlescale
set wr_vecnames
run
wrdata wave.dat v(sense) v(proxy)
quit
.endc
.end
'''
            (temp/'case.cir').write_text(circuit)
            run=subprocess.run([spice,'-b','case.cir'],cwd=temp,capture_output=True,text=True)
            assert run.returncode==0 and 'Error' not in run.stderr,run.stdout+run.stderr
            data=np.loadtxt(temp/'wave.dat',skiprows=1);at=(sample-start)*1e-6
            sense=float(np.interp(at,data[:,0],data[:,1]));proxy=float(np.interp(at,data[:,0],data[:,2]))
            falling=next(float(e['time_us']) for e in events if e['event']=='LOW' and int(e['pin'])==row_pin and float(e['time_us'])>=sample)
            post_fall=float(np.interp((falling-start+0.2)*1e-6,data[:,0],data[:,1]))
            scale=2**cfg['ADC_bits']
            record=dict(order=name,key_pF_assumed=key_pf,ADC_API_delay_us_assumed=latency,sample_after_row_us=sample-row,sense_at_sample_V=sense,ideal_gain_proxy_at_sample_V=proxy,ADC_code_proxy=max(0,min(scale-1,round(proxy/cfg['ADC_full_scale_V']*scale))),ideal_proxy_clipped_at_sample=gain*sense>=cfg['row_drive_V_assumption']-cfg['amplifier_high_rail_headroom_V_assumption'],sense_0_2us_after_row_fall_V=post_fall)
            if latency==0 and key_pf in [cfg['released_key_pF_assumption'],cfg['pressed_key_pF_assumption']]:curves[name,key_pf]=(data,row-start,acquire-row,sample-row)
            return record
        for name in mutants:
            for key in [cfg['released_key_pF_assumption'],cfg['pressed_key_pF_assumption']]:samples.append(simulate(name,key,0))
        sensitivities=[simulate('correct',key,delay) for key in cfg['key_pF_sensitivity'] for delay in cfg['ADC_API_latency_us_sensitivity']]
    def record(name,key):return next(s for s in samples if s['order']==name and s['key_pF_assumed']==key)
    correct_delta=record('correct',cfg['pressed_key_pF_assumption'])['ADC_code_proxy']-record('correct',cfg['released_key_pF_assumption'])['ADC_code_proxy']
    bad_delta=record('rise-before-release',cfg['pressed_key_pF_assumption'])['ADC_code_proxy']-record('rise-before-release',cfg['released_key_pF_assumption'])['ADC_code_proxy']
    assert correct_delta>32 and abs(bad_delta)<correct_delta/20,(correct_delta,bad_delta)
    for key in [cfg['released_key_pF_assumption'],cfg['pressed_key_pF_assumption']]:
        assert abs(record('correct',key)['ADC_code_proxy']-record('fall-before-clamp',key)['ADC_code_proxy'])<=1,'Cleanup must not retrospectively change the sampled value'
        assert abs(record('correct',key)['sense_0_2us_after_row_fall_V'])<abs(record('fall-before-clamp',key)['sense_0_2us_after_row_fall_V'])/20
    IMAGE.mkdir(exist_ok=True);outputs=[]
    for zh in [False,True]:
        if zh:
            for p in ['/System/Library/Fonts/PingFang.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf']:
                if Path(p).exists():font_manager.fontManager.addfont(p)
            plt.rcParams.update({'font.family':['Arial Unicode MS','PingFang SC','DejaVu Sans'],'svg.fonttype':'none','axes.unicode_minus':False})
        suffix='.zh-CN' if zh else '';fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True,layout='constrained')
        for name,color,style in [('correct','#147d64','-'),('rise-before-release','#c83b3b','--')]:
            for key,alpha in [(cfg['released_key_pF_assumption'],0.55),(cfg['pressed_key_pF_assumption'],1.0)]:
                data,row,acquire,sample=curves[name,key]
                label=({'correct':'修正顺序','rise-before-release':'先升行再释放'}[name]+f'，假设 {key:g} pF') if zh else f'{name}, assumed {key:g} pF'
                axes[0].plot(data[:,0]*1e6-row,data[:,1]*1000,style,color=color,alpha=alpha,label=label)
                axes[1].plot(data[:,0]*1e6-row,data[:,2],style,color=color,alpha=alpha)
        _,_,acquire,sample=curves['correct',cfg['released_key_pF_assumption']]
        for ax in axes:
            ax.axvline(0,color='#46526b',linewidth=0.8);ax.axvspan(acquire,sample,color='#97b7d1',alpha=0.2);ax.axvline(sample,color='#46526b',linestyle=':');ax.grid(alpha=.2)
        axes[0].plot([],[],':',color='#46526b',label='修正顺序的采样示意时刻' if zh else 'Correct-order sample proxy')
        axes[0].set_ylabel('感应节点（mV）' if zh else 'Sense node (mV)');axes[1].set_ylabel('理想增益／限幅示意（V）' if zh else 'Ideal gain/rail proxy (V)');axes[1].set_xlabel('相对行上升沿的时间（us）' if zh else 'Time from row rising edge (us)');axes[0].legend(fontsize=8,loc='upper right')
        fig.suptitle('RC 示例模型：实际网表与实际核心 GPIO 顺序\n按键电容、GPIO 耗时及寄生参数均为假设；实物仍待验收' if zh else 'Illustrative RC model: actual netlist + production core GPIO order\nKey capacitance, GPIO costs and parasitics are assumptions; physical qualification remains open',fontsize=11)
        for ext in ['png','svg']:
            p=IMAGE/('analog-waveform'+suffix+'.'+ext);fig.savefig(p,dpi=180);outputs.append(p)
            if ext=='svg':p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
        plt.close(fig)
    table=DOC/'analog-waveform-sensitivity.csv'
    with table.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(sensitivities[0]),lineterminator='\n');writer.writeheader();writer.writerows(sensitivities)
    outputs.append(table)
    files=[Path(__file__),inputs,netlist,reference,scanner,ROOT/'firmware/target/src/gpio_modes.h',ROOT/'firmware/target/src/scanner_control.c',ROOT/'firmware/target/src/scanner_control.h',target_check,ROOT/'firmware/yeti60/core.c',ROOT/'firmware/yeti60/core.h',ROOT/'firmware/yeti60/board_pins.h',ROOT/'tests/yeti60/sim.c',ROOT/'tests/yeti60/waveform.c']
    report=dict(status='model-regression-passed-physical-open',physical_verification=False,ngspice_version=version,tool_versions={'numpy':np.__version__,'matplotlib':matplotlib.__version__,'clang':subprocess.check_output([clang,'--version'],text=True).splitlines()[0]},netlist_electrical_values=electrical,nominal_closed_loop_gain=gain,scanner_timing=timing,order_mutants_rejected=rejected,illustrative_cases=samples,sensitivities=sensitivities,illustrative_correct_delta_ADC_codes=correct_delta,illustrative_wrong_rise_delta_ADC_codes=bad_delta,ADC_API_latency_qualified=False,key_capacitance_measured=False,opamp_dynamic_model=False,AFE_saturation_qualified=False,not_verified=['Actual NiZ capacitance, parasitic extraction, GPIO edge/driver timing','Real SAADC acquisition instant, software/USB/BLE preemption, offsets and noise','Op-amp stability/saturation recovery, mux charge injection, analog margins and physical interference'],source_sha256={str(p.relative_to(ROOT)):sha(p) for p in files},outputs={str(p.relative_to(ROOT)):sha(p) for p in outputs})
    report['diagnostic_counter']={'clock_hz':32768,'nominal_tick_us':1e6/32768,'one_tick_quantization_guard':True,'hardware_sample_timestamp':False,'absolute_time_accuracy_qualified':False}
    (AUD/'analog-waveform.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Actual-core rise/fall order mutants rejected; RC model correct/incorrect deltas:',correct_delta,bad_delta)
    print('Timing/capacitance sensitivities:',len(sensitivities),'(illustrative; no hardware qualification)')
if __name__=='__main__':main()
