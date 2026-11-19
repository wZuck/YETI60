#!/usr/bin/env python3
"""Build removable M05 tool parking supports on the cover screw datums."""

import json
from pathlib import Path

from shapely.geometry import box as rectangle

from build_e73_service_case import HEAD_DIA, POCKET_DEPTH, cylinder, prism, skin_z
from build_e73_service_tool import GUIDES_X, GUIDES_Z, LANDING_U, TOP_BELOW_EXIT, case_bounds, envelope_motion
from cad_geometry import bounds, intersection_volume, load
from check_e73_corner_harness import cut
from check_e73_corner_service import AUDIT, PORTS, ROOT, read, sha, translated_union_bounds, verify
from check_yeti60_assembly import box, move
from check_yeti60_interconnects import write_step
from e73_corner_retention import boolean
from e73_service_leads import PARK_TRAVEL
from export_e73_retention_prints import mesh
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepCheck import BRepCheck_Analyzer


BASE = ROOT/'hardware/e73-hhkb-corner/mechanical/service-case-m05'
OUT = BASE/'parking-support'
ARM_LOW = -21.43
ARM_HIGH = -20.04
RAIL_BOTTOM = -30.
SHELF_THICKNESS = 2.2
SEAT_Z = -26.92
SADDLE_V = (10.3,13.4)
SADDLE_U_HALF = 2.1
SLOT_U_HALF = 1.175
RAIL_V = (17.2,23.2)
SCREW_V = 20.2
RAIL_THREAD_DEPTH = 3.2
SHELF_APPROACH = 12.


def combine(shapes):
    joined, *pieces = shapes
    for piece in pieces:
        joined = boolean(joined, piece, BRepAlgoAPI_Fuse)
    assert BRepCheck_Analyzer(joined).IsValid()
    return joined


def frame_geometry(ref, nominal):
    _, vx, vy = PORTS[ref]
    origin = (*nominal[:2], 0)
    def to_local_xy(x, y):
        dx, dy = x-origin[0], y-origin[1]
        return vx*dx+vy*dy, -vy*dx+vx*dy
    def xy(u, v):
        return origin[0]+vx*u-vy*v,origin[1]+vy*u+vx*v
    def block(bb):
        return box(case_bounds(origin,vx,vy,bb))
    return block, xy, to_local_xy


def support_shoe(block, xy, u, v, fastener):
    cx,cy = xy(u,v)
    half = 2.6
    raw = block([u-half,v-half,ARM_LOW,u+half,v+half,-8])
    x,y,_,X,Y,_ = bounds(raw)
    discard = prism(rectangle(x-.02,y-.02,X+.02,Y+.02),
                    lambda x,y: skin_z(x,y)+POCKET_DEPTH, 20)
    seat_z = fastener['head_seat_z_mm']
    shelf_z = fastener['shelf_center_z_mm']
    shoe = cut(raw,discard)
    recess = cylinder(cx,cy,ARM_LOW-.01,HEAD_DIA/2,seat_z-ARM_LOW+.01)
    thru = cylinder(cx,cy,seat_z-.03,1.15,shelf_z-seat_z+1)
    return cut(cut(shoe,recess),thru)


def make_carrier(ref, datums, nominal):
    block, xy, local = frame_geometry(ref,nominal)
    screws = [(local(*f['xy_mm']),f) for f in datums['fasteners']]
    slots = [LANDING_U+offset for offset in GUIDES_X]
    u_values = [p[0] for p,_ in screws]+slots
    umin,umax = min(u_values)-3.2,max(u_values)+3.2
    spine = block([umin,RAIL_V[0],RAIL_BOTTOM,umax,RAIL_V[1],ARM_HIGH])
    supports = [spine]
    for (u,v),fastener in screws:
        shoe = support_shoe(block,xy,u,v,fastener)
        # Stop the arm short of the cover screw counterbore. Its outer end
        # overlaps the vertical spine while it stays above the tool grips.
        neck = block([u-2.6,v+2.32,ARM_LOW,u+2.6,RAIL_V[0]+.25,ARM_HIGH])
        supports.extend((shoe,neck))
        # Stiffen the outboard strips without entering the tool's projected
        # axial sweep. The actual modeled strokes are tested again below.
        left = LANDING_U-6.5-PARK_TRAVEL[ref]-.35
        right = LANDING_U+6.5+.35
        strips = [(u-2.6,min(left,u+2.6)),(max(right,u-2.6),u+2.6)]
        for a,b in strips:
            if b-a>=.7:
                supports.append(block([a,v+2.32,-26.,b,RAIL_V[0]+.25,ARM_HIGH]))
    shape = combine(supports)
    for u in slots:
        x,y = xy(u,SCREW_V)
        shape = cut(shape,cylinder(x,y,RAIL_BOTTOM-.03,1.675,RAIL_THREAD_DEPTH+.03))
    return shape


