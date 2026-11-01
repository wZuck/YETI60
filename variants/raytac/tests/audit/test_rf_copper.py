import sys,unittest
from pathlib import Path
from unittest.mock import patch
import pcbnew as pcb
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
import screen_yeti60_interference as screen
class Copper(unittest.TestCase):
 def test_current_minimum_projection_is_clear(self):
  r=screen.screen(ROOT,'raytac',False)
  self.assertTrue(all(l['GND_union_mm2']==l['non_GND_union_mm2']==0 for l in r['layers']))
 def test_real_copper_injection_is_detected_on_every_layer(self):
  for layer in screen.LAYERS:
   b=pcb.LoadBoard(str(ROOT/'hardware/ec60-nrf52840/EC60-nRF52840.kicad_pcb'));m=next(f for f in b.GetFootprints() if f.GetReference()=='U1');roi=screen.vendor_projection(m,'raytac')[1]
   t=pcb.PCB_TRACK(b);t.SetStart(pcb.VECTOR2I(pcb.FromMM(roi[0]+.6),pcb.FromMM(roi[1]+1)));t.SetEnd(pcb.VECTOR2I(pcb.FromMM(roi[0]+1.6),pcb.FromMM(roi[1]+1)));t.SetWidth(pcb.FromMM(.2));t.SetLayer(layer);t.SetNet(b.FindNet('ADC'));b.Add(t)
   with patch.object(screen.pcb,'LoadBoard',return_value=b):r=screen.screen(ROOT,'raytac',False)
   self.assertGreater(next(l for l in r['layers'] if l['layer']==b.GetLayerName(layer))['non_GND_union_mm2'],.1)
if __name__=='__main__':unittest.main()
