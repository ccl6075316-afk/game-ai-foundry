"""Source-only reconstruction preserves source lineage and rejects stale inputs."""
import unittest
from pathlib import Path
import volume_fish as v
from volume_source_archive import plan_source_archive
import test_volume_fish as fixtures


class SourceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.VolumeTests(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        f = self.f; f.plan()
        self.mapping = f.root / 'source-only.json'; self.target = f.root / 'new-fish.json'
        v.write_json(self.mapping, {'historical_handoff':str(f.handoff), 'historical_profile':str(f.profile),
                                   'source':str(f.source), 'reference':str(f.reference)})

    def plan(self):
        return plan_source_archive(self.mapping, self.f.profile, self.target)

    def test_pending_old_model_does_not_prevent_source_reuse_or_grant_model_acceptance(self):
        f=self.f; old=f.handoff.read_bytes(); f.raw.unlink(); f.brief.unlink(); f.manifest.unlink()
        h=self.plan(); self.assertEqual(h['style_visual_review'],'pending')
        ledger=v.read_json(Path(h['production']['review']))
        self.assertEqual(ledger['evidence'],{})
        self.assertTrue(all(row['result']=='pending' for row in ledger['stages'].values()))
        self.assertNotIn('accepted_archive',h)
        self.assertEqual(v.fresh_handoff(self.target)['source_review']['status'],'accepted')
        self.assertIsNone(h['source']['generation_reference_image'])
        self.assertEqual(old,f.handoff.read_bytes()); self.assertFalse(f.raw.exists())

    def test_required_generation_reference_is_relocated_after_hash_verification(self):
        f=self.f; old=v.read_json(f.handoff); source=old['source']
        source.update(generation_reference_required=True, generation_reference_image='/old/style.png',
                      generation_reference_sha256=v.sha(f.reference),
                      generation_reference_evidence={'kind':'pipeline_task','task_id':source['generation_task_id'],
                                                     'command_sha256':'fixture-command'})
        v.write_json(f.handoff,old)
        h=self.plan()
        self.assertEqual(h['source']['generation_reference_image'],str(f.reference))
        self.assertEqual(v.fresh_handoff(self.target)['source'],h['source'])

    def test_missing_source_acceptance_and_fake_generation_rejected(self):
        f=self.f; original=v.read_json(f.handoff)
        for field,value in [('review','pending'),('generation','local_file')]:
            import copy
            h=copy.deepcopy(original)
            if field=='review':h['source_review']['status']=value
            else:h['source']['generation_stage']=value
            v.write_json(f.handoff,h)
            with self.subTest(field=field),self.assertRaises(v.VolumeError):self.plan()

    def test_changed_source_and_reference_rejected(self):
        for p in [self.f.source,self.f.reference]:
            original=p.read_bytes();p.write_bytes(original+b'changed')
            with self.subTest(path=p.name),self.assertRaises(v.VolumeError):self.plan()
            p.write_bytes(original)

    def test_modified_historical_receipt_and_mapping_rejected_after_plan(self):
        self.plan();f=self.f;original=f.handoff.read_bytes()
        h=v.read_json(f.handoff);h['source_review']['note']='changed';v.write_json(f.handoff,h)
        with self.assertRaises(v.VolumeError):v.fresh_handoff(self.target)
        f.handoff.write_bytes(original)
        m=v.read_json(self.mapping);m['reference']=str(f.source);v.write_json(self.mapping,m)
        with self.assertRaises(v.VolumeError):v.fresh_handoff(self.target)

    def test_outputs_cannot_overwrite_historical_inputs(self):
        with self.assertRaises(v.VolumeError):plan_source_archive(self.mapping,self.f.profile,self.f.handoff)
        self.plan();h=v.read_json(self.target);h['outputs']['glb']=str(self.f.source);v.write_json(self.target,h)
        with self.assertRaises(v.VolumeError):v.fresh_handoff(self.target)


if __name__=='__main__':unittest.main()
