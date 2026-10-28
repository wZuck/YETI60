#!/usr/bin/env python3
"""Source-sized CAD engineering assembly sheets, separate English/Chinese assets."""
import hashlib,json,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle,Circle,FancyBboxPatch
from matplotlib import font_manager
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/engineering/images';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
M=ROOT/'.assembly-work/render-meshes.json';mesh=json.loads(M.read_text());fitpath=ROOT/'docs/audit/yeti60-assembly.json';fit=json.loads(fitpath.read_text());assert mesh['assembly_report_sha256']==sha(fitpath)
for p,h in fit['source_sha256'].items():assert sha(ROOT/p)==h
plt.rcParams.update({'svg.fonttype':'path','svg.hashsalt':'YETI60-P2','font.size':9,'axes.edgecolor':'#cbd5df','text.color':'#183246','axes.labelcolor':'#183246','savefig.facecolor':'#f6f8fa'})
from export_yeti60_render_meshes import tessellate
UDB=ROOT/'.assembly-work/daughterboard/daughterboard.step'
udb_report=json.loads((ROOT/'docs/audit/yeti60-daughterboard.json').read_text());assert sha(UDB)==udb_report['exported_step_sha256']
udb=tessellate(UDB);uspec=json.loads((ROOT/'mechanical/assembly-spec.json').read_text())['daughterboard']
for v in udb['vertices_mm']:v[0]+=uspec['source_to_case_x_offset'];v[1]+=uspec['source_to_case_y_offset'];v[2]+=uspec['pcb_bottom_z']
mesh['meshes']['daughterboard']=udb
COL={'daughterboard':'#547a83','bottom':'#a1abb3','top':'#adb7bd','plate':'#c8d2d8','pcb':'#36836c'}

def projected(v,offset=0):
 v=np.asarray(v,dtype=float).copy();v[:,0]-=214.312707;v[:,1]+=153.70968;v[:,2]+=offset
 return np.column_stack((.94*v[:,0]+.34*v[:,1],-.12*v[:,0]+.48*v[:,1]+.90*v[:,2]))
def cad(ax,name,offset):
 d=mesh['meshes'][name];v=np.array(d['vertices_mm']);tris=np.array(d['triangles']);p=projected(v,offset);depth=v[:,2]+offset-v[:,1]*.65
 ids=np.argsort(np.mean(depth[tris],axis=1));poly=PolyCollection(p[tris[ids]],facecolors=COL[name],edgecolors='none',rasterized=True);ax.add_collection(poly)
def rect3(ax,bb,offset,color,alpha=1):
 x,y,z,X,Y,Z=bb;v=np.array([[a,b,c] for a,b,c in [(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)]]);p=projected(v,offset)
 faces=[[0,1,2,3],[0,1,5,4],[1,2,6,5],[3,2,6,7],[0,3,7,4],[4,5,6,7]];ax.add_collection(PolyCollection(p[faces],facecolors=color,edgecolors='#52646d',linewidths=.22,alpha=alpha))
def label(ax,text,xyz,loc):
 q=projected([xyz])[0];ax.annotate(text,q,xytext=loc,fontsize=9,ha='left',va='center',arrowprops={'arrowstyle':'-','lw':.7,'color':'#526879'},bbox={'fc':'#f6f8fa','ec':'none','pad':2})
def dim(ax,a,b,text,x=7):
 ax.annotate('',(x,a),(x,b),arrowprops={'arrowstyle':'<->','lw':.7,'color':'#385e74'});ax.text(x+.7,(a+b)/2,text,va='center',fontsize=8)
def title(ax,n,t):ax.text(0,1.03,n+'  '+t,transform=ax.transAxes,fontsize=13,fontweight='bold')
def save(fig,stem):
 for ext in ['svg','png']:fig.savefig(OUT/(stem+'.'+ext),dpi=170,bbox_inches='tight',metadata={'Date':None} if ext=='svg' else None)
 for p in [OUT/(stem+'.svg')]:p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
 plt.close(fig)

