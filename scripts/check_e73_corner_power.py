#!/usr/bin/env python3
"""Read-only CORNER-04 power, charge-headroom and solder-wicking review."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import pcbnew as pcb

from check_yeti60_signal_paths import build_graph
from kicad_sexpr import child, loads

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hardware/e73-hhkb-corner'
BOARD = BASE / 'EC60-nRF52840.kicad_pcb'
LAYERS = (pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu)
TEMP_C = 60
COPPER_RHO_20 = .01724  # ohm mm²/m
COPPER_ALPHA = .00393


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def uid(item):
    return item.m_Uuid.AsString()


def route_checks(board, power, profile):
    local = power['local_path_limits']
    delivery = [('J4.1', 'J5.1'), ('J1.1', 'F1.2'), ('F1.1', 'U5.13'),
                ('F1.1', 'U1.27'), ('J2.1', 'U5.2'), ('U5.11', 'U6.5')]
    control = [('U1.3', 'U5.6', 'R42'), ('U1.7', 'U5.5', 'R43'), ('U1.6', 'U5.4', 'R44')]
    ports = [(entry['from'], entry['to']) for entry in local] + delivery
    ports += [(source, sink) for source, sink, _ in control]
    ports += [(sink, ref+'.1') for _, sink, ref in control]
    pin = lambda name: tuple(name.split('.'))
    pads = {(f.GetReference(), p.GetNumber()): p for f in board.GetFootprints() for p in f.Pads()
            if p.GetNumber()}
    nets = {pads[pin(source)].GetNetname() for source, _ in ports}
    graph, nodes, _ = build_graph(board, nets)
    layers = {'B.Cu': profile['outer_copper_mm'], 'F.Cu': profile['outer_copper_mm'],
              'In1.Cu': profile['inner_copper_mm'], 'In2.Cu': profile['inner_copper_mm']}
    values = {}
    for source, sink in ports:
        a, b = pin(source), pin(sink)
        net = pads[a].GetNetname()
        assert pads[b].GetNetname() == net, (source, sink, net)
        length, _, indices = graph.path(nodes[a], {nodes[b]})
        traces = [graph.edges[index] for index in indices if graph.edges[index]['kind'] == 'trace']
        assert traces
        ohms = sum(COPPER_RHO_20 * edge['length_mm']/1000 /
                   (edge['width_mm']*layers[edge['layer']]) for edge in traces)
        values[source+' to '+sink] = {
            'net': net, 'contact_aware_path_mm': length,
            'trace_width_min_mm': min(e['width_mm'] for e in traces),
            'trace_layers': sorted({e['layer'] for e in traces}),
            'trace_only_20C_ohm': ohms,
            'vertical_graph_edges': sum(graph.edges[index]['kind']=='via' for index in indices),
        }
    for entry in local:
        row = values[entry['from']+' to '+entry['to']]
        assert row['contact_aware_path_mm'] <= entry['max_length_mm']
        assert row['trace_width_min_mm'] >= entry['min_width_mm']
        assert row['trace_layers'] == ['B.Cu'] and row['vertical_graph_edges'] == 0
        row['project_limits'] = {'max_mm': entry['max_length_mm'], 'min_width_mm': entry['min_width_mm']}
    footprints = {f.GetReference(): f for f in board.GetFootprints()}
    for ref, expected in {'U5': 'BQ24074RGT', 'U6': 'TPS63031DSK', 'R40': '2.21k/1%',
                          'R55': '69.8k/1%', 'R56': '1.69k/1%', 'R42': '100k',
                          'R43': '100k', 'R44': '100k'}.items():
        assert footprints[ref].GetValue() == expected, ref
    for ref in ('R42','R43','R44'):
        assert pads[ref,'2'].GetNetname() == 'GND'
    assert [pads['SW100',str(i)].GetNetname() for i in (1,2,3)] == ['VSYS','REG_EN','GND']
    assert pads['U5','17'].GetNetname() == pads['U6','11'].GetNetname() == 'GND'
    return values


def layer_shapes(footprint, layer):
    items = [p for p in footprint.Pads() if p.IsOnLayer(layer)]
    items += [g for g in footprint.GraphicalItems() if g.GetLayer() == layer]
    shapes = []
    for item in items:
        if isinstance(item, pcb.PAD):
            # Current overlapping lands and windows use zero margin. Fail on
            # future expansion rather than approximate the plotted aperture.
            margin = (item.GetSolderMaskExpansion(layer) if layer in (pcb.F_Mask, pcb.B_Mask)
                      else item.GetSolderPasteMargin(layer).EuclideanNorm())
            assert margin == 0, (footprint.GetReference(), item.GetNumber(), layer, margin)
        polygon = pcb.SHAPE_POLY_SET()
        item.TransformShapeToPolygon(polygon, layer, 0, pcb.FromMM(.001), pcb.ERROR_OUTSIDE)
        assert polygon.OutlineCount()
        shapes.append(polygon)
    return shapes


def process_checks(board, path, power, profile):
    assert board.GetCopperLayerCount() == 4
    assert pcb.ToMM(board.GetDesignSettings().GetBoardThickness()) == profile['CAD_finished_envelope_mm']
    native = loads(path.read_text())
    stack = child(child(native, 'setup'), 'stackup')
    cu = {entry[1]: float(child(entry,'thickness')[1])
          for entry in stack if isinstance(entry,list) and entry[0]=='layer'
          and child(entry,'type')[1]=='copper'}
    assert cu == {'F.Cu': .035, 'In1.Cu': .0152, 'In2.Cu': .0152, 'B.Cu': .035}
    postprocess = child(native, 'setup')
    assert all(child(postprocess,key)[1] == 'no' for key in ('filling','capping'))
    assert all(child(child(postprocess,key),which)[1]=='no' for key in ('plugging','covering')
               for which in ('front','back'))
    assert all(child(child(postprocess,'tenting'),side)[1]=='yes' for side in ('front','back'))
    vias = sorted((t for t in board.GetTracks() if isinstance(t,pcb.PCB_VIA)), key=uid)
    non_vias = [t for t in board.GetTracks() if not isinstance(t,pcb.PCB_VIA)]
    assert min(pcb.ToMM(t.GetWidth()) for t in non_vias) >= .127
    diameters = Counter()
    for via in vias:
        assert via.GetViaType() == pcb.VIATYPE_THROUGH and (via.TopLayer(),via.BottomLayer()) == (pcb.F_Cu,pcb.B_Cu)
        diameter = pcb.ToMM(via.GetWidth(pcb.F_Cu))
        drill = pcb.ToMM(via.GetDrillValue())
        assert diameter >= .50 and drill >= .30 and diameter-drill >= .2-1e-8
        diameters[diameter,drill] += 1
    hole_gap = min((a.GetPosition()-b.GetPosition()).EuclideanNorm()/1e6
                   - pcb.ToMM(a.GetDrillValue()+b.GetDrillValue())/2
                   for i,a in enumerate(vias) for b in vias[:i])
    assert hole_gap >= .25-1e-6
    # Check each contact land on its mounted face. Include the larger annulus
    # to enumerate candidates, then compare the actual drill against apertures.
    overlaps = []
    for footprint in board.GetFootprints():
        copper, mask, paste = ((pcb.F_Cu,pcb.F_Mask,pcb.F_Paste)
                               if footprint.GetLayer()==pcb.F_Cu else (pcb.B_Cu,pcb.B_Mask,pcb.B_Paste))
        for pad in footprint.Pads():
            if pad.GetAttribute()!=pcb.PAD_ATTRIB_SMD or not pad.IsOnLayer(copper):
                continue
            land = pad.GetEffectiveShape(copper)
            nearby = land.BBox()
            nearby.Inflate(pcb.FromMM(.5))
            for via in vias:
                location = via.GetPosition()
                if not nearby.Contains(location) or not pcb.SHAPE.Collide(land,via.GetEffectiveShape(copper),0):
                    continue
                gaps = {}
                for layer in (mask,paste):
                    shapes = layer_shapes(footprint,layer)
                    if shapes:
                        distances = [0 if shape.Contains(location) else shape.Distance(location) for shape in shapes]
                        gaps[board.GetLayerName(layer)] = (pcb.ToMM(min(distances))
                                                          - pcb.ToMM(via.GetDrillValue())/2)
                overlaps.append({'reference': footprint.GetReference(), 'pad': pad.GetNumber(),
                                 'via_uuid': uid(via), 'net': via.GetNetname(),
                                 'xy_PCB_mm': list(pcb.ToMM(location)), 'drill_mm': pcb.ToMM(via.GetDrillValue()),
                                 'same_footprint_drill_to_aperture_mm': gaps})
    return {
        'layer_thickness_mm': cu, 'through_vias': len(vias),
        'via_size_counts': [{'diameter_mm': d,'drill_mm': h,'count': n} for (d,h),n in sorted(diameters.items())],
        'minimum_via_drill_edge_gap_mm': hole_gap,
        'minimum_trace_width_mm': min(pcb.ToMM(t.GetWidth()) for t in non_vias),
        'annulus_overlaps_SMD_lands': overlaps,
    }


def charge_screen(paths, harness):
    wires = {(w['family'],w['pin']): w['free_length_mm'] for w in harness['variants'][0]['wires']}
    usb_pins = [('usb','1'),('usb','4'),('power','1'),('power','2')]
    lead_lengths = sum(wires[pin] for pin in usb_pins)
    trace_ohms = sum(paths[p]['trace_only_20C_ohm']
                     for p in ('J4.1 to J5.1','J1.1 to F1.2','F1.1 to U5.13'))
    wire_ohms = COPPER_RHO_20 * lead_lengths/1000 / .0804  # AWG28 nominal copper area
    hot_ohms = (trace_ohms + wire_ohms) * (1+COPPER_ALPHA*(TEMP_C-20))
    rows = []
    for incoming in (4.75,5,5.25):
        for current in (.10,.45,.50):
            u5 = incoming-hot_ohms*current
            rows.append({'type_c_input_V_assumed':incoming, 'current_A_assumed':current,
                         'included_path_drop_V':hot_ohms*current,
                         'U5_IN_V_before_unmodeled_losses':u5,
                         'margin_to_BQ_max_DPM_V_before_unmodeled_losses':u5-4.63,
                         'margin_to_nRF_VBUS_min_V_before_unmodeled_losses':u5-4.35})
    maximum_charge_A = 975/(2210*.99)
    thermal = []
    for battery in (3.1,3.7,4.2):
        dissipation = (5.25-battery)*maximum_charge_A + (5.25-4.5)*.04
        thermal.append({'IN_V':5.25, 'BAT_V_assumed':battery, 'OUT_V_assumed':4.5,
                        'OUT_A_assumed':.04, 'BAT_A_max_programmed':maximum_charge_A,
                        'linear_loss_W_before_thermal_derating':dissipation})
    return {
        'copper_temperature_C_assumed':TEMP_C, 'AWG28_copper_area_mm2_assumed':.0804,
        'four_wire_free_lengths_sum_mm':lead_lengths, 'wire_loop_20C_ohm':wire_ohms,
        'positive_PCB_centerline_20C_ohm':trace_ohms, 'modeled_series_at_temperature_ohm':hot_ohms,
        'excluded': ['PCB ground return and via barrels','C5 traces','both fuses',
                     'mated contacts and crimp joints','external USB cable and source droop',
                     'U1 dedicated branch voltage drop and ground differential'],
        'input_headroom_sensitivity': rows, 'BQ24074_dissipation_sensitivity': thermal,
        'current_A_min_typ_max':[797/(2210*1.01),890/2210,maximum_charge_A],
        'BQ24074_VIN_DPM_min_typ_max_V':[4.35,4.5,4.63],
        'nRF52840_VBUS_min_V':4.35,
        'BQ24074_CV_min_typ_max_V':[4.16,4.2,4.23],
        'BQ24074_RGT_JEDEC_RthetaJA_C_per_W':44.5,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pcb', type=Path, default=BOARD)
    parser.add_argument('--output', type=Path, default=BASE/'audit/power-process.json')
    args = parser.parse_args()
    path = args.pcb.resolve()
    assert path == BOARD or args.output.resolve() != BASE/'audit/power-process.json'
    power_path = ROOT/'hardware/e73-power-repair-spec.json'
    profile_path = ROOT/'mechanical/pcb-fabrication-spec.json'
    harness_path = BASE/'audit/harness-study.json'
    board_hash = sha(path)
    board = pcb.LoadBoard(str(path))
    power, profile, harness = (load(p) for p in (power_path,profile_path,harness_path))
    assert not harness['failures']
    assert harness['source_sha256'][str(BOARD.relative_to(ROOT))] == sha(BOARD)
    paths = route_checks(board,power,profile)
    process = process_checks(board,path,power,profile)
    source_paths = [path, path.with_suffix('.kicad_pro'), power_path, profile_path, harness_path,
                    Path(__file__), ROOT/'scripts/check_yeti60_signal_paths.py', ROOT/'scripts/kicad_sexpr.py',
                    ROOT/'mechanical/assembly-spec.json']
    digests = {str(p.relative_to(ROOT)):sha(p) for p in source_paths}
    assert sha(path) == board_hash
    document = {
        'status':'source-bound-power-process-review-open',
        'source_sha256':digests, 'physical_verification':False, 'production_approved':False,
        'local_power_paths':paths, 'fabrication_geometry':process, 'charge_headroom':charge_screen(paths,harness),
        'references':{'charger':power['sources']['BQ24074'], 'regulator':power['sources']['TPS63031'],
                      'USB_VBUS':'https://docs.nordicsemi.com/r/bundle/ps_nrf52840/page/power.html',
                      'fabrication':profile['capabilities_url'],
                      'via_covering':'https://jlcpcb.com/help/article/pcb-via-covering'},
    }
    args.output.write_text(json.dumps(document,indent=2)+'\n')
    print(document['status'], 'vias:', process['through_vias'],
          'annulus overlaps:', len(process['annulus_overlaps_SMD_lands']))


if __name__ == '__main__':
    main()
