"""Replay the local SW1 ground repair from the audited CORNER-05 board."""
import hashlib

from kicad_sexpr import child, loads
from e73_corner_charge_repair import copper


def point(pcb, xy):
    return pcb.VECTOR2I(*(pcb.FromMM(v) for v in xy))


def check_geometry(board, patch, stage):
    import pcbnew as pcb

    items = {t.m_Uuid.AsString(): t for t in board.GetTracks()}
    via = items[patch['via_uuid']]
    track = items[patch['segment_uuid']]
    expected = patch[stage]
    assert via.GetClass() == 'PCB_VIA' and track.GetClass() == 'PCB_TRACK'
    assert via.GetNetname() == track.GetNetname() == 'GND'
    assert (via.GetViaType(), via.TopLayer(), via.BottomLayer()) == (pcb.VIATYPE_THROUGH, pcb.F_Cu, pcb.B_Cu)
    assert all(via.GetWidth(layer) == pcb.FromMM(expected['land_mm'])
               for layer in (pcb.F_Cu, pcb.In1_Cu, pcb.In2_Cu, pcb.B_Cu))
    assert via.GetDrillValue() == pcb.FromMM(expected['drill_mm'])
    assert via.GetPosition() == track.GetStart() == point(pcb, expected['center_PCB_mm'])
    assert track.GetLayer() == pcb.B_Cu and track.GetWidth() == pcb.FromMM(.2)
    assert track.GetEnd() == point(pcb, (323.188, 122.337))
    return via, track


def apply(path, patch):
    import pcbnew as pcb

    source = path.read_bytes()
    assert hashlib.sha256(source).hexdigest() == patch['baseline_pcb_sha256']
    original = copper(loads(source.decode()))
    board = pcb.LoadBoard(str(path))
    via, track = check_geometry(board, patch, 'before')
    after = patch['after']
    via.SetPosition(point(pcb, after['center_PCB_mm']))
    via.SetWidth(pcb.FromMM(after['land_mm']))
    via.SetDrill(pcb.FromMM(after['drill_mm']))
    track.SetStart(via.GetPosition())
    check_geometry(board, patch, 'after')
    board.BuildConnectivity()
    assert pcb.ZONE_FILLER(board).Fill(board.Zones())
    assert pcb.SaveBoard(str(path), board)
    actual = copper(loads(path.read_text()))
    assert actual.keys() == original.keys()
    changed = {key for key in actual if actual[key] != original[key]}
    assert changed == {patch['via_uuid'], patch['segment_uuid']}
    assert all(child(actual[key], 'net')[1] == 'GND' for key in changed)
    check_geometry(pcb.LoadBoard(str(path)), patch, 'after')
    return [{'uuid': key, 'net': 'GND'} for key in sorted(changed)]
