"""E73 retention study, adapted from the project Raytac geometry helper."""
import math
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Fuse
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Pnt,gp_Ax2,gp_Dir
from check_yeti60_assembly import box
from check_yeti60_interconnects import conformal_base,surface_z
from e73_corner_harness_paths import sweep_wire

def boolean(a,b,op):
    q=op(a,b);q.Build();assert q.IsDone() and BRepCheck_Analyzer(q.Shape()).IsValid();return q.Shape()
def slot(shape,axis,origin,length,radius):
    cutter=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*origin),gp_Dir(*axis)),radius,length).Shape();return boolean(shape,cutter,BRepAlgoAPI_Cut)
def build(spec,case,routes,exits,pcb_bottom=-2):
    g=spec['guides'];depth=g['depth'];bond=g['bond_gap'];pair=g['pair_groove_radius'];r=g['groove_radius'];items=[];films=[]
    def add(name,shape,mount,family,center,bond_pair=None):
        items.append({'name':name,'shape':shape,'mount':mount,'family':family,'datum_case_mm':center,'bond_pair':bond_pair})
    def film(name,bb):
        # Model the complete folded strap, including its two bonding legs.
        # Flat tape floating below a groove is not a retained assembly.
        t=g['retention_film_thickness'];above=name.startswith('BAT-')
        if above:bb[5]=bb[2]+t
        else:bb[2]=bb[5]-t
        shape=box(bb)
        owner=next(q for q in items if q['name']==name.removesuffix('-film'))
        z=owner['datum_case_mm'][2];end=z-(.4 if above else -.7)
        if name=='PWR-F-lower-film':end=z+.5
        lo=min(bb[2],end);hi=max(bb[5],end)
        for a,b in [(bb[1]-t,bb[1]),(bb[4],bb[4]+t)]:
            shape=boolean(shape,box([bb[0],a,lo,bb[3],b,hi]),BRepAlgoAPI_Fuse)
        films.append({'name':name,'shape':shape,'category':'retention-film','color':'amber','group':'interconnect','family':owner['family'],'bond_pair':owner['name'],'mount':owner['mount'],'datum_case_mm':owner['datum_case_mm'],'folded_strap':True,'film_thickness_mm':t})
    def usb_slots(shape,axis,origin,end,z):
        for off,rad in [(0,pair),(-1.5,r),(1.5,r)]:
            point=[origin[0],origin[1],z];point[1 if axis==(1,0,0) else 0]+=off;shape=slot(shape,axis,point,end,rad)
        return shape
    # Rear guides bond to the underside of the retained ledge, avoiding a thin floor web.
    z=spec['usb']['low_z'];y=spec['usb']['rear_y'];roof=spec['case_pocket']['bounds_case_mm'][5]
    front=g['USB_rear_front_half_width']
    tolerance=2*g['guide_print_tolerance']
    assert g['lid_roof_nominal']-tolerance>=g['minimum_floor_web']-1e-6
    off=abs(g['rear_front_step_boundary_y_mm']-y)
    assert abs(z)-math.sqrt(max(0,pair*pair-off*off))-abs(g['rear_front_step_roof_z_mm'])-tolerance>=g['minimum_floor_web']-1e-6
    assert front-1.5-r-2*g['guide_print_tolerance']>=g['minimum_floor_web']-1e-6,'Rear clip front wall too thin'
    for i,x in enumerate(g['USB_rear_x'],1):
        bb=[x-depth/2,y-front,z,x+depth/2,y+2.7,roof-bond];s=usb_slots(box(bb),(1,0,0),(x-depth/2-.01,y,z),depth+.02,z);s=boolean(s,box([x-depth/2-.01,y-front-.01,g['rear_front_step_roof_z_mm'],x+depth/2+.01,g['rear_front_step_boundary_y_mm'],roof+1]),BRepAlgoAPI_Cut);add('USB-R'+str(i),s,'case-roof','usb',[x,y,z]);film('USB-R'+str(i)+'-film',[x-depth/2,y-front,z-1.0,x+depth/2,y+2.7,z-.9])
    # Front loop bases/lids: no floor machining; separate halves accept already crimped cables.
    for i,(x,y) in enumerate([(spec['usb']['drop_x'],g['USB_down_y']),(exits['C5'][0],g['USB_front_y'])],1):
        z=spec['usb']['front_z'];floor=surface_z(case,x,y)+bond;bb=[x-2.7,y-depth/2,floor,x+2.7,y+depth/2,z];assert z-pair-floor-2*g['guide_print_tolerance']>=g['minimum_floor_web']-1e-6
        base=conformal_base(bb,case,bond);base=usb_slots(base,(0,1,0),(x,y-depth/2-.01,z),depth+.02,z)
        lid=box([x-2.7,y-depth/2,z+.05,x+2.7,y+depth/2,z+pair+g['lid_roof_nominal']]);lid=usb_slots(lid,(0,1,0),(x,y-depth/2-.01,z),depth+.02,z)
        add('USB-F'+str(i)+'-base',base,'case-floor','usb',[x,y,z]);add('USB-F'+str(i)+'-lid',lid,'removable-cover','usb',[x,y,z],'USB-F'+str(i)+'-base')
        # Two replaceable side patches bridge the base/lid seam; no floating lid.
        t=g['retention_film_thickness']
        for side,(x0,x1)in enumerate([(x-2.7-t,x-2.7),(x+2.7,x+2.7+t)],1):
            films.append({'name':'USB-F'+str(i)+'-seam-'+str(side),'shape':box([x0,y-depth/2,z-.7,x1,y+depth/2,z+.7]),'category':'retention-film','color':'amber','group':'interconnect','family':'usb','bond_pair':['USB-F'+str(i)+'-base','USB-F'+str(i)+'-lid'],'mount':'case-floor','datum_case_mm':[x,y,z],'folded_strap':False,'film_thickness_mm':t})
    # Existing three-channel battery route, with removable film retention.
    y=spec['battery']['rear_y'];z=spec['battery']['rear_z'];bw=g['battery_half_width_mm']
    assert bw-2-r-tolerance>=g['minimum_floor_web']-1e-6,'Battery front wall too thin'
    for i,x in enumerate(g['battery_x'],1):
        floor=surface_z(case,x,y)+bond;shape=conformal_base([x-depth/2,y-bw,floor,x+depth/2,y+bw,z],case,bond)
        for off in [-2,0,2]:shape=slot(shape,(1,0,0),(x-depth/2-.01,y+off,z),depth+.02,r)
        add('BAT-R'+str(i),shape,'case-floor','battery',[x,y,z]);film('BAT-R'+str(i)+'-film',[x-depth/2,y-bw,z+.4,x+depth/2,y+bw,z+.5])
    # Power guides follow the PCB and remain above the battery envelope.
    y=spec['power']['rear_y'];z=spec['power']['high_z'];top=pcb_bottom-bond
    for i,x in enumerate(g['power_x'],1):
        shape=box([x-depth/2,y-1.7,z,x+depth/2,y+1.7,top])
        for off in [-.5,.5]:shape=slot(shape,(1,0,0),(x-depth/2-.01,y+off,z),depth+.02,r)
        add('PWR-R'+str(i),shape,'PCB','power',[x,y,z]);film('PWR-R'+str(i)+'-film',[x-depth/2,y-1.7,z-.5,x+depth/2,y+1.7,z-.4])
    # Two-level removable fan-out at J1: the red conductor is installed before the black one.
    x=g['power_fan_x'];y=exits['J1'][1];upper=box([x-depth/2,y-2.5,z,x+depth/2,y+2.5,top]);upper=boolean(upper,sweep_wire(routes['power']['1'],2*r),BRepAlgoAPI_Cut);add('PWR-F-upper',upper,'PCB','power',[x,y,z])
    low=spec['power']['low_z'];shape=box([x-depth/2,y-2.5,low,x+depth/2,y+2.5,z-.6]);shape=boolean(shape,sweep_wire(routes['power']['2'],2*r),BRepAlgoAPI_Cut)
    for a,b in [(y-2.5,y-1.8),(y+1.8,y+2.5)]:shape=boolean(shape,box([x-depth/2,a,z-.6,x+depth/2,b,z-.05]),BRepAlgoAPI_Fuse)
    add('PWR-F-lower',shape,'PCB-removable','power',[x,y,low],'PWR-F-upper')
    t=g['retention_film_thickness']
    for side,(y0,y1)in enumerate([(y-2.5-t,y-2.5),(y+2.5,y+2.5+t)],1):
        films.append({'name':'PWR-F-seam-'+str(side),'shape':box([x-depth/2,y0,z-.7,x+depth/2,y1,z+.75]),'category':'retention-film','color':'amber','group':'interconnect','family':'power','bond_pair':['PWR-F-upper','PWR-F-lower'],'mount':'PCB','datum_case_mm':[x,y,z],'folded_strap':False,'film_thickness_mm':t})
    film('PWR-F-lower-film',[x-depth/2,y-2.5,low-.5,x+depth/2,y+2.5,low-.4])
    assert len(items)==16
    return items,films
