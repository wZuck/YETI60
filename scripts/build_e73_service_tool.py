#!/usr/bin/env python3
"""Build and screen the parallel-jaw accessory for the M05 service ports."""

import json
from pathlib import Path

import ezdxf
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

from build_e73_m05_harness import OUT, matched_spec
from cad_geometry import load
from check_e73_corner_harness import bodies, cut, datums, pcb_solid
from check_e73_corner_service import (
    AUDIT, PORTS, ROOT, nearest, plug_bounds, read, sha, translated_union_bounds, verify,
)
from check_yeti60_assembly import box, move
from check_yeti60_interconnects import write_step
from e73_corner_harness_paths import envelope_wire, paired_data
from e73_corner_retention import build
from e73_service_leads import BATTERY_GUIDE_STATIONS, PARK_DROP, PARK_TRAVEL, flex_routes, position_exits


TOOLS = OUT/'tool'
TOP_BELOW_EXIT = 18.5
TIP_BELOW_EXIT = .42
STEP_BELOW_EXIT = 2.1
BLADE_WIDTH = .8
OPEN_ALLOWANCE = .10
LANDING_U = -.45
GUIDES_X = (-4.2, 4.2)
GUIDES_Z = -3.1
CLAMP_Z = -7.9
MOUNTING_Z = (-2., -5.)
LAYERS = ('PROFILE', 'DRILL')


def bore_y(x, z, diameter):
    axis = gp_Ax2(gp_Pnt(x, -.01, z), gp_Dir(0, 1, 0))
    return BRepPrimAPI_MakeCylinder(axis, diameter/2, 5.02).Shape()


def grip():
    handle = box([-6, 0, -10, 6, 5, 0])
    handle = cut(handle, box([-2.55, -.05, -6.55, 2.55, .73, .05]))
    for x in GUIDES_X:
        handle = cut(handle, bore_y(x, GUIDES_Z, 2.15))
    handle = cut(handle, bore_y(0, CLAMP_Z, 3.25))
    for z in MOUNTING_Z:
        handle = cut(handle, bore_y(0, z, 2.15))
    return handle


def blade_profile(path):
    doc = ezdxf.new()
    doc.units = 4
    for layer in LAYERS:
        doc.layers.new(layer)
    space = doc.modelspace()
    profile = [(-2.5,-6.5), (2.5,-6.5), (2.5,0), (.9,0), (.9,TOP_BELOW_EXIT-STEP_BELOW_EXIT),
               (.4,TOP_BELOW_EXIT-STEP_BELOW_EXIT), (.4,TOP_BELOW_EXIT-TIP_BELOW_EXIT),
               (-.4,TOP_BELOW_EXIT-TIP_BELOW_EXIT), (-.4,TOP_BELOW_EXIT-STEP_BELOW_EXIT),
               (-.9,TOP_BELOW_EXIT-STEP_BELOW_EXIT), (-.9,0), (-2.5,0)]
    space.add_lwpolyline(profile, close=True, dxfattribs={'layer':LAYERS[0]})
    for z in MOUNTING_Z:
        space.add_circle((0,z), 1.075, dxfattribs={'layer':LAYERS[1]})
    doc.saveas(path)


def local_parts(pins, sign, opening):
    signed = lambda a,b: sorted((sign*a, sign*b))
    edge = (pins+1)/2+opening
    a,b = signed(edge, edge+BLADE_WIDTH)
    c,d = signed(edge+.07, edge+5.07)
    return {
        'tip': [LANDING_U-.4,a,-STEP_BELOW_EXIT,LANDING_U+.4,b,-TIP_BELOW_EXIT],
        'shaft': [LANDING_U-.9,a,-TOP_BELOW_EXIT,LANDING_U+.9,b,-STEP_BELOW_EXIT],
        'tang': [LANDING_U-2.5,a,-TOP_BELOW_EXIT-6.5,LANDING_U+2.5,b,-TOP_BELOW_EXIT],
        'handle': [LANDING_U-6,c,-TOP_BELOW_EXIT-10,LANDING_U+6,d,-TOP_BELOW_EXIT],
    }


def case_bounds(frame, vx, vy, local):
    def transform(u, v, z):
        return (frame[0]+vx*u-vy*v,frame[1]+vy*u+vx*v,frame[2]+z)
    lo = transform(*local[:3])
    hi = transform(*local[3:])
    return [min(a,b) for a,b in zip(lo,hi)]+[max(a,b) for a,b in zip(lo,hi)]


def envelope_motion(exit_point, ref, sign):
    pins,vx,vy = PORTS[ref]
    open_bounds = local_parts(pins, sign, OPEN_ALLOWANCE)
    closed_bounds = local_parts(pins, sign, 0)
    sweep = {}
    for step, locals_, position, vector in [
        ('approach', open_bounds, [exit_point[0], exit_point[1], exit_point[2]-20], (0,0,20)),
        ('close', open_bounds, exit_point, (sign*vy*OPEN_ALLOWANCE,-sign*vx*OPEN_ALLOWANCE,0)),
        ('axial', closed_bounds, exit_point, (PARK_TRAVEL[ref]*vx,PARK_TRAVEL[ref]*vy,0)),
        ('lower', closed_bounds, [exit_point[0]+PARK_TRAVEL[ref]*vx,exit_point[1]+PARK_TRAVEL[ref]*vy,exit_point[2]], (0,0,-PARK_DROP)),
    ]:
        hardware = {'outer_fasteners': [LANDING_U-6.5,-16,-TOP_BELOW_EXIT-11,
                                        LANDING_U+6.5,16,-TOP_BELOW_EXIT+.2]} if sign==1 else {}
        sweep[step] = {key:box(translated_union_bounds(case_bounds(position,vx,vy,bb),vector))
                       for key,bb in dict(locals_, **hardware).items()}
    return sweep


