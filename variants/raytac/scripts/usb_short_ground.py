"""Check filled ground islands independently of KiCad's zone-item grouping."""
from shapely.geometry import Polygon
from shapely.ops import unary_union


def connected_ground(native):
    regions = []
    layer_indices = {}
    # One nanometre only repairs polygon arithmetic at coincident edges.
    for layer, shapes in native['ground_copper'].items():
        copper = unary_union([Polygon(p['outer'], p['holes']).buffer(0) for p in shapes]).buffer(.000001)
        pieces = list(copper.geoms) if copper.geom_type == 'MultiPolygon' else [copper]
        layer_indices[layer] = []
        for piece in pieces:
            layer_indices[layer].append(len(regions)); regions.append((layer, piece))
    parent = list(range(len(regions)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for connector in native['ground_vertical_connectors']:
        touches = []
        for layer, shapes in connector['by_layer'].items():
            geometry = unary_union([Polygon(p['outer'], p['holes']).buffer(0) for p in shapes])
            touches += [i for i in layer_indices[layer] if regions[i][1].intersects(geometry)]
        for i in touches[1:]:
            parent[find(i)] = find(touches[0])
    groups = {}
    for i, (layer, piece) in enumerate(regions):
        groups.setdefault(find(i), []).append(dict(layer=layer, area_mm2=piece.area, bounds_mm=list(piece.bounds)))
    assert len(groups) == 1, ('Disconnected filled ground copper', list(groups.values()))
    return dict(connected_components=len(groups), layer_regions=len(regions),
                vertical_connectors_checked=len(native['ground_vertical_connectors']),
                coordinate_join_allowance_mm=.000001,
                method='Union filled ground, pads and tracks separately by layer; join layers only through GND vias/PTH pads',
                limitation='Connectivity only; no return-current, impedance, thermal or EMC solution')
