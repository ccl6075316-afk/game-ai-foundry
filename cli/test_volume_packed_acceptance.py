"""Guard real accepted packed evidence against silent omissions and relaxed limits."""
import copy,hashlib,sys,unittest,numpy as np
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'cli'))
import volume_packed_acceptance as gate
from volume_sop import check_native_lip_report,check_fin_volume_report

class PackedAcceptanceTests(unittest.TestCase):
 def setUp(self):
  names=['FinA','FinB'];rules=[dict(name=n,closing_faces=[],skin_faces=[0,1,2],source_baseline=[[0,0],[0,1]])for n in names]
  self.profile=dict(fins=rules,tail_root_height_domain=[0,1],rejected_fin_model_sha256='old')
  self.candidates=dict(model=dict(path='fixture.glb',sha256='model'),source_image=dict(sha256='image'),species_profile=dict(sha256='profile'),editable_blend=dict(sha256='blend'))
  rows=[dict(name=n,closing_faces=[],missing_rays=[],source_baseline=[[0,0],[0,1]],complete_original_root_domain_preserved=True,actual_samples=[dict(face=i,source_t=t,normal_thickness_mm=thick)for i,t,thick in [(0,.2,2),(1,.5,1),(2,.9,.5)]for _ in range(4)],transparent_source_samples=[])for n in names]
  ref=lambda p:dict(path=p,sha256='fixture')
  self.volume=dict(ok=True,kind='actual_packed_source_fin_volume_and_tail_section',species='nile_tilapia',model_sha256='model',profile_sha256='profile',source_correspondence=ref('source'),root490=ref('roots'),membrane490=ref('membranes'),rejected_original=ref('negative'),current=dict(fins=rows,tail_section=dict(sections=[{}, {}, {}],max_error_mm=.1,root_height_domain=[0,1],same_declared_attachment_plane=True)))
  self.lip=dict(ok=True,kind='preserved_complete_anterior_native_chart',species='nile_tilapia',model_sha256='model',source_sha256='image',baseline_native_chart=ref('chart'),complete_body_chart_preserved=True,auxiliary_color_contribution_changes=0,actual_3d_rim_transport=dict(upper_edges=2,lower_edges=2))
  u=[[0,0],[1,0],[0,1]];f=[[0,1,2]];image=b'native-pixels';material={'name':'original'}
  fixtures={'source':dict(ok=True,kind='saved_packed_source_row_correspondence',model_sha256='model',blend_sha256='blend',maximum_bidirectional_position_error_native=0.,source_vertex_count=6,export_vertex_count=6),'roots':dict(ok=True,model_sha256='model',samples=[{}]*490,tolerance_cm=.10,max_penetration_cm=.60,summary={n:dict(failed_contact_samples=0)for n in names}),'membranes':dict(ok=True,model_sha256='model',poses=490,root_collar_mm=.5,penetration_tolerance_mm=.02,summary={n:dict(failed_poses=0)for n in names}),'negative':dict(ok=False,model_sha256='old',current=[dict(name=n,missing_rays=[0])for n in names]),'chart':dict(source_sha256='image',accepted_material_scope='complete body and integrated mouth chart',parts=[dict(role=r,uv=copy.deepcopy(u),indices=copy.deepcopy(f))for r in ['body_skin','mouth']],embedded_image_sha256=hashlib.sha256(image).hexdigest(),material=material)}
  doc=dict(extras=dict(geometry_parts=[dict(role=r,vertex_start=i*3,vertex_count=3,index_start=i*3,index_count=3)for i,r in enumerate(['body_skin','mouth'])]),images=[dict(bufferView=0)],bufferViews=[dict(byteOffset=0,byteLength=len(image))],materials=[material])
  patch=mock.patch.object(gate,'_load',side_effect=lambda ref:copy.deepcopy(fixtures[ref['path']]));patch.start();self.addCleanup(patch.stop)
  patch=mock.patch.object(gate,'_arrays',return_value=(doc,image,{},dict(TEXCOORD_0=np.array(u+u)),np.array([[0,1,2],[3,4,5]])));patch.start();self.addCleanup(patch.stop)
 def check_volume(self,report):
  failures=[];check_fin_volume_report(report,self.candidates,'nile_tilapia',lambda *a:failures.append(a),'volume',self.profile);return failures
 def check_lip(self,report):
  failures=[];check_native_lip_report(report,self.candidates,'nile_tilapia',lambda *a:failures.append(a),'lip');return failures
 def test_complete_packed_source_and_all_gates_are_accepted(self):
  self.assertEqual(self.check_volume(self.volume),[]);self.assertEqual(self.check_lip(self.lip),[])
 def test_generic_pass_does_not_satisfy_either_contract(self):
  self.assertTrue(self.check_volume({'ok':True}));self.assertTrue(self.check_lip({'ok':True}))
 def test_missing_fin_is_rejected(self):
  r=copy.deepcopy(self.volume);r['current']['fins'].pop();self.assertTrue(self.check_volume(r))
 def test_missing_actual_surface_probe_is_rejected(self):
  r=copy.deepcopy(self.volume);r['current']['fins'][0]['actual_samples'].pop();self.assertTrue(self.check_volume(r))
 def test_constant_shell_is_rejected(self):
  r=copy.deepcopy(self.volume)
  for row in r['current']['fins']:
   for sample in row['actual_samples']:sample['normal_thickness_mm']=1.
  self.assertTrue(self.check_volume(r))
 def test_changed_source_geometry_correspondence_is_rejected(self):
  original=gate._load
  def altered(ref):
   r=copy.deepcopy(original(ref))
   if ref==self.volume['source_correspondence']:r['maximum_bidirectional_position_error_native']=.001
   return r
  with mock.patch.object(gate,'_load',side_effect=altered):self.assertTrue(self.check_volume(self.volume))
 def test_relaxed_membrane_collar_is_rejected(self):
  original=gate._load
  def altered(ref):
   r=copy.deepcopy(original(ref))
   if ref==self.volume['membrane490']:r['root_collar_mm']=.6
   return r
  with mock.patch.object(gate,'_load',side_effect=altered):self.assertTrue(self.check_volume(self.volume))
 def test_changed_preserved_body_uv_is_rejected(self):
  original=gate._load
  def altered(ref):
   r=copy.deepcopy(original(ref));r['parts'][0]['uv'][0][0]+=.01;return r
  with mock.patch.object(gate,'_load',side_effect=altered):self.assertTrue(self.check_lip(self.lip))

if __name__=='__main__':unittest.main()
