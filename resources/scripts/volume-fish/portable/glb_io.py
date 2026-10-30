"""Strict GLB/accessor readers shared with Blender preflight (no image dependency)."""
if not __debug__:
    raise RuntimeError('Optimized Python is unsupported: required validation assertions are disabled')

import hashlib
import json
from pathlib import Path
import struct
import numpy as np

DTYPES={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}
LANES={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read_glb(path):
    return read_glb_snapshot(path)[:2]

def read_glb_snapshot(path):
    raw = Path(path).read_bytes()
    doc, binary = parse_glb_bytes(raw)
    return doc, binary, hashlib.sha256(raw).hexdigest()

def parse_glb_bytes(raw):
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


def validate_skin_attributes(doc, binary, primitive, joint_count):
    """Reject invalid raw slots before named effective-weight comparison."""
    attrs = primitive['attributes']
    joints = arrays(doc, binary, attrs['JOINTS_0'])
    weights = arrays(doc, binary, attrs['WEIGHTS_0'])
    count = doc['accessors'][attrs['POSITION']]['count']
    if joints.shape != (count, 4) or weights.shape != (count, 4):
        raise ValueError('Skin attributes require four slots per source vertex')
    if not (np.isfinite(joints).all() and np.isfinite(weights).all()):
        raise ValueError('Nonfinite skin attributes')
    if joint_count <= 0 or not ((joints >= 0).all() and (joints < joint_count).all() and (joints == np.floor(joints)).all()):
        raise ValueError('Joint indices must be nonnegative integers within the skin')
    if not (weights >= 0).all() or not (np.abs(weights.sum(axis=1) - 1) < 1e-5).all():
        raise ValueError('Skin weights must be nonnegative and normalized within 1e-5')


def material_semantics(d):
    assert len(d['materials'])==1 and len(d['textures'])==1 and len(d['images'])==1
    m=d['materials'][0]
    assert set(m)<={'name','pbrMetallicRoughness','alphaMode','alphaCutoff','doubleSided','extensions','emissiveFactor'},'Unsupported packed material feature'
    assert m.get('extensions',{}) in ({},{'KHR_materials_specular':{'specularFactor':0}}),'Unsupported material extension'
    p=m.get('pbrMetallicRoughness',{})
    assert set(p)<={'baseColorTexture','baseColorFactor','roughnessFactor','metallicFactor'},'Unsupported material map'
    t=p['baseColorTexture']
    assert set(t)<={'index','texCoord'},'Unsupported texture mapping'
    tex=d['textures'][t['index']];sampler=d['samplers'][tex.get('sampler',0)]
    return {'alphaMode':m.get('alphaMode','OPAQUE'),'alphaCutoff':m.get('alphaCutoff',.5),'doubleSided':m.get('doubleSided',False),'roughnessFactor':p.get('roughnessFactor',1),'metallicFactor':p.get('metallicFactor',1),'baseColorFactor':p.get('baseColorFactor',[1,1,1,1]),'texture_texCoord':t.get('texCoord',0),'magFilter':sampler.get('magFilter',9729),'minFilter':sampler.get('minFilter',9729),'wrapS':sampler.get('wrapS',10497),'wrapT':sampler.get('wrapT',10497),'specularFactor':m.get('extensions',{}).get('KHR_materials_specular',{}).get('specularFactor',1),'emissiveFactor':m.get('emissiveFactor',[0,0,0])}
