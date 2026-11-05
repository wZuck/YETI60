#!/usr/bin/env python3
"""Continuous bounded plate and switch envelopes, plus gasket bearing coverage.

Acceptance limits are requirements for measured finished parts, not untested
supplier guarantees. Full-keyboard service/fit and foam behavior remain open.
"""
import hashlib
import json
import math
from pathlib import Path
import ezdxf
from shapely.geometry import box as rectangle,Point
from shapely.ops import unary_union
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Vec

from build_usb_short_plate import profiles
from cad_geometry import load,bounds
from check_yeti60_assembly import box,distance,wire
from check_usb_short_closed_assembly import hashes

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'hardware/usb-short-route'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


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
    bb[0]-=xy;bb[1]-=xy;bb[3]+=xy;bb[4]+=xy;bb[2]-=sum(terms.values())
    return box(bb),dict(downward_terms_mm=terms,downward_sum_mm=sum(terms.values()),XY_allowance_each_axis_mm=xy,bounds_case_mm=bb)


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


def main():
    fit=read(BASE/'mechanical-fit-spec.json');assembly=read(BASE/'audit/assembly.json');built=read(BASE/'audit/plate-build.json');closed=read(BASE/'audit/closed-assembly.json')
    for r in [assembly,built,closed]:hashes(r['source_sha256'])
    hashes(built['outputs']);hashes(closed['case']['outputs'])
    doc=ezdxf.readfile(ROOT/fit['plate']['output']);bottom=load(BASE/'mechanical/yeti60-bottom-short-usb.step');top=load(ROOT/'mechanical/generated/yeti60-top.step')
    envelope=plate_envelope(doc,fit,assembly['nominal_stack'])
    travel=read(BASE/'interconnect-spec.json')['case_service_relief']['vertical_extraction_mm']
    rows=[screen(bottom,envelope,fit,'plate-bottom-static'),screen(top,envelope,fit,'plate-top-static'),screen(bottom,plate_envelope(doc,fit,assembly['nominal_stack'],travel),fit,'plate-bottom-continuous-extraction')]
    part=next(p for p in assembly['component_envelopes'] if p['ref']=='SW100')
    env,terms=switch_envelope(part,fit,read(ROOT/'mechanical/assembly-spec.raytac.json'),read(ROOT/'mechanical/pcb-fabrication-spec.json'))
    rows.append(screen(bottom,env,fit,'SW100-bottom'))
    gaskets=gasket_coverage(doc,fit,{'lower':bottom,'upper':top})
    sources=[Path(__file__),ROOT/'scripts/build_usb_short_plate.py',BASE/'mechanical-fit-spec.json',BASE/'audit/plate-build.json',BASE/'audit/assembly.json',BASE/'audit/closed-assembly.json',ROOT/'mechanical/assembly-spec.raytac.json',ROOT/'mechanical/pcb-fabrication-spec.json',ROOT/'mechanical/generated/yeti60-top.step',BASE/'mechanical/yeti60-bottom-short-usb.step',ROOT/'scripts/cad_geometry.py',ROOT/'scripts/check_yeti60_assembly.py',ROOT/'scripts/check_usb_short_closed_assembly.py',BASE/'interconnect-spec.json']
    report=dict(status='bounded-plate-switch-design-fit-passed',physical_verification=False,manufacturing_released=False,complete_keyboard_tolerance_qualified=False,
                acceptance_limits_are_measured_requirements=True,plate_and_switch_bounded_envelopes_passed=True,interfaces=rows,switch_budget=terms,gasket_bearing_checks=gaskets,
                gasket_force_creep_and_adhesive_qualified=False,
                remaining=['Incoming and installed dimensional measurement','Other components, caps, NiZ mechanisms, stabilizers and full flexible service motion','Foam compression force/creep and adhesive qualification','Physical electrical/thermal/RF acceptance'],
                source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources})
    (BASE/'audit/tolerance-fit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Bounded plate/switch fit passed; minimum residual',min(r['remaining_air_gap_mm'] for r in rows),'mm; complete keyboard/physical qualification remains open',flush=True)


if __name__=='__main__':main()
