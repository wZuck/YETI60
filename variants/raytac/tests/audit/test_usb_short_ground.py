"""An isolated filled island must not be joined by a shared zone identity."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from usb_short_ground import connected_ground


def square(x):
    return dict(outer=[[x,0],[x+1,0],[x+1,1],[x,1]],holes=[])


class GroundFailures(unittest.TestCase):
    def test_two_islands_on_one_layer_rejected(self):
        with self.assertRaises(AssertionError):
            connected_ground(dict(ground_copper={'B.Cu':[square(0),square(2)]},ground_vertical_connectors=[]))

    def test_projection_alone_does_not_join_layers(self):
        with self.assertRaises(AssertionError):
            connected_ground(dict(ground_copper={'F.Cu':[square(0)],'B.Cu':[square(0)]},ground_vertical_connectors=[]))

    def test_physical_ground_via_joins_layers(self):
        native=dict(ground_copper={'F.Cu':[square(0)],'B.Cu':[square(0)]},ground_vertical_connectors=[dict(uuid='test-through-via',by_layer={'F.Cu':[square(.1)],'B.Cu':[square(.1)]})])
        self.assertEqual(connected_ground(native)['connected_components'],1)


if __name__=='__main__':unittest.main()
