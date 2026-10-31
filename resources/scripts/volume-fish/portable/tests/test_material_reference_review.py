import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from material_reference_review import check_reference_review
from fish_asset_spec import ROOT
from parts import sha

class MaterialReviewTests(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory(dir=ROOT/'work/fish-portable-tools');self.addCleanup(t.cleanup);self.base=Path(t.name)
  self.source=self.base/'source.png';self.front=self.base/'front.png';self.bad=self.base/'rejected.png';self.evidence=self.base/'comparison.png'
  for p in [self.source,self.front,self.bad,self.evidence]:p.write_bytes(p.name.encode())
  self.review=self.base/'review.json';self.author=self.base/'author.json'
  self.report={'kind':'source_surface_material_review','ok':True,'status':'operator_reviewed','source_sha256':sha(self.source),'reference_sha256':sha(self.front),'rejected_reference_sha256':[sha(self.bad)],'zones':[{'source_observation':'Smooth unscaled forehead','reference_observation':'Smooth forehead','adopted_scope':'Central skin only'}],'comparison_evidence':[self.ref(self.evidence)]}
  self.cfg={'source':str(self.source),'source_sha256':sha(self.source),'front_color_image':self.ref(self.front),'interocular_material':{'image':self.ref(self.front)}};self.save()
 def ref(self,p):return {'path':str(p),'sha256':sha(p)}
 def save(self):
  self.review.write_text(json.dumps(self.report),encoding='utf8');self.cfg['material_reference_review']=self.ref(self.review);self.author.write_text(json.dumps(self.cfg),encoding='utf8')
 def test_actual_review_binding_and_legacy_absence(self):
  self.assertTrue(check_reference_review(self.author)['ok']);self.cfg.pop('material_reference_review');self.author.write_text(json.dumps(self.cfg),encoding='utf8');self.assertIsNone(check_reference_review(self.author))
 def test_rejected_image_cannot_be_reintroduced_by_rebinding_config(self):
  self.cfg['front_color_image']=self.ref(self.bad);self.save()
  with self.assertRaisesRegex(ValueError,'rejected'):check_reference_review(self.author)
 def test_central_donor_cannot_silently_differ(self):
  self.cfg['interocular_material']['image']=self.ref(self.bad);self.save()
  with self.assertRaisesRegex(ValueError,'Central'):check_reference_review(self.author)
 def test_stale_source_and_missing_comparison_rejected(self):
  self.source.write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'source mismatch'):check_reference_review(self.author)
  self.cfg['source_sha256']=self.report['source_sha256']=sha(self.source);self.save();self.evidence.unlink()
  with self.assertRaisesRegex(ValueError,'Missing reference'):check_reference_review(self.author)
