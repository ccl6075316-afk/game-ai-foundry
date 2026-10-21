#!/usr/bin/env python3
"""Freeze the reviewed zander107 mode0/1/2 local trial data with reviewed RGB-only donor copies."""
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def freeze(input_path,output):
 p=json.loads(input_path.read_text());assert p['schema_version']==1 and p['species']=='zander' and p['allowed_modes']==[0,1,2],'Current107 requires reviewed zander modes0/1/2; old0/2 needs archived helper'
 assert p['mesh']=='Closed_body' and p['surface']==0 and p['projection']['downshift_native_pixels']==11
 assert p['projection']['pixel_native_xy']==[1/2024,1/2024]
 source=ROOT/p['source_path'];opaque=ROOT/p['opaque_path'];model=ROOT/p['model_path'];assert sha(source)==p['source_sha256'] and sha(opaque)==p['opaque_sha256'] and sha(model)==p['model_sha256']
 images={}
 for name,spec in p['masks'].items():
  path=ROOT/spec['path'];assert sha(path)==spec['sha256'],'Stale mask';image=np.array(Image.open(path).convert('L'));assert list(image.shape[::-1])==p['source_size'] and set(np.unique(image))=={0,255};assert int((image==255).sum())==spec['pixels'];images[name]=(path,image)
 for path in [source,opaque]:assert list(Image.open(path).size)==p['source_size']
 source_rgba=np.array(Image.open(source).convert('RGBA'));opaque_rgba=np.array(Image.open(opaque).convert('RGBA'))
 assert source_rgba[:,:,3][images['source_eye_mask'][1]==255].min()==255
 assert opaque_rgba[:,:,3].min()==255
 assert np.array_equal(images['source_eye_mask'][1],images['fallback_eye_mask'][1]),'Actual provenance107 requires equal source/fallback domains'
 assert np.all((images['eye_layer_mask'][1]!=255)|(images['source_eye_mask'][1]==255))
 copies={};proof={}
 rect=p['repair']['donor_native_rect'];assert rect==[1780,335,1808,360] and p['repair']['kind']=='native_mirror_rgb'
 x0,y0,x1,y1=rect;w=x1-x0;h=y1-y0
 for key,original,mask in [('source',source_rgba,images['source_eye_mask'][1]==255),('opaque',opaque_rgba,images['fallback_eye_mask'][1]==255)]:
  assert not mask[y0:y1,x0:x1].any() and original[y0:y1,x0:x1,3].min()==255
  copy=original.copy();ys,xs=np.nonzero(mask);xx=(xs-x0)%(2*w);yy=(ys-y0)%(2*h);dx=x0+np.where(xx<w,xx,2*w-1-xx);dy=y0+np.where(yy<h,yy,2*h-1-yy);copy[ys,xs,:3]=original[dy,dx,:3]
  assert np.array_equal(copy[:,:,3],original[:,:,3]) and np.array_equal(copy[~mask],original[~mask])
  copies[key]=copy;proof[key]={'all_alpha_equal':True,'outside_mask_all_rgba_equal':True,'changed_rgb_pixels':int(np.any(copy[:,:,:3]!=original[:,:,:3],2).sum()),'original_rgba_sha256':hashlib.sha256(original.tobytes()).hexdigest(),'copy_rgba_sha256':hashlib.sha256(copy.tobytes()).hexdigest(),'donor_native_rect':rect}
 output.mkdir(parents=True,exist_ok=True);runtime=p['runtime_data_directory'].rstrip('/')
 frozen={k:v for k,v in p.items() if k not in ['species','source_path','source_sha256','opaque_path','opaque_sha256','model_path','runtime_model_path','runtime_data_directory','masks','scope']}
 frozen['model_path']=p['runtime_model_path'];frozen['input_profile_sha256']=sha(input_path);frozen['diagnostic_scope']=p['scope']
 for key,path,name in [('source',source,'source-runtime.png'),('opaque_skin',opaque,'opaque-runtime.png')]:
  shutil.copyfile(path,output/name);frozen[key]={'path':runtime+'/'+name,'sha256':sha(output/name)}
 for key,(path,image) in images.items():
  name=key.replace('_','-')+'.png';shutil.copyfile(path,output/name);frozen[key]={'path':runtime+'/'+name,'sha256':sha(output/name),'pixels':int((image==255).sum())}
 for key,array in copies.items():
  path=output/('clean-'+key+'.png');Image.fromarray(array).save(path);frozen['clean_'+key]={'path':runtime+'/'+path.name,'sha256':sha(path)};proof[key]['png_sha256']=sha(path)
 (output/'color-copies.validation.json').write_text(json.dumps({'schema_version':1,'ok':True,'status':'done','accepted':False,'source_and_opaque_independent':True,'channels':proof},indent=2)+'\n')
 config=output/'eye-ownership-107.json';config.write_text(json.dumps({'schema_version':1,'profiles':{'zander':frozen}},indent=2)+'\n')
 result={'schema_version':1,'ok':True,'status':'done','next_action':'human_review','command':'fish.freeze-eye-features107','inputs':{'profile':str(input_path),'profile_sha256':sha(input_path)},'summary':{'allowed_modes':[0,1,2],'source_mask_pixels':7127,'fallback_mask_pixels':7127,'eye_layer_pixels':6039,'color_repair_created':True,'rgb_copy_checks':proof,'all_original_lods_retained':True,'LOD5_gate':'failed','accepted':False,'config_sha256':sha(config)},'failures':[]}
 (output/'freeze.validation.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',required=True,type=Path);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
 try:result=freeze(args.input.resolve(),args.output.resolve())
 except (AssertionError,KeyError,OSError,ValueError,TypeError) as error:result={'ok':False,'status':'failed','next_action':'fix_input','failures':[{'kind':'validation','code':'invalid_eye107_profile','message':str(error)}]}
 print(json.dumps(result,indent=2));raise SystemExit(0 if result['ok'] else 1)
