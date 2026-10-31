import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from compact_free_fin_contour import compact

class ContourTests(unittest.TestCase):
 def fixture(self):return {'polygon':[[0,0],[.25,0],[.5,0],[1,0],[1,.05],[1,1],[.5,1],[0,1]],'source_baseline':[[0,0],[.25,0],[.5,0],[1,0]],'root_attachment':{'root_band':.065,'blend_end':.28}}
 def test_free_straight_sample_removed_baseline_and_transition_retained(self):
  f=self.fixture();new,removed=compact(f,1)
  self.assertEqual(removed,[6]);self.assertIn([1,.05],new['polygon']);self.assertEqual(new['source_baseline'],f['source_baseline']);self.assertEqual(len(f['polygon']),8)
 def test_small_real_shape_corner_is_retained(self):
  f=self.fixture();f['polygon'][6]=[.5,.99];new,removed=compact(f,1)
  self.assertEqual(removed,[]);self.assertEqual(new,f)
