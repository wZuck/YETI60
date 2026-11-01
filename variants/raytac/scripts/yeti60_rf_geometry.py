#!/usr/bin/env python3
"""Exact allowed replacement of the original EC60 right vertical edge."""
import math


def wing_profile(spec):
    x,top,X,bottom=spec['proposed_PCB_wing_XY']
    r=spec['PCB_wing_corner_radius']
    assert x==spec['original_right_edge_X'] and r>=.5
    assert X-x>2*r and bottom-top>2*r
    inset=r*(1-1/math.sqrt(2))
    # Each tuple is (kind, start, end[, arc midpoint]), in PCB coordinates.
    return [
        ('line',(x,105.90966),(x,top-r)),
        ('arc',(x,top-r),(x+r,top),(x+inset,top-inset)),
        ('line',(x+r,top),(X-r,top)),
        ('arc',(X-r,top),(X,top+r),(X-inset,top+inset)),
        ('line',(X,top+r),(X,bottom-r)),
        ('arc',(X,bottom-r),(X-r,bottom),(X-inset,bottom-inset)),
        ('line',(X-r,bottom),(x+r,bottom)),
        ('arc',(x+r,bottom),(x,bottom+r),(x+inset,bottom+inset)),
        ('line',(x,bottom+r),(x,159.00966)),
    ]


def expected_outline(original, spec, pcb):
    """Preserve every original edge except the explicitly replaced line."""
    x=round(spec['original_right_edge_X']*1e6)
    ends={(x,round(105.90966*1e6)),(x,round(159.00966*1e6))}
    old=[v for v in original if {(v[1],v[2]),(v[3],v[4])}==ends]
    assert len(old)==1 and old[0][0]==int(pcb.SHAPE_T_SEGMENT)
    output=[v for v in original if v!=old[0]]
    def nm(q):return tuple(round(v*1e6) for v in q)
    for kind,a,z,*middle in wing_profile(spec):
        mid=nm(middle[0]) if middle else (0,0)
        output.append((int(pcb.SHAPE_T_ARC if kind=='arc' else pcb.SHAPE_T_SEGMENT),
                       *nm(a),*nm(z),*mid,old[0][-1]))
    return sorted(output)


def matches_controlled_outline(original, actual, spec, pcb):
    expected=expected_outline(original,spec,pcb)
    x=round(spec['original_right_edge_X']*1e6)
    ends={(x,round(105.90966*1e6)),(x,round(159.00966*1e6))}
    replaced=next(v for v in original if {(v[1],v[2]),(v[3],v[4])}==ends)
    remaining=list(actual)
    # Every retained original line/arc stays exact, including its orientation.
    for edge in original:
        if edge==replaced:continue
        if edge not in remaining:return False
        remaining.remove(edge)
        expected.remove(edge)
    if len(remaining)!=len(expected):return False
    for edge in expected:
        def equal(other):
            if edge[0]!=other[0] or edge[-1]!=other[-1]:return False
            # KiCad normalizes concave arc orientation and reconstructs integer
            # arc centers. Allow 100 nm only on the nine replacement primitives;
            # this is far below the declared 0.2 mm routing tolerance.
            tolerance=100 if edge[0]==int(pcb.SHAPE_T_ARC) else 0
            close=lambda a,b:all(abs(x-y)<=tolerance for x,y in zip(a,b))
            ends_match=(close(edge[1:3],other[1:3]) and close(edge[3:5],other[3:5])) or (close(edge[1:3],other[3:5]) and close(edge[3:5],other[1:3]))
            return ends_match and close(edge[5:7],other[5:7])
        match=next((other for other in remaining if equal(other)),None)
        if match is None:return False
        remaining.remove(match)
    return not remaining
