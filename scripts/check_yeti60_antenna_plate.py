#!/usr/bin/env python3
"""BRep plate projection near antennas; never equate proximity with RF attenuation."""
import csv
import hashlib
import json
import math
from pathlib import Path
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from cad_geometry import intersection_volume
from check_yeti60_assembly import build_plate
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    spec=ROOT/'mechanical/assembly-spec.json';stack=json.loads(spec.read_text())['stack']
    z=stack['plate_bottom_z'];thickness=stack['plate_thickness']
    assert thickness==1.2
    plate,_=build_plate(z)
    layout=ROOT/'docs/audit/interference-layout.json';variants=json.loads(layout.read_text())['variants']
    result={}
    for name,data in variants.items():
        x0,y0,x1,y1=data['screen_bounds_mm']
        column=BRepPrimAPI_MakeBox(gp_Pnt(x0,-y1,z),x1-x0,y1-y0,thickness).Shape()
        area=intersection_volume(plate,column)/thickness
        result[name]={'metal_plate_projection_mm2':area,'screen_area_mm2':data['screen_area_mm2'],
                      'nearest_module_mounting_plane_to_plate_mm':stack['pcb_to_plate_gap']+stack['pcb_thickness'],
                      'status':'nearby-metal-requires-antenna-qualification' if area>1e-6 else 'projection-clear-nearby-metal-still-unqualified',
                      'limits':'Projected plate metal, not a physical collision or computed RF loss. Antenna conductor Z is not supplied by vendor.'}
    fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    with (ROOT/'docs/testing/afe-ac.csv').open() as s:ac=list(csv.DictReader(s))
    axes[0].semilogx([float(r['frequency_Hz']) for r in ac],[20*math.log10(math.hypot(float(r['out_real_V_per_V']),float(r['out_imag_V_per_V']))) for r in ac])
    axes[0].set(xlabel='Frequency (Hz)',ylabel='Disturbance gain (dB)',title='TI OPA350 model / actual feedback topology')
    with (ROOT/'docs/testing/afe-transient.csv').open() as s:tran=list(csv.DictReader(s))
    base=float(tran[0]['out_V'])
    axes[1].plot([float(r['time_s'])*1e6 for r in tran],[(float(r['out_V'])-base)*1e3 for r in tran])
    axes[1].set(xlabel='Time (us)',ylabel='Output change (mV)',title='Assumed 1mV disturbance starts at 20us')
    for ax in axes:ax.grid(True,alpha=.25)
    fig.suptitle('Model sensitivity only: no measured key capacitance or RF coupling',fontsize=11)
    image=ROOT/'docs/testing/images/afe-disturbance.png';fig.savefig(image,dpi=170)
    axes[0].set(xlabel='频率（Hz）',ylabel='扰动增益（dB）',title='TI OPA350 模型／实际反馈拓扑')
    axes[1].set(xlabel='时间（us）',ylabel='输出变化（mV）',title='假设 1mV 扰动从 20us 开始')
    fig.suptitle('仅为模型敏感性：未测实际按键电容或射频耦合',fontsize=11)
    font=font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc')
    for text in [fig._suptitle,*[t for ax in axes for t in [ax.title,ax.xaxis.label,ax.yaxis.label]]]:text.set_fontproperties(font)
    zh_image=ROOT/'docs/testing/images/afe-disturbance.zh-CN.png';fig.savefig(zh_image,dpi=170);plt.close(fig)
    sources=[layout,spec,ROOT/'mechanical/felk60_plate_hhkb.audited.dxf',ROOT/'scripts/check_yeti60_assembly.py',
             ROOT/'scripts/cad_geometry.py',ROOT/'docs/testing/afe-ac.csv',ROOT/'docs/testing/afe-transient.csv',Path(__file__)]
    report={'status':'plate-proximity-screen-completed','physical_test_performed':False,'production_approved':False,
            'variants':result,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},
            'outputs':{str(p.relative_to(ROOT)):sha(p) for p in [image,zh_image]}}
    (ROOT/'docs/audit/interference-plate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
