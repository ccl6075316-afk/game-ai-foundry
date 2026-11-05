"""New existing-pixel source gate must not fabricate or inherit model review."""
import copy
import unittest
from pathlib import Path
import volume_fish as v
import test_volume_fish as fixtures
from volume_reviewed_source import plan_reviewed_source


class ReviewedSourceTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.VolumeTests();self.f.setUp();self.addCleanup(self.f.tearDown)
        f=self.f;f.plan()
        self.historical_profile=f.root/'historical-profile.json';self.historical_profile.write_bytes(f.profile.read_bytes())
        self.review=f.root/'existing-review.json';self.output=f.root/'new-model.json'
        self.receipt={'schema_version':1,'kind':'fish_existing_pixels_review','species':f.profile_data['species'],'real_length_cm':30,
                      'source':{'path':str(f.source),'sha256':v.sha(f.source)},'style_reference':{'path':str(f.reference),'sha256':v.sha(f.reference)},
                      'review':{'status':'accepted','reviewer':'fixture operator','reviewed_at':'2026-11-04T12:00:00+08:00','observations':dict(source='Full still visible',style='Pixel clusters reviewed',species='Identity reviewed',limitations='Hidden widths unknown')},
                      'provenance':{'kind':'existing_pixels','description':'Surviving accepted pixels; old generation reference is unavailable',
                                    'historical_handoff':{'path':str(f.handoff),'sha256':v.sha(f.handoff)},
                                    'historical_profile':{'path':str(self.historical_profile),'sha256':v.sha(self.historical_profile)}}}
        self.receipt['review']['evidence']={'source':{'path':str(f.source),'sha256':v.sha(f.source),'observation':'Actual source image reviewed'},'style':{'path':str(f.reference),'sha256':v.sha(f.reference),'observation':'Actual style image reviewed'}}
        self.save()
    def save(self):v.write_json(self.review,self.receipt)
    def plan(self):return plan_reviewed_source(self.review,self.f.profile,self.output)
    def test_missing_generation_inputs_not_fabricated_and_new_ledger_pending(self):
        f=self.f;original=f.handoff.read_bytes();f.raw.unlink();f.brief.unlink();f.manifest.unlink()
        h=self.plan();self.assertEqual(h['source_review']['source'],'operator_existing_pixel_review')
        self.assertEqual(h['style_visual_review'],'pending');self.assertNotIn('generation_task_id',h['source'])
        self.assertNotIn('brief',h);self.assertNotIn('assets_manifest',h)
        ledger=v.read_json(Path(h['production']['review']));self.assertEqual(ledger['evidence'],{})
        self.assertTrue(all(s['result']=='pending' for s in ledger['stages'].values()))
        self.assertEqual(v.fresh_handoff(self.output)['source'],h['source']);self.assertEqual(original,f.handoff.read_bytes())
        self.assertFalse(f.raw.exists())
    def test_pending_blank_observations_and_fake_pipeline_rejected(self):
        original=copy.deepcopy(self.receipt)
        for mutate in [lambda r:r['review'].update(status='pending'),lambda r:r['review'].update(reviewer=''),
                       lambda r:r['review']['observations'].update(limitations=''),lambda r:r['provenance'].update(kind='pipeline'),
                       lambda r:r['review'].update(reviewed_at='2026-11-04'),lambda r:r['review'].pop('evidence'),
                       lambda r:r['review']['evidence']['source'].update(sha256='0'*64)]:
            self.receipt=copy.deepcopy(original);mutate(self.receipt);self.save()
            with self.assertRaises(v.VolumeError):self.plan()
    def test_species_length_style_and_source_hash_rejected(self):
        original=copy.deepcopy(self.receipt)
        for mutate in [lambda r:r.update(species='wrong'),lambda r:r.update(real_length_cm=60),
                       lambda r:r['source'].update(sha256='0'*64),lambda r:r['style_reference'].update(sha256='0'*64)]:
            self.receipt=copy.deepcopy(original);mutate(self.receipt);self.save()
            with self.assertRaises(v.VolumeError):self.plan()
    def test_historical_source_changed_unaccepted_and_wrong_species_rejected(self):
        h=v.read_json(self.f.handoff)
        for mutate in [lambda r:r['source'].update(sha256='0'*64),lambda r:r['source_review'].update(status='pending'),
                       lambda r:r['profile_snapshot'].update(sha256='0'*64)]:
            bad=copy.deepcopy(h);mutate(bad);v.write_json(self.f.handoff,bad)
            self.receipt['provenance']['historical_handoff']['sha256']=v.sha(self.f.handoff);self.save()
            with self.assertRaises(v.VolumeError):self.plan()
    def test_frozen_inputs_and_receipt_reject_changes(self):
        self.plan()
        for p in [self.f.source,self.f.reference,self.f.profile,self.f.handoff,self.historical_profile,self.review]:
            old=p.read_bytes();p.write_bytes(old+b' ')
            with self.subTest(path=p.name),self.assertRaises(v.VolumeError):v.fresh_handoff(self.output)
            p.write_bytes(old)
    def test_handoff_source_review_cannot_be_rewritten(self):
        self.plan();h=v.read_json(self.output);h['source_review']['reviewer']='changed';v.write_json(self.output,h)
        with self.assertRaises(v.VolumeError):v.fresh_handoff(self.output)
    def test_existing_output_or_ledger_and_input_overwrite_rejected(self):
        with self.assertRaises(v.VolumeError):plan_reviewed_source(self.review,self.f.profile,self.f.source)
        v.write_json(self.output.with_name(self.output.stem+'-sop-review.json'),{})
        with self.assertRaises(v.VolumeError):self.plan()
    def test_output_paths_may_not_redirect(self):
        self.plan();h=v.read_json(self.output);h['outputs']['glb']=str(self.f.source);v.write_json(self.output,h)
        with self.assertRaises(v.VolumeError):v.fresh_handoff(self.output)
    def test_cli_plan_to_fresh_integration(self):
        from click.testing import CliRunner
        from gamefactory import cli
        import json
        result=CliRunner().invoke(cli,['volume','reviewed-source-plan','--review',str(self.review),'--profile',str(self.f.profile),'--output',str(self.output),'--json'])
        self.assertEqual(result.exit_code,0,result.output)
        self.assertTrue(json.loads(result.output)['ok'])
        self.assertEqual(v.fresh_handoff(self.output)['style_visual_review'],'pending')
    def test_historical_profile_identity_not_filename_substring(self):
        old=v.read_json(self.f.handoff);p=v.read_json(self.historical_profile);p['species']='another_species';v.write_json(self.historical_profile,p)
        old['profile_snapshot']['sha256']=v.sha(self.historical_profile);v.write_json(self.f.handoff,old)
        self.receipt['provenance']['historical_handoff']['sha256']=v.sha(self.f.handoff)
        self.receipt['provenance']['historical_profile']['sha256']=v.sha(self.historical_profile);self.save()
        with self.assertRaises(v.VolumeError):self.plan()


if __name__=='__main__':unittest.main()
