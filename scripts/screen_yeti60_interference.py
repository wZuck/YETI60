#!/usr/bin/env python3
"""Read-only copper/USB screening of BOTH alternatives with native KiCad geometry.

This is a layout screen, not an electromagnetic field solver or USB compliance test.
"""
import hashlib
import json
from pathlib import Path
import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[1]
LAYERS = [pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rect(bounds):
    x0, y0, x1, y1 = bounds
    poly = pcb.SHAPE_POLY_SET(); poly.NewOutline()
    for x, y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]:
        poly.Append(pcb.FromMM(x), pcb.FromMM(y))
    return poly


def rings(poly):
    result = []
    for index in range(poly.OutlineCount()):
        outline = poly.COutline(index)
        result.append([[pcb.ToMM(outline.CPoint(i).x), pcb.ToMM(outline.CPoint(i).y)]
                       for i in range(outline.PointCount())])
    return result


def classify(ground_areas, formal):
    if any(area > .001 for area in ground_areas):
        return 'failed-vendor-keepout' if formal else 'risk-copper-in-provisional-antenna-band'
    return 'minimum-projection-clear-metal-and-vendor-review-still-required'


def screen(folder, name):
    path = folder/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'
    board = pcb.LoadBoard(str(path))
    module = next(f for f in board.GetFootprints() if f.GetReference()=='U1')
    # Rectangles are in top-view PCB coordinates, transformed from vendor drawings.
    # Raytac: local y=-7.75..-3.95, x=+-5.25; bottom rotation +90 degrees.
    # E73: vendor x=15..18, y=-13..0; bottom rotation -90 degrees.
    if name=='raytac':
        expected=(347.,125.,90.); body=[339.25,119.75,354.75,130.25]
        roi=[350.95,119.75,354.75,130.25]; formal=True
    else:
        expected=(354.6,116.5,-90.); body=[341.6,116.5,354.6,134.5]
        roi=[341.6,131.5,354.6,134.5]; formal=False
    actual=(pcb.ToMM(module.GetPosition().x),pcb.ToMM(module.GetPosition().y),module.GetOrientationDegrees())
    assert all(abs(a-b)<1e-5 for a,b in zip(actual,expected)), 'Update vendor-to-PCB transform after module movement'
    region=rect(roi); layer_records=[]; primitives=[]
    for layer in LAYERS:
        # Union before measuring: overlapping pad/track/zone copper is counted once.
        ground=pcb.SHAPE_POLY_SET(); other=pcb.SHAPE_POLY_SET(); hits=[]
        def add(poly, net, label):
            cut=pcb.SHAPE_POLY_SET(); cut.BooleanIntersection(poly,region)
            if cut.Area() <= 0: return
            (ground if net=='GND' else other).BooleanAdd(cut)
            hits.append({'item':label,'net':net})
        for footprint in board.GetFootprints():
            for pad in footprint.Pads():
                if pad.IsOnLayer(layer):
                    add(pad.GetEffectivePolygon(layer),pad.GetNetname(),footprint.GetReference()+'.'+pad.GetNumber())
        for track in board.GetTracks():
            if track.IsOnLayer(layer):
                shape=pcb.SHAPE_POLY_SET()
                track.TransformShapeToPolygon(shape,layer,0,pcb.FromMM(.002),pcb.ERROR_INSIDE)
                add(shape,track.GetNetname(),track.GetClass())
        for zone in board.Zones():
            if zone.IsOnLayer(layer) and not zone.GetIsRuleArea():
                add(zone.GetFilledPolysList(layer),zone.GetNetname(),'filled-zone')
        layer_records.append({'layer':board.GetLayerName(layer),'GND_union_mm2':round(ground.Area()/1e12,6),
                              'non_GND_union_mm2':round(other.Area()/1e12,6),'intersecting_items':hits})
        primitives.append({'layer':board.GetLayerName(layer),'ground':rings(ground),'other':rings(other),
                           'GND_mm2':ground.Area()/1e12})
    usb={}
    for net in ['D+','USB_DP','D-','USB_DM']:
        tracks=[t for t in board.GetTracks() if t.GetNetname()==net]
        segments=[t for t in tracks if not isinstance(t,pcb.PCB_VIA)]
        usb[net]={'total_track_mm':round(sum(pcb.ToMM(t.GetLength()) for t in segments),6),
                  'via_count':sum(isinstance(t,pcb.PCB_VIA) for t in tracks),
                  'layers':sorted({t.GetLayerName() for t in segments}),
                  'widths_mm':sorted({round(pcb.ToMM(t.GetWidth()),6) for t in segments})}
    plus=sum(usb[n]['total_track_mm'] for n in ['D+','USB_DP'])
    minus=sum(usb[n]['total_track_mm'] for n in ['D-','USB_DM'])
    # Aggregate length includes stubs. Do not label this as matched end-to-end delay.
    record={'module':module.GetValue(),'module_origin_mm':list(actual[:2]),'rotation_deg':actual[2],
            'body_pcb_bounds_mm':body,'screen_bounds_mm':roi,'screen_area_mm2':round(region.Area()/1e12,6),
            'formal_vendor_dimension':formal,'layers':layer_records,
            'status':classify([r['GND_union_mm2'] for r in layer_records],formal),
            'USB':{'nets':usb,'positive_total_track_mm':plus,'negative_total_track_mm':minus,
                   'aggregate_length_difference_mm':round(abs(plus-minus),6),
                   'status':'requires-return-path-impedance-and-eye-verification',
                   'limits':'Track sums include branch stubs; exclude pads, series resistors, module routing, C5 and cable. No impedance or pair-coupling extraction.'},
            'source_sha256':{str(path.relative_to(ROOT)):sha(path)}}
    draw(name,body,roi,primitives)
    draw(name,body,roi,primitives,True)
    return record


