"""Head-width deformation differentials and continuity used by preserved rigs."""
import unittest
from revise_head_width import gain_at

class HeadWidthTests(unittest.TestCase):
 def test_rear_region_is_exact_identity(self):
  s=[[0,1],[.85,1],[.95,2],[1,6]]
  for u in [-1,0,.2,.8,.85]:self.assertEqual(gain_at(s,u),(1,0))
 def test_derivative_agrees_with_numerical_deformation(self):
  s=[[0,1],[.85,1],[.95,2],[1,6]];h=1e-7
  for u in [.86,.9,.94,.96,.98,.99]:
   g,d= gain_at(s,u);num=(gain_at(s,u+h)[0]-gain_at(s,u-h)[0])/(2*h);self.assertAlmostEqual(d,num,places=5)
 def test_station_joins_are_smooth_without_overshoot(self):
  s=[[0,1],[.85,1],[.95,2],[1,6]]
  for u,g in s:
   self.assertAlmostEqual(gain_at(s,u)[0],g);self.assertAlmostEqual(gain_at(s,u)[1],0.)
  values=[gain_at(s,i/1000)[0] for i in range(1001)];self.assertTrue(all(1<=x<=6 for x in values));self.assertTrue(all(x<=y for x,y in zip(values,values[1:])))
if __name__=='__main__':unittest.main()
