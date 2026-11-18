"""Continuous per-pin wire inclusion in physical E73 guide channels."""
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Ax2,gp_Pnt,gp_Dir
from cad_geometry import bounds
from check_yeti60_assembly import box,move
from check_e73_corner_harness import cut
from e73_fit_geometry import volume
from e73_corner_harness_paths import sweep_wire

def capture(part,wires,nominal_routes,spec,delta=0):
 name=part['name'];family=part['family'];x,y,z=part['datum_case_mm'];shift=delta if part['mount'].startswith('PCB')else 0;z+=shift;g=spec['guides'];profile=g['guide_print_tolerance'];depth=g['depth'];front=name.startswith('USB-F');axis=(0,1,0)if front else(1,0,0)
 slab=box([x-7,y-depth/2,-30,x+7,y+depth/2,30]if front else[x-depth/2,y-7,-30,x+depth/2,y+7,30]);pins=list(nominal_routes[family])
 if name=='PWR-F-upper':pins=['1']
 elif name=='PWR-F-lower':pins=['2']
 records=[]
 for pin in pins:
  if name.startswith('PWR-F'):
   channel=move(sweep_wire(nominal_routes[family][pin],2*(g['groove_radius']-profile)),z=shift)
  else:
   offset=0.;radius=g['groove_radius']-profile
   if family=='usb':
    if pin in ['2','3']:radius=g['pair_groove_radius']-profile
    else:
     offset=1.5 if pin=='1'else-1.5
     if front:offset*=1 if name.startswith('USB-F1')else-1
     else:offset*=-1
   elif family=='battery':offset={'1':2,'2':0,'3':-2}[pin]
   else:offset=-.5 if pin=='1'else .5
   origin=[x+offset,y-depth/2-.02,z]if front else[x-depth/2-.02,y+offset,z]
   channel=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*origin),gp_Dir(*axis)),radius,depth+.04).Shape()
  common=BRepAlgoAPI_Common(wires[family,pin],slab);common.Build();assert common.IsDone();local=common.Shape();v=volume(local);outside=volume(cut(local,channel))if v>1e-9 else 0
  records.append(dict(pin=pin,wire_volume_in_station_mm3=v,outside_shrunk_channel_mm3=outside,captured=v>.01 and outside<1e-6))
 return records

def bond_areas(film,by_name,epsilon=.005):
 """Estimate intended mating area with a small controlled inward translation.

 Flat, floating tape has zero bonded area and must not pass as a retaining
 strap. These are geometry checks, never adhesive-strength qualifications.
 """
 from cad_geometry import intersection_volume
 result=[];owner=film['bond_pair'];names=owner if isinstance(owner,list)else[owner]
 if film['folded_strap']:
  for sign in [-1,1]:
   shifted=move(film['shape'],y=sign*epsilon);area=intersection_volume(shifted,by_name[names[0]]['shape'])/epsilon;result.append(dict(owner=names[0],side=sign,estimated_contact_area_mm2=area,bonded=area>=.3))
 else:
  sign=1 if film['name'].endswith('-1')else-1
  shifted=move(film['shape'],**({'x':sign*epsilon}if film['name'].startswith('USB-F')else{'y':sign*epsilon}))
  for name in names:
   area=intersection_volume(shifted,by_name[name]['shape'])/epsilon;result.append(dict(owner=name,side=sign,estimated_contact_area_mm2=area,bonded=area>=.3))
 return result
