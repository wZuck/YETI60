#!/usr/bin/env python3
"""Draw installed retainer stations from the current checked assembly bounds."""
import hashlib,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from e73_corner_harness_paths import point_at
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/e73-hhkb-corner'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 paths=[BASE/'audit/retention-study.json',BASE/'audit/retention-prints.json',BASE/'audit/harness-study.json']
 reports=[json.loads(p.read_text())for p in paths]
 for report in reports:
  for section in ['source_sha256','outputs']:
   for rel,digest in report[section].items():assert sha(ROOT/rel)==digest,('Stale retention drawing input',rel)
 study,prints,harness=reports;parts=study['variants'][0]['parts'];assert len(parts)==33 and len(prints['rigid_parts'])==16
 outputs={};plt.rcParams['font.family']=['Arial Unicode MS','DejaVu Sans'];plt.rcParams['svg.hashsalt']='yeti60-e73-retention'
 for zh in [False,True]:
  fig=plt.figure(figsize=(14,10),facecolor='#f3f1e8');gs=fig.add_gridspec(3,2,height_ratios=[1.1,1,1]);plan=fig.add_subplot(gs[0,:]);left=fig.add_subplot(gs[1,0]);right=fig.add_subplot(gs[1,1]);info=fig.add_subplot(gs[2,:]);info.axis('off')
  for ax in [plan,left,right]:
   ax.set_facecolor('#fbfaf5');ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)')
   ax.add_patch(Rectangle((228.5,-149),85,43,fc='#d9d8cb',ec='#787970',lw=.7))
   for family,wires in harness['variants'][0]['routes'].items():
    for path in wires.values():
     points=[]
     for segment in path:
      count=max(1,math.ceil(segment['length']/.4));points+=segment['points']if segment['kind']=='twist'else[point_at(segment,i/count)for i in range(count+1)]
     ax.plot([p[0]for p in points],[p[1]for p in points],color={'usb':'#315b83','power':'#a44e2d','battery':'#7d7a22'}[family],lw=.6,alpha=.7)
   for p in parts:
    x,y,z,X,Y,Z=p['bounds_case_mm'];film=p['film'];ax.add_patch(Rectangle((x,y),X-x,Y-y,fc='none'if film else'#457661',ec='#bb7026'if film else'#244738',lw=.7,ls='--'if film else'-',alpha=.9))
    if not film:
     label=p['name'];offset=(0,12)if p['mount']=='case-roof'else(8,-17)if label.startswith('BAT')else(0,-23)if label.startswith('PWR-R')else(12,14)
     if ax is plan and label in ['PWR-R1','PWR-R2','BAT-R2','USB-F1-lid','USB-F2-lid','PWR-F-lower']:continue
     if ax is plan and label=='BAT-R1':label='BAT-R1 / R2';offset=(4,-17)
     if ax is left:
      offset={'PWR-R1':(-23,-29),'PWR-R2':(28,-48),'BAT-R1':(0,21),'BAT-R2':(0,21),'PWR-F-upper':(-5,24),'PWR-F-lower':(10,-35)}.get(label,offset)
     if ax is right and label.startswith('USB-F'):offset=(-12,23)if label.endswith('base')else(15,-27)
     ax.annotate(label,((x+X)/2,(y+Y)/2),xytext=offset,textcoords='offset points',fontsize=8,ha='center',arrowprops=dict(arrowstyle='-',lw=.5,color='#59685e'))
  plan.set_xlim(112,352);plan.set_ylim(-169,-94);left.set_xlim(121,179);left.set_ylim(-132,-100);right.set_xlim(182,223);right.set_ylim(-164,-132)
  plan.set_title('安装坐标俯视：绿色为刚性件，橙色虚线为胶膜；不是打印排版'if zh else'Installed case-frame plan: green rigid parts, orange dashed films; not print layout',loc='left',fontsize=12)
  left.set_title('电源分线与电池后侧固定件'if zh else'Power fan-out and battery rear guides',loc='left',fontsize=11);right.set_title('USB 前侧底座和可拆盖'if zh else'USB front bases and removable lids',loc='left',fontsize=11)
  lines=['16 件刚性件＋17 片胶膜；每个编号各 1 件。胶膜 STEP 禁止打印。','打印件使用局部毫米 STL；安装位置使用 assembly-reference STEP。','支架成品三维表面点误差 ≤0.05 mm；剩余薄壁 ≥0.30 mm；粘接层名义 0.10 mm。','胶膜含胶总厚 ≤0.075 mm；模板折后按实际 STEP 包络修剪。','图示为经过检查的静态安装位置，不表示人手／工具装拆路径已验收。']if zh else['16 rigid parts + 17 film pieces; one per ID. Never print film STEP models.','Fabricate local-mm STL; locate installed parts using assembly-reference STEP.','Finished guide surface-point error <=0.05 mm; remaining web >=0.30 mm; nominal bondline 0.10 mm.','Film total thickness including adhesive <=0.075 mm; fold and trim blanks to the actual STEP envelope.','This is a checked static placement plan. Human/tool installation and service access remain open.']
  info.text(.01,.95,'\n\n'.join(lines),va='top',fontsize=11,color='#243e32');fig.suptitle('YETI60 / E73 / CORNER-05',x=.07,ha='left',fontweight='bold',fontsize=18);fig.subplots_adjust(top=.91,bottom=.03,left=.07,right=.97,hspace=.6,wspace=.3)
  for ext in ['png','svg']:
   p=ROOT/'docs/engineering/images'/('e73-retention'+('.zh-CN'if zh else'')+'.'+ext);fig.savefig(p,dpi=170,metadata={'Date':None}if ext=='svg'else{})
   if ext=='svg':p.write_text('\n'.join(line.rstrip()for line in p.read_text().splitlines())+'\n')
   outputs[str(p.relative_to(ROOT))]=sha(p)
  plt.close(fig)
 report=dict(status='source-bound-retainer-placement-plans-generated',physical_verification=False,source_sha256={str(p.relative_to(ROOT)):sha(p)for p in paths+[Path(__file__),ROOT/'scripts/e73_corner_harness_paths.py']},outputs=outputs)
 (BASE/'audit/retention-drawing.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'])
if __name__=='__main__':main()
