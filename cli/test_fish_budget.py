import unittest
from fish_budget import triangle_policy,check_triangle_budget

class DisplayBudgetTests(unittest.TestCase):
 def test_sharks_have_minimum_3500_4000_tier_and_keep_larger_tiers(self):
  for species in ['blacktip_reef_shark','scalloped_hammerhead','great_hammerhead','smooth_hammerhead','whale_shark']:
   for cm,preferred,hard in [(30,3500,4000),(120,3500,4000),(150,3500,4000),(300,3500,4000),(300.001,5500,6000),(600,5500,6000),(600.001,7500,8000)]:
    with self.subTest(species=species,cm=cm):
     p=triangle_policy(cm,species=species);self.assertEqual((p['preferred_triangles'],p['hard_triangles']),(preferred,hard));self.assertTrue(check_triangle_budget(hard,cm,species=species)['ok'])
     with self.assertRaisesRegex(ValueError,'exceeded'):check_triangle_budget(hard+1,cm,species=species)
 def test_eight_metre_whale_shark_exception(self):
  self.assertTrue(check_triangle_budget(10000,800,species='whale_shark')['ok'])
  with self.assertRaises(ValueError):check_triangle_budget(10001,800,species='whale_shark')
  self.assertEqual(triangle_policy(800,species='great_hammerhead')['hard_triangles'],8000)

 def test_new_shark_can_declare_taxonomic_group_without_name_guessing(self):
  self.assertEqual(triangle_policy(80,species='new_species',anatomical_group='shark')['hard_triangles'],4000)
  self.assertEqual(triangle_policy(80,species='shark_named_nonshark')['hard_triangles'],2000)
  for value in [None,0,float('nan')]:
   with self.assertRaises(ValueError):triangle_policy(value,anatomical_group='shark')
 def test_strict_thresholds_and_units(self):
  for cm,preferred,hard in [(73.66,1500,2000),(120,1500,2000),(120.0001,3500,4000),(150,3500,4000),(300,3500,4000),(300.0001,5500,6000),(600,5500,6000),(600.0001,7500,8000),(800,7500,8000)]:
   with self.subTest(cm=cm):
    p=triangle_policy(cm);self.assertEqual((p['preferred_triangles'],p['hard_triangles']),(preferred,hard))
 def test_actual_limit_enforced_and_smaller_mesh_accepted(self):
  for cm,hard in [(120,2000),(150,4000),(400,6000),(800,8000)]:
   self.assertTrue(check_triangle_budget(hard,cm)['ok'])
   self.assertTrue(check_triangle_budget(1000,cm)['preferred_met'])
   with self.assertRaisesRegex(ValueError,'exceeded'):check_triangle_budget(hard+1,cm)
 def test_declared_config_cannot_promote_small_fish_to_larger_tier(self):
  with self.assertRaisesRegex(ValueError,'display-length'):check_triangle_budget(3500,73.66,4000)
  with self.assertRaisesRegex(ValueError,'exceeded'):check_triangle_budget(2500,150,2000)
 def test_invalid_or_unknown_length_never_grants_more_budget(self):
  for value in [None,True,0,-1,float('nan'),float('inf'),'150']:
   with self.subTest(value=value),self.assertRaises(ValueError):triangle_policy(value)
 def test_counts_are_not_faces_or_booleans(self):
  for value in [True,1.5,-1,None]:
   with self.assertRaises(ValueError):check_triangle_budget(value,150)
