"""Native-pixel-preserving atlas and one-surface packing for compatible skinned GLBs.

This creates isolated performance candidates, not an accepted replacement asset.
Geometry, normal, joint, weight and animation values are retained; UV addresses
change to a non-resampled atlas. Disconnected parts remain disconnected.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import numpy as np
from PIL import Image

DTYPES={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}
LANES={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read_glb(path):
    raw=Path(path).read_bytes()
    assert len(raw)>=20 and raw[:4]==b'glTF' and struct.unpack_from('<I',raw,4)[0]==2
    assert struct.unpack_from('<I',raw,8)[0]==len(raw),'Truncated GLB'
    offset=12;doc=None;binary=None
    while offset<len(raw):
        length,kind=struct.unpack_from('<II',raw,offset);offset+=8
        chunk=raw[offset:offset+length];assert len(chunk)==length;offset+=length
        if kind==0x4e4f534a:assert doc is None;doc=json.loads(chunk)
        elif kind==0x004e4942:assert binary is None;binary=chunk
        else:raise ValueError('Unsupported GLB chunk')
    assert doc is not None and binary is not None and len(doc['buffers'])==1
    return doc,binary

def arrays(doc,binary,index):
    a=doc['accessors'][index];assert 'sparse' not in a,'Sparse accessor unsupported'
    view=doc['bufferViews'][a['bufferView']];assert view.get('buffer',0)==0
    dtype=np.dtype(DTYPES[a['componentType']]);lanes=LANES[a['type']]
    stride=view.get('byteStride',dtype.itemsize*lanes)
    offset=view.get('byteOffset',0)+a.get('byteOffset',0)
    assert stride>=dtype.itemsize*lanes and offset+(a['count']-1)*stride+dtype.itemsize*lanes<=len(binary)
    return np.ndarray((a['count'],lanes),dtype=dtype,buffer=binary,offset=offset,strides=(stride,dtype.itemsize)).copy()

def write_glb(path,doc,binary):
    doc['buffers']=[{'byteLength':len(binary)}]
    j=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode();j+=b' '*((-len(j))%4)
    b=bytes(binary)+b'\0'*((-len(binary))%4)
    Path(path).write_bytes(struct.pack('<4sII',b'glTF',2,12+8+len(j)+8+len(b))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(b),0x004e4942)+b)

def check_paths(model,output):
    model=Path(model).resolve();output=Path(output).resolve()
    assert model.is_file() and model.suffix.lower()=='.glb'
    root=Path(__file__).resolve().parents[3]
    allowed=any(output.is_relative_to(root/name)for name in ('work','output'))
    if output.is_relative_to(root/'projects'):
        relative=output.relative_to(root/'projects').parts
        allowed=allowed or (len(relative)>=2 and relative[1]=='experiments')
    assert allowed,'Output must be in this Foundry work/output or projects/<project>/experiments'
    assert not (model==output or output in model.parents),'Output aliases input'
    assert output!=model.parent,'Output must be a separate candidate directory'
    for name in ('merged-mask.glb','merged-opaque.glb','atlas.png','packing.validation.json'):
        assert not (output/name).exists(),'Refuse overwriting candidate '+name
    return model,output

def material_settings(mat):
    m=copy.deepcopy(mat);m.pop('name',None);m.pop('alphaMode',None);m.pop('alphaCutoff',None)
    pbr=m.setdefault('pbrMetallicRoughness',{});pbr.pop('baseColorTexture',None);pbr.pop('baseColorFactor',None)
    assert set(pbr)<= {'metallicFactor','roughnessFactor'},'Other PBR maps require a multi-map atlas'
    assert set(m)<= {'doubleSided','pbrMetallicRoughness','extensions'},'Unsupported material feature'
    # This packer remaps only baseColorTexture. An opaque extension object can
    # contain texture indices, so accepting arbitrary extensions would retain
    # stale references after reducing the image/texture arrays to one atlas.
    extensions=m.get('extensions',{})
    assert extensions in ({},{'KHR_materials_specular':{'specularFactor':0}}),'Unsupported material extension; only known scalar specular=0 is supported'
    pbr.setdefault('roughnessFactor',1);pbr.setdefault('metallicFactor',1);m.setdefault('doubleSided',False)
    return m

def wrap_indices(values,size,mode):
    if mode==10497:return np.mod(values,size)
    if mode==33071:return np.clip(values,0,size-1)
    if mode==33648:
        t=np.mod(values,2*size);return np.where(t<size,t,2*size-1-t)
    raise ValueError('Unsupported texture wrapping')

def source_region(doc,binary,material,uv,padding):
    pbr=material.get('pbrMetallicRoughness',{});t=pbr.get('baseColorTexture')
    factor=np.asarray(pbr.get('baseColorFactor',[1,1,1,1]),dtype='<f4')
    assert factor.shape==(4,) and np.isfinite(factor).all()
    assert np.all(factor>=0)and np.all(factor<=1),'Base color factor outside supported range'
    mode=material.get('alphaMode','OPAQUE');assert mode in ('MASK','OPAQUE')
    assert mode!='MASK' or material.get('alphaCutoff',.5)==.5,'Different alpha thresholds'
    assert factor[3]==1,'Nonunit factor alpha needs explicit opacity handling'
    if not t:
        linear=factor[:3].astype(float)
        encoded=np.where(linear<=.0031308,12.92*linear,1.055*np.power(linear,1/2.4)-.055)
        rgb=np.rint(encoded*255).astype(np.uint8);rgba=np.r_[rgb,np.uint8(255)]
        quantized=rgb.astype(float)/255
        decoded=np.where(quantized<=.04045,quantized/12.92,np.power((quantized+.055)/1.055,2.4))
        proof={'source_linear_RGBA':factor.tolist(),'target_sRGB_RGB':encoded.tolist(),'atlas_sRGB8_RGBA':rgba.tolist(),'decoded_linear_RGB':decoded.tolist(),'linear_RGB_error':(decoded-linear).tolist(),'max_sRGB_encoding_error':float(np.abs(quantized-encoded).max()),'scope':'RGBA8 constant-patch quantization, not final screen pixel error; actual GPU parity still required.'}
        return {'pixels':np.tile(rgba,(1+2*padding,1+2*padding,1)),'origin':[0,0],'source_size':[1,1],'factor':factor,'constant':True,'constant_color_encoding':proof,'source_rgba_sha256':None,'wrap':[33071,33071]}
    assert np.array_equal(factor,np.ones(4,dtype='<f4')),'Nonwhite textured factor requires an explicit offline color bake'
    assert set(t)<= {'index','texCoord'} and t.get('texCoord',0)==0,'Unsupported texture transform/UV set'
    tex=doc['textures'][t['index']];sampler=doc.get('samplers',[{}])[tex.get('sampler',0)]
    assert sampler.get('magFilter',9729)==9728 and sampler.get('minFilter',9729)==9728,'Nearest nonmip source required'
    image=doc['images'][tex['source']];assert 'bufferView'in image and image.get('mimeType')=='image/png'
    view=doc['bufferViews'][image['bufferView']];payload=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
    pixels=np.asarray(Image.open(io.BytesIO(payload)).convert('RGBA'));h,w=pixels.shape[:2]
    lo=np.floor(uv.min(axis=0)*[w,h]).astype(int)-padding
    hi=np.floor(uv.max(axis=0)*[w,h]).astype(int)+padding+1
    assert np.all(hi>lo) and np.prod(hi-lo)<20_000_000,'Unbounded tiled UV domain'
    modes=[sampler.get('wrapS',10497),sampler.get('wrapT',10497)]
    xs=wrap_indices(np.arange(lo[0],hi[0]),w,modes[0]);ys=wrap_indices(np.arange(lo[1],hi[1]),h,modes[1])
    crop=pixels[ys[:,None],xs[None,:]].copy()
    if mode=='OPAQUE':crop[:,:,3]=255
    return {'pixels':crop,'origin':lo.tolist(),'source_size':[w,h],'factor':factor,'constant':False,'source_rgba_sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),'wrap':modes,'source_pixels':pixels}

def pack_regions(regions):
    # Fixed power-of-two row packing preserves pixel scale; no image resampling.
    area=sum(r['pixels'].shape[0]*r['pixels'].shape[1] for r in regions)
    minimum=max(r['pixels'].shape[1] for r in regions)
    width=2**math.ceil(math.log2(max(minimum,math.sqrt(area))))
    while width<=8192:
        x=y=row_height=0
        for r in sorted(regions,key=lambda r:r['pixels'].shape[0],reverse=True):
            h,w=r['pixels'].shape[:2]
            if x+w>width:y+=row_height;x=0;row_height=0
            r['placement']=[x,y];x+=w;row_height=max(row_height,h)
        height=2**math.ceil(math.log2(max(1,y+row_height)))
        if height<=8192:break
        width*=2
    assert width<=8192 and height<=8192,'Native atlas exceeds 8192 limit'
    atlas=np.zeros((height,width,4),dtype=np.uint8)
    for r in regions:
        h,w=r['pixels'].shape[:2];x,y=r['placement'];atlas[y:y+h,x:x+w]=r['pixels']
    return atlas

def build(model,output,padding=3):
    model,output=check_paths(model,output);before=sha(model);doc,binary=read_glb(model)
    assert padding>=2 and padding<=32
    parent={child:i for i,n in enumerate(doc['nodes'])for child in n.get('children',[])}
    nodes=[(i,n)for i,n in enumerate(doc['nodes'])if 'mesh'in n];assert nodes
    assert len({n.get('skin')for _,n in nodes})==1 and all('skin'in n for _,n in nodes),'One shared skin required'
    assert len({parent.get(i)for i,_ in nodes})==1,'Mesh nodes must have same parent'
    assert all(set(n)<= {'mesh','name','skin','extras'}for _,n in nodes),'Mesh-local transforms need explicit baking'
    assert all(c['target']['node']not in [i for i,_ in nodes]for a in doc.get('animations',[])for c in a['channels']),'Animated mesh nodes unsupported'
    parts=[];settings=None;all_arrays={};indices=[];cursor=0;index_cursor=0
    for node_i,node in nodes:
        mesh=doc['meshes'][node['mesh']];assert set(mesh)<= {'name','primitives','extras'}
        for surface,pr in enumerate(mesh['primitives']):
            assert pr.get('mode',4)==4 and set(pr)<= {'attributes','indices','material','mode'},'Triangle primitive without morph targets required'
            attrs={k:arrays(doc,binary,v)for k,v in pr['attributes'].items()}
            assert set(attrs)=={'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'},'Unexpected vertex semantic'
            assert all(not doc['accessors'][v].get('normalized',False)for v in pr['attributes'].values()),'Normalized attribute requires explicit decoding'
            assert np.isfinite(attrs['TEXCOORD_0']).all()
            mat=doc['materials'][pr['material']];current=material_settings(mat)
            if settings is None:settings=current
            assert settings==current,'Incompatible PBR/material settings'
            ids=arrays(doc,binary,pr['indices']).reshape(-1);count=len(attrs['POSITION'])
            assert ids.size%3==0 and ids.min()>=0 and ids.max()<count
            region=source_region(doc,binary,mat,attrs['TEXCOORD_0'],padding)
            part={'node_index':node_i,'node':node['name'],'surface':surface,'source_material':mat['name'],'source_alpha_mode':mat.get('alphaMode','OPAQUE'),'old_vertex_count':count,'new_vertex_range':[cursor,cursor+count],'new_index_range':[index_cursor,index_cursor+len(ids)],'triangles':len(ids)//3,'attributes':attrs,'source_indices':ids,'region':region}
            parts.append(part);indices.append(ids.astype('<u4')+cursor);cursor+=count;index_cursor+=len(ids)
    regions=[p['region']for p in parts];atlas=pack_regions(regions);ah,aw=atlas.shape[:2]
    max_pixel_error=0.;mismatch=0;compared=0
    rng=np.random.default_rng(163)
    for part in parts:
        region=part['region'];attrs=part['attributes'];uv=attrs['TEXCOORD_0'];xy=np.asarray(region['placement']);origin=np.asarray(region['origin']);size=np.asarray(region['source_size'])
        if region['constant']:new_uv=np.tile((xy+[padding+.5,padding+.5])/[aw,ah],(len(uv),1)).astype('<f4')
        else:new_uv=((uv.astype(np.float64)*size-origin+xy)/[aw,ah]).astype('<f4')
        part['new_uv']=new_uv
        for key,value in attrs.items():all_arrays.setdefault(key,[]).append(new_uv if key=='TEXCOORD_0'else value)
        if not region['constant']:
            # Actual triangle-interior sample reconstruction checks nearest texels,
            # not just atlas image copying. All source UVs remain affine.
            tri=part['source_indices'].reshape(-1,3);weights=rng.dirichlet([1,1,1],size=(len(tri),128))
            old=np.einsum('tbc,tcd->tbd',weights,uv[tri]).reshape(-1,2)
            new=np.einsum('tbc,tcd->tbd',weights,new_uv[tri]).reshape(-1,2)
            pixel_error=np.abs(new*[aw,ah]-(old*size-origin+xy));max_pixel_error=max(max_pixel_error,float(pixel_error.max()))
            old_idx=np.floor(old*size).astype(int);new_idx=np.floor(new*[aw,ah]).astype(int)
            src=region['source_pixels'];sx=wrap_indices(old_idx[:,0],size[0],region['wrap'][0]);sy=wrap_indices(old_idx[:,1],size[1],region['wrap'][1]);expected=src[sy,sx].copy()
            if part['source_alpha_mode']=='OPAQUE':expected[:,3]=255
            actual=atlas[new_idx[:,1],new_idx[:,0]];mismatch+=int(np.any(expected!=actual,axis=1).sum());compared+=len(actual)
    # Tiny address rounding near original nearest boundaries is quantified rather
    # than hidden. A systematic shift is always blocked, as is any >.001px error.
    assert max_pixel_error<.001,(max_pixel_error,'Atlas UV error')
    joined={k:np.concatenate(v)for k,v in all_arrays.items()};joined_ids=np.concatenate(indices)
    output.mkdir(parents=True,exist_ok=True);atlas_path=output/'atlas.png';encoded=io.BytesIO();Image.fromarray(atlas).save(encoded,format='PNG',optimize=True)
    atlas_bytes=encoded.getvalue();packed=copy.deepcopy(doc);packed['meshes']=[{'name':'Packed disconnected fish parts','primitives':[]}]
    for i,n in nodes:
        packed['nodes'][i].pop('mesh')
        if i==nodes[0][0]:packed['nodes'][i]['mesh']=0
        else:packed['nodes'][i].pop('skin',None)
    # Rebuild only referenced data; no duplicate old full-canvas images or dead
    # geometry streams remain in the candidate BIN.
    packed['bufferViews']=[];packed['accessors']=[];new_binary=bytearray();mapping={}
    def append_bytes(payload,target=None):
        new_binary.extend(b'\0'*((-len(new_binary))%4));v={'buffer':0,'byteOffset':len(new_binary),'byteLength':len(payload)}
        if target:v['target']=target
        idx=len(packed['bufferViews']);packed['bufferViews'].append(v);new_binary.extend(payload);return idx
    def append_array(value,descriptor,target=None):
        a=copy.deepcopy(descriptor);a.pop('byteOffset',None);a.pop('sparse',None);a['bufferView']=append_bytes(value.tobytes(),target);a['count']=len(value)
        idx=len(packed['accessors']);packed['accessors'].append(a);return idx
    def retain(index):
        if index not in mapping:mapping[index]=append_array(arrays(doc,binary,index),doc['accessors'][index])
        return mapping[index]
    for skin in packed.get('skins',[]):
        if 'inverseBindMatrices'in skin:skin['inverseBindMatrices']=retain(skin['inverseBindMatrices'])
    for animation in packed.get('animations',[]):
        for sampler in animation['samplers']:
            for k in ('input','output'):sampler[k]=retain(sampler[k])
    dtype_map={'float32':5126,'uint8':5121,'uint16':5123,'uint32':5125}
    attrs_out={}
    for key,value in joined.items():
        a={'componentType':dtype_map[value.dtype.name],'type':'VEC'+str(value.shape[1])}
        if key=='POSITION':a.update(min=value.min(axis=0).tolist(),max=value.max(axis=0).tolist())
        attrs_out[key]=append_array(value,a,34962)
    idx_out=append_array(joined_ids.reshape(-1,1),{'componentType':5125,'type':'SCALAR'},34963)
    packed['meshes'][0]['primitives']=[{'attributes':attrs_out,'indices':idx_out,'material':0}]
    packed['samplers']=[{'magFilter':9728,'minFilter':9728,'wrapS':33071,'wrapT':33071}]
    packed['textures']=[{'sampler':0,'source':0}];packed['images']=[{'name':'Native-pixel fish atlas','bufferView':append_bytes(atlas_bytes),'mimeType':'image/png'}]
    material=copy.deepcopy(settings);material.update(name='Packed fish native pixels',alphaMode='MASK',alphaCutoff=.5);material['pbrMetallicRoughness']['baseColorTexture']={'index':0}
    packed['materials']=[material];packed['extras']={'purpose':'Isolated one-material performance candidate; source checkpoint unchanged','source_model_sha256':before,'geometry_parts':[{'name':p['node'],'surface':p['surface'],'vertex_range':p['new_vertex_range'],'index_range':p['new_index_range']}for p in parts]}
    for label,alpha in [('merged-mask','MASK'),('merged-opaque','OPAQUE')]:
        packed['materials'][0]['alphaMode']=alpha
        if alpha=='OPAQUE':packed['materials'][0].pop('alphaCutoff',None)
        write_glb(output/(label+'.glb'),packed,new_binary)
    assert sha(model)==before,'Input changed'
    # Verify the written GLBs, including attributes and indexed part boundaries.
    candidate,cb=read_glb(output/'merged-mask.glb');q=candidate['meshes'][0]['primitives'][0]
    verified={k:arrays(candidate,cb,v)for k,v in q['attributes'].items()};new_indices=arrays(candidate,cb,q['indices']).reshape(-1)
    for part in parts:
        start,end=part['new_vertex_range'];si,ei=part['new_index_range']
        for key,value in part['attributes'].items():
            if key!='TEXCOORD_0':assert np.array_equal(verified[key][start:end],value),(part['node'],key)
        assert np.array_equal(new_indices[si:ei]-start,part['source_indices'])
    assert candidate['nodes']==packed['nodes']
    for old,new in zip(doc.get('animations',[]),candidate.get('animations',[])):
        assert old['channels']==new['channels']
        for a,b in zip(old['samplers'],new['samplers']):
            assert a.get('interpolation','LINEAR')==b.get('interpolation','LINEAR')
            for k in ('input','output'):assert np.array_equal(arrays(doc,binary,a[k]),arrays(candidate,cb,b[k]))
    for old,new in zip(doc['skins'],candidate['skins']):
        assert old['joints']==new['joints']
        if 'inverseBindMatrices'in old:assert np.array_equal(arrays(doc,binary,old['inverseBindMatrices']),arrays(candidate,cb,new['inverseBindMatrices']))
    opaque,ob=read_glb(output/'merged-opaque.glb');opaque_expected=copy.deepcopy(candidate);opaque_expected['materials'][0]['alphaMode']='OPAQUE';opaque_expected['materials'][0].pop('alphaCutoff',None)
    assert opaque==opaque_expected and ob==cb
    atlas_path.write_bytes(atlas_bytes)
    report={'ok':True,'kind':'native_pixel_single_material_candidate_packing','scope':'Isolated GLB experiment. No editable blend claim, no final fish acceptance, no installation. Native pixel data unresampled; finite FLOAT32 UV interpolation can differ only at quantified boundary-near samples.','input_model':str(model),'input_sha256':before,'builder_sha256':sha(__file__),'candidates':{name:{'path':str(output/(name+'.glb')),'sha256':sha(output/(name+'.glb'))}for name in ('merged-mask','merged-opaque')},'atlas':{'path':str(atlas_path),'sha256':sha(atlas_path),'size':[aw,ah],'padding_px':padding,'resampled':False},'surface_count_before':len(parts),'surface_count_after':1,'vertices':cursor,'triangles':len(joined_ids)//3,'bones':len({j for s in doc['skins']for j in s['joints']}),'checks':{'geometry_normals_joints_weights_exact':True,'directed_indices_exact':True,'animation_channels_sampling_exact':True,'inverse_bind_matrices_exact':True,'MASK_OPAQUE_differ_only_material_alpha_setting':True,'input_unchanged':True,'body_opaque_alpha_forced_in_atlas':True,'constant_color_baked_sRGB8_without_vertex_color_dependency':True},'nearest_sampling_probe':{'triangle_interior_samples':compared,'RGBA_mismatches':mismatch,'max_pixel_coordinate_error':max_pixel_error,'interpretation':'Floating point nearest-boundary probe; not a visual acceptance score. GPU view parity is independently required.'},'parts':[{'node':p['node'],'surface':p['surface'],'source_material':p['source_material'],'source_alpha_mode':p['source_alpha_mode'],'vertices':p['old_vertex_count'],'triangles':p['triangles'],'new_vertex_range':p['new_vertex_range'],'new_index_range':p['new_index_range'],'old_UV_min':p['attributes']['TEXCOORD_0'].min(axis=0).tolist(),'old_UV_max':p['attributes']['TEXCOORD_0'].max(axis=0).tolist(),'atlas_placement':p['region']['placement'],'virtual_crop_origin':p['region']['origin'],'virtual_crop_size':[p['region']['pixels'].shape[1],p['region']['pixels'].shape[0]],'source_size':p['region']['source_size'],'source_wrap':p['region']['wrap'],'source_RGBA_sha256':p['region']['source_rgba_sha256'],'constant_color_encoding':p['region'].get('constant_color_encoding')}for p in parts]}
    (output/'packing.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--padding',type=int,default=3);a=p.parse_args()
    r=build(a.model,a.output,a.padding);print(json.dumps({k:r[k]for k in ('ok','surface_count_before','surface_count_after','vertices','triangles','bones','atlas','nearest_sampling_probe')},ensure_ascii=False))

if __name__=='__main__':main()
