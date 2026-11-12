"""E73 independent bounded-fit geometry, adapted from this repository's Raytac checks.

The source plate/case remain immutable; this module does not import Raytac code.
A dimensional envelope is a requirement for incoming and installed measurement.
"""
import math
import ezdxf
from ezdxf.path import make_path
from shapely.geometry import Point, Polygon, box as rectangle
from shapely.ops import unary_union
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepTools import BRepTools
from OCP.gp import gp_Pnt, gp_Vec
from cad_geometry import bounds
from check_yeti60_assembly import box, distance, wire


def profiles(doc, chord=.002):
    rows = []
    for e in doc.modelspace().query('LWPOLYLINE'):
        p = Polygon([(-v.x, -v.y) for v in make_path(e).flattening(chord)])
        assert p.is_valid
        rows.append((p.area, e, p))
    return sorted(rows, key=lambda row:-row[0])


def internal_contract(doc):
    outer = profiles(doc)[0][1]
    # DXF entity data excluding the changing external profile. Handles and
    # complete bulges/vertices are retained for all key/stabilizer/fastener cuts.
    return [str(e.dxfattribs()) + (str(list(e.get_points())) if e.dxftype() == 'LWPOLYLINE' else '')
            for e in doc.modelspace() if e is not outer]


def build_shape(doc, z, thickness):
    rows = profiles(doc)
    builder = BRepBuilderAPI_MakeFace(wire([(x,y,z) for x,y in rows[0][2].exterior.coords],True))
    for _, _, p in rows[1:]:
        builder.Add(wire([(x,y,z) for x,y in p.exterior.coords],False))
    for c in doc.modelspace().query('CIRCLE'):
        r = c.dxf.radius
        n = max(64, math.ceil(math.pi/math.acos(1-.002/r)))
        points = [(-c.dxf.center.x+r*math.cos(2*math.pi*i/n),
                   -c.dxf.center.y+r*math.sin(2*math.pi*i/n),z) for i in range(n)]
        builder.Add(wire(points,False))
    assert builder.IsDone()
    shape = BRepPrimAPI_MakePrism(builder.Face(),gp_Vec(0,0,thickness)).Shape()
    assert BRepCheck_Analyzer(shape).IsValid()
    return shape


def plate_envelope(doc,fit,stack,travel=0):
    p=fit['plate'];r=p['maximum_profile_point_error_XY_radial_mm']+p['maximum_installed_point_error_XY_radial_mm']
    # Circumscribe the declared disk despite Shapely's polygonal arc chords.
    radius=r+.0001;assert radius*math.cos(math.pi/256)>=r
    poly=profiles(doc,p['profile_chord_mm'])[0][2].buffer(radius,quad_segs=64)
    dz=p['maximum_installed_surface_error_Z_mm'];z=stack['plate_bottom_z']-dz
    face=BRepBuilderAPI_MakeFace(wire([(x,y,z) for x,y in poly.exterior.coords],True)).Face()
    return BRepPrimAPI_MakePrism(face,gp_Vec(0,0,stack['plate_thickness_mm']+2*dz+travel)).Shape()


def switch_envelope(part,fit,assembly_spec,fabrication):
    s=fit['switch'];stack=assembly_spec['pcb_fastener'];bb=part['bounds_case_mm'][:]
    xy=s['maximum_installed_XY_envelope_growth_each_axis_mm']+s['maximum_installed_board_point_error_XY_each_axis_mm']
    terms=dict(board_growth=max(fabrication['ordinary_thickness_acceptance_range_mm'])-fabrication['CAD_finished_envelope_mm'],
               shoulder=stack['shoulder_length_tolerance'],film=stack['top_insulator_thickness_tolerance'],
               installed_plate_Z=fit['plate']['maximum_installed_surface_error_Z_mm'],
               mounted_board_bow=s['maximum_additional_mounted_PCB_downward_bow_mm'],
               installed_height=s['maximum_installed_height_below_local_PCB_mm']-part['height_envelope_mm'])
    assert min(terms.values())>=0
    bb[0]-=xy;bb[1]-=xy;bb[3]+=xy;bb[4]+=xy;bb[2]-=math.fsum(terms.values())
    return box(bb),dict(downward_terms_mm=terms,downward_sum_mm=math.fsum(terms.values()),XY_allowance_each_axis_mm=xy,bounds_case_mm=bb)


