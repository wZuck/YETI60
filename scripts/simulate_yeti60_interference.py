#!/usr/bin/env python3
"""Run pinned TI OPA350 AC/transient models; never infer RF immunity from SPICE."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'.study-work/acceptance/spice'
URL='https://www.ti.com/lit/zip/sbom071'
ZIP_SHA='4a7d9342611e78eb5c49221bdfe18000ad6293564fd24aad239e0c7c176142e0'
MODEL_SHA='4fd8ddfc56c146339fde8c2874196765d92cbe755aa08347fd823d987c34180d'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def check_topology(path):
    tree=ET.parse(path)
    parts={c.attrib['ref']:c.findtext('value') for c in tree.findall('.//components/comp')}
    assert parts['R16']=='100k' and parts['R17']=='1k' and parts['C10']=='220p'
    nets={n.attrib['name']:{(x.attrib['ref'],x.attrib['pin']) for x in n} for n in tree.findall('.//nets/net')}
    for net,nodes in {'ADC':{('U3','6'),('R16','1')},'Net-(JP1-B)':{('U3','2'),('R16','2'),('R17','1')},
                      'APLEX_OUT_PIN_0':{('U3','3'),('C10','1'),('U2','3'),('U4','3')},
                      'GND':{('R17','2'),('C10','2')}}.items():
        assert nodes<=nets[net], 'AFE topology changed; bench must be reviewed'
    for col in range(15):
        bleeders=[ref for ref,pin in nets['COL'+str(col)] if ref.startswith('R') and parts.get(ref)=='100k' and (ref,'2') in nets['GND']]
        assert len(bleeders)==1


def read_vectors(path):
    return [[float(v) for v in row.split()] for row in path.read_text().splitlines()[1:] if row.strip()]


def nearest(rows,x):return min(rows,key=lambda r:abs(r[0]-x))


def run_bench(template,rmux,cload,c10,rshunt):
    circuit=template.replace('Rmux col sense 100',f'Rmux col sense {rmux}').replace('Cload out 0 10p',f'Cload out 0 {cload}p').replace('C10 sense 0 220p',f'C10 sense 0 {c10}p').replace('rshunt=1e12',f'rshunt={rshunt}')
    (CACHE/'bench.cir').write_text(circuit)
    # ngspice can exit zero after a failed analysis. Reject diagnostics AND missing/invalid vectors.
    for name in ['ac.txt','transient.txt']:(CACHE/name).unlink(missing_ok=True)
    run=subprocess.run(['ngspice','-b','bench.cir'],cwd=CACHE,capture_output=True,text=True,timeout=60)
    log=run.stdout+run.stderr
    assert run.returncode==0 and not any(w in log.lower() for w in ['error:', 'aborted', 'timestep too small']),log[-3000:]
    ac=read_vectors(CACHE/'ac.txt');tran=read_vectors(CACHE/'transient.txt')
    assert len(ac)>=300 and len(tran)>1000
    assert all(math.isfinite(v) for row in ac+tran for v in row)
    baseline=tran[0][2];end=tran[-1][2]
    assert 0.45<baseline<0.56 and 0.55<end<0.66, 'Invalid DC operating point'
    assert all(-.05<r[2]<3.35 for r in tran)
    gain=lambda row:math.hypot(row[1],row[2])
    assert 99<gain(ac[0])<103, 'Low-frequency gain must agree with 101x topology'
    record={'mux_ohm':rmux,'ADC_load_pF':cload,'C10_pF':c10,'rshunt_ohm':rshunt,
            'DC_output_V':baseline,'step_output_delta_mV':(end-baseline)*1000,
            'at_5us_after_step_delta_mV':(nearest(tran,25e-6)[2]-baseline)*1000,
            'at_45us_after_step_delta_mV':(nearest(tran,65e-6)[2]-baseline)*1000,
            'gain_10Hz_V_per_V':gain(ac[0]),
            'gain_1kHz_V_per_V':gain(nearest(ac,1e3)),
            'gain_100kHz_V_per_V':gain(nearest(ac,1e5)),
            'gain_1MHz_V_per_V':gain(ac[-1])}
    return record,ac,tran,log


def main():
    CACHE.mkdir(parents=True,exist_ok=True)
    assert shutil.which('ngspice'), 'Install ngspice to run the analog bench'
    package=CACHE/'sbom071.zip'
    if not package.exists():
        request=urllib.request.Request(URL,headers={'User-Agent':'YETI60 engineering audit'})
        with urllib.request.urlopen(request,timeout=45) as source:package.write_bytes(source.read())
    assert sha(package)==ZIP_SHA, 'Vendor model changed: review before accepting a new hash'
    with zipfile.ZipFile(package) as archive:(CACHE/'OPAx350.LIB').write_bytes(archive.read('OPAx350.LIB'))
    assert sha(CACHE/'OPAx350.LIB')==MODEL_SHA
    # Only a local work-directory initialization file; no user/global configuration changes.
    (CACHE/'.spiceinit').write_text('set ngbehavior=ltpsa\n')
    sources=[ROOT/'tests/interference/afe.cir',Path(__file__)]
    for folder in [ROOT,ROOT/'variants/raytac']:
        path=folder/'hardware/ec60-nrf52840/netlist.xml';check_topology(path);sources.append(path)
    template=sources[0].read_text();records=[]
    for rmux,cload,c10 in itertools.product([60,100,200],[5,10,50],[198,220,242]):
        record,*_=run_bench(template,rmux,cload,c10,'1e12');records.append(record)
    alt,*_=run_bench(template,100,10,220,'1e13');records.append(alt)
    nominal,ac,tran,log=run_bench(template,100,10,220,'1e12')
    assert abs(alt['DC_output_V']-nominal['DC_output_V'])<.001
    assert abs(alt['gain_10Hz_V_per_V']-nominal['gain_10Hz_V_per_V'])<.1
    outputs={}
    for filename,header,rows in [('afe-ac.csv',['frequency_Hz','out_real_V_per_V','out_imag_V_per_V'],ac),
                                 ('afe-transient.csv',['time_s','sense_V','out_V'],tran),
                                 ('afe-sensitivity.csv',list(records[0]),[list(r.values()) for r in records])]:
        path=ROOT/'docs/testing'/filename
        with path.open('w',newline='') as stream:
            writer=csv.writer(stream,lineterminator='\n');writer.writerow(header);writer.writerows(rows)
        outputs[str(path.relative_to(ROOT))]=sha(path)
    logpath=ROOT/'docs/testing/afe-ngspice.log';logpath.write_text('\n'.join(line.rstrip() for line in log.splitlines())+'\n');outputs[str(logpath.relative_to(ROOT))]=sha(logpath)
    report={'status':'analog-model-checks-passed-hardware-immunity-unverified','physical_test_performed':False,
            'production_approved':False,'engine':subprocess.check_output(['ngspice','--version'],text=True).splitlines()[1],
            'model':{'url':URL,'archive_sha256':ZIP_SHA,'member':'OPAx350.LIB','member_sha256':MODEL_SHA,
                     'version':'TI Final 1.5, 2022-06-01','redistributed':False},
            'topology':'Non-inverting OPA350, R16=100k, R17=1k, C10=220p, selected column bleeder=100k',
            'nominal':nominal,'sensitivity_cases':len(records),
            'calculation':{'ideal_noise_gain':101,'nominal_R_C_time_constant_us':100100*220e-12*1e6,
                           'nominal_R_C_pole_Hz':1/(2*math.pi*100100*220e-12)},
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},'outputs':outputs,
            'assumptions':['Mux Ron=60/100/200 ohm, ADC capacitive load=5/10/50pF are sensitivity assumptions, not measured or guaranteed values',
                           'C10=198/220/242pF is an imposed +/-10% sensitivity sweep; confirm fitted component tolerance',
                           '1mV disturbance at column bleeder ground with 5mV DC bias; not a measured keyboard disturbance',
                           'rshunt=1e12 required for TI-model convergence; alternate 1e13 DC/gain cross-check within 1mV/0.1V/V'],
            'not_verified':['No extracted key/mutual capacitances, mux switching charge injection or ADC sample-and-hold model',
                            'No power-regulator or charger switching model or RF rectification; AC sweep stops at 1MHz',
                            'No 2.4GHz radiated susceptibility, USB eye, ESD or whole-board electromagnetic simulation',
                            'No physical pressed/released distributions or calibrated noise margin']}
    (ROOT/'docs/audit/interference-analog.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'cases':len(records),'nominal':nominal},indent=2))


if __name__=='__main__':main()
