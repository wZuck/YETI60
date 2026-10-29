#!/usr/bin/env python3
"""Enforce the user's ordinary-JLC process constraint against native geometry."""
import hashlib
import json
import math
from pathlib import Path
import pcbnew as pcb

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    profile_path = ROOT/'mechanical/pcb-fabrication-spec.json'
    profile = json.loads(profile_path.read_text())
    board = pcb.LoadBoard(str(BOARD))
    assert board.GetCopperLayerCount() == 4
    assert abs(pcb.ToMM(board.GetDesignSettings().GetBoardThickness())-profile['CAD_finished_envelope_mm']) < 1e-6
    vias = [v for v in board.GetTracks() if v.GetClass() == 'PCB_VIA']
    assert vias
    for via in vias:
        assert via.GetViaType() == pcb.VIATYPE_THROUGH, 'Blind/buried/laser via prohibited'
        assert (via.TopLayer(), via.BottomLayer()) == (pcb.F_Cu, pcb.B_Cu)
        assert pcb.ToMM(via.GetDrillValue()) >= .3-1e-8
        assert pcb.ToMM(via.GetWidth(pcb.F_Cu)) >= .5-1e-8
    # Same-net holes still need real laminate between drills. Copper clearance alone
    # does not reject coincident/repeated layer-change vias.
    minimum_hole_gap = math.inf
    rules = json.loads(BOARD.with_suffix('.kicad_pro').read_text())['board']['design_settings']['rules']
    required_gap = max(rules['min_hole_clearance'], rules['min_hole_to_hole'])
    for index, via in enumerate(vias):
        for other in vias[:index]:
            gap = (via.GetPosition()-other.GetPosition()).EuclideanNorm()/1e6 - pcb.ToMM(via.GetDrillValue()+other.GetDrillValue())/2
            minimum_hole_gap = min(minimum_hole_gap, gap)
            assert gap >= required_gap-1e-6, ('Via drills overlap or violate laminate clearance', via.m_Uuid.AsString(), other.m_Uuid.AsString(), gap)
    module = next(f for f in board.GetFootprints() if f.GetReference() == 'U1')
    collisions = []
    for pad in module.Pads():
        if not pad.IsOnLayer(pcb.B_Cu):
            continue
        for via in vias:
            if pcb.SHAPE.Collide(pad.GetEffectiveShape(pcb.B_Cu), via.GetEffectiveShape(pcb.B_Cu), 0):
                collisions.append([pad.GetNumber(), via.m_Uuid.AsString()])
    assert not collisions, ('Module via-in-pad needs removal', collisions)
    assert not profile['blind_buried_laser_allowed'] and not profile['resin_fill_copper_cap_required']
    report = {'status':'ordinary-process-geometry-passed', 'production_approved':False,
              'profile':profile['profile'], 'through_vias':len(vias), 'blind_buried_vias':0,
              'minimum_via_drill_mm':min(pcb.ToMM(v.GetDrillValue()) for v in vias),
              'minimum_via_diameter_mm':min(pcb.ToMM(v.GetWidth(pcb.F_Cu)) for v in vias),
              'module_via_in_pad':collisions,
              'minimum_via_drill_edge_gap_mm':minimum_hole_gap,
              'required_drill_edge_gap_mm':required_gap,
              'nominal_order_thickness_mm':1.6,
              'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [BOARD,profile_path,Path(__file__)]},
              'limits':['Ordinary JLC ordering/DFM review remains required',
                        'U5 ordinary open thermal via requires paste-wicking review; no resin filling/capping specified',
                        'Nominal CAD stack does not certify actual board thickness or hardware behavior']}
    (ROOT/'docs/audit/yeti60-ordinary-process.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'{len(vias)} ordinary through vias; no blind/buried vias or module vias-in-pad')


if __name__ == '__main__':
    main()
