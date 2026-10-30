"""Register continuous skin completion, protecting explicit original pixel domains.

Similarity alignment and nearest sampling do not grant visual/anatomical approval.
Polygons are species-specific source pixels, never inferred from another fish.
"""
import argparse,json,hashlib,shutil
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from parts import read,sha,fresh_output

def register(source,generated,protection,output):
    out=fresh_output(output);assert not out.exists();config=read(protection)
    original=np.asarray(Image.open(source).convert('RGBA'));gen=np.asarray(Image.open(generated).convert('RGBA'))
    assert config['source_sha256']==sha(source) and config['source_size']==[original.shape[1],original.shape[0]]
    sift=cv2.SIFT_create();a,da=sift.detectAndCompute(cv2.cvtColor(original[:,:,:3],cv2.COLOR_RGB2GRAY),None);b,db=sift.detectAndCompute(cv2.cvtColor(gen[:,:,:3],cv2.COLOR_RGB2GRAY),None)
    assert da is not None and db is not None,'No usable image features'
    matches=[pair[0]for pair in cv2.BFMatcher().knnMatch(da,db,k=2)if len(pair)==2 and pair[0].distance<.7*pair[1].distance];assert len(matches)>=20
    src=np.float32([a[m.queryIdx].pt for m in matches]);dst=np.float32([b[m.trainIdx].pt for m in matches]);matrix,inliers=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=3)
    assert matrix is not None and inliers.sum()>=20,'Insufficient reliable registration'
    scale=float(np.hypot(matrix[0,0],matrix[1,0]));rotation=float(np.degrees(np.arctan2(matrix[1,0],matrix[0,0])));assert .5<scale<2 and abs(rotation)<3,'Registration changes source orientation/scale unexpectedly'
    errors=np.linalg.norm(cv2.transform(src.reshape(-1,1,2),matrix).reshape(-1,2)-dst,axis=1);rms=float(np.sqrt(np.mean(errors[inliers[:,0]>0]**2)));assert rms<2
    h,w=original.shape[:2];aligned=cv2.warpAffine(gen,cv2.invertAffineTransform(matrix),(w,h),flags=cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT)
    mask=np.zeros((h,w),dtype='uint8')
    for poly in config['protected_polygons_px']:
        points=np.asarray(poly,dtype='int32');assert len(points)>=3 and (points>=0).all() and (points[:,0]<w).all() and (points[:,1]<h).all();cv2.fillPoly(mask,[points],1)
    protected=mask>0;result=aligned.copy();result[protected]=original[protected];assert np.array_equal(result[protected],original[protected])
    out.mkdir(parents=True);shutil.copyfile(generated,out/'generated.png');target=out/'body-source.png';Image.fromarray(result).save(target)
    receipt={'ok':True,'kind':'registered_continuous_body_skin','source_sha256':sha(source),'generated_sha256':sha(generated),'protection_sha256':sha(protection),'registration':{'matrix_original_to_generated':matrix.tolist(),'inliers':int(inliers.sum()),'matches':len(matches),'rms_pixels':rms,'sampling':'nearest'},'protected_RGBA_exact':True,'protected_pixels':int(protected.sum()),'textures':{'generated_skin':{'path':str(target),'sha256':sha(target),'size':[w,h]}},'visual_review':'pending','scope':'Generated body skin only; exact original pixels in explicit protected regions. No geometry, fin-shape, anatomy or visual acceptance.'}
    (out/'material-inputs.validation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['source','generated','protection','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--json',action='store_true');a=p.parse_args()
    try:r=register(a.source,a.generated,a.protection,a.output);print(json.dumps({'ok':True,'registration':r['registration'],'protected_pixels':r['protected_pixels']}))
    except (AssertionError,ValueError,OSError,KeyError)as e:print(json.dumps({'ok':False,'next_action':'fix_input','error':str(e)}));raise SystemExit(1)
