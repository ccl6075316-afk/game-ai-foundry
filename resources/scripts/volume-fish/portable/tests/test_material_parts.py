import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from material_parts import from_author_report

class AuthorPartsTests(unittest.TestCase):
 def fixture(self):
  p={'parts':[{'name':'Body_0','logical_name':'Body','role':'body','source_node':'Body','source_surface':0},{'name':'Adipose_0','logical_name':'Adipose','role':'fin','source_node':'Adipose','source_surface':0}]}
  packing={'parts':[{'node':'Body','surface':n}for n in range(3)]+[{'node':'Adipose','surface':0}]}
  a={'ok':True,'model_sha256':'actual','body_surface_roles':{'0':'body_skin','1':'body_skin','2':'mouth'}}
  return p,packing,a
 def test_new_front_chart_surfaces_and_adipose_ownership_preserved(self):
  p,k,a=self.fixture();r=from_author_report(p,k,a,'Body','actual')
  self.assertEqual([x['role']for x in r['parts']],['body_skin','body_skin','mouth','fin']);self.assertEqual(r['parts'][-1],p['parts'][-1]);self.assertEqual(len(p['parts']),2)
 def test_stale_report_and_missing_fin_block(self):
  p,k,a=self.fixture()
  with self.assertRaises(AssertionError):from_author_report(p,k,a,'Body','changed')
  k['parts'].pop()
  with self.assertRaisesRegex(AssertionError,'Missing source fin'):from_author_report(p,k,a,'Body','actual')
