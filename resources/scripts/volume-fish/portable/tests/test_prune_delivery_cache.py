"""Deletion planning must reject stale and escaped inputs before changing files."""
import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import prune_delivery_cache as prune

class CachePlanTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.original=prune.ROOT;prune.ROOT=self.root
  self.addCleanup(setattr,prune,'ROOT',self.original)
  self.d=self.root/'projects/game/experiments/fish/delivery';self.d.mkdir(parents=True)
  self.model=self.d/'fish.glb';self.model.write_bytes(b'fixture')
  self.report=self.d/'gate.json';self.report.write_text('{"ok":true}')
  self.manifest={'ok':True,'status':'done','model':str(self.model),'model_sha256':prune.sha(self.model),'stages':[{'ok':True,'status':'done','report':str(self.report),'report_sha256':prune.sha(self.report)}]}
  self.save()
 def save(self):(self.d/'manifest.json').write_text(json.dumps(self.manifest))
 def test_late_stale_report_rejects_without_removing_frames(self):
  f=self.d/'review/frames/frame-0001.jpg';f.parent.mkdir(parents=True);f.write_bytes(b'frame')
  self.report.write_text('{"ok":false}')
  with self.assertRaises(AssertionError):prune.plan(self.d)
  self.assertTrue(f.exists());self.assertTrue(self.model.exists())
 def test_only_redundant_frames_selected_source_and_phases_retained(self):
  d=self.d/'review/frames';d.mkdir(parents=True)
  for n in [0,1,16,287]:(d/f'frame-{n:04d}.jpg').write_bytes(b'frame')
  result=prune.plan(self.d)
  self.assertEqual([Path(x['path']).name for x in result['removed']],['frame-0001.jpg'])
  self.assertEqual(len(result['retained_samples_and_frames']),3)
  self.assertTrue(all(p.exists()for p in d.iterdir()))
 def test_unfinished_run_and_outside_experiments_rejected(self):
  self.manifest['status']='running';self.save()
  with self.assertRaises(AssertionError):prune.plan(self.d)
  with self.assertRaises(AssertionError):prune.plan(self.root)
