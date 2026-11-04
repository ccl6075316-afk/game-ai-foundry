"""Actual library/current side views and finite axial envelopes, no approval."""
import argparse,hashlib,json,sys,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from inspect_hammerhead_library import render
from measure_hammerhead_head_field import load_reference,load_candidate,vertical
from portable.glb_io import read_glb,arrays
ROOT=Path(__file__).resolve().parents[3]
def projected_bounds(v,f,x):
 t=v[f];a=t;b=np.roll(t,-1,axis=1);k=(a[:,:,0]-x)*(b[:,:,0]-x)<0
 if not np.any(k) and not np.any(abs(a[:,:,0]-x)<1e-7):return None
 q=a[k]+((x-a[:,:,0][k])/(b[:,:,0][k]-a[:,:,0][k]))[:,None]*(b[k]-a[k]);q=np.concatenate([q,a[abs(a[:,:,0]-x)<1e-7]]);return [float(q[:,1].min()),float(q[:,1].max())]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--model',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--registration',type=float);a=ap.parse_args();o=a.output.resolve();assert not o.exists()and'/experiments/'in str(o);o.mkdir()
 p=ROOT/'projects/fishing-2d/experiments/scalloped-art-rebuild-20261102';ref=ROOT/'resources/fish-database/artifacts/fishing-master-cdn-cnformal1-20261102/mesh-exports/f516b1aa036a3161d9504b4b29a8523861e22d658d417078e60c6e95ca44f6a8.obj';L=2.4914281368255615;nose=1.032794117647059
 rv,rf=load_reference(ref);cv,cf=load_candidate(a.model,L,nose);rows=[]
 for x in np.linspace(.025,.4,151):
  z=.015;r=vertical(rv[rf],float(x),z);c=vertical(cv[cf],float(x),z);rows.append(dict(p=float(x),offcentre_over_length=z,reference=r,current=c))
 anchor=min(rows,key=lambda r:abs(r['p']-.35));dy=(anchor['current']['top']+anchor['current']['bottom']-anchor['reference']['top']-anchor['reference']['bottom'])/2
 if a.registration is not None:dy=a.registration
 # Complete original OBJ includes its eye and oral groups; keep actual UVs.
 rawv=[];rawuv=[];ff=[];uv=[]
 for l in ref.read_text().splitlines():
  if l.startswith('v '):rawv.append(list(map(float,l.split()[1:])))
  elif l.startswith('vt '):rawuv.append(list(map(float,l.split()[1:])))
  elif l.startswith('f '):
   q=[x.split('/')for x in l.split()[1:]];ff.append([int(x[0])-1 for x in q]);uv.extend([rawuv[int(x[1])-1]for x in q])
 rawv=np.array(rawv)[:,[1,2,0]];rawv[:,0]-=rawv[:,0].min();rawv/=1.62865174;ff=np.array(ff);tex=np.array(Image.open(p/'library-review-20261103/reference-diffuse.png').convert('RGBA'))
 d,b=read_glb(a.model);groups=[]
 for n in d['nodes']:
  if 'mesh'not in n:continue
  for t in d['meshes'][n['mesh']]['primitives']:
   v=arrays(d,b,t['attributes']['POSITION']).astype(float);v[:,0]=(nose-v[:,0])/L;v[:,2]*=-1;v[:,1:]/=L;f=arrays(d,b,t['indices']).reshape(-1,3);im=None
   mat=d['materials'][t['material']];tx=mat.get('pbrMetallicRoughness',{}).get('baseColorTexture')
   if tx is not None:
    img=d['images'][d['textures'][tx['index']]['source']];vbuf=d['bufferViews'][img['bufferView']];im=np.array(Image.open(io.BytesIO(b[vbuf.get('byteOffset',0):vbuf.get('byteOffset',0)+vbuf['byteLength']])).convert('RGBA'))
   groups.append((v,f,arrays(d,b,t['attributes']['TEXCOORD_0'])if'TEXCOORD_0'in t['attributes']else None,im))
 # Finite rasterizer supports a single depth buffer. Assemble per-face RGBA
 # separately for diagnostic texture; clay comparison includes all meshes.
 vv=np.concatenate([q[0]for q in groups]);off=0;fs=[]
 for v,f,_,_ in groups:fs.append(f+off);off+=len(v)
 fs=np.concatenate(fs);sheet=Image.new('RGB',(1800,1000),'white');dr=ImageDraw.Draw(sheet)
 for row,(v,f,label)in enumerate([(rawv,ff,'Original library | full length1, species unverified'),(vv,fs,'Current | full length1')]):
  v=v.copy()
  if row==0:v[:,1]+=dy
  for col,view in enumerate(['side','top']):
   im=render(v,f,(900,465),view,[.175,-.02,0],.40);sheet.paste(im,(col*900,row*500+35));dr.text((col*900+10,row*500+10),label+' | '+view,fill='black')
 sheet.save(o/'head-gill-side-top.jpg',quality=95)
 # Actual library texture, no eye or jaw geometry redrawn.
 v=rawv.copy();v[:,1]+=dy;im=render(v[ff].reshape(-1,3),np.arange(len(ff)*3).reshape(-1,3),(1800,700),'side',[.175,-.02,0],.40,np.array(uv),tex,True);im.save(o/'library-side-texture.png')
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 full_side=[dict(p=float(p),reference=projected_bounds(rv,rf,float(p)),current=projected_bounds(cv,cf,float(p)),lower_uncontaminated_by_reference_fins=bool(p<=.22501))for p in np.linspace(.0125,.25,96)]
 report=dict(full_side_rows=full_side,kind='actual_library_head_gill_side_audit',model_sha256=sha(a.model),reference_sha256=sha(ref),normalization='Each whole longitudinal rest extent1; X snout->tail,Y up,Z transverse. Same scale/camera. Reference translated vertically only by actual off-centre body midpoint at p=.35.',reference_vertical_registration_over_length=dy,length_m=L,finite_rows=rows,reference_identity='Game model, species unverified, user permits head/neck reference; no adult biological measurement.',limits=['Reference open mouth versus own nearly closed cavity, jaw pose not blindly copied.','Offcentre.015L finite chord, not maximum sagittal body height; fins are present in original mesh but these channels/stations must be visually checked.','Diagnostic software rendering, not original-game screenshot or material acceptance.'])
 (o/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(output=str(o),dy=dy)))
if __name__=='__main__':main()
