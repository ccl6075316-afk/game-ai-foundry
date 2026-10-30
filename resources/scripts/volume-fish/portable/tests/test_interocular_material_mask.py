import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from interocular_material_mask import target_eye_material_allowance

class InterocularMaterialMaskTest(unittest.TestCase):
    def test_identical_side_uv_does_not_remove_central_forehead(self):
        # The rejected UV-rectangle-only mask zeroed BOTH positions.
        xy=np.array([[1280,400],[1280,400],[1280,400]],float)
        got=target_eye_material_allowance(xy,np.array([0,.35,.9]),[[1220,326,1355,466]],12,.25,.45)
        self.assertEqual(got[0],1);self.assertAlmostEqual(got[1],.5);self.assertEqual(got[2],0)
    def test_actual_lateral_eye_remains_protected(self):
        side=np.linspace(.45,1,20);xy=np.tile([1290,390],(20,1))
        self.assertTrue(np.all(target_eye_material_allowance(xy,side,[[1220,326,1355,466]],12,.25,.45)==0))
    def test_outside_source_eye_is_not_suppressed(self):
        self.assertEqual(target_eye_material_allowance([[1200,400]],[1],[[1220,326,1355,466]],12,.25,.45)[0],1)
    def test_invalid_region_parameters_rejected(self):
        for fade,a,b in [(0,.25,.45),(12,.45,.25),(12,-.1,.5)]:
            with self.assertRaises(ValueError):target_eye_material_allowance([[1280,400]],[0],[[1220,326,1355,466]],fade,a,b)

if __name__=='__main__':unittest.main()
