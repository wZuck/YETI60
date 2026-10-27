#!/usr/bin/env python3
"""Render the audited PCB with KiCad 10, and encode a genuine 3D turntable.

Requires Pillow, kicad-cli, ffmpeg and KiCad's standard 3D model library.
The render-only board and raw frames live in ignored .render-work/. Electrical
sources are never rewritten. J2/SW100 are explicitly illustrative body proxies.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
except ImportError:
    sys.path.insert(0, os.environ.get('KICAD_AUDIT_PYTHONPATH', '/tmp/yaeckb-pcb-audit/python'))
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from kicad_sexpr import loads, dumps, child, children, Atom

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/ec60-nrf52840'
SOURCE = BASE / 'EC60-nRF52840.kicad_pcb'
OUT = ROOT / 'renders/ec60-nrf52840'
WORK = ROOT / '.render-work'
CLI = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
MODELS = Path(os.environ.get('KICAD10_3DMODEL_DIR', '/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels'))
FONT = os.environ.get('RENDER_FONT', '/System/Library/Fonts/Helvetica.ttc')
MONO = os.environ.get('RENDER_MONO_FONT', '/System/Library/Fonts/SFNSMono.ttf')
ACCENT = (109, 231, 187)
MUTED = (142, 163, 181)
WHITE = (235, 244, 250)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size, mono=False):
    path = MONO if mono else FONT
    if Path(path).exists():
        return ImageFont.truetype(path, size)
    for fallback in ('DejaVuSans.ttf', 'Arial.ttf'):
        try:
            return ImageFont.truetype(fallback, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def box_vrml(parts):
    # KiCad's legacy WRL unit is 0.1 inch = 2.54 mm.
    text = ['#VRML V2.0 utf8', '# Illustrative render body; not a mechanical qualification model.']
    for center, size, color in parts:
        center = [v / 2.54 for v in center]
        size = [v / 2.54 for v in size]
        text.append('Transform { translation %s children [ Shape { appearance Appearance { material Material { diffuseColor %s specularColor .25 .25 .25 shininess .25 } } geometry Box { size %s } } ] }' % (
            ' '.join(map(str, center)), ' '.join(map(str, color)), ' '.join(map(str, size))))
    return '\n'.join(text) + '\n'


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(exist_ok=True)
    proxy_dir = OUT / 'models'
    proxy_dir.mkdir(exist_ok=True)
    # Plan-view outlines follow the footprint; these heights are illustrative.
    white, metal, black = (.88, .87, .80), (.60, .65, .67), (.08, .10, .12)
    (proxy_dir / 'J2-illustrative.wrl').write_text(box_vrml([
        ((0, 3.2, 1.65), (9.8, 1.2, 3.3), white),
        ((-4.35, -.3, 1.65), (1.1, 6, 3.3), white),
        ((4.35, -.3, 1.65), (1.1, 6, 3.3), white),
        ((0, -.3, .35), (8, 6, .7), white),
        *[((x, 0, 1.4), (.45, 5.4, .45), metal) for x in (-2, 0, 2)]
    ]))
    (proxy_dir / 'SW100-illustrative.wrl').write_text(box_vrml([
        ((0, 0, .8), (9, 3.6, 1.6), metal),
        ((-2.5, -2.5, 1), (1.6, 2, 1.5), black),
    ]))
    board = loads(SOURCE.read_text())
    resolutions = []
    proxies = {'J2': 'J2-illustrative.wrl', 'SW100': 'SW100-illustrative.wrl'}
    geometry_only = set(json.loads((BASE / 'metadata-audit.json').read_text())['non_purchased_geometry_references']) | {'REF**'}
    for fp in children(board, 'footprint'):
        ref = next(str(p[2]) for p in children(fp, 'property') if str(p[1]) == 'Reference')
        old_models = children(fp, 'model')
        fp[:] = [v for v in fp if v not in old_models]
        if ref in geometry_only:
            continue
        if ref in proxies:
            path = proxy_dir / proxies[ref]
            fp.append([Atom('model'), str(path), [Atom('offset'), [Atom('xyz'), Atom('0'), Atom('0'), Atom('0')]],
                       [Atom('scale'), [Atom('xyz'), Atom('1'), Atom('1'), Atom('1')]],
                       [Atom('rotate'), [Atom('xyz'), Atom('0'), Atom('0'), Atom('0')]]])
            resolutions.append({'ref': ref, 'kind': 'illustrative-proxy', 'model': str(path.relative_to(ROOT)), 'height_qualified': False})
            continue
        loaded = 0
        for model in old_models:
            original = str(model[1])
            if original == 'Housing_SSOP/TSSOP-16.wrl':
                # The same footprint already includes its newer SSOP STEP.
                resolutions.append({'ref': ref, 'kind': 'discard-obsolete-duplicate', 'original': original})
                continue
            relative = re.sub(r'^\$\{KICAD\d+_3DMODEL_DIR\}/', '', original)
            if relative.endswith('.wrl'):
                relative = relative[:-4] + '.step'
            kind = 'standard-model'
            if ref == 'J1':
                relative = 'Connector_JST.3dshapes/JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal.step'
                # The retained footprint shifts all pads by +0.0625 mm Y
                # relative to KiCad's standard footprint. 3D Y is inverted.
                child(child(model, 'offset'), 'xyz')[1:] = [Atom('0'), Atom('-0.0625'), Atom('0')]
                kind = 'matching-standard-part-with-origin-adjustment'
            if ref == 'U5':
                relative = 'Package_DFN_QFN.3dshapes/WQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm.step'
                kind = 'package-visual-substitute-not-height-qualified'
            path = MODELS / relative
            if not path.is_file():
                raise FileNotFoundError(f'{ref}: no render model: {path}')
            model[1] = str(path)
            fp.append(model)
            loaded += 1
            resolutions.append({'ref': ref, 'kind': kind, 'original': original, 'model': relative, 'sha256': digest(path)})
        if not loaded:
            raise ValueError(f'{ref}: assembled component has no model')
    target = WORK / 'EC60-render.kicad_pcb'
    target.write_text(dumps(board) + '\n')
    shutil.copyfile(BASE / 'EC60-nRF52840.kicad_pro', target.with_suffix('.kicad_pro'))
    return target, resolutions


def native(board, path, width, height, side, rotate, quality='basic', zoom=1.32):
    if not path.exists():
        cmd = [CLI, 'pcb', 'render', '--output', str(path), '--width', str(width), '--height', str(height),
               '--side', side, '--rotate=' + rotate, '--zoom', str(zoom), '--quality', quality,
               '--background', 'transparent', '--light-top', '.8', '--light-bottom', '.8', '--light-camera', '.4', str(board)]
        with path.with_suffix('.log').open('w') as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    with Image.open(path) as image:
        image.load()
        if image.getbbox() is None or abs(image.width-width)>64 or abs(image.height-height)>64:
            raise ValueError('Invalid native image: ' + str(path))
        # KiCad rounds raytracing dimensions to its tile size. Center-pad the
        # small difference; never stretch the PCB or change its aspect ratio.
        if image.size != (width,height):
            normalized=Image.new('RGBA',(width,height))
            normalized.alpha_composite(image.convert('RGBA'),((width-image.width)//2,(height-image.height)//2))
            normalized.save(path)


def background(size):
    w, h = size
    im = Image.new('RGBA', size)
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        d.line((0, y, w, y), fill=(int(12 + 5*t), int(23 + 9*t), int(34 + 11*t), 255))
    return im


def header(im, subtitle, small=False):
    d = ImageDraw.Draw(im)
    scale = im.width / 2000
    def pos(x, y): return (int(x*scale), int(y*scale))
    d.text(pos(85, 55), 'Y E T I 6 0   /   E C 6 0', font=font(int(23*scale), True), fill=ACCENT)
    d.text(pos(80, 105), 'Single nRF52840', font=font(int(68*scale)), fill=WHITE)
    d.text(pos(84, 191), subtitle, font=font(int(27*scale)), fill=MUTED)
    d.line((*pos(85, 250), *pos(1915, 250)), fill=(47, 65, 80), width=1)
    d.text(pos(1570, 65), '2026.10 / PCB', font=font(int(23*scale), True), fill=MUTED)


def board_paste(im, layer, rect):
    crop = layer.crop(layer.getbbox())
    fitted = ImageOps.contain(crop, (rect[2]-rect[0], rect[3]-rect[1]), Image.Resampling.LANCZOS)
    x = rect[0] + (rect[2]-rect[0]-fitted.width)//2
    y = rect[1] + (rect[3]-rect[1]-fitted.height)//2
    shadow = Image.new('RGBA', im.size)
    silhouette = Image.new('RGBA', fitted.size, (0, 0, 0, 0))
    silhouette.putalpha(fitted.getchannel('A').point(lambda p: int(p*.45)))
    shadow.alpha_composite(silhouette, (x, y+22))
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    im.alpha_composite(fitted, (x, y))


def footer(im):
    d = ImageDraw.Draw(im)
    scale = im.width / 2000
    y = im.height - int(113*scale)
    d.line((int(85*scale), y-25, int(1915*scale), y-25), fill=(47, 65, 80))
    d.text((int(85*scale), y), 'ONE CONTROLLER  /  FOUR COPPER LAYERS', font=font(int(22*scale), True), fill=WHITE)
    d.text((int(85*scale), y+int(36*scale)), 'CAD visualization / J2, SW100 & U5 models illustrative / SI & RF analysis pending', font=font(int(20*scale)), fill=MUTED)


def stills(board, jobs):
    specs = [('front', 'top', '25,0,-10'), ('back', 'bottom', '20,0,10')]
    def render(spec):
        name, side, rot = spec
        path = WORK / ('still-' + name + '.png')
        native(board, path, 2600, 1600, side, rot, 'high', 1.38)
        return name, path
    with ThreadPoolExecutor(max_workers=min(jobs, 2)) as pool:
        results = list(pool.map(render, specs))
    images = {name: Image.open(path).convert('RGBA') for name, path in results}
    for name, subtitle in [('front', 'F.Cu / Electrocapacitive sensing surface'), ('back', 'B.Cu / Controller, charging and analog electronics')]:
        canvas = background((2400, 1500))
        header(canvas, subtitle)
        board_paste(canvas, images[name], (90, 350, 2310, 1275))
        footer(canvas)
        canvas.convert('RGB').save(OUT / ('pcb-' + name + '.png'), optimize=True)
    overview = background((2400, 1900))
    header(overview, 'Two sides. One controller. Original EC60 sensing geometry.')
    for name, y, label in [('front', 375, '01 / SENSING SIDE'), ('back', 1015, '02 / COMPONENT SIDE')]:
        ImageDraw.Draw(overview).text((102, y), label, font=font(26, True), fill=ACCENT)
        board_paste(overview, images[name], (100, y+60, 2300, y+620))
    footer(overview)
    overview.convert('RGB').save(OUT / 'pcb-overview.png', optimize=True)


def animate(board, frames, fps, jobs):
    raw, composed = WORK / 'raw', WORK / 'frames'
    raw.mkdir(exist_ok=True)
    composed.mkdir(exist_ok=True)
    def render(i):
        angle = 25 + 360*i/frames
        roll = -8*math.cos(2*math.pi*i/frames)
        p = raw / f'{i:04d}.png'
        native(board, p, 1600, 900, 'top', f'{angle:.6f},0,{roll:.6f}', zoom=1.3)
        canvas = background((1600, 1000))
        face = 'F.Cu / Sensing surface' if math.cos(math.radians(angle)) >= 0 else 'B.Cu / Component side'
        header(canvas, '360-degree 3D turntable / ' + face, True)
        canvas.alpha_composite(Image.open(p).convert('RGBA'), (0, 90))
        footer(canvas)
        canvas.convert('RGB').save(composed / f'{i:04d}.png')
        return i
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for n, future in enumerate(as_completed([pool.submit(render, i) for i in range(frames)]), 1):
            future.result()
            if n % 12 == 0 or n == frames:
                print(f'Animation {n}/{frames}', flush=True)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-framerate', str(fps), '-i', str(composed/'%04d.png'),
                    '-frames:v', str(frames), '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(OUT/'pcb-turntable.mp4')], check=True)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(OUT/'pcb-turntable.mp4'), '-filter_complex',
                    'fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3',
                    '-loop', '0', str(OUT/'pcb-turntable.gif')], check=True)
    # Contact sheet for visual QA: includes both faces, near-edge poses and loop.
    indices = [0, frames//8, frames//4, frames//2, 3*frames//4, frames-1]
    sheet = Image.new('RGB', (1200, 750), (12, 23, 34))
    for j, i in enumerate(indices):
        thumb = Image.open(composed/f'{i:04d}.png').resize((400, 250), Image.Resampling.LANCZOS)
        sheet.paste(thumb, ((j%3)*400, (j//3)*375))
    sheet.save(WORK/'animation-contact-sheet.jpg')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=int, default=144)
    parser.add_argument('--fps', type=int, default=24)
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--stills-only', action='store_true')
    args = parser.parse_args()
    if args.frames < 16 or args.fps < 1 or args.jobs < 1:
        parser.error('frames >= 16, fps >= 1 and jobs >= 1 required')
    audit = json.loads((BASE/'audit-current.json').read_text())
    source_hash = digest(SOURCE)
    if audit['status'] != 'cad-checks-passed' or audit['source_sha256'][SOURCE.name] != source_hash:
        raise ValueError('Render source is not the audited PCB')
    # Cache directory is specific to the source, visual recipe and model library.
    global WORK
    recipe_hash = digest(Path(__file__))
    WORK = WORK / (source_hash[:12] + '-' + recipe_hash[:12])
    WORK.mkdir(parents=True, exist_ok=True)
    board, resolutions = prepare()
    renderer_version = subprocess.check_output([CLI, '--version'], text=True).strip()
    cache_inputs = {'models': resolutions, 'frames': args.frames, 'fps': args.fps, 'renderer': renderer_version}
    cache_key = hashlib.sha256(json.dumps(cache_inputs, sort_keys=True).encode()).hexdigest()[:12]
    WORK = WORK / cache_key
    WORK.mkdir(exist_ok=True)
    render_board = WORK / board.name
    shutil.copyfile(board, render_board)
    shutil.copyfile(board.with_suffix('.kicad_pro'), render_board.with_suffix('.kicad_pro'))
    board = render_board
    print('Prepared render-only snapshot; design source unchanged', flush=True)
    stills(board, args.jobs)
    print('Stills complete', flush=True)
    if not args.stills_only:
        animate(board, args.frames, args.fps, args.jobs)
    if digest(SOURCE) != source_hash:
        raise ValueError('Design PCB changed during render')
    outputs = {p.name: {'sha256': digest(p), 'bytes': p.stat().st_size} for p in OUT.iterdir() if p.suffix in (('.png',) if args.stills_only else ('.png', '.gif', '.mp4'))}
    manifest = {'source': str(SOURCE.relative_to(ROOT)), 'source_sha256': source_hash,
                'recipe_sha256': recipe_hash, 'renderer': renderer_version,
                'animation': {'frames': args.frames, 'fps': args.fps, 'seconds': args.frames/args.fps, 'dimensions': [1600,1000], 'rotation': 'full 360 degrees about X; gentle Z oscillation', 'quality': 'basic'} if not args.stills_only else None,
                'stills': {'quality': 'high', 'native_dimensions': [2600,1600]},
                'model_resolutions': resolutions, 'outputs': outputs,
                'limits': ['render-only substitutions do not modify the design or frozen footprint library', 'J2 and SW100 are illustrative bodies; U5 uses a generic package model', 'Not an assembled keyboard, enclosure fit test, SI or RF simulation']}
    (OUT/'render-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Render source hash verified unchanged; assets and manifest complete', flush=True)


if __name__ == '__main__':
    main()
