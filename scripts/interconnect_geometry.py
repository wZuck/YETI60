"""Exact circular bends and round-wire sweeps, in the FELK60 case frame."""
import math
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipe
from OCP.GC import GC_MakeArcOfCircle
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2, gp_Circ
from OCP.BRepCheck import BRepCheck_Analyzer


def add(a, b): return tuple(x+y for x, y in zip(a, b))
def sub(a, b): return tuple(x-y for x, y in zip(a, b))
def mul(a, k): return tuple(x*k for x in a)
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def norm(a): return math.sqrt(dot(a, a))
def unit(a): return mul(a, 1/norm(a))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def left(tangent): return unit(cross((0, 0, 1), tangent))


def line(a, b):
    assert norm(sub(a, b)) > 1e-7
    return {'kind': 'line', 'start': tuple(a), 'end': tuple(b), 'length': norm(sub(a, b))}


def arc(a, m, b, c):
    r = norm(sub(a, c))
    n = unit(cross(sub(a, c), sub(m, c)))
    theta = math.acos(max(-1, min(1, dot(unit(sub(a, c)), unit(sub(b, c))))))
    assert 0 < theta < math.pi and abs(norm(sub(b, c))-r) < 1e-6
    return {'kind': 'arc', 'start': tuple(a), 'mid': tuple(m), 'end': tuple(b),
            'center': tuple(c), 'normal': n, 'radius': r, 'length': r*theta}


def tangent(piece, end=False):
    if piece['kind'] == 'line': return unit(sub(piece['end'], piece['start']))
    return unit(cross(piece['normal'], sub(piece['end' if end else 'start'], piece['center'])))


def s_bend(start, direction, height, radius, rise_axis=(0, 0, 1)):
    """Two tangent circular arcs; both end tangents remain horizontal."""
    if abs(height)<1e-8:return [],tuple(start),0.
    d = unit(direction); z = mul(unit(rise_axis), 1 if height > 0 else -1)
    assert abs(dot(d, z)) < 1e-7
    theta = math.acos(1-abs(height)/(2*radius)); run = 2*radius*math.sin(theta)
    def first(t): return add(start, add(mul(d, radius*math.sin(t)), mul(z, radius*(1-math.cos(t)))))
    middle = first(theta)
    def second(t): return add(middle, add(mul(d, radius*(math.sin(theta)-math.sin(theta-t))), mul(z, radius*(math.cos(theta-t)-math.cos(theta)))))
    end = second(theta)
    return [arc(start, first(theta/2), middle, add(start, mul(z, radius))),
            arc(middle, second(theta/2), end, sub(end, mul(z, radius)))], end, run


def rounded_polyline(points, radius):
    pieces = []; previous = tuple(points[0])
    for a, b, c in zip(points, points[1:], points[2:]):
        incoming, outgoing = unit(sub(b, a)), unit(sub(c, b))
        theta = math.acos(max(-1, min(1, dot(incoming, outgoing))))
        assert 1e-6 < theta < math.pi-1e-6
        trim = radius*math.tan(theta/2)
        entry, exit = sub(b, mul(incoming, trim)), add(b, mul(outgoing, trim))
        assert dot(sub(entry, previous), incoming) >= -1e-6, 'Bends overlap'
        if norm(sub(entry, previous)) > 1e-7: pieces.append(line(previous, entry))
        inward = unit(sub(outgoing, mul(incoming, math.cos(theta))))
        center = add(entry, mul(inward, radius))
        mid = add(center, mul(unit(add(sub(entry, center), sub(exit, center))), radius))
        pieces.append(arc(entry, mid, exit, center)); previous = exit
    if norm(sub(points[-1], previous)) > 1e-7: pieces.append(line(previous, points[-1]))
    return pieces


def offset_path(pieces, lateral):
    result = []
    for piece in pieces:
        a = add(piece['start'], mul(left(tangent(piece)), lateral))
        b = add(piece['end'], mul(left(tangent(piece, True)), lateral))
        if piece['kind'] == 'line': result.append(line(a, b)); continue
        if abs(piece['normal'][2]) > .999:
            # A parallel XY arc shares its original center.
            center = piece['center']; r = norm(sub(a, center))
            mid = add(center, mul(unit(sub(piece['mid'], center)), r))
        else:
            assert abs(piece['normal'][2]) < 1e-7, 'Only XY and vertical-plane bends are supported'
            shift = mul(left(tangent(piece)), lateral)
            center, mid = add(piece['center'], shift), add(piece['mid'], shift)
        result.append(arc(a, mid, b, center))
    validate(result)
    return result


def validate(pieces):
    for a, b in zip(pieces, pieces[1:]):
        assert norm(sub(a['end'], b['start'])) < 1e-6, 'Discontinuous wire'
        assert dot(tangent(a, True), tangent(b)) > .999999, 'Non-tangent wire joint'


def sweep(pieces, diameter):
    validate(pieces); spine = BRepBuilderAPI_MakeWire()
    for p in pieces:
        if p['kind'] == 'line': edge = BRepBuilderAPI_MakeEdge(gp_Pnt(*p['start']), gp_Pnt(*p['end'])).Edge()
        else: edge = BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(*p['start']), gp_Pnt(*p['mid']), gp_Pnt(*p['end'])).Value()).Edge()
        spine.Add(edge)
    assert spine.IsDone()
    profile = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(gp_Circ(gp_Ax2(gp_Pnt(*pieces[0]['start']), gp_Dir(*tangent(pieces[0]))), diameter/2)).Edge()).Wire()
    face = BRepBuilderAPI_MakeFace(profile).Face(); operation = BRepOffsetAPI_MakePipe(spine.Wire(), face)
    operation.Build(); shape = operation.Shape()
    assert operation.IsDone() and BRepCheck_Analyzer(shape).IsValid()
    return shape