def make_shelf(ref, nominal):
    block, xy, _ = frame_geometry(ref,nominal)
    slots = [LANDING_U+offset for offset in GUIDES_X]
    z = RAIL_BOTTOM-SHELF_THICKNESS
    crossbar = block([slots[0]-2.5,16.4,z,slots[1]+2.5,23.0,RAIL_BOTTOM])
    parts = [crossbar]
    for u in slots:
        parts.append(block([u-SADDLE_U_HALF,SADDLE_V[0],z,u+SADDLE_U_HALF,16.5,RAIL_BOTTOM]))
        parts.append(block([u-SADDLE_U_HALF,SADDLE_V[0],z,u+SADDLE_U_HALF,SADDLE_V[1],-25.1]))
    shape = combine(parts)
    for u in slots:
        x,y = xy(u,SCREW_V)
        shape = cut(shape,cylinder(x,y,z-.03,1.15,SHELF_THICKNESS+.06))
        shape = cut(shape,block([u-SLOT_U_HALF,SADDLE_V[0]-.02,SEAT_Z,
                                 u+SLOT_U_HALF,SADDLE_V[1]+.02,-24.5]))
        shape = cut(shape,block([u-SADDLE_U_HALF-.02,10.45,-30.1,
                                 u+SADDLE_U_HALF+.02,12.8,-29.1]))
    return shape


def shelf_approach_envelopes(block):
    """Conservative complete travel boxes after accounting for open rod slots."""
    slots = [LANDING_U+offset for offset in GUIDES_X]
    z = RAIL_BOTTOM-SHELF_THICKNESS
    boxes = [[slots[0]-2.5,16.4,z,slots[1]+2.5,23.,RAIL_BOTTOM]]
    for u in slots:
        lo,hi = u-SADDLE_U_HALF,u+SADDLE_U_HALF
        boxes.append([lo,SADDLE_V[0],z,hi,16.5,RAIL_BOTTOM])
        boxes.append([lo,SADDLE_V[0],z,hi,SADDLE_V[1],SEAT_Z])
        for x,X in [(lo,u-SLOT_U_HALF),(u+SLOT_U_HALF,hi)]:
            boxes.append([x,SADDLE_V[0],SEAT_Z,X,SADDLE_V[1],-25.1])
    return [box(translated_union_bounds(bounds(block(bb)),(0,0,-SHELF_APPROACH))) for bb in boxes]


