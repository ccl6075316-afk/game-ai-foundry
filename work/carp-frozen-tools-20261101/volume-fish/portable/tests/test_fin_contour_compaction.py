import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from compact_free_fin_contour import compact,native_pixel_mask

class ContourTests(unittest.TestCase):
 def fixture(self):return {'polygon':[[0,0],[.25,0],[.5,0],[1,0],[1,.05],[1,1],[.5,1],[0,1]],'source_baseline':[[0,0],[.25,0],[.5,0],[1,0]],'root_attachment':{'root_band':.065,'blend_end':.28}}
 def test_free_straight_sample_removed_baseline_and_transition_retained(self):
  f=self.fixture();new,removed=compact(f,1)
  self.assertEqual(removed,[6]);self.assertIn([1,.05],new['polygon']);self.assertEqual(new['source_baseline'],f['source_baseline']);self.assertEqual(len(f['polygon']),8)
 def test_small_real_shape_corner_is_retained(self):
  f=self.fixture();f['polygon'][6]=[.5,.99];new,removed=compact(f,1)
  self.assertEqual(removed,[]);self.assertEqual(new,f)
 def test_native_pixel_ownership_does_not_use_rounded_vertex_rasterization(self):
  import numpy as np
  from PIL import Image,ImageDraw
  old=[[.125,.125],[.375,.25],[.625,.375],[.875,.875],[.125,.875]];new=old[:1]+old[2:]
  np.testing.assert_array_equal(native_pixel_mask(old,[17,17]),native_pixel_mask(new,[17,17]))
  def rounded(poly):
   im=Image.new('1',(17,17));ImageDraw.Draw(im).polygon([(round(x*17),round(y*17))for x,y in poly],fill=1);return np.asarray(im)
  self.assertFalse(np.array_equal(rounded(old),rounded(new)))
 def test_real_contour_change_is_visible_in_native_ownership(self):
  import numpy as np
  old=[[.1,.1],[.9,.1],[.9,.9],[.1,.9]];new=[[.1,.1],[.5,.1],[.9,.9],[.1,.9]]
  self.assertFalse(np.array_equal(native_pixel_mask(old,[30,20]),native_pixel_mask(new,[30,20])))
