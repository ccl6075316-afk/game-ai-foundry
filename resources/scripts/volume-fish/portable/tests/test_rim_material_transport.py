import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rim_material_transport import ordered_boundary,nearest_arc,side_curve_donor,bounded_roi_coordinates

class RimMaterialTransportTest(unittest.TestCase):
    def test_actual_longitudinal_phase_survives_same_transverse_coordinate(self):
        # A projected-Y-only lookup collapses these two distinct lip positions.
        c=np.array([[0,-1,0],[1,-1,1],[2,0,2],[1,1,1],[0,1,0]],float)
        b=ordered_boundary(c,[(0,1),(1,2),(2,3),(3,4)])
        d,s=nearest_arc(c[:2],b)
        self.assertTrue(np.allclose(d,0));self.assertGreater(s[1],s[0])
        xy=side_curve_donor(s,b[1][-1],d,np.array([[10,50],[30,40],[50,20]]),True)
        self.assertFalse(np.allclose(xy[0],xy[1]))
    def test_front_meets_once_without_reflected_repetition(self):
        p=np.array([0,1,2,3,4],float);xy=side_curve_donor(p,4,np.zeros(5),[[10,30],[20,20],[30,10]],True)
        self.assertTrue(np.allclose(xy[:,0],[10,20,30,20,10]))
    def test_reject_branched_and_disconnected_boundary(self):
        c=np.array([[0,0,0],[1,0,0],[2,0,0],[1,1,0],[4,1,0],[5,1,0]],float)
        for e in [[(0,1),(1,2),(1,3)],[(0,1),(1,2),(3,4),(4,5),(5,3)]]:
            with self.assertRaises(ValueError):ordered_boundary(c,e)
    def test_generated_donor_never_leaves_central_roi(self):
        xy=bounded_roi_coordinates(np.array([-8,.5,8]),np.array([8,.5,-8]),[400,130,740,610],[1145,1374])
        self.assertTrue(np.all(xy>=[400,130]));self.assertTrue(np.all(xy<=[740,610]))
        with self.assertRaises(ValueError):bounded_roi_coordinates(np.zeros(1),np.zeros(1),[0,0,1145,1374],[1145,1374])

if __name__=='__main__':unittest.main()