def checked_stages(case, native, assembly, spec, exits, guides, delta):
    bottom,_ = datums(native, assembly, spec)
    fixed = bodies(native, assembly, spec, bottom, delta)
    fixed['M05 bottom'] = case
    fixed['PCB'] = pcb_solid(bottom+delta, assembly['stack']['pcb_thickness']-delta)
    for part in guides:
        fixed[part['name']] = move(part['shape'],z=delta) if part['mount'].startswith('PCB') else part['shape']
    results = []
    for ref in ('J2','J4'):
        x,y,z = exits[ref]
        for sign in (-1,1):
            for step, parts in envelope_motion([x,y,z+delta],ref,sign).items():
                tests = {name:nearest(solid,fixed,.35) for name,solid in parts.items()}
                intersections = [(name,q) for name,checks in tests.items() for q in checks
                                 if q['intersection_mm3']>1e-7]
                if intersections:
                    raise AssertionError((ref, sign, step, delta, intersections))
                results.append({'ref':ref, 'PCB_bottom_offset_mm':delta, 'side':sign,
                                'stage':step,'nearest_rigid_clearances':tests})
    return results


def check_wire_poses(exits, spec, delta):
    states = (
        ('J2', (0,0,0,0)), ('J2', (.5,0,0,0)),
        ('J2', (1,0,0,0)), ('J2', (1,1,0,0)),
        ('J4', (1,1,0,0)), ('J4', (1,1,.5,0)),
        ('J4', (1,1,1,0)), ('J4', (1,1,1,1)),
    )
    wire = spec['wire']
    envelope = wire['insulation_od_max']+2*wire['case_and_route_position_allowance']
    results = []
    for ref,state in states:
        posed = position_exits(exits,*state)
        routes,center,_ = flex_routes(spec,exits,posed,delta)
        routes['usb'].update(paired_data(center,spec)[0])
        obstacles = {family+'.'+pin:envelope_wire(path,envelope)
                     for family, leads in routes.items() for pin,path in leads.items()}
        pins,vx,vy = PORTS[ref]
        x,y,z = posed[ref]
        frame = [x,y,z+delta]
        hits = []
        for side in (-1,1):
            for key,bb in local_parts(pins,side,0).items():
                for item in nearest(box(case_bounds(frame,vx,vy,bb)),obstacles,.25):
                    hits.append(dict(item,part=key,side=side))
        assert not any(item['gap_mm']<.15 for item in hits), (ref,state,delta,hits)
        results.append({'ref':ref,'state':state,'PCB_bottom_offset_mm':delta,
                        'wire_placement_envelope_diameter_mm':envelope,'near_wire_gaps':hits})
    return results


def main():
    hatch = read(AUDIT/'service-case-m05.json')
    harness = read(AUDIT/'m05-harness.json')
    for report in (hatch,harness):
        verify(report)
    assembly = read(ROOT/'mechanical/assembly-spec.json')
    spec = matched_spec(read(ROOT/'hardware/e73-corner-harness-spec.json'))
    ret = read(ROOT/'hardware/e73-corner-retention-spec.json')
    spec['guides'] = dict(ret['guides'],battery_x=BATTERY_GUIDE_STATIONS)
    native = read(AUDIT/'harness-native.json')
    bottom,exits = datums(native,assembly,spec)
    case = load(OUT/'bottom-m05-REVIEW.step')
    seated,_,_ = flex_routes(spec,exits,exits,0)
    guides,films = build(spec,case,seated,exits,bottom)
    checks = []
    wire_poses = []
    for item in harness['trial_variants']:
        delta = assembly['stack']['pcb_thickness']-item['PCB_thickness_mm']
        checks.extend(checked_stages(case,native,assembly,spec,exits,guides+films,delta))
        wire_poses.extend(check_wire_poses(exits,spec,delta))
    TOOLS.mkdir(exist_ok=True)
    # The same printed grip is used twice, rotated 180 degrees about Z.
    # Use the existing mesh checks and local case-independent template.
    grip_files = []
    handle = grip()
    step = TOOLS/'parallel-grip.step'
    write_step(handle,step)
    from export_e73_retention_prints import mesh
    stl = step.with_suffix('.stl')
    metrics = mesh(handle,stl)
    grip_files.extend((step,stl))
    profile = TOOLS/'blade-06mm-profile.dxf'
    blade_profile(profile)
    grip_files.append(profile)
    inputs = dict(harness['source_sha256'], **{
        str(path.relative_to(ROOT)):sha(path) for path in (AUDIT/'m05-harness.json', Path(__file__))})
    result = {
        'status':'M05-service-tool-rigid-access-screened',
        'source_sha256':inputs,
        'outputs':{str(path.relative_to(ROOT)):sha(path) for path in grip_files},
        'physical_verification':False,
        'manufacturing_released':False,
        'notes':[
            'The grip and blade envelope is a trial tool. Shaft insulation, grip force and repeated axial withdrawal require a real connector and case.',
            'Housing dimensions and rear contact face are taken from public drawings and conservative bounding boxes. The downloadable vendor STEP was not used.',
            'The continuous check covers the tool against the case and installed rigid geometry. Flexible leads are checked at discrete matching poses. Grip on the actual molded housing remains a physical check.',
        ],
        'references':{
            'JST_SH_catalog':'https://www.jst.com/wp-content/uploads/2025/06/eSH.pdf',
            'JST_handling':'https://www.jst-mfg.com/product/pdf/eng/handling_e.pdf',
        },
        'grip_metrics':metrics,
        'tool_stroke_checks':checks,
        'sampled_wire_pose_checks':wire_poses,
    }
    (AUDIT/'m05-tool.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],len(checks))


if __name__ == '__main__':
    main()
