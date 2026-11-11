"""Controlled nine-conductor routes for the short-USB Raytac PCB."""
import math
from interconnect_geometry import line,arc,s_bend,rounded_polyline,offset_path,validate,add,mul,tangent

def length(path):return sum(p['length'] for p in path)
def chain(*parts):
    result=[p for part in parts for p in part];validate(result);return result

def paths(spec,exits,delta=0):
    u=spec['usb'];r=u['bend_radius'];start=tuple(v+(delta if i==2 else 0) for i,v in enumerate(exits['J4']))
    # Initial turn uses the internal rear pocket; its exterior is unchanged.
    initial=rounded_polyline([start,(start[0],u['rear_y'],start[2]),(u['drop_start_x'],u['rear_y'],start[2])],u['initial_radius'])
    drop,end,_=s_bend(initial[-1]['end'],(-1,0,0),u['low_z']-start[2],r)
    c5=tuple(exits['C5']);run=math.sqrt(4*r*abs(c5[2]-u['last_z'])-(c5[2]-u['last_z'])**2)
    ramp=(c5[0],c5[1]-u['end_straight']-run,u['last_z'])
    rear=[line(end,(u['rise_x'],u['rear_y'],u['low_z']))]
    rise,high,_=s_bend(rear[-1]['end'],(-1,0,0),u['cross_z']+delta-u['low_z'],r)
    high_path=rounded_polyline([high,(u['drop_x'],u['rear_y'],high[2]),(u['drop_x'],u['drop_y'],high[2])],r)
    lower,low,_=s_bend(high_path[-1]['end'],(0,-1,0),u['front_z']-high[2],r)
    front=rounded_polyline([low,(u['drop_x'],u['front_y'],u['front_z']),(c5[0],u['front_y'],u['front_z']),(c5[0],u['return_lower_y'],u['front_z'])],r)
    lower2,last,_=s_bend(front[-1]['end'],(0,1,0),u['last_z']-u['front_z'],r)
    finish,end2,_=s_bend(ramp,(0,1,0),c5[2]-u['last_z'],r)
    usb=chain(initial,drop,rear,rise,high_path,lower,front,lower2,[line(last,ramp)],finish,[line(end2,c5)])
    out={'usb':{str(i):offset_path(usb,o) for i,o in enumerate([1.5,.5,-.5,-1.5],1)}}
    p=spec['power'];z=p['high_z']+delta;start=tuple(v+(delta if i==2 else 0) for i,v in enumerate(exits['J5']));target=tuple(v+(delta if i==2 else 0) for i,v in enumerate(exits['J1']))
    turn=rounded_polyline([start,(start[0],start[1]+p['initial_radius'],start[2]),(start[0]-p['initial_radius'],start[1]+p['initial_radius'],start[2])],p['initial_radius'])
    side,last,_=s_bend(turn[-1]['end'],(-1,0,0),p['rear_y']-turn[-1]['end'][1],p['side_radius'],(0,1,0))
    rise,last2,_=s_bend(last,(-1,0,0),z-last[2],p['side_radius'])
    common=chain(turn,side,rise,[line(last2,(p['cross_start_x'],p['rear_y'],z))])
    rp=p['turn_radius'];entry=p['left_x']+rp
    tailxy=rounded_polyline([(entry,p['rear_y'],z),(p['left_x'],p['rear_y'],z),(p['left_x'],target[1],z),(p['left_x']-rp,target[1],z)],rp)
    out['power']={}
    for pin,offset,shift in [('1',.5,2),('2',-.5,-2)]:
        early=offset_path(common,offset);at=early[-1]['end'];crossing=[]
        if pin=='2':
            q,at,_=s_bend(at,(-1,0,0),p['cross_side_shift'],p['side_radius'],(0,1,0));crossing+=q
        to=(p['cross_lower_start_x'],at[1],at[2]);crossing.append(line(at,to));at=to
        q,at,_=s_bend(at,(-1,0,0),p['low_z']+delta-at[2],p['side_radius']);crossing+=q
        to=(p['cross_end_x'],at[1],at[2]);crossing.append(line(at,to));at=to
        q,at,_=s_bend(at,(-1,0,0),z-at[2],p['side_radius']);crossing+=q
        if pin=='2':
            q,at,_=s_bend(at,(-1,0,0),-p['cross_side_shift'],p['side_radius'],(0,1,0));crossing+=q
        to=(p['low_start_x'],at[1],at[2]);crossing.append(line(at,to));early=chain(early,crossing);at=to;lower=[]
        level=z if pin=='1' else p['low_z']+delta
        if pin=='2':lower,at,_=s_bend(at,(-1,0,0),level-at[2],p['side_radius'])
        tail=offset_path(tailxy,offset)
        if level!=z:
            for piece in tail:
                for key in ['start','end','mid','center']:
                    if key in piece:piece[key]=tuple(v+(level-z if i==2 else 0) for i,v in enumerate(piece[key]))
        joined=chain(early,lower,[line(at,tail[0]['start'])],tail)
        fan,at,_=s_bend(joined[-1]['end'],(-1,0,0),shift,p['fan_radius'],(0,1,0))
        last,at,_=s_bend(at,(-1,0,0),target[2]-at[2],p['fan_radius'])
        goal=(target[0],target[1]+(1.5 if pin=='1' else -1.5),target[2])
        assert at[0]>goal[0],('Insufficient power fan-out length',pin,at,goal)
        out['power'][pin]=chain(joined,fan,last,[line(at,goal)])
    # Battery route retains its verified pack/header datums and conductor order.
    b=spec['battery'];target=tuple(exits['pack']);r=b['radius'];z=b['rear_z']
    start=tuple(v+(delta if i==2 else 0) for i,v in enumerate(exits['J2']))
    fan_radius=b['header_fanout_radius_mm'];fan_shift=max(abs(a-bb) for a,bb in zip(b['lateral_offsets'],b['header_lateral_offsets']))
    fan_run=math.sqrt(4*fan_radius*fan_shift-fan_shift**2)
    centre_after=(start[0],start[1]+fan_run,start[2])
    lead,last,_=s_bend(centre_after,(0,1,0),z-start[2],r)
    main=rounded_polyline([last,(start[0],b['rear_y'],z),(b['side_x'],b['rear_y'],z),(b['side_x'],b['drop_y'],z)],r)
    drop,last,_=s_bend(main[-1]['end'],(0,-1,0),target[2]-z,r)
    final=rounded_polyline([last,(b['side_x'],target[1],target[2]),target],r)
    battery=chain(lead,main,drop,final)
    out['battery']={}
    for index,(offset,header_offset) in enumerate(zip(b['lateral_offsets'],b['header_lateral_offsets']),1):
        pin=str(index)
        wire_start=(start[0]-header_offset,start[1],start[2])
        if offset!=header_offset:
            fan,_,_=s_bend(wire_start,(0,1,0),header_offset-offset,fan_radius,(1,0,0))
        else:
            fan=[line(wire_start,(wire_start[0],wire_start[1]+fan_run,wire_start[2]))]
        out['battery'][pin]=chain(fan,offset_path(battery,offset))
    return out,usb

