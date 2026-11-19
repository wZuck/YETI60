#!/usr/bin/env python3
"""Draw source-bound case-frame routing plans and export nine lead targets."""
import csv,hashlib,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
from e73_corner_harness_paths import point_at
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/e73-hhkb-corner'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 report_path=BASE/'audit/harness-study.json';r=json.loads(report_path.read_text());assert r['status']=='continuous-wire-study-passed-guides-open'and not r['failures']and len(r['variants'])==3
 for p,h in r['source_sha256'].items():assert sha(ROOT/p)==h,('Stale harness drawing input',p)
 s=json.loads((ROOT/'hardware/e73-corner-harness-spec.json').read_text());a=json.loads((ROOT/'mechanical/assembly-spec.json').read_text());c=json.loads((ROOT/'.assembly-work/e73-corner/copper.json').read_text());assert c['source_sha256']['hardware/e73-hhkb-corner/EC60-nRF52840.kicad_pcb']==sha(BASE/'EC60-nRF52840.kicad_pcb');nominal=r['variants'][0];outputs={}
 target=BASE/'mechanical/harness-conductors.csv';rows=[]
 for w in nominal['wires']:
  f,pin=w['family'],w['pin'];ref={'usb':'J4','power':'J5','battery':'J2'}[f];far={'usb':'C5','power':'J1','battery':'pack'}[f];far_pin=pin if f=='usb'else ('1'if pin=='1'else'4')if f=='power'else{'1':'PACK+','2':'PACK-','3':'NTC'}[pin]
  rows.append(dict(Harness=f,MainboardReference=ref,MainboardPin=pin,FarReference=far,FarPin=far_pin,Color=s[f]['colors'][pin],FreeLength_mm=f'{w["free_length_mm"]:.3f}',Definition='Insulation between housing exit planes / pack strain-relief face; not cut length',Status='Engineering target; retention and supplier crimp qualification open'))
 with target.open('w',newline='')as f:writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");writer.writeheader();writer.writerows(rows)
 outputs[str(target.relative_to(ROOT))]=sha(target)
 target=BASE/'mechanical/harness-conductors.zh-CN.csv'
 with target.open('w',newline='')as f:
  writer=csv.writer(f,lineterminator="\n");writer.writerow(['线束','主板位号','主板针号','远端位号','远端针号','颜色','自由长度_mm','长度定义','状态'])
  for row in rows:writer.writerow([{'usb':'USB','power':'电源桥','battery':'电池'}[row['Harness']],row['MainboardReference'],row['MainboardPin'],row['FarReference'],row['FarPin'],{'red':'红','black':'黑','white':'白','green':'绿','yellow':'黄'}[row['Color']],row['FreeLength_mm'],'两插头出口面／保护包应力释放面之间的绝缘长度，不是裁线长度','工程目标；固定件及供应商压接仍待验收'])
 outputs[str(target.relative_to(ROOT))]=sha(target)
 plt.rcParams['font.family']=['Arial Unicode MS','DejaVu Sans'];plt.rcParams['svg.hashsalt']='yeti60-e73-corner-harness'
 for zh in [False,True]:
  fig=plt.figure(figsize=(14,9),facecolor='#f3f1e8');grid=fig.add_gridspec(2,2,height_ratios=[1.25,1],width_ratios=[1.1,1]);ax=fig.add_subplot(grid[0,:]);zoom=fig.add_subplot(grid[1,0]);info=fig.add_subplot(grid[1,1]);info.axis('off')
  for view in [ax,zoom]:
   view.set_facecolor('#fbfaf5')
   for q in c['outline']:view.add_patch(Polygon([(x,-y)for x,y in q['outer']],closed=True,facecolor='#dfe9dc',edgecolor='#58725b',lw=.7))
   x,y,X,Y=a['battery']['bounds_xy'];view.add_patch(Rectangle((x,y),X-x,Y-y,fc='#d3d3ca',ec='#73756c',alpha=.8,zorder=2))
   for family,wires in nominal['routes'].items():
    for pin,path in wires.items():
     points=[]
     for p in path:points+=p['points']if p['kind']=='twist'else[point_at(p,i/max(1,math.ceil(p['length']/.25)))for i in range(max(1,math.ceil(p['length']/.25))+1)]
     color=s[family]['colors'][pin];color={'white':'#808c95','yellow':'#b19004','green':'#26835a','black':'#242727','red':'#bc4538'}[color];view.plot([p[0]for p in points],[p[1]for p in points],lw=.9,color=color,zorder=4,ls='--'if family=='battery'else'-')
   for name,point in r['connector_exits_case_mm'].items():
    view.plot(point[0],point[1],marker='o',ms=3,color='#173e34',zorder=5);view.annotate('电池包'if zh and name=='pack'else name,(point[0],point[1]),xytext=(4,-10 if name=='J5'else 5),textcoords='offset points',fontsize=9,fontweight='bold')
   view.set_aspect('equal');view.grid(alpha=.15);view.set_xlabel('X (mm)');view.set_ylabel('Y (mm)')
  ax.set_xlim(91,359);ax.set_ylim(-200,-94);zoom.set_xlim(311,353);zoom.set_ylim(-138,-98)
  ax.set_title('九根导线坐标图：从上方透视主板下方线束；固定件仍待完成'if zh else'Nine-conductor case-frame plan: PCB shown transparent; retainers open',loc='left',fontsize=13,pad=12)
  zoom.set_title('J4／旋转后的 J5：真实出口及前侧绕行'if zh else'J4 / rotated J5: native exits and front detour',loc='left',fontsize=11)
  text=['线束 / 针    自由长度 mm'if zh else'Harness / pin    Free length mm']+[f'{({"usb":"USB","power":"电源桥","battery":"电池"}[w["family"]]if zh else w["family"]):8s} {w["pin"]:>2s}     {w["free_length_mm"]:8.3f}'for w in nominal['wires']]
  text+=['','含公差绝缘外径 ≤0.65 mm；不是裁线长度'if zh else'Insulation OD incl. tolerance <=0.65 mm; not cut lengths','USB 数据对几何等长；不代表阻抗／实物验收'if zh else'USB data geometrically matched; impedance/physical tests open','M04 内部线槽；外壳外包围尺寸保持'if zh else'M04 internal channel; exterior envelope retained','工程示意；不是照片、理线件或整机装配放行'if zh else'Engineering plan, not a photo or complete assembly release']
  info.text(.01,.97,'\n'.join(text),transform=info.transAxes,va='top',fontsize=10,linespacing=1.6)
  fig.suptitle('YETI60 / E73 / CORNER-06',x=.07,ha='left',fontweight='bold',fontsize=18);fig.subplots_adjust(top=.9,left=.07,right=.97,bottom=.07,hspace=.35,wspace=.2)
  for ext in ['png','svg']:
   target=ROOT/'docs/engineering/images'/('e73-corner-harness'+('.zh-CN'if zh else'')+'.'+ext);fig.savefig(target,dpi=160,metadata={'Date':None}if ext=='svg'else{});
   if ext=='svg':target.write_text('\n'.join(line.rstrip()for line in target.read_text().splitlines())+'\n')
   outputs[str(target.relative_to(ROOT))]=sha(target)
  plt.close(fig)
 report=dict(status='source-bound-nine-lead-plans-generated',physical_verification=False,manufacturing_released=False,source_sha256={str(p.relative_to(ROOT)):sha(p)for p in [report_path,ROOT/'hardware/e73-corner-harness-spec.json',ROOT/'mechanical/assembly-spec.json',BASE/'EC60-nRF52840.kicad_pcb',Path(__file__),ROOT/'scripts/e73_corner_harness_paths.py']},outputs=outputs)
 (BASE/'audit/harness-drawing.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':main()