def main():
 outputs={}
 for zh in [False,True]:
  font=font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc' if zh else '/System/Library/Fonts/Helvetica.ttc');plt.rcParams['font.family']=font.get_name()
  fig=plt.figure(figsize=(16,12),facecolor='#f6f8fa');gs=fig.add_gridspec(2,2,width_ratios=[2.05,1],height_ratios=[1.1,1],hspace=.23,wspace=.12);ax=fig.add_subplot(gs[:,0]);ax.set_aspect('equal');ax.axis('off')
  title(ax,'01','总成分解图' if zh else 'Assembly exploded view')
  cad(ax,'bottom',0)
  cad(ax,'daughterboard',15)
  cad(ax,'pcb',90)
  for h in fit['mounting_hole_matches']:
   x,y=h['pcb_center_case_mm'];rect3(ax,[x-1.75,y-1.75,-.31,x+1.75,y+1.75,4.19],90,'#b69b55')
  p=fit['battery_candidates'][0]['bounds_case_mm'];rect3(ax,p,35,'#849c72')
  cad(ax,'plate',160)
  for k in fit['active_key_positions']:rect3(ax,[k['x']-6.9,k['y']-6.6,5.39,k['x']+6.9,k['y']+6.6,10.9],160,'#57616b')
  cad(ax,'top',230)
  for k in fit['active_key_positions']:rect3(ax,[k['x']-7,k['y']-7,12.3,k['x']+7,k['y']+7,19],300,'#ded8c8')
  for txt,xyz,loc in [
   (('M08 60 个键帽，外形示意' if zh else 'M08 60 caps, shape illustrative'),(340,-170,319),(175,300)),
   (('M01 上壳，原尺寸派生 CAD' if zh else 'M01 Top shell, derived unscaled CAD'),(345,-190,236),(175,235)),
   (('M03–M07 定位板及 60 套感应机构' if zh else 'M03–M07 Plate + 60 EC mechanisms'),(345,-180,167),(175,170)),
   (('M09–M12 29 套支柱／绝缘／螺钉' if zh else 'M09–M12 29 fastener/insulator sets'),(340,-170,93),(175,116)),
   (('主板，成品厚 1.59 mm' if zh else 'Main PCB, 1.59 mm finished'),(345,-180,88),(175,94)),
   (('默认电池包 85×43×4.8 mm' if zh else 'Default pack 85 x 43 x 4.8 mm'),(313,-128,30),(175,43)),
   (('M02 底壳，含嵌件孔及检修孔' if zh else 'M02 Bottom, insert seats/service port'),(345,-175,-5),(175,-22))]:label(ax,txt,xyz,loc)
  ax.set_xlim(-181,335);ax.set_ylim(-59,340);ax.set_anchor('N')
  label(ax,('后侧 USB 子板，原生 CAD' if zh else 'Rear USB daughterboard, native CAD'),(214.3,-111,7),(175,14))
  ax.text(-175,-50,('外壳包围尺寸 325.700×125.200×31.190 mm；分解高度仅为示意' if zh else 'Case envelope 325.700 x 125.200 x 31.190 mm; exploded offsets are illustrative'),fontsize=9)
  side=fig.add_subplot(gs[0,1]);title(side,'02','紧固件剖面 / mm' if zh else 'Fastener section / mm');side.set_xlim(-7,18);side.set_ylim(-5.4,7);side.axis('off')
  for bb,col in [((-6,4.19,12,1.2),'#acbbc3'),((-6,-2,12,1.59),'#36836c'),((-1.75,-.31,3.5,4.5),'#b69b55'),((-2.25,-.41,4.5,.1),'#d4a741'),((-3,-2.8,6,.8),'#7793a1'),((-.8,-2.8,1.6,5),'#b4bcc3'),((-1.6,-3.9,3.2,1.1),'#8999a2'),((-1,4.19,2,1),'#b69b55')]:side.add_patch(Rectangle(bb[:2],bb[2],bb[3],fc=col,ec='#294453',lw=.5))
  dim(side,-.41,4.19,'4.60',8);dim(side,-2,-.41,'1.59',11);side.text(-6,5.8,('1.2 不锈钢板，M2 螺纹' if zh else '1.2 stainless plate, M2 threads'),fontsize=9)
  side.text(-6,-5,('4.50 黄铜肩 + 0.10 绝缘膜\nPEEK 垫片 0.8；M1.6×5 螺钉' if zh else '4.50 brass shoulder + 0.10 film\n0.8 PEEK washer; M1.6 x 5 screw'),fontsize=9)
  boxax=fig.add_subplot(gs[1,1]);title(boxax,'03','接线及装配顺序' if zh else 'Connections and sequence');boxax.axis('off')
  texts=(['后侧 USB 子板 → 主板 J1','1 VBUS  2 D−  3 D+  4 GND','电池 → J2：1 正极 2 地 3 NTC','J3：1 3.3V  2 SWDIO  3 地','      4 SWDCLK  5 复位 6 地','','① 冷粘嵌件并检查螺纹','② 组装定位板、轴座和胶碗弹簧','③ 绝缘支柱后固定 PCB','④ 固定子板／电池，逐线检查极性','⑤ 校准后合壳并检查行程','','轴座／键帽为示意；不是公差验收图'] if zh else ['Rear USB daughterboard -> main J1','1 VBUS   2 D-   3 D+   4 GND','Battery -> J2: 1 +   2 GND   3 NTC','J3: 1 3.3V  2 SWDIO  3 GND','    4 SWDCLK  5 RESET  6 GND','','1  Cold-bond inserts; inspect threads','2  Plate, housings, domes and springs','3  Insulate standoffs; fasten PCB','4  Secure UDB/pack; check every pin','5  Calibrate, close case, check travel','','Housing/cap shapes illustrative; not an acceptance drawing'])
  boxax.text(0,.98,'\n'.join(texts),va='top',fontsize=9,linespacing=1.7)
  fig.suptitle('YETI60  /  '+('工程装配图  ·  默认 P2' if zh else 'Engineering assembly  /  Default P2'),x=.05,ha='left',fontsize=20,fontweight='bold');fig.subplots_adjust(top=.89,left=.04,right=.97,bottom=.07)
  stem='assembly.zh-CN' if zh else 'assembly';save(fig,stem)
  # Default pocket, actual case-frame axes and thickness section, independently dimensioned.
  pocket=json.loads((ROOT/'docs/audit/yeti60-battery-pocket.json').read_text());spec=json.loads((ROOT/'mechanical/battery-pocket-study.json').read_text());pb=spec['pocket_bounds_case_mm'];bb=spec['pack_bounds_case_mm'];fig,(plan,sec)=plt.subplots(1,2,figsize=(15,7),gridspec_kw={'width_ratios':[1.5,1]},facecolor='#f6f8fa')
  title(plan,'01','底壳内部俯视 / mm' if zh else 'Bottom interior plan / mm')
  d=mesh['meshes']['bottom'];v=np.asarray(d['vertices_mm']);tri=np.asarray(d['triangles']);plan.add_collection(PolyCollection(v[tri,:2],facecolors='#d8dfe3',edgecolors='none',rasterized=True))
  for e in fit['component_envelopes']:
   b=e['bounds_case_mm'];plan.add_patch(Rectangle((b[0],b[1]),b[3]-b[0],b[4]-b[1],fc='#6d7c87',alpha=.6,lw=.2))
  for h in fit['mounting_hole_matches']:plan.add_patch(Circle(h['pcb_center_case_mm'],3,fc='none',ec='#607f90',lw=.5))
  for b,c,txt in [(bb,'#5c94af','1600 mAh')]:
   plan.add_patch(Rectangle((b[0],b[1]),b[3]-b[0],b[4]-b[1],fc=c,ec='#234c62',alpha=.85));plan.text((b[0]+b[3])/2,(b[1]+b[4])/2,txt,ha='center',va='center',fontsize=9)
  plan.add_patch(FancyBboxPatch((pb[0],pb[1]),pb[3]-pb[0],pb[4]-pb[1],boxstyle='round,pad=0,rounding_size=1',fc='none',ec='#cf792e',lw=1.6))
  plan.plot([pb[0]-4,pb[3]+4],[pb[1],pb[1]],'--',c='#c26e2e',lw=1);plan.text(pb[3]+6,pb[1],'A–A',va='center');plan.set_xlim(48,380);plan.set_ylim(-211,-91);plan.set_aspect('equal');plan.set_xlabel('X / mm');plan.set_ylabel('Y / mm');plan.grid(alpha=.15)
  plan.text(55,-204,('P2 默认单电芯；完整电池包仍须供方签图' if zh else 'P2 default single cell; supplier pack drawing required'),fontsize=9)
  title(sec,'02','A–A 临界剖面，电池包为投影 / mm' if zh else 'A–A critical section, pack projected / mm')
  # Display a cut normal to X at the most critical front edge of the recess.
  n=pocket['underside_plane']['normal'];p=pocket['underside_plane']['point'];y=pb[1];outer=p[2]-(n[1]*(y-p[1])+n[0]*((pb[0]+pb[3])/2-p[0]))/n[2]
  left,right=pb[0]-5,pb[3]+5;floor=pb[2]
  sec.fill_between([left,right],[outer,outer],[-5.91,-5.91],color='#d8dfe3');sec.add_patch(Rectangle((pb[0],floor),pb[3]-pb[0],8,fc='#f6f8fa'));sec.add_patch(Rectangle((bb[0],bb[2]),bb[3]-bb[0],bb[5]-bb[2],fc='#5c94af',ec='#234c62'));sec.plot([left,right],[-5.91,-5.91],'--',c='#c26e2e',lw=.8);sec.plot([left,right],[-2,-2],c='#36836c',lw=3)
  sec.text(bb[0],-1.2,('PCB 底面 z = −2.00' if zh else 'PCB underside z = -2.00'),fontsize=9);sec.text(bb[0]+3,-7,('完整包络 85×43×4.8\n含保护板／NTC／包覆／增长余量' if zh else 'Full envelope 85 x 43 x 4.8\nPCM / NTC / wrap / growth included'),fontsize=8)
  sec.text(bb[0],-11.3,('槽底 z = −9.60\n原内底 z = −5.91，去料深 3.69' if zh else 'Pocket floor z = -9.60\nOriginal floor -5.91; depth 3.69'),fontsize=8)
  sec.annotate('',(right+2,outer),(right+2,floor),arrowprops={'arrowstyle':'<->','lw':.8});sec.text(right+3,(outer+floor)/2,('法向最小 3.959\n扣公差后 3.659' if zh else 'Normal min 3.959\n3.659 after tolerance'),va='center',fontsize=8)
  sec.set_xlim(left-1,right+38);sec.set_ylim(-16,0);sec.set_xlabel('X / mm');sec.set_ylabel('Z / mm');sec.grid(alpha=.15)
  fig.suptitle('YETI60  /  '+('默认 1600 mAh 电池槽' if zh else 'Default 1600 mAh battery recess'),fontsize=20,fontweight='bold',x=.06,ha='left');fig.subplots_adjust(top=.81,wspace=.24,bottom=.15)
  save(fig,'battery-pocket.zh-CN' if zh else 'battery-pocket')
 for p in OUT.iterdir():
  if p.suffix in ['.png','.svg']:outputs[str(p.relative_to(ROOT))]=sha(p)
 report={'status':'generated','recipe_sha256':sha(Path(__file__).resolve()),'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [fitpath,ROOT/'docs/audit/yeti60-battery-pocket.json',ROOT/'mechanical/assembly-spec.json',ROOT/'mechanical/battery-pocket-study.json',ROOT/'docs/audit/yeti60-daughterboard.json',ROOT/'scripts/export_yeti60_daughterboard.py']},'geometry_sources':mesh['geometry_sources'],'mesh_export_recipe_sha256':mesh['export_recipe_sha256'],'outputs':outputs,'limits':['Exploded offsets are for presentation, original case meshes are unscaled','Thread/housing/keycap envelopes schematic; CAD is not a first-article acceptance','Default custom pack still requires a supplier-signed drawing and physical acceptance']}
 (ROOT/'docs/audit/yeti60-assembly-drawings.json').write_text(json.dumps(report,indent=2)+'\n');print('English and Chinese assembly/pocket engineering sheets generated')
if __name__=='__main__':main()
