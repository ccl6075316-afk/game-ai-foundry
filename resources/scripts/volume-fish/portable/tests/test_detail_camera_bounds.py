"""Reject the actual native-unit detail-focus mistake before GPU capture."""
import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_delivery_checks import check_detail_cameras

class DetailCameraTests(unittest.TestCase):
 def setUp(self):
  self.positions=np.array([[-.5,-.25,-.10],[.5,.25,.10]])
  self.scale=.17813736616469228
 def detail(self,center,size=.045):return [{'name':'mouth','at':center,'size':size}]
 def test_rejects_native_focus_that_produced_blank_mouth_images(self):
  with self.assertRaisesRegex(AssertionError,'game meters'):
   check_detail_cameras(self.positions,self.scale,self.detail([.455,-.055,0]))
 def test_actual_scaled_mouth_focus_is_inside_model(self):
  check_detail_cameras(self.positions,self.scale,self.detail((np.array([.455,-.055,0])*self.scale).tolist()))
 def test_rejects_invalid_camera_values(self):
  for center,size in [([float('nan'),0,0],.045),([0,0],.045),([0,0,0],0),([0,0,0],-1)]:
   with self.subTest(center=center,size=size),self.assertRaises(AssertionError):check_detail_cameras(self.positions,self.scale,self.detail(center,size))
