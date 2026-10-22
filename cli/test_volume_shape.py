"""Station interpolation and native provenance gates without Blender dependency."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from volume_shape import validate_revision, width_scale, revision_source, vertical_position, validate_root_attachment, root_attachment_gain, root_attachment_inset


class NativeRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        digest=lambda data:hashlib.sha256(data).hexdigest()
        for name in ['base.blend','base.glb']:(self.root/name).write_bytes(name.encode())
        self.current={'source':{'sha256':'a'*64},'style_contract':{'pixel_art':True,'source_sha256':'a'*64,'style_reference_sha256':'b'*64,'texture_filter':'nearest','roughness':1}}
        old=copy.deepcopy(self.current)
        old.update(kind='fish_volume_handoff',status='done',style_visual_review='accepted',outputs={'blend':r'E:\old\base.blend','glb':r'E:\old\base.glb'},style_review={'reviewer':'command_operator','note':'Inspected native model','hashes':{'source_sha256':'a'*64,'blend_sha256':digest(b'base.blend'),'glb_sha256':digest(b'base.glb')}})
        (self.root/'old.json').write_text(json.dumps(old))
        self.revision={'source_handoff':'old.json','source_handoff_sha256':digest((self.root/'old.json').read_bytes()),'source_blend':'base.blend','source_glb':'base.glb','blend_sha256':digest(b'base.blend'),'glb_sha256':digest(b'base.glb'),'stations':[[0,.1,.1],[.5,.1,.05],[1,.1,.1]]}

    def test_smooth_ratios_interpolate_without_overshoot(self):
        rows=self.revision['stations']
        self.assertEqual(width_scale(rows,-1),1)
        self.assertEqual(width_scale(rows,.5),.5)
        self.assertAlmostEqual(width_scale(rows,.25),.75)
        self.assertTrue(all(.5<=width_scale(rows,i/1000)<=1 for i in range(1001)))
        self.assertLess(abs(width_scale(rows,.500001)-width_scale(rows,.5)),1e-9)

    def test_station_validation_rejects_executable_unknown_nonfinite_and_unsorted(self):
        for change in [{'script':'anything'},{'stations':[[.5,.1,.1],[.2,.1,.1]]},{'stations':[[0,float('nan'),.1],[1,.1,.1]]},{'stations':[[0,.1,1],[1,.1,.1]]}]:
            invalid={**self.revision,**change}
            with self.subTest(change=change),self.assertRaises(ValueError):validate_revision(invalid)

    def test_archived_native_paths_are_bound_to_accepted_hashes(self):
        self.assertEqual(revision_source(self.revision,self.root,self.current)['status'],'done')
        (self.root/'base.blend').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'blend'):revision_source(self.revision,self.root,self.current)

    def test_texture_replacement_rejected(self):
        other=copy.deepcopy(self.current);other['source']['sha256']='c'*64
        with self.assertRaisesRegex(ValueError,'original source'):revision_source(self.revision,self.root,other)

    def test_output_cannot_replace_accepted_native_input(self):
        other=copy.deepcopy(self.current);other['outputs']={'blend':str(self.root/'base.blend')}
        with self.assertRaisesRegex(ValueError,'overwrite accepted'):revision_source(self.revision,self.root,other)

    def test_historical_acceptance_cannot_change_after_plan(self):
        (self.root/'old.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'handoff hash'):revision_source(self.revision,self.root,self.current)

    def test_vertical_mapping_matches_landmark_extents_and_smoothly_interpolates(self):
        # Aspect H/W=.5; v=.2/.8 become z=+.15/-.15. Target v=.4/.6 => +/- .05.
        rows=[[0,.2,.8,.2,.8],[1,.2,.8,.4,.6]]
        self.assertAlmostEqual(vertical_position(rows,1,.15,.5),.05)
        self.assertAlmostEqual(vertical_position(rows,1,-.15,.5),-.05)
        self.assertAlmostEqual(vertical_position(rows,.5,.15,.5),.1)
        self.assertEqual(vertical_position([],0,.12,.5),.12)
        self.assertAlmostEqual(vertical_position(rows,2,.15,.5),.05)
        self.assertLess(abs(vertical_position(rows,.000001,.15,.5)-.15),1e-9)
        shifted=[[0,.2,.8,.1,.7],[1,.2,.8,.1,.7]]
        self.assertAlmostEqual(vertical_position(shifted,.3,0,.5),.05)

    def test_vertical_validation_rejects_crossed_nonfinite_unsorted_or_excessive_scales(self):
        for rows in [[],[[0,.8,.2,.4,.6],[1,.2,.8,.4,.6]],[[1,.2,.8,.4,.6],[0,.2,.8,.4,.6]],[[0,.2,.8,float('nan'),.6],[1,.2,.8,.4,.6]],[[0,.2,.8,.49,.51],[1,.2,.8,.4,.6]]]:
            with self.subTest(rows=rows),self.assertRaises(ValueError):validate_revision({**self.revision,'vertical_stations':rows})
        validate_revision({**self.revision,'vertical_stations':[[0,.2,.8,.2,.8],[1,.2,.8,.4,.6]]})

    def test_broad_snout_width_is_bounded_and_explicit(self):
        validate_revision({**self.revision,'stations':[[0,.001,.012],[1,.01,.01]]})
        with self.assertRaises(ValueError):validate_revision({**self.revision,'stations':[[0,.001,.013],[1,.01,.01]]})

    def test_contact_gain_covers_full_root_band_without_changing_distal_fin(self):
        option={'mode':'body_surface','root_band':.05,'blend_end':.35,'inset':.001}
        validate_root_attachment(option)
        for t in [0,.025,.05]:self.assertEqual(root_attachment_gain(t,.05,.35),1)
        for t in [.35,.75,1]:self.assertEqual(root_attachment_gain(t,.05,.35),0)
        self.assertAlmostEqual(root_attachment_gain(.2,.05,.35),.5)
        for change in [{'mode':'script'},{'root_band':.5,'blend_end':.3},{'inset':float('nan')},{'inset':.1},{'unknown':0}]:
            with self.subTest(change=change),self.assertRaises(ValueError):validate_root_attachment({**option,**change})

    def test_full_sloping_fin_base_is_zero_across_all_segments(self):
        from volume_shape import validate_fin_baseline,fin_baseline_parameter
        base=[[.2,.6],[.4,.4],[.7,.35]];poly=[base[0],[.3,.1],[.65,.05],base[-1],base[1]]
        validate_fin_baseline(base)
        for p in [base[0],base[1],base[-1],[.3,.5],[.55,.375]]:
            self.assertAlmostEqual(fin_baseline_parameter(p,base,poly,.5),0)
        self.assertGreater(fin_baseline_parameter([.45,.1],base,poly,.5),.7)
        # Unlike the old anchor dot product, the anterior end stays a root too.
        self.assertEqual(fin_baseline_parameter(base[-1],base,poly,.5),0)
        for invalid in [[],[[0,0]],[[0,0],[0,0]],[[0,0],[1,float('nan')]],[[0,0],[1,2]]]:
            with self.assertRaises(ValueError):validate_fin_baseline(invalid)

    def test_posterior_surface_region_is_explicit_and_bounded(self):
        option={'mode':'body_surface','root_band':.05,'blend_end':.35,'inset':.001}
        validate_root_attachment({**option,'surface_region':'posterior'})
        with self.assertRaises(ValueError):validate_root_attachment({**option,'surface_region':'anywhere'})

    def test_free_membrane_clearance_is_optional_finite_and_bounded(self):
        option={'mode':'body_surface','root_band':.05,'blend_end':.26,'inset':.00004}
        validate_root_attachment(option)
        for value in [0,.0025,.02]:validate_root_attachment({**option,'surface_clearance':value})
        for value in [-.001,.0201,float('nan'),float('inf'),True,'0.0025']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                validate_root_attachment({**option,'surface_clearance':value})

    def test_finite_median_collar_keeps_distinct_root_depths_and_legacy_inset(self):
        option={'mode':'body_surface','root_band':.025,'blend_end':.32,'inset':.000025}
        for t in [0,.000001,.015,.025,.5,1]:
            self.assertEqual(root_attachment_inset(t,option),option['inset'])
        collar={**option,'root_band_depth':.00004};validate_root_attachment(collar)
        depths=[root_attachment_inset(t,collar) for t in [0,.005,.015,.025]]
        self.assertEqual(len({round(d,7) for d in depths}),4)
        # Smooth121's frozen300cm display: even worst aligned half-thickness
        # plus the deepest median collar stays below the existing0.5mm seam.
        self.assertLess((max(depths)+.00015/2)*3000,.5)
        for change in [{'root_band_depth':0},{'root_band_depth':-.001},{'root_band_depth':.0051},{'root_band_depth':float('nan')},{'root_band_depth':True},{'root_band_depth':.001,'root_band':0}]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                validate_root_attachment({**option,**change})

    def test_basal_geometry_spacing_is_explicit_finite_and_bounded(self):
        option={'mode':'body_surface','root_band':.025,'blend_end':.32,'inset':.000025}
        validate_root_attachment(option)
        for spacing in [.0001,.0005,.004,.02]:validate_root_attachment({**option,'baseline_spacing':spacing})
        for spacing in [0,.00009,.0201,float('nan'),float('inf'),True,'0.0005']:
            with self.subTest(spacing=spacing),self.assertRaises(ValueError):
                validate_root_attachment({**option,'baseline_spacing':spacing})


if __name__=='__main__':unittest.main()
