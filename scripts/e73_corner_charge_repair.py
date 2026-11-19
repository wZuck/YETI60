"""Replay the bounded charging copper repair after the exact CORNER-04 build."""

import hashlib
from kicad_sexpr import child, children, dumps, loads

KINDS = ('arc', 'via', 'segment')
WINDOWS = {
    'USB_5V': (86,115,123,151),
    'VBUS': (86,110,119,124),
    'USB_FEED': (334,105,351,117),
    'GND': (106,142,124,149),
}



def copper(tree):
    return {child(q, 'uuid')[1]:q for kind in KINDS for q in children(tree,kind)}


def patch_board(base, patch):
    assert not patch['candidate_default_selected']
    original = copper(base)
    records = patch['retired']
    assert len(records) == len({item['UUID'] for item in records}) == 68
    for record in records:
        form = original[record['UUID']]
        assert child(form, 'net')[1] == record['net'] in WINDOWS
        assert hashlib.sha256(dumps(form).encode()).hexdigest() == record['sha256']
        base.remove(form)
    seen = set(copper(base))
    for source in patch['added']:
        form = loads(source)
        identifier = child(form,'uuid')[1]
        net = child(form,'net')[1]
        assert identifier not in seen and form[0] in ('segment','via') and net in WINDOWS
        seen.add(identifier)
        x, y, X, Y = WINDOWS[net]
        points = [child(form,key)[1:3] for key in (('at',) if form[0]=='via' else ('start','end'))]
        assert all(x <= float(a) <= X and y <= float(b) <= Y for a,b in points), source
        if form[0]=='via':
            assert child(form,'layers')[1:] == ['F.Cu','B.Cu']
            assert float(child(form,'size')[1]) == .5 and float(child(form,'drill')[1]) == .3
        base.append(form)
    assert len(patch['added']) == 33
    return base


def apply(path, patch):
    import pcbnew as pcb

    assert hashlib.sha256(path.read_bytes()).hexdigest() == patch['source_PCB_sha256']
    tree = patch_board(loads(path.read_text()), patch)
    expected = copper(tree)
    path.write_text(dumps(tree)+'\n')
    board = pcb.LoadBoard(str(path))
    assert pcb.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    assert pcb.SaveBoard(str(path), board)
    assert copper(loads(path.read_text())) == expected, 'Charge repair changed after refill'
    return [{'uuid': row['UUID'], 'net': row['net']} for row in patch['retired']]