def seated_checks(ref, carrier, shelf, variants, nominal, assembled_exit):
    result = []
    block,_,_ = frame_geometry(ref,nominal)
    sweep = shelf_approach_envelopes(block)
    for shape in sweep:
        assert intersection_volume(shape,carrier)<1e-7, (ref,'shelf approach blocked by carrier')
    for variant in variants:
        target = next(item['wire_exit_case_mm'] for item in variant['parked_housings'] if item['ref']==ref)
        thickness = variant['PCB_thickness_mm']
        dz = target[2]-nominal[2]
        x,y,z = assembled_exit
        for side in (-1,1):
            for stage, parts in envelope_motion([x,y,z+dz],ref,side).items():
                for name, shape in parts.items():
                    assert intersection_volume(shape,carrier)<1e-7, (ref,thickness,stage,name)
        center_z = target[2]-TOP_BELOW_EXIT+GUIDES_Z
        # The two saddles are outside the handles and their screw heads.
        # With the shelf slid inward along V they receive the exposed rods.
        shim = center_z-1-SEAT_Z
        assert 0.05 <= shim <= .6
        rod_ends = {str(i):block([u-1,9.8,center_z-1,u+1,12.5,center_z+1])
                    for i,u in enumerate((LANDING_U+v for v in GUIDES_X))}
        # Envelope of the clamp hardware in the saddle zone. Retain the
        # original tool seat and reserve space for its central screw.
        clamping_screw = block([LANDING_U-1.65,8.8,target[2]-28.10,
                               LANDING_U+1.65,16,target[2]-24.70])
        hand_guard = block([LANDING_U-6.2,-8.2,target[2]-29,
                            LANDING_U+6.2,8.2,target[2]-18.30])
        for name, part in [('clamp shaft',clamping_screw),('grips',hand_guard),*rod_ends.items()]:
            assert all(intersection_volume(shape,part)<1e-7 for shape in sweep), (ref,thickness,name)
            assert intersection_volume(shelf,part)<1e-7
        assert intersection_volume(shelf,carrier)<1e-7, (ref,'shelf and carrier')
        result.append({'PCB_thickness_mm':thickness,'rod_axis_case_z_mm':center_z,
                       'nominal_shim_mm':shim,
                       'nominal_slot_side_reserve_mm':SLOT_U_HALF-1,
                       'vertical_unshimmed_shelf_approach_mm':SHELF_APPROACH,
                       'shelf_swept_sections':len(sweep)})
    return result


def output_pair(name, shape):
    ste = OUT/(name+'.step')
    stl = ste.with_suffix('.stl')
    write_step(shape,ste)
    loaded = load(ste)
    assert max(abs(a-b) for a,b in zip(bounds(shape),bounds(loaded))) < .00002
    origin = bounds(shape)[:3]
    local = move(shape, *[-coordinate for coordinate in origin])
    metrics = mesh(local,stl)
    return (ste,stl), dict(metrics, STL_origin_in_case_mm=origin)


def main():
    source_paths = [AUDIT/name for name in ('service-case-m05.json','m05-harness.json','m05-tool.json')]
    case_report,harness,tool = [read(path) for path in source_paths]
    for report in (case_report,harness,tool):
        verify(report)
    shell = load(BASE/'bottom-m05-REVIEW.step')
    exits = read(AUDIT/'harness-study.json')['connector_exits_case_mm']
    variants = harness['trial_variants']
    OUT.mkdir(exist_ok=True)
    results = []
    outputs = []
    for datums in case_report['ports']:
        ref = datums['ref']
        nominal = next(e['wire_exit_case_mm'] for e in variants[0]['parked_housings'] if e['ref']==ref)
        carrier = make_carrier(ref,datums,nominal)
        shelf = make_shelf(ref,nominal)
        assert intersection_volume(carrier,shell)<1e-6, (ref,'anchor mounting mismatch')
        assert intersection_volume(shelf,shell)<1e-6
        checked = seated_checks(ref,carrier,shelf,variants,nominal,exits[ref])
        records = {}
        for label, shape in [('carrier',carrier),('rod-shelf',shelf)]:
            files, metrics = output_pair(ref+'-'+label, shape)
            outputs.extend(files)
            records[label] = metrics
        results.append({'ref':ref,'checks':checked,'media':records})
    dependencies = [*source_paths,Path(__file__),ROOT/'scripts/export_e73_retention_prints.py']
    provenance = dict(tool['source_sha256'], **{str(p.relative_to(ROOT)):sha(p) for p in dependencies})
    provenance.update(tool['outputs'])
    (AUDIT/'m05-parking-support.json').write_text(json.dumps({
        'status':'M05-parking-support-design-screened',
        'source_sha256':provenance,
        'outputs':{str(p.relative_to(ROOT)):sha(p) for p in outputs},
        'physical_verification':False,
        'manufacturing_released':False,
        'ports':results,
        'limits':[
            'The fixed carrier clears the tool strokes. The detachable shelf can rise from below around the parked rods in the nominal geometry. Inspect shim fit, tie preload and lateral retention on the actual assembled parts.',
            'The parked housing pose remains the one in the M05 lift check. Verify it with sample leads before moving the PCB. The supports are removable bench fixtures.',
        ],
    }, indent=2)+'\n')
    print('M05-parking-support-design-screened', flush=True)


if __name__ == '__main__':
    main()
