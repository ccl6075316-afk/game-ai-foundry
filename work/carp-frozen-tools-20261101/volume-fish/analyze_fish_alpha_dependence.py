"""Sample actual rest triangles' texture alpha; never reports screen-hole percentage."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image
from pack_fish_material_atlas import arrays,read_glb,wrap_indices

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def analyze(model,samples=1024):
    model=Path(model).resolve();doc,binary=read_glb(model);rows=[]
    assert samples>0 and samples<=16384 and samples&(samples-1)==0,'Use a power-of-two sample count'
    ids=np.arange(samples,dtype=np.uint32);v=np.zeros(samples)
    bits=int(np.log2(samples))
    for bit in range(bits):v+=((ids>>bit)&1)/(2**(bit+1))
    q=np.sqrt((ids+.5)/samples);bary=np.column_stack((1-q,q*(1-v),q*v))
    for node in doc['nodes']:
        if 'mesh'not in node:continue
        for surface,pr in enumerate(doc['meshes'][node['mesh']]['primitives']):
            mat=doc['materials'][pr['material']]
            if mat.get('alphaMode','OPAQUE')!='MASK':continue
            pbr=mat.get('pbrMetallicRoughness',{});tex=doc['textures'][pbr['baseColorTexture']['index']];im=doc['images'][tex['source']];view=doc['bufferViews'][im['bufferView']]
            raw=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']];pixels=np.asarray(Image.open(io.BytesIO(raw)).convert('RGBA'));h,w=pixels.shape[:2]
            sampler=doc.get('samplers',[{}])[tex.get('sampler',0)];wrap=[sampler.get('wrapS',10497),sampler.get('wrapT',10497)]
            positions=arrays(doc,binary,pr['attributes']['POSITION']);uv=arrays(doc,binary,pr['attributes']['TEXCOORD_0']);tri=arrays(doc,binary,pr['indices']).reshape(-1,3)
            coords=np.einsum('bc,tcd->tbd',bary,uv[tri]);pixel=np.floor(coords*[w,h]).astype(int)
            xs=wrap_indices(pixel[:,:,0],w,wrap[0]);ys=wrap_indices(pixel[:,:,1],h,wrap[1]);alpha=pixels[ys,xs,3].astype(float)/255.*pbr.get('baseColorFactor',[1,1,1,1])[3]
            rejected=alpha<float(mat.get('alphaCutoff',.5));pertri=rejected.sum(axis=1);fraction=pertri/samples
            pos=positions[tri].astype(float);areas=np.linalg.norm(np.cross(pos[:,1]-pos[:,0],pos[:,2]-pos[:,0]),axis=1)*.5
            worst=[]
            for ti in np.argsort(-pertri)[:12]:
                if not pertri[ti]:break
                witnesses=[]
                for sample_i in np.flatnonzero(rejected[ti])[:3]:
                    witnesses.append({'barycentric':bary[sample_i].tolist(),'UV':coords[ti,sample_i].tolist(),'source_pixel':[int(xs[ti,sample_i]),int(ys[ti,sample_i])],'rest_POSITION':(bary[sample_i]@pos[ti]).tolist(),'alpha':float(alpha[ti,sample_i])})
                worst.append({'triangle_index':int(ti),'vertex_indices':tri[ti].tolist(),'rejected_samples':int(pertri[ti]),'fraction':float(fraction[ti]),'rest_triangle_area_native':float(areas[ti]),'witnesses':witnesses})
            rows.append({'part':node.get('name'),'surface':surface,'material':mat.get('name'),'source_image_RGBA_sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),'source_size':[w,h],'sampler_wrap':wrap,'triangles':len(tri),'samples_per_triangle':samples,'total_samples':int(rejected.size),'alpha_below_cutoff_samples':int(rejected.sum()),'unweighted_triangle_sample_fraction':float(rejected.mean()),'rest_area_weighted_fraction':float(np.dot(fraction,areas)/areas.sum()),'triangles_with_any_rejected_samples':int((pertri>0).sum()),'worst_triangles':worst})
    return {'ok':True,'kind':'actual_UV_triangle_alpha_dependence','model':str(model),'model_sha256':sha(model),'checker_sha256':sha(__file__),'method':'Deterministic uniform-area barycentric Hammersley samples on every actual MASK triangle, nearest original source image and original sampler wrap/cutoff. No source alpha threshold changed.','scope':'Rest geometric triangle sampling, including both sides and sidewalls. Fractions are NOT visible screen-hole percentages, visual severity, alpha source area or proof of action-time visibility. Body occlusion, camera projection and sample convergence are not measured. Actual same-view GPU captures decide visual acceptability.','parts':rows}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[3];out=a.output.resolve()
    assert out.is_relative_to(root/'work')or out.is_relative_to(root/'output')or out.is_relative_to(root/'projects/fishing-2d/experiments')
    assert out!=a.model.resolve() and not out.exists(),'Refuse input alias or overwriting evidence'
    result=analyze(a.model);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'ok':True,'parts':[{k:x[k]for k in ('part','triangles','alpha_below_cutoff_samples','total_samples','unweighted_triangle_sample_fraction','rest_area_weighted_fraction')}for x in result['parts']]}))

if __name__=='__main__':main()