def draw(name,body,roi,layers,zh=False):
    # Four separate layer views; actual clipped copper, no inferred RF field colors.
    from xml.sax.saxutils import escape
    title='天线投影与实际主板铜' if zh else 'antenna projection / actual host copper'
    legend='顶视；绿色为接地铜，橙色为其他网络，红框为检查区。未进行射频场仿真。' if zh else 'Top view; green GND, orange other nets; red rectangle = screening region. No RF field simulation.'
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="600" viewBox="0 0 1200 600">',
         '<rect width="1200" height="600" fill="#f6f7f9"/>',
         f'<text x="35" y="40" font-family="sans-serif" font-size="23">{name.upper()} — {title}</text>',
         f'<text x="35" y="70" font-family="sans-serif" font-size="15">{legend}</text>']
    for index,data in enumerate(layers):
        bx=45+index*295; by=120; scale=13
        def xy(x,y):return (bx+(x-body[0])*scale,by+(y-body[1])*scale)
        x,y=xy(body[0],body[1]);w=(body[2]-body[0])*scale;h=(body[3]-body[1])*scale
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff" stroke="#718096"/>')
        for key,color in [('ground','#269b76'),('other','#ef9b45')]:
            for ring in data[key]:
                points=' '.join(f'{xy(x,y)[0]:.3f},{xy(x,y)[1]:.3f}' for x,y in ring)
                svg.append(f'<polygon points="{points}" fill="{color}" fill-opacity=".85"/>')
        x,y=xy(roi[0],roi[1]);w=(roi[2]-roi[0])*scale;h=(roi[3]-roi[1])*scale
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="#d62728" stroke-width=".4" stroke-dasharray="4 3"/>')
        svg.append(f'<text x="{bx}" y="395" font-family="sans-serif" font-size="20">{escape(data["layer"])}</text>')
        area=f'接地铜 {data["GND_mm2"]:.6f} mm²' if zh else f'GND {data["GND_mm2"]:.6f} mm²'
        svg.append(f'<text x="{bx}" y="425" font-family="sans-serif" font-size="16">{area}</text>')
    note=('Raytac minimum 10.5 x 3.8 mm projection from manufacturer section 2.3; wider keepout recommended.' if name=='raytac'
          else 'E73 last 3 mm antenna-end band is an engineering screen only; manufacturer gives no numeric host keepout.')
    if zh:note=('Raytac 厂商第 2.3 节最小投影为 10.5×3.8 mm；建议进一步扩大净空。' if name=='raytac' else 'E73 天线端最后 3 mm 仅为工程检查区，厂商未给出数字化主板净空要求。')
    holes='图中只画相交外轮廓，视觉上省略孔洞；JSON 并集面积保留原生孔洞。' if zh else 'Only intersection outlines shown; polygon holes omitted visually. JSON union areas retain native polygon holes.'
    plate='定位板投影和距离另行检查；机械不相交不能证明射频净空合格。' if zh else 'Plate projection and separation are evaluated separately. Mechanical non-collision does not establish RF clearance.'
    svg.extend([f'<text x="35" y="460" font-family="sans-serif" font-size="16">{note}</text>',
                f'<text x="35" y="490" font-family="sans-serif" font-size="16">{holes}</text>',
                f'<text x="35" y="520" font-family="sans-serif" font-size="16">{plate}</text>','</svg>'])
    suffix='.zh-CN' if zh else ''
    (ROOT/f'docs/testing/images/{name}-antenna-copper{suffix}.svg').write_text('\n'.join(svg)+'\n')


def main():
    report={'status':'screening-completed-design-blockers-open','physical_test_performed':False,
            'field_solver_performed':False,'production_approved':False,
            'variants':{n:screen(ROOT if n=='e73' else ROOT/'variants/raytac',n) for n in ['e73','raytac']},
            'source_sha256':{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},
            'geometry_error_mm':.002,
            'limits':['No measured antenna impedance, efficiency, detuning, RSSI or packet-error rate',
                      'Host copper only: internal module copper is absent from native host PCB',
                      'E73 ROI is provisional; obtain manufacturer-approved antenna keepout before release']}
    (ROOT/'docs/audit/interference-layout.json').write_text(json.dumps(report,indent=2)+'\n')
    for n,r in report['variants'].items():print(n,r['status'],[(l['layer'],l['GND_union_mm2']) for l in r['layers']],r['USB']['aggregate_length_difference_mm'])


if __name__=='__main__':main()
