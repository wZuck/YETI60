#!/usr/bin/env python3
"""Export the checked candidate, preserving native and CAM evidence separately."""
import csv
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
import pcbnew as pcb
from usb_short_passive_contract import verify_passives
from usb_short_power_contract import verify_layout
from kicad_sexpr import loads, dumps, child, children, form
from export_yeti60_usb_reference import polygons

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/usb-short-route'
OUT = BASE / 'fabrication'
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
LAYERS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu', 'F.Mask', 'B.Mask',
          'F.Paste', 'B.Paste', 'F.SilkS', 'B.SilkS', 'Edge.Cuts']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_sources():
    verify_passives(); verify_layout()
    native = json.loads((BASE / 'audit/native-check.json').read_text())
    assert native['status'] == 'native-candidate-checks-passed'
    assert native['strict_DRC_errors'] == native['unconnected_items'] == native['schematic_parity_items'] == 0
    assert not native['power_layout_rework_open']
    for path, digest in native['source_sha256'].items():
        assert sha(ROOT/path) == digest, ('Stale native source', path)
    return native


def native_map(path, purchased):
    board = pcb.LoadBoard(str(path))
    assert board.GetCopperLayerCount() == 4
    vias = [v for v in board.GetTracks() if isinstance(v, pcb.PCB_VIA)]
    assert len(vias) == 815
    holes = []; pads = []; positions = {}; paste = []; excluded_paste = []; ipc_pads = []
    for via in vias:
        assert via.GetViaType() == pcb.VIATYPE_THROUGH
        assert (via.TopLayer(), via.BottomLayer()) == (pcb.F_Cu, pcb.B_Cu)
        assert pcb.ToMM(via.GetDrillValue()) >= .3-1e-8
        assert pcb.ToMM(via.GetWidth(pcb.F_Cu)) >= .5-1e-8
        holes.append(dict(owner=via.m_Uuid.AsString(), plated=True,
                          center_mm=[pcb.ToMM(via.GetPosition().x), -pcb.ToMM(via.GetPosition().y)],
                          size_mm=[pcb.ToMM(via.GetDrillValue())]*2, kind='circle',net=via.GetNetname()))
    for f in board.GetFootprints():
        ref = f.GetReference()
        if ref in purchased:
            positions[ref] = dict(x_mm=pcb.ToMM(f.GetPosition().x), y_mm=-pcb.ToMM(f.GetPosition().y),
                                  angle_deg=f.GetOrientationDegrees(), side='bottom' if f.IsFlipped() else 'top',
                                  value=f.GetValue(),package=str(f.GetFPID().GetLibItemName()))
        for p in f.Pads():
            drill = p.GetDrillSize()
            if drill.x or drill.y:
                x, y = pcb.ToMM(p.GetPosition().x), -pcb.ToMM(p.GetPosition().y)
                width, height = pcb.ToMM(drill.x), pcb.ToMM(drill.y)
                record = dict(owner=ref+'.'+p.GetNumber(), uuid=p.m_Uuid.AsString(),
                              plated=p.GetAttribute()==pcb.PAD_ATTRIB_PTH,
                              center_mm=[x,y], size_mm=[width,height], kind='circle')
                if drill.x != drill.y:
                    assert p.GetOrientationDegrees() == 0, 'Rotated slot needs an explicit native transform'
                    dx,dy = max(0,width-height)/2,max(0,height-width)/2
                    record.update(kind='slot',diameter_mm=min(width,height),
                                  endpoints_mm=[[x-dx,y-dy],[x+dx,y+dy]])
                holes.append(record)
            accesses=[0] if drill.x or drill.y else [n for layer,n in [(pcb.F_Cu,1),(pcb.B_Cu,4)] if p.IsOnLayer(layer)]
            if p.GetNumber():assert accesses,'Numbered internal-only pad requires a separate IPC test-access policy'
            for access in accesses:
                ipc_pads.append(dict(ref=ref,pin=p.GetNumber() or None,net=p.GetNetname(),
                                     center_mm=[pcb.ToMM(p.GetPosition().x),-pcb.ToMM(p.GetPosition().y)],
                                     access_layer=access))
            if ref in purchased and p.GetNumber():
                q = p.GetBoundingBox()
                pads.append(dict(ref=ref, pin=p.GetNumber(), net=p.GetNetname(),
                                 center_mm=[pcb.ToMM(p.GetPosition().x), -pcb.ToMM(p.GetPosition().y)],
                                 bbox_mm=[[pcb.ToMM(q.GetLeft()), -pcb.ToMM(q.GetBottom())],
                                          [pcb.ToMM(q.GetRight()), -pcb.ToMM(q.GetTop())]],
                                 layer='B.Cu' if f.IsFlipped() else 'F.Cu'))
            if p.IsOnLayer(pcb.B_Paste):
                margin = p.GetSolderPasteMargin(pcb.B_Paste)
                assert margin.x == margin.y == 0, 'Nonzero paste margin needs a CAM native-envelope comparator'
                q = p.GetBoundingBox()
                entry = dict(ref=ref,pin=p.GetNumber(),center_mm=[pcb.ToMM(p.GetPosition().x),-pcb.ToMM(p.GetPosition().y)],
                             bbox_mm=[[pcb.ToMM(q.GetLeft()),-pcb.ToMM(q.GetBottom())],
                                      [pcb.ToMM(q.GetRight()),-pcb.ToMM(q.GetTop())]])
                if ref == 'JP1':excluded_paste.append(entry)
                else:
                    assert ref in purchased, ('Unpurchased stencil aperture',ref)
                    paste.append(entry)
    bb = board.GetBoardEdgesBoundingBox()
    outline = pcb.SHAPE_POLY_SET(); assert board.GetBoardPolygonOutlines(outline,False)
    points = [point for polygon in polygons(outline) for point in polygon['outer']]
    return dict(copper_layers=4, through_vias=len(vias), holes=holes, fitted_pads=pads,
                positions=positions, paste_apertures=paste, excluded_paste=excluded_paste,ipc_pad_sites=ipc_pads,
                outline_polygons_mm=[[[x,-y] for x,y in p['outer']] for p in polygons(outline)],
                bounds_mm=[[min(p[0] for p in points), -max(p[1] for p in points)],
                                               [max(p[0] for p in points), -min(p[1] for p in points)]],
                outline_stroke_bounds_mm=[[pcb.ToMM(bb.GetLeft()), -pcb.ToMM(bb.GetBottom())],
                                         [pcb.ToMM(bb.GetRight()), -pcb.ToMM(bb.GetTop())]],
                coordinate_frame='KiCad absolute origin, millimetres; Gerber/Excellon Y is negative native PCB Y; bottom X is not mirrored')


