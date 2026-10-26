"""Measured head sections must replace, not depend on, regular trunk rings."""
import copy
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'resources/scripts/volume-fish'))
from retarget_reviewed_side import SideField,resolve_paths


class ReviewedSideFieldTests(unittest.TestCase):
    def setUp(self):
        self.plan={'support_sections':[[-.5,-.1,.1,.2],[.5,-.1,.1,.2]],
                   'x_stations':[[-.5,-.5],[.5,.5]],'top_px':[[0,30],[100,30]],
                   'bottom_px':[[0,70],[100,70]],'source_left':0,
                   'source_length':100,'source_axis_y':50}
        self.irregular=np.array([[-.3,0,.15],[.1,.1,-.2],[.42,-.1,.17]])

    def test_measured_sections_work_without_any_regular_rings(self):
        field=SideField(self.plan,self.irregular)
        points=np.array([[.4,-.1,.12],[.4,0,.17],[.4,.1,-.12]])
        actual=field(points)
        np.testing.assert_allclose(actual[:,1],[-.2,0,.2])
        np.testing.assert_array_equal(actual[:,[0,2]],points[:,[0,2]])

    def test_missing_measured_sections_reject_irregular_body(self):
        plan=copy.deepcopy(self.plan);del plan['support_sections']
        with self.assertRaisesRegex(ValueError,'requires measured'):
            SideField(plan,self.irregular)

    def test_relative_inputs_resolve_from_recipe_not_working_directory(self):
        recipe=Path('/repo/resources/volume-fish/example.json')
        plan={'path_base':'../..','baseline':'work/base','output':'work/new','source':'/archive/source.png'}
        resolved=resolve_paths(plan,recipe)
        self.assertEqual(resolved['baseline'],'/repo/work/base')
        self.assertEqual(resolved['output'],'/repo/work/new')
        self.assertEqual(resolved['source'],'/archive/source.png')
        self.assertEqual(plan['baseline'],'work/base')

    def test_bad_sections_fail_before_building_any_geometry(self):
        bad=[[],[[0,0,1,1]],[[1,0,1,1],[0,0,1,1]],
             [[0,0,0,1],[1,0,1,1]],[[0,0,1,-1],[1,0,1,1]],
             [[0,0,1,1],[1,0,float('nan'),1]]]
        for sections in bad:
            with self.subTest(sections=sections),self.assertRaises(ValueError):
                SideField({**self.plan,'support_sections':sections},self.irregular)

    def test_mouth_alignment_preserves_outer_envelope_and_width(self):
        plan=copy.deepcopy(self.plan)
        plan['mouth_alignment']={'old_curve':[[-.5,0],[.5,0]],
                                 'source_curve':[[0,60],[100,60]],'support':[0,.3]}
        points=np.array([[.4,-.1,.1],[.4,0,.17],[.4,.1,-.1]])
        actual=SideField(plan,self.irregular)(points)
        np.testing.assert_allclose(actual[:,1],[-.2,-.1,.2])
        np.testing.assert_array_equal(actual[:,2],points[:,2])
        self.assertTrue(np.all(np.diff(actual[:,1])>0))


if __name__=='__main__':unittest.main()
