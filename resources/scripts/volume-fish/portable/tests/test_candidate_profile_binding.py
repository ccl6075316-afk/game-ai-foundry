import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from candidate_profile_binding import check_profiles
from fish_asset_spec import ROOT
from parts import sha

class ProfileBindingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'work/fish-portable-tools');self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
  self.profile=self.base/'geometry.json';self.profile.write_text(json.dumps({'species':'fixture'}));self.root=self.base/'roots.json';self.author=self.base/'author.json';self.review=self.base/'review.json'
  self.root.write_text(json.dumps({'items':[{'species':'fixture','body':'Body','profile':str(self.profile),'profile_sha256':sha(self.profile)}]}));self.author.write_text(json.dumps({'body':'Body','profile':str(self.profile)}));self.review.write_text(json.dumps({'body':'Body','geometry_profile':str(self.profile)}))
 def test_same_own_profile_accepted_without_visual_approval(self):
  self.assertTrue(check_profiles(self.author,self.root,self.review)['ok'])
 def test_same_species_equal_bytes_but_different_revision_path_rejected(self):
  other=self.base/'old.json';other.write_bytes(self.profile.read_bytes());self.review.write_text(json.dumps({'body':'Body','geometry_profile':str(other)}))
  with self.assertRaisesRegex(ValueError,'profile differs'):check_profiles(self.author,self.root,self.review)
 def test_stale_root_hash_rejected(self):
  self.profile.write_text(json.dumps({'species':'fixture','changed':True}))
  with self.assertRaisesRegex(ValueError,'Stale'):check_profiles(self.author,self.root,self.review)
 def test_body_mismatch_rejected(self):
  self.author.write_text(json.dumps({'body':'WrongBody','profile':str(self.profile)}))
  with self.assertRaisesRegex(ValueError,'body identity'):check_profiles(self.author,self.root,self.review)
