"""Static oral cleft limits and landmark/jaw relationships."""
import copy,json,unittest
from pathlib import Path
from volume_mouth import validate_oral_jaws,validate_oral_context,slit_v,jaw_shift

class OralJawsTests(unittest.TestCase):
    def setUp(self):
        self.profile=json.loads((Path(__file__).resolve().parents[1]/'resources/volume-fish/peacock-bass-oral-jaws-060b.profile.json').read_text(encoding='utf-8'))
        self.data=self.profile['oral_jaws']
    def test_context_and_landmarks(self):
        validate_oral_context(self.data,self.profile['body'],self.profile['rig']['spine'])
        for u,v in (self.data['corner'],self.data['front']):self.assertAlmostEqual(slit_v(self.data,u),v)
        self.assertLess(slit_v(self.data,self.data['front'][0]),slit_v(self.data,self.data['corner'][0]))
    def test_jaw_projection_and_unchanged_posterior(self):
        front=self.data['front'];corner=self.data['corner']
        self.assertLess(jaw_shift(self.data,front[0],front[1]-.01),0)
        self.assertGreater(jaw_shift(self.data,front[0],front[1]+.01),0)
        for v in [0,.5,1]:self.assertEqual(jaw_shift(self.data,corner[0]-.01,v),0)
    def test_rejects_nonfinite_or_executable_fields(self):
        for key,value in [('gap',float('nan')),('lip_bevel',True),('gap',0),('upper_retraction',-.01),('script','bad')]:
            data=copy.deepcopy(self.data);data[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):validate_oral_jaws(data)
    def test_rejects_wrong_orientation_and_outside_shell(self):
        with self.assertRaises(ValueError):validate_oral_context(self.data,self.profile['body'],list(reversed(self.profile['rig']['spine'])))
        for point in [[.5,.5],[self.data['front'][0],.01]]:
            data=copy.deepcopy(self.data);data['front']=point
            with self.assertRaises(ValueError):validate_oral_context(data,self.profile['body'],self.profile['rig']['spine'])

    def test_shorter_curved_lip_has_downturned_front(self):
        profile=json.loads((Path(__file__).resolve().parents[1]/'resources/volume-fish/peacock-bass-oral-jaws-062e.profile.json').read_text(encoding='utf-8'))
        data=profile['oral_jaws'];validate_oral_context(data,profile['body'],profile['rig']['spine'])
        self.assertLess(data['front'][0]-data['corner'][0],self.data['front'][0]-self.data['corner'][0])
        path=data['slit_path'];apex=min(path,key=lambda p:p[1])
        self.assertLess(apex[1],data['front'][1])
        for a,b in zip(path,path[1:]):
            values=[slit_v(data,a[0]+(b[0]-a[0])*i/20) for i in range(21)]
            self.assertTrue(all(min(a[1],b[1])-1e-9<=v<=max(a[1],b[1])+1e-9 for v in values))
        self.assertGreater(data['lip_roll']['lower_ratio'],1)
        last=profile['body']['sections'][-1];previous=profile['body']['sections'][-2]
        self.assertGreater(last[2],previous[2]) # lower outer edge turns down
        self.assertGreater(last[2]-data['front'][1],data['front'][1]-last[1])

    def test_rejects_folded_path_and_excessive_lip_roll(self):
        for changes in [dict(slit_path=[self.data['corner'],[.1,.5],self.data['front']]),dict(lip_roll={'radius':.005,'height':.008,'lower_ratio':2}),dict(lip_roll={'radius':.01,'height':float('inf'),'lower_ratio':1})]:
            data=copy.deepcopy(self.data);data.update(changes)
            with self.assertRaises(ValueError):validate_oral_jaws(data)

    def test_separate_jaw_context_and_rejects_incompatible_shell_roll(self):
        profile=json.loads((Path(__file__).resolve().parents[1]/'resources/volume-fish/peacock-bass-separate-jaw-063c.profile.json').read_text(encoding='utf-8'))
        data=profile['oral_jaws'];validate_oral_context(data,profile['body'],profile['rig']['spine'])
        self.assertLess(data['separate_lower']['rear_u'],data['corner'][0])
        for key,value in [('thickness',0),('half_width',float('nan')),('bottom_width_ratio',1.5),('rear_u',data['front'][0])]:
            bad=copy.deepcopy(data);bad['separate_lower'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_oral_jaws(bad)
        data['lip_roll']={'radius':.01,'height':.002,'lower_ratio':1.5}
        with self.assertRaises(ValueError):validate_oral_jaws(data)

    def test_articulated_jaw_rejects_invalid_hinge_range_and_root(self):
        profile=json.loads((Path(__file__).resolve().parents[1]/'resources/volume-fish/peacock-bass-articulated-jaw-064a.profile.json').read_text(encoding='utf-8'))
        data=profile['oral_jaws'];validate_oral_context(data,profile['body'],profile['rig']['spine'])
        for key,value in [('max_open_degrees',90),('max_open_degrees',float('nan')),('hinge',[.1,.1]),('rigid_start_u',data['articulation']['fixed_root_u'])]:
            bad=copy.deepcopy(data);bad['articulation'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_oral_jaws(bad)
        bad=copy.deepcopy(data);bad.pop('separate_lower')
        with self.assertRaises(ValueError):validate_oral_jaws(bad)

    def test_section_lips_reject_folded_stations_and_invalid_cross_sections(self):
        profile=json.loads((Path(__file__).resolve().parents[1]/'resources/volume-fish/peacock-bass-section-lips-066c.profile.json').read_text(encoding='utf-8'))
        data=profile['oral_jaws'];validate_oral_context(data,profile['body'],profile['rig']['spine'])
        for index,value in [(0,.1),(1,float('nan')),(2,0),(3,-.001),(6,1.5)]:
            bad=copy.deepcopy(data);bad['separate_lower']['lip_sections'][2][index]=value
            with self.subTest(index=index),self.assertRaises(ValueError):validate_oral_jaws(bad)
        bad=copy.deepcopy(data);bad['separate_lower']['lip_sections'].pop()
        with self.assertRaises(ValueError):validate_oral_jaws(bad)
        bad=copy.deepcopy(data);bad['separate_lower'].pop('lip_sections')
        with self.assertRaises(ValueError):validate_oral_jaws(bad)

    def test_independent_lower_path_validation(self):
        profile=json.loads((Path(__file__).resolve().parents[1]/'resources/volume-fish/peacock-bass-lower-tip-068a.profile.json').read_text(encoding='utf-8'))
        data=profile['oral_jaws'];validate_oral_context(data,profile['body'],profile['rig']['spine'])
        for row,value in [(0,[.1,.1]),(-1,[.99,.5]),(2,[float('nan'),.5])]:
            bad=copy.deepcopy(data);bad['separate_lower']['lip_path'][row]=value
            with self.subTest(row=row),self.assertRaises(ValueError):validate_oral_jaws(bad)

    def test_reference_jaw_rejects_folded_sections_and_wrong_reference_pose(self):
        profile=json.loads((Path(__file__).resolve().parents[1]/'resources/volume-fish/peacock-bass-source-fit-069b.profile.json').read_text(encoding='utf-8'))
        data=profile['oral_jaws'];validate_oral_context(data,profile['body'],profile['rig']['spine'])
        for key,value in [('open_degrees',12),('web_end_u',.99),('side_projection_start_u',.1)]:
            bad=copy.deepcopy(data);bad['separate_lower']['reference_shape'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_oral_jaws(bad)
        for index,value in [(0,.1),(1,float('nan')),(2,0),(3,.2)]:
            bad=copy.deepcopy(data);bad['separate_lower']['reference_shape']['sections'][2][index]=value
            with self.subTest(index=index),self.assertRaises(ValueError):validate_oral_jaws(bad)
        bad=copy.deepcopy(data);bad['separate_lower']['lip_path']=[data['corner'],data['front']]
        with self.assertRaises(ValueError):validate_oral_jaws(bad)

if __name__=='__main__':unittest.main()