def point_at(p,t):
    from interconnect_geometry import sub,cross,dot
    if p['kind']=='line':return add(p['start'],mul(sub(p['end'],p['start']),t))
    v=sub(p['start'],p['center']);n=p['normal'];a=p['length']/p['radius']*t
    rotated=add(add(mul(v,math.cos(a)),mul(cross(n,v),math.sin(a))),mul(n,dot(n,v)*(1-math.cos(a))))
    return add(p['center'],rotated)

def frame_at(p,t):
    from interconnect_geometry import unit,cross,sub
    T=unit(sub(p['end'],p['start'])) if p['kind']=='line' else unit(cross(p['normal'],sub(point_at(p,t),p['center'])))
    N=unit(cross((0,0,1),T));return T,N,cross(T,N)

def smooth(t):return t*t*t*(10+t*(-15+6*t))

def curve_for_piece(p):
    from OCP.GeomAPI import GeomAPI_Interpolate
    from OCP.collections import HArray1_gp_Pnt
    from OCP.gp import gp_Pnt,gp_Vec
    arr=HArray1_gp_Pnt(1,len(p['points']))
    for i,pt in enumerate(p['points'],1):arr.SetValue(i,gp_Pnt(*pt))
    op=GeomAPI_Interpolate(arr,False,1e-8);op.Load(gp_Vec(*p['tangent_start']),gp_Vec(*p['tangent_end']),True);op.Perform();assert op.IsDone();return op.Curve()