def deterministic_zip(target, files):
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o100644 << 16
            z.writestr(info, data)


def main():
    native = checked_sources(); OUT.mkdir(exist_ok=True)
    board = BASE/'EC60-nRF52840.kicad_pcb'; before = sha(board)
    with (BASE/'mainboard-purchase.csv').open(newline='') as f:
        purchased = {r.strip() for row in csv.DictReader(f) for r in row['References'].split(',')}
    assert len(purchased) == 75 and not purchased & {'JP1', 'R30', 'R31'}
    mapping = native_map(board, purchased)
    with tempfile.TemporaryDirectory(prefix='yeti60-candidate-cam-') as d:
        work = Path(d)
        def run(*args,input_board=board):
            subprocess.run([CLI, 'pcb', 'export', *args, str(input_board)], check=True, capture_output=True)
        fab_layers = [layer for layer in LAYERS if 'Paste' not in layer]
        run('gerbers', '--check-zones', '--layers', ','.join(fab_layers), '--no-protel-ext', '--subtract-soldermask', '-o', str(work))
        run('drill', '--format', 'excellon', '--drill-origin', 'absolute', '--excellon-units', 'mm',
            '--excellon-zeros-format', 'decimal', '--excellon-oval-format', 'route', '--excellon-separate-th', '--generate-report',
            '--report-path', str(work/'drill-report.txt'), '-o', str(work))
        # KiCad's IPC exporter always uses the auxiliary origin. Normalize
        # only that coordinate setting in an isolated copy, never source Cu.
        tree = loads(board.read_text()); setup = child(tree,'setup')
        origin = child(setup,'aux_axis_origin')
        if origin is None:setup.append(form('aux_axis_origin',0,0))
        else:origin[1:] = [0,0]
        ipc_dir = work/'ipc-source';ipc_dir.mkdir()
        ipc_board = ipc_dir/board.name; ipc_board.write_text(dumps(tree)+'\n')
        subprocess.run([CLI,'pcb','export','ipcd356','-o',str(work/'mainboard.ipc'),str(ipc_board)],check=True,capture_output=True)
        # JP1 must stay open. Omit its two paste apertures in a paste-only
        # copy, preserving the source board and every copper/pad position.
        stencil_tree = loads(board.read_text()); removed_paste = 0
        for f in children(stencil_tree,'footprint'):
            properties={str(p[1]):str(p[2]) for p in children(f,'property')}
            if properties.get('Reference') != 'JP1':continue
            for p in children(f,'pad'):
                layers=child(p,'layers')
                if 'B.Paste' in layers:layers.remove('B.Paste');removed_paste+=1
        assert removed_paste == len(mapping['excluded_paste']) == 2
        stencil_dir=work/'stencil-source';stencil_dir.mkdir()
        stencil_board=stencil_dir/board.name;stencil_board.write_text(dumps(stencil_tree)+'\n')
        stencil_plot=work/'stencil-plot';stencil_plot.mkdir()
        (stencil_dir/board.with_suffix('.kicad_pro').name).write_bytes(board.with_suffix('.kicad_pro').read_bytes())
        run('gerbers','--layers','B.Paste,Edge.Cuts','--no-protel-ext','-o',str(stencil_plot),input_board=stencil_board)
        paste_name=board.stem+'-B_Paste.gbr'
        (work/paste_name).write_bytes((stencil_plot/paste_name).read_bytes())
        run('pos', '--format', 'csv', '--units', 'mm', '--side', 'both', '-o', str(work/'positions-raw.csv'))
        with (work/'positions-raw.csv').open(newline='') as f:
            raw = list(csv.DictReader(f))
        positions = [row for row in raw if row['Ref'] in purchased]
        assert {row['Ref'] for row in positions} == purchased
        with (work/'positions.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(raw[0]), lineterminator='\n')
            writer.writeheader(); writer.writerows(positions)
        (work/'positions-raw.csv').unlink()
        # Normalize only generation timestamps, preserving all CAM coordinates.
        for p in work.iterdir():
            if not p.is_file():continue
            text = p.read_text()
            text = re.sub(r'20\d\d-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:[.+Z0-9:-]*)', '2000-01-01T00:00:00', text)
            p.write_text(text)
        required = {board.stem+'-'+layer.replace('SilkS','Silkscreen').replace('.','_')+'.gbr' for layer in fab_layers}
        assert required <= {p.name for p in work.iterdir()}, ('Missing exported Gerber layer', sorted(required - {p.name for p in work.iterdir()}))
        gerbers = {p.name:p.read_bytes() for p in work.iterdir() if p.name in required or p.suffix.lower() in ['.drl','.gbrjob']}
        stencil_names = {board.stem+'-'+layer.replace('.','_')+'.gbr' for layer in ['B.Paste','Edge.Cuts']}
        stencil = {p.name:p.read_bytes() for p in work.iterdir() if p.name in stencil_names}
        assert len([n for n in gerbers if n.endswith('.drl')]) == 2
        assert len(stencil) == 2
        deterministic_zip(OUT/'yeti60-raytac-candidate-gerbers.zip', gerbers)
        deterministic_zip(OUT/'yeti60-raytac-candidate-bottom-stencil.zip', stencil)
        for name in ['positions.csv','mainboard.ipc','drill-report.txt']:
            (OUT/name).write_bytes((work/name).read_bytes())
    assert sha(board) == before, 'CAM export modified the native PCB'
    sources = native['source_sha256'] | {str(p.relative_to(ROOT)):sha(p) for p in [
        Path(__file__), BASE/'audit/native-check.json', ROOT/'mechanical/pcb-fabrication-spec.json',
        ROOT/'scripts/kicad_sexpr.py', ROOT/'scripts/export_yeti60_usb_reference.py']}
    mapping.update(source_sha256=sources)
    (OUT/'native-map.json').write_text(json.dumps(mapping, indent=2)+'\n')
    outputs = {str(p.relative_to(ROOT)):sha(p) for p in OUT.iterdir() if p.is_file() and p.name in [
        'yeti60-raytac-candidate-gerbers.zip','yeti60-raytac-candidate-bottom-stencil.zip',
        'positions.csv','mainboard.ipc','drill-report.txt','native-map.json']}
    report = dict(status='candidate-CAM-exported-independent-verification-required',
                  manufacturing_released=False, physical_verification=False, production_approved=False,
                  source_sha256=sources, outputs=outputs, layer_order=LAYERS[:4], fitted_components=75,
                  order_thickness_mm=1.6, stackup='JLC04161H-7628',
                  no_special_via_process=True, legacy_archive_replaced=False)
    (BASE/'audit/fabrication-export.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Candidate CAM exported from checked native PCB; independent readback remains required')


if __name__=='__main__':main()
