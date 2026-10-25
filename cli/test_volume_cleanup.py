"""Dense evidence cleanup must reject a bad set before removing any sample."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

script=Path(__file__).resolve().parents[1]/'resources/scripts/volume-fish/validate_fin_completion.py'
spec=importlib.util.spec_from_file_location('fin_cleanup',script)
cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)

class DenseEvidenceCleanupTests(unittest.TestCase):
 def setUp(self):
  workspace=Path(__file__).resolve().parents[1]/'work';workspace.mkdir(exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(dir=workspace);self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.directory=self.root/'fish';self.directory.mkdir()
  self.samples=[self.directory/f'sample-{i:03d}.json'for i in range(2)]
  for i,path in enumerate(self.samples):path.write_text(json.dumps({'pose':i}))
  self.rows=[{'posed_mesh_json':str(p),'sha256':cleanup.sha(p)}for p in self.samples]
  self.export=self.directory/'export.validation.json'
 def save(self):self.export.write_text(json.dumps({'samples':self.rows}))
 def test_success_keeps_hash_receipt_and_deletes_only_samples(self):
  self.save();cleanup.discard_passing_samples(self.export,self.directory)
  self.assertTrue(self.export.exists());self.assertTrue(all(not p.exists()for p in self.samples))
  receipt=json.loads((self.directory/'sample-cleanup.validation.json').read_text())
  self.assertTrue(receipt['ok']);self.assertEqual(receipt['status'],'done')
  self.assertEqual([x['sha256']for x in receipt['removed']],[x['sha256']for x in self.rows])
 def test_late_hash_mismatch_removes_nothing(self):
  self.rows[1]['sha256']='0'*64;self.save()
  with self.assertRaisesRegex(AssertionError,'changed'):cleanup.discard_passing_samples(self.export,self.directory)
  self.assertTrue(all(p.exists()for p in self.samples))
 def test_outside_sample_rejected_before_any_deletion(self):
  outside=self.root/'sample-999.json';outside.write_text('{}')
  self.rows[1]={'posed_mesh_json':str(outside),'sha256':cleanup.sha(outside)};self.save()
  with self.assertRaisesRegex(AssertionError,'Unexpected'):cleanup.discard_passing_samples(self.export,self.directory)
  self.assertTrue(outside.exists());self.assertTrue(all(p.exists()for p in self.samples))
 def test_duplicate_sample_rejected_before_any_deletion(self):
  self.rows.append(self.rows[0].copy());self.save()
  with self.assertRaisesRegex(AssertionError,'Duplicate'):cleanup.discard_passing_samples(self.export,self.directory)
  self.assertTrue(all(p.exists()for p in self.samples))

if __name__=='__main__':unittest.main()