def paired_data(centre,spec):
    """Three rear turns, half-turn down and half-turn back; bends stay planar.

    Every twist has zero angular/radial derivative at each end. Constant-phase
    arc portions are exact offset circles. Straight twist portions use a bounded
    spline interpolation; collision checks additionally use the entire pair tube.
    """
    from interconnect_geometry import sub,norm
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.GeomLProp import GeomLProp_CLProps
    phase=0.;amplitude=spec['usb']['endpoint_pair_radius'];result={'2':[],'3':[]};twists=[]
    for p in centre:
        role=None
        if p['kind']=='line':
            T,_,_=frame_at(p,0)
            if p['length']>60 and T[0]<-.99 and abs(p['start'][1]-spec['usb']['rear_y'])<1e-6 and abs(p['start'][2]-spec['usb']['low_z'])<1e-6:role='rear'
            elif p['length']>15 and T[1]<-.99 and abs(p['start'][0]-spec['usb']['drop_x'])<1e-6 and abs(p['start'][2]-spec['usb']['front_z'])<1e-6:role='down'
            elif p['length']>10 and T[1]>.99 and abs(p['start'][2]-spec['usb']['front_z'])<1e-6:role='return'
        end_phase=phase+(2*math.pi*spec['usb']['twist_turns'] if role=='rear' else math.pi if role else 0)
        end_a=spec['usb']['bulk_pair_radius'] if role=='rear' else spec['usb']['endpoint_pair_radius'] if role=='return' else amplitude
        for pin,sign in [('2',1),('3',-1)]:
            def at(t):
                T,N,B=frame_at(p,t);h=smooth(t) if role else 0.;a=amplitude+(end_a-amplitude)*h;theta=phase+(end_phase-phase)*h
                return add(point_at(p,t),add(mul(N,sign*a*math.cos(theta)),mul(B,sign*a*math.sin(theta))))
            if role:
                n=max(64,math.ceil(abs(end_phase-phase)/math.pi*128),math.ceil(p['length']/.4));points=[at(i/n) for i in range(n+1)]
                q={'kind':'twist','points':points,'start':points[0],'end':points[-1],'tangent_start':frame_at(p,0)[0],'tangent_end':frame_at(p,1)[0],'role':role,'phase_start':phase,'phase_end':end_phase,'radius_start':amplitude,'radius_end':end_a,'centre_piece':p}
                curve=curve_for_piece(q);edge=BRepBuilderAPI_MakeEdge(curve).Edge();prop=GProp_GProps();BRepGProp.LinearProperties_s(edge,prop);q['length']=prop.Mass()
                da=abs(end_a-amplitude);dp=abs(end_phase-phase);L=p['length'];amax=max(amplitude,end_a)
                bound=6*da/L**2+amax*(1.875*dp/L)**2+2*(1.875*da/L)*(1.875*dp/L)+amax*6*dp/L**2
                q['curvature_radius_lower_bound_mm']=1/bound
                minimum=min(1/max(GeomLProp_CLProps(curve,curve.FirstParameter()+(curve.LastParameter()-curve.FirstParameter())*i/1024,2,1e-8).Curvature(),1e-12) for i in range(1025));q['spline_sampled_minimum_radius_mm']=minimum
                assert min(minimum,1/bound)>=4,(role,'twist radius',minimum,1/bound)
                result[pin].append(q)
            elif p['kind']=='line':result[pin].append(line(at(0),at(1)))
            else:
                _,N,B=frame_at(p,0);u=sign*amplitude*math.cos(phase);v=sign*amplitude*math.sin(phase)
                c=add(p['center'],mul(B,v) if abs(p['normal'][2])>.999 else mul(N,u));q=arc(at(0),at(.5),at(1),c);assert q['radius']>=4;result[pin].append(q)
        if role:twists.append({'role':role,'centre_piece':p,'phase_start':phase,'phase_end':end_phase,'pair_envelope_radius_mm':max(amplitude,end_a)+.4,'length_mm':p['length']})
        phase=end_phase;amplitude=end_a
    assert [t['role'] for t in twists]==['rear','down','return']
    for pin,path in result.items():
        for a,b in zip(path,path[1:]):assert norm(sub(a['end'],b['start']))<1e-6
    assert abs(length(result['2'])-length(result['3']))<1.0
    return result,twists

def sweep_wire(path,diameter):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge,BRepBuilderAPI_MakeWire,BRepBuilderAPI_MakeFace
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipe
    from OCP.GC import GC_MakeArcOfCircle
    from OCP.gp import gp_Pnt,gp_Dir,gp_Ax2,gp_Circ
    from OCP.BRepCheck import BRepCheck_Analyzer
    wire=BRepBuilderAPI_MakeWire()
    for p in path:
        if p['kind']=='line':edge=BRepBuilderAPI_MakeEdge(gp_Pnt(*p['start']),gp_Pnt(*p['end'])).Edge()
        elif p['kind']=='arc':edge=BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(*p['start']),gp_Pnt(*p['mid']),gp_Pnt(*p['end'])).Value()).Edge()
        else:edge=BRepBuilderAPI_MakeEdge(curve_for_piece(p)).Edge()
        wire.Add(edge)
    assert wire.IsDone()
    t=path[0]['tangent_start'] if path[0]['kind']=='twist' else frame_at(path[0],0)[0]
    profile=BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(*path[0]['start']),gp_Dir(*t)),diameter/2)).Edge()).Wire();face=BRepBuilderAPI_MakeFace(profile).Face();op=BRepOffsetAPI_MakePipe(wire.Wire(),face);op.Build();assert op.IsDone() and BRepCheck_Analyzer(op.Shape()).IsValid();return op.Shape()


def envelope_wire(path,diameter):
    """Exact regular sweeps plus conservative straight tubes around data twists."""
    from OCP.TopoDS import TopoDS_Compound
    from OCP.BRep import BRep_Builder
    c=TopoDS_Compound();builder=BRep_Builder();builder.MakeCompound(c);current=[]
    for p in path:
        if p['kind']=='twist':
            if current:builder.Add(c,sweep_wire(current,diameter));current=[]
            a=max(p['radius_start'],p['radius_end']);builder.Add(c,sweep_wire([p['centre_piece']],diameter+2*a+.01))
        else:current.append(p)
    if current:builder.Add(c,sweep_wire(current,diameter))
    return c
