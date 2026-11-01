"""A seventh-fin fixture must not silently approve a trout missing adipose."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_delivery_checks import check_fin_inventory

class InventoryTests(unittest.TestCase):
 def fixture(self):
  names=['Dorsal','Adipose','Anal','Caudal','Pectoral_left','Pectoral_right','Pelvic_left','Pelvic_right']
  profile={'fins':[{'name':n,'paired':n in ['Pectoral','Pelvic']}for n in ['Dorsal','Adipose','Anal','Caudal','Pectoral','Pelvic']]}
  actual=[n+'_mesh'for n in names]
  return {'body_names':['Closed_body'],'fin_names':actual},{'fins':dict.fromkeys(actual,{})},profile
 def test_trout_eight_fins_accepted_as_explicit_inventory(self):
  m,a,p=self.fixture();check_fin_inventory('Closed_body',m,a,p)
 def test_missing_adipose_still_fails_when_both_manifest_and_plan_have_seven(self):
  m,a,p=self.fixture();m['fin_names'].remove('Adipose_mesh');del a['fins']['Adipose_mesh']
  with self.assertRaisesRegex(AssertionError,'own species'):check_fin_inventory('Closed_body',m,a,p)
 def test_duplicates_and_invented_extra_fin_fail(self):
  m,a,p=self.fixture();m['fin_names'].append('Dorsal_mesh')
  with self.assertRaises(AssertionError):check_fin_inventory('Closed_body',m,a,p)
  m,a,p=self.fixture();m['fin_names'].append('Invented');a['fins']['Invented']={}
  with self.assertRaises(AssertionError):check_fin_inventory('Closed_body',m,a,p)
