#!/usr/bin/env python3
"""Rasterize dimensioned native polygons without inventing electrode artwork."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
from shapely import make_valid, unary_union
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def union(items):
    return unary_union([make_valid(Polygon(p['outer'], p['holes'])) for p in items if len(p['outer']) >= 3])


def main():
    source = ROOT / '.assembly-work/usb-short-assembly/surfaces.json'
    data = json.loads(source.read_text())
    for p,h in data['source_sha256'].items():
        assert sha(ROOT/p) == h, p
    outline = union(data['outline']); bb = outline.bounds
    scale = 24  # 24 pixels / mm; a print-independent visual map.
    size = (round((bb[2]-bb[0])*scale), round((bb[3]-bb[1])*scale))

    def mask(geometry):
        image = Image.new('L',size,0); draw = ImageDraw.Draw(image)
        def paint(poly):
            if poly.geom_type == 'Polygon':
                xy = lambda coords: [((x-bb[0])*scale,(y-bb[1])*scale) for x,y in coords]
                draw.polygon(xy(poly.exterior.coords),fill=255)
                for ring in poly.interiors: draw.polygon(xy(ring.coords),fill=0)
            elif hasattr(poly,'geoms'):
                for p in poly.geoms: paint(p)
        paint(geometry)
        return image

    outputs = {}
    for side, record in data['surfaces'].items():
        copper = union(record['copper']).intersection(outline)
        openings = union(record['pad_mask_openings']).intersection(copper)
        image = Image.new('RGB',size,(26,68,43))
        image.paste((42,92,55),mask=mask(copper))
        image.paste((168,133,53),mask=mask(openings))
        target = BASE / 'assembly' / ('pcb-surface-'+side+'.png')
        image.save(target)
        outputs[str(target.relative_to(ROOT))] = sha(target)
    report = dict(status='native-surface-visual-maps-generated', outputs=outputs,
        pcb_bounds_XY_mm=list(bb), raster_pixels_per_mm=scale, source_sha256=data['source_sha256'] | {
            str(Path(__file__).resolve().relative_to(ROOT)):sha(Path(__file__))},
        limits=[data['scope'], 'The flat colour maps are not Gerbers or proof of a specific final surface finish'])
    (BASE/'audit/assembly-surfaces.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Front/back native surface visual maps:',size)


if __name__ == '__main__':
    main()
