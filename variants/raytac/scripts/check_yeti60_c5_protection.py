#!/usr/bin/env python3
"""Verify actual C5 paths reach protected TI I/O lands, not optional NC pads."""
import hashlib,json
from pathlib import Path
import pcbnew as pcb
from check_yeti60_signal_paths import build_graph
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/usb-daughterboard/upstream/UDB.kicad_pcb'
DATASHEET='https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf'
def verify(board):
    graph,ports,pads=build_graph(board,{'DP','DN'})
    fps={f.GetReference():f for f in board.GetFootprints()}
    assert 'TPD4E05U06' in fps['U1'].GetValue()
    records=[]
    for net,output,inputs,protected in [('DP','3',['A6','B6'],['1','4']),('DN','2',['A7','B7'],['2','5'])]:
        for number in protected:assert pads['U1',number].GetNetname()==net
        for number in inputs:
            length,nodes,edges=graph.path(ports['J1',number],{ports['J2',output]})
            distances={p:graph.path(ports['U1',p],set(nodes))[0] for p in protected}
            assert min(distances.values())<=.5,'No local protected I/O on USB path'
            records.append({'net':net,'connector_pad':number,'J2_pad':output,'path_mm':length,'protected_pin_distances_mm':distances})
    # Pin 3/8 ground continuity, including physical filled zones; this is not
    # an inductance measurement. The upstream native DRC also reports 0 opens.
    conn=board.GetConnectivity()
    for number in ['3','8']:
        start=next(p for p in fps['U1'].Pads() if p.GetNumber()==number)
        assert start.GetNetname()=='GND'
        todo=[start];seen=set();found=False
        while todo:
            item=todo.pop();uid=item.m_Uuid.AsString()
            if uid in seen:continue
            seen.add(uid)
            if item.GetClass()=='PAD' and item.GetParentFootprint().GetReference()=='J2' and item.GetNumber()=='4':found=True;break
            todo.extend(i for i in conn.GetConnectedItems(item) if i.GetNetname()=='GND')
        assert found,'ESD ground does not reach cable ground'
    return records

def main():
    b=pcb.LoadBoard(str(SOURCE));records=verify(b)
    report={'status':'protected-I/O-coverage-passed','physical_verification':False,'production_approved':False,
      'datasheet':DATASHEET,'protected_IO_pins':['1','2','4','5'],'GND_pins':['3','8'],
      'NC_routing_pins':['6','7','9','10'],'paths':records,
      'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE,Path(__file__),ROOT/'scripts/check_yeti60_signal_paths.py']},
      'limits':['Geometric connectivity, not board ESD certification, USB eye or return inductance qualification','Upstream C5 native DRC defaults disclose courtyard/library/edge-clearance findings; obtain supplier DFM, preferably use populated C5 for first prototype']}
    (ROOT/'docs/audit/C5-protection.json').write_text(json.dumps(report,indent=2)+'\n')
    print('C5 data protection: all four USB connector data pads reach real protected channels; both ESD grounds connected')
if __name__=='__main__':main()
