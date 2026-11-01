"""Bake existing UV footprint repair parameters; never invent a new patch ROI.

Copies the existing shader's repair equations in linear color. Only its exact
polygon pixels change. Body-owned protected marks and all other RGBA stay exact.
"""
import argparse,json,re,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def linear(c):return np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
def srgb(c):return np.where(c<=.0031308,c*12.92,1.055*np.maximum(c,0)**(1/2.4)-.055)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['material','inputs','output']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[3];out=a.output.resolve();assert out.is_relative_to(root) and any(k in out.relative_to(root).parts for k in ['experiments','work','output']) and not out.exists();out.mkdir()
    receipt=read(a.inputs);textures=receipt['textures'];text=a.material.read_text(encoding='utf8')
    def parameter(key,lanes):
        match=re.search(r'^shader_parameter/'+key+r' = PackedVector\dArray\(([^\n]*)\)',text,re.M);assert match,key
        return np.asarray([float(v)for v in match[1].split(',')]).reshape(-1,lanes)
    count=int(re.search(r'^shader_parameter/patch_count = (\d+)',text,re.M)[1]);meta=parameter('patch_meta',4);rect=parameter('patch_rect',4);points=parameter('patch_points',2)
    def load(key):
        r=textures[key];assert sha(r['path'])==r['sha256'];return np.asarray(Image.open(r['path']).convert('RGBA'))
    source=load('source_texture');opaque=load('opaque_skin');protected=load('pectoral142_mask')[:,:,0]>0;result=source.copy();h,w=source.shape[:2]
    src=source.astype(float)/255;src[:,:,:3]=linear(src[:,:,:3]);fallback=opaque.astype(float)/255;fallback[:,:,:3]=linear(fallback[:,:,:3])
    def sample(image,u,v):return image[np.clip((v*h).astype(int),0,h-1),np.clip((u*w).astype(int),0,w-1)]
    yy,xx=np.mgrid[:h,:w];u=(xx+.5)/w;v=(yy+.5)/h;changed=np.zeros((h,w),bool);patches=[]
    for j in range(count):
        start,n,lo,hi=meta[j];poly=points[int(start):int(start+n)];inside=np.zeros((h,w),bool);top=np.ones((h,w));bottom=np.zeros((h,w))
        for pt,other in zip(poly,np.roll(poly,-1,axis=0)):
            if other[1]!=pt[1]:inside^=((pt[1]>v)!=(other[1]>v))&(u<pt[0]+(v-pt[1])*(other[0]-pt[0])/(other[1]-pt[1]))
            if other[0]!=pt[0]:
                mask=(pt[0]>u)!=(other[0]>u);at=pt[1]+(u-pt[0])*(other[1]-pt[1])/(other[0]-pt[0]);top=np.where(mask,np.minimum(top,at),top);bottom=np.where(mask,np.maximum(bottom,at),bottom)
        mask=inside&~protected&~changed
        donor_u=lo+np.mod(u-rect[j,0],max(.0001,hi-lo));donor_v=v.copy()
        for k in range(24):donor_v=np.where(sample(src,donor_u,donor_v)[:,:,3]>.95,donor_v,np.maximum(0,donor_v-2/h))
        grain=sample(src,donor_u,donor_v);grain=np.where((grain[:,:,3]<.95)[:,:,None],sample(fallback,donor_u,donor_v),grain)
        above=sample(src,u,np.maximum(0,top-4/h));below=sample(src,u,np.minimum(1,bottom+4/h));luma=np.array([.2126,.7152,.0722]);gl=grain[:,:,:3]@luma
        for value in [above,below]:value[:]=np.where(((value[:,:,3]<.95)|((value[:,:,:3]@luma)<gl*.65))[:,:,None],grain,value)
        along=np.clip((v-top)/np.maximum(.0001,bottom-top),0,1)[:,:,None];repair=above*(1-along)+below*along
        nearby=sample(src,donor_u,np.maximum(0,donor_v-3/h));repair[:,:,:3]=np.clip(repair[:,:,:3]+.35*(grain[:,:,:3]-nearby[:,:,:3]),0,1);repair[:,:,3]=1
        rgb=np.rint(np.clip(srgb(repair[:,:,:3]),0,1)*255).astype('uint8');result[:,:,:3][mask]=rgb[mask];changed|=mask;patches.append({'patch':j,'pixels':int(mask.sum())})
    # Keep exact original alpha: opaque body fill is authored separately.
    assert np.array_equal(result[~changed],source[~changed]) and np.array_equal(result[protected],source[protected])
    image_path=out/'body-source.png';Image.fromarray(result).save(image_path)
    report={'ok':True,'kind':'existing_shader_uv_footprint_bake','source_material':str(a.material.resolve()),'source_material_sha256':sha(a.material),'input_receipt_sha256':sha(a.inputs),'patches':patches,'changed_pixels':int(np.any(source!=result,axis=2).sum()),'protected_pixels':int(protected.sum()),'outside_and_protected_RGBA_exact':True,'textures':{'baked_skin':{'path':str(image_path),'sha256':sha(image_path),'size':[w,h]}},'scope':'Existing shader UV patch only; chart/head/rest material branches are not baked by this tool. Actual hidden-fin body review still required.'}
    (out/'material-inputs.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'changed_pixels':report['changed_pixels']}))
if __name__=='__main__':main()