def screen(case,envelope,fit,name):
    nominal=distance(case,envelope);case_radius=math.sqrt(3)*fit['case_maximum_coordinate_error_each_axis_mm']
    remaining=nominal-case_radius-fit['geometric_computation_guard_mm']
    assert remaining>=fit['minimum_residual_air_gap_mm'],('Bounded fit reserve exhausted',name,remaining)
    return dict(interface=name,continuous_envelope_gap_mm=nominal,case_coordinate_error_L2_bound_mm=case_radius,
                computation_guard_mm=fit['geometric_computation_guard_mm'],remaining_air_gap_mm=remaining)


def bearing_faces(shape,z):
    result=[];ex=TopExp_Explorer(shape,TopAbs_FACE)
    while ex.More():
        f=TopoDS.Face(ex.Current());bb=bounds(f)
        if abs(bb[2]-z)<1e-6 and abs(bb[5]-z)<1e-6:result.append(f)
        ex.Next()
    assert result
    return result


def gasket_coverage(doc,fit,cases):
    polys=profiles(doc);holes=[p for _,_,p in polys[1:]]
    holes += [Point(-c.dxf.center.x,-c.dxf.center.y).buffer(c.dxf.radius,quad_segs=128) for c in doc.modelspace().query('CIRCLE')]
    material=polys[0][2].difference(unary_union(holes));p=fit['plate'];g=fit['gaskets']
    eroded=material.buffer(-(p['maximum_profile_point_error_XY_radial_mm']+p['maximum_installed_point_error_XY_radial_mm']))
    result=[];sx,sy=g['finished_size_XY_mm'];placement=g['maximum_cut_and_placement_point_error_XY_each_axis_mm']
    for layer,z in [('lower',3.19),('upper',6.39)]:
        faces=bearing_faces(cases[layer],z)
        for i,(x,y) in enumerate(g['centers_case_XY_mm'],1):
            plate_pad=rectangle(x-sx/2-placement,y-sy/2-placement,x+sx/2+placement,y+sy/2+placement)
            assert eroded.contains(plate_pad),('Gasket leaves worst-case plate metal',layer,i)
            # Include both gasket cut/placement and case planar-coordinate error.
            a=placement+fit['case_maximum_coordinate_error_each_axis_mm']
            pad=rectangle(x-sx/2-a,y-sy/2-a,x+sx/2+a,y+sy/2+a)
            face=BRepBuilderAPI_MakeFace(wire([(u,v,z) for u,v in pad.exterior.coords],True)).Face();area=0
            for support in faces:
                op=BRepAlgoAPI_Common(face,support);op.Build();assert op.IsDone()
                prop=GProp_GProps();BRepGProp.SurfaceProperties_s(op.Shape(),prop);area+=prop.Mass()
            assert abs(area-pad.area)<1e-5,('Gasket leaves case bearing',layer,i,area,pad.area)
            result.append(dict(layer=layer,index=i,nominal_area_mm2=sx*sy,case_expanded_area_mm2=pad.area,case_supported_area_mm2=area,plate_supported_after_XY_allowances=True))
    return result


def volume(s):
    p=GProp_GProps();BRepGProp.VolumeProperties_s(s,p);return abs(p.Mass())


def external_faces(shape):
    result=[];faces=TopExp_Explorer(shape,TopAbs_FACE)
    while faces.More():
        f=TopoDS.Face(faces.Current());bb=bounds(f);surf=BRepAdaptor_Surface(f);u0,u1,v0,v1=BRepTools.UVBounds_s(f);p=gp_Pnt();du=gp_Vec();dv=gp_Vec();surf.D1((u0+u1)/2,(v0+v1)/2,p,du,dv);n=du.Crossed(dv)
        if n.Magnitude()>1e-9:
            n.Normalize()
            if f.Orientation()==TopAbs_REVERSED:n.Reverse()
            if (n.Z()<-.3 and bb[5]<-7) or (n.Y()>.3 and bb[4]>-96) or (n.X()>.3 and bb[3]>375) or (n.X()<-.3 and bb[0]<53):result.append(f)
        faces.Next()
    assert result;return result
