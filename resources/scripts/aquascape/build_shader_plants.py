"""One native-resolution atlas and one unskinned mesh per plant species.

UV2 encodes leaf distance and phase. Vertex color encodes the true leaf anchor
in model bounds, plus a leaf mask. No sampled animation textures are produced.
"""
import argparse,io,json,math,copy
from pathlib import Path
import numpy as np
from PIL import Image
from build_from_art import Glb
from rig_plant_current import read_glb,array
from optimize_scenery import load,save,sha,metrics

def build(source,out,atlas_path):
    d,b=read_glb(source);images=[]
    for image in d['images']:
        view=d['bufferViews'][image['bufferView']];off=view.get('byteOffset',0)
        images.append(Image.open(io.BytesIO(b[off:off+view['byteLength']])).convert('RGBA'))
    pad=8;area=sum((im.width+pad*2)*(im.height+pad*2) for im in images)
    width=2**math.ceil(math.log2(max(max(im.width+pad*2 for im in images),math.sqrt(area))))
    xy=[];x=0;y=0;line=0
    for im in images:
        if x+im.width+pad*2>width:y+=line;x=0;line=0
        xy.append((x+pad,y+pad));x+=im.width+pad*2;line=max(line,im.height+pad*2)
    height=2**math.ceil(math.log2(y+line));atlas=Image.new('RGBA',(width,height),(0,0,0,255))
    for im,(x,y) in zip(images,xy):
        # Repeat native edge colors into the gutters. No source resampling.
        a=np.pad(np.asarray(im),((pad,pad),(pad,pad),(0,0)),mode='edge')
        atlas.paste(Image.fromarray(a),(x-pad,y-pad))
    atlas.save(atlas_path)
    allv=np.vstack([array(d,b,p['attributes']['POSITION']) for m in d['meshes'] for p in m['primitives']]);low=allv.min(0);size=np.maximum(np.ptp(allv,axis=0),1e-6)
    parts={k:[] for k in ['POSITION','NORMAL','TEXCOORD_0','TEXCOORD_1','COLOR_0']}
    for mesh in d['meshes']:
        leaf=mesh['name'].startswith('traced_leaf_');leaf_id=int(mesh['name'].rsplit('_',1)[1])-1 if leaf else 0
        for p in mesh['primitives']:
            attrs=p['attributes'];v=array(d,b,attrs['POSITION']);uv=array(d,b,attrs['TEXCOORD_0']);normal=array(d,b,attrs['NORMAL'])
            mat=d['materials'][p['material']];ti=mat['pbrMetallicRoughness']['baseColorTexture']['index'];ii=d['textures'][ti]['source'];im=images[ii];x,y=xy[ii]
            atlas_uv=(uv*np.array(im.size)+[x,y])/[width,height]
            color=np.zeros((len(v),4),dtype='float32');aux=np.zeros((len(v),2),dtype='float32')
            if leaf:
                js=array(d,b,attrs['JOINTS_0']);ws=array(d,b,attrs['WEIGHTS_0']);joint=int(np.min(js[ws>0]));node=d['nodes'][d['skins'][0]['joints'][joint]]
                anchor=np.asarray(node['translation']);color[:,:3]=(anchor-low)/size;color[:,3]=1
                aux[:,0]=np.clip(1-uv[:,1],0,1);aux[:,1]=(leaf_id*.61803398875)%1
            parts['POSITION'].append(v);parts['NORMAL'].append(normal);parts['TEXCOORD_0'].append(atlas_uv);parts['TEXCOORD_1'].append(aux);parts['COLOR_0'].append(color)
    g=Glb();mat=g.material(atlas,'native_art_atlas');attrs={k:g.accessor(np.vstack(v),'VEC2' if k.startswith('TEXCOORD') else 'VEC4' if k=='COLOR_0' else 'VEC3') for k,v in parts.items()}
    g.doc['meshes']=[{'name':source.stem+'_shader','primitives':[{'attributes':attrs,'material':mat,'mode':4}]}];g.doc['nodes']=[{'name':source.stem,'mesh':0}];g.doc['scenes'][0]['nodes']=[0]
    g.doc['extras']={'anchor_min':low.tolist(),'anchor_size':size.tolist(),'animation':'procedural; no bones or frame cache','native_atlas_size':[width,height]};g.save(out)
    return {'id':source.stem,'model':str(out),'atlas':str(atlas_path),'anchor_min':low.tolist(),'anchor_size':size.tolist(),'native_atlas_size':[width,height],**metrics(out),'source_sha256':sha(source)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    rows=[build(src,a.output/(src.stem+'.glb'),a.output/(src.stem+'.png')) for src in sorted(a.input.glob('*.glb'))]
    save(a.output/'shader-plants.validation.json',{'schema_version':1,'command':'aquascape.shader-plant-build','ok':True,'status':'done','next_action':'human_review','outputs':rows,'failures':[],'user_acceptance':'pending'})
    print(json.dumps({'ok':True,'species':len(rows),'triangles':sum(r['triangles'] for r in rows)}))
if __name__=='__main__':main()
