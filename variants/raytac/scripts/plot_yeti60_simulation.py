#!/usr/bin/env python3
"""Plot actual host-simulation trace data; never synthesize hardware measurements."""
import csv,hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];TRACE=ROOT/'docs/audit/yeti60-firmware-trace.csv';OUT=ROOT/'renders/yeti60-firmware';OUT.mkdir(exist_ok=True)
plt.rcParams['svg.hashsalt']='YETI60'
rows=[r for r in csv.DictReader(TRACE.open()) if r['scenario']=='single-keys'][:4];assert len(rows)==4
x=[(int(r['time_us'])-int(rows[0]['time_us']))/1000 for r in rows];y=[int(r['sample_0_0']) for r in rows];pressed=[int(r['pressed_0_0']) for r in rows]
fig,(a,b)=plt.subplots(2,1,figsize=(10,5.8),sharex=True,gridspec_kw={'height_ratios':[2,1]},layout='constrained')
a.step(x,y,where='post',color='#21745d',label='Mock ADC sample');a.scatter(x,y,color='#21745d');a.axhline(2000,ls='--',color='#bc7756',label='Press threshold');a.axhline(1500,ls=':',color='#586f9b',label='Release threshold');a.set_ylabel('ADC code');a.legend(loc='upper right',ncol=3,fontsize=8);a.grid(alpha=.2)
b.step(x,pressed,where='post',color='#364f72');b.scatter(x,pressed,color='#364f72');b.set_yticks([0,1],['Released','Pressed']);b.set_ylim(-.25,1.3);b.set_xlabel('Modeled time from first completed frame (ms)');b.grid(alpha=.2)
fig.suptitle('YETI60 host-simulated two-frame debounce\nActual core trace; ADC/GPIO mocked, time includes configured waits only',fontsize=13)
fig.savefig(OUT/'debounce.png',dpi=180);fig.savefig(OUT/'debounce.svg',metadata={'Date':None});plt.close(fig)
# Matplotlib SVG paths contain harmless line-end spaces; normalize for Git.
svg=OUT/'debounce.svg';svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'plot-manifest.json').write_text(json.dumps({'trace_sha256':sha(TRACE),'recipe_sha256':sha(Path(__file__)),'matplotlib':matplotlib.__version__,'outputs':{p.name:sha(p) for p in [OUT/'debounce.png',OUT/'debounce.svg']},'limits':'First four successful single-key frames only; mock ADC/GPIO and wait-based model clock, not physical latency or noise'},indent=2)+'\n')
print('YETI60 trace-derived PNG/SVG plot complete')
