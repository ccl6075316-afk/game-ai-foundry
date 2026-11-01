"""Independent preservation and source-section check for posterior assembly repair.

No visual acceptance is inferred from this check. Fixed-canvas contour audits,
actual GPU review and current full dynamic contact reports remain mandatory.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
from freeze_surface_ownership import read_glb,accessor

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))

def main():
 p=argparse.ArgumentParser()
 for key in ['before','after','parameters','output']:p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();root=Path(__file__).resolve().parents[3];params=read(a.parameters)['profiles'];old=read(a.before)['items'];new=read(a.after)['items'];rows=[]
 assert {r['species'] for r in old}=={r['species'] for r in new}
 for before in old:
  sp=before['species'];after=next(r for r in new if r['species']==sp);cfg=params[sp]
  assert sha(before['model'])==before['model_sha256'] and sha(after['model'])==after['model_sha256']
  d,b=read_glb(Path(before['model']));nd,nb=read_glb(Path(after['model']));assert nb[:len(b)]==b
  for key in ['nodes','skins','animations','images','materials','textures','samplers']:assert d.get(key)==nd.get(key),key
  changed=[];oldbody=[];newbody=[]
  for n in d['nodes']:
   if 'mesh' not in n:continue
   name=n['name'];ps=d['meshes'][n['mesh']]['primitives'];qs=nd['meshes'][n['mesh']]['primitives'];assert len(ps)==len(qs)
   for si,(bp,ap) in enumerate(zip(ps,qs)):
    assert bp['material']==ap['material'] and set(bp['attributes'])==set(ap['attributes'])
    assert np.array_equal(accessor(d,b,bp['indices']),accessor(nd,nb,ap['indices']))
    v=accessor(d,b,bp['attributes']['POSITION']);w=accessor(nd,nb,ap['attributes']['POSITION'])
    if name=='Closed_body':oldbody.append(v);newbody.append(w)
    for key,index in bp['attributes'].items():
     x=accessor(d,b,index);y=accessor(nd,nb,ap['attributes'][key]);assert x.shape==y.shape
     if np.array_equal(x,y):continue
     changed.append([name,si,key]);assert name in ['Closed_body','Caudal'] and key in ['POSITION','NORMAL','TEXCOORD_0']
     if name=='Closed_body':
      front=v[:,0]+.5>=cfg['body_blend_end_u'];assert np.array_equal(x[front],y[front]),'Anterior body changed'
      if key=='POSITION':assert np.array_equal(x[:,[0,2]],y[:,[0,2]])
      if key=='TEXCOORD_0':assert si==0
    if name=='Caudal':
     assert before['fins'][name]['ids']==after['fins'][name]['ids']
     ids=np.array(before['fins'][name]['ids']);assert np.allclose(w[ids],after['fins'][name]['rest_points_gltf'],atol=1e-9,rtol=0)
     uv=accessor(nd,nb,ap['attributes']['TEXCOORD_0'])
     profile=read(root/'resources/volume-fish'/f'{sp.replace("_","-")}-121.profile.json');aspect=profile['source_aspect_ratio']
     assert np.max(np.abs(uv-np.c_[w[:,0]+.5,.5-w[:,1]*aspect]))<1e-6,'Material projection does not follow repaired geometry'
  source=root/f'projects/fishing-2d/experiments/blender-fish/hammer-pair-121/accepted/{sp}/inputs/char_{sp}_side121_nobg.png';im=np.array(Image.open(source));h,width=im.shape[:2];x=round(cfg['cap_u']*width);ys=np.flatnonzero(im[:,x,3]>128);target=ys[[0,-1]]
  def cap_pixels(body):
   v=np.concatenate(body);cap=v[np.abs(v[:,0]-(cfg['cap_u']-.5))<1e-6];return np.array([(.5-cap[:,1].max()*aspect)*h,(.5-cap[:,1].min()*aspect)*h])
  before_error=float(np.max(np.abs(cap_pixels(oldbody)-target)));after_error=float(np.max(np.abs(cap_pixels(newbody)-target)))
  assert before_error>20 and after_error<1.01,'Source endpoint constraint must reject historical shoulders'
  rows.append({'ok':True,'species':sp,'before_sha256':sha(before['model']),'model_sha256':sha(after['model']),'source_sha256':sha(source),'changed_attributes':changed,'complete_root_count':len(ids),'source_cap_error_px_before':before_error,'source_cap_error_px_after':after_error,'old_bad_cap_negative_control_failed':True,'original_binary_rig_sources_other_meshes_anterior_body_preserved':True,'caudal_uv_matches_actual_side_geometry':True})
 result={'ok':True,'records':rows,'checker_sha256':sha(__file__),'parameters_sha256':sha(a.parameters),'limits':'Source cap and preservation constraints only; full fixed-canvas contours and actual textured/gray dynamic reviews are separate.'}
 a.output.write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
