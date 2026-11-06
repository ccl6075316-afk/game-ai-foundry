"""Compare actual retained parts across a tail-only source export.

This measures unchanged parts and dependencies. It grants no physical/visual pass.
"""
import sys,json,hashlib,io
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image
from glb_io import read_glb,arrays,sha
def unpack(path):
    d,b=read_glb(path);records={};textures=[]
    for image in d.get('images',[]):
        if 'bufferView'in image:
            view=d['bufferViews'][image['bufferView']];raw=b[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
            im=Image.open(io.BytesIO(raw)).convert('RGBA');textures.append({'size':im.size,'rgba_sha256':hashlib.sha256(im.tobytes()).hexdigest()})
    parts=d.get('extras',{}).get('geometry_parts')
    for node in d['nodes']:
        if 'mesh'not in node:continue
        skin=d['skins'][node['skin']];bones=[d['nodes'][i].get('name',str(i))for i in skin['joints']]
        for surface,p in enumerate(d['meshes'][node['mesh']]['primitives']):
            attrs={k:arrays(d,b,v)for k,v in p['attributes'].items()};faces=arrays(d,b,p['indices']).reshape(-1,3)
            groups=[]
            if parts:
                groups=[((part['source_node'],int(part.get('source_surface',0))),faces[part['index_start']//3:(part['index_start']+part['index_count'])//3],part['role'])for part in parts]
            else:groups=[((node.get('name',''),surface),faces,'fin'if any(k in node.get('name','')for k in ['Caudal','Dorsal','Anal','Pectoral','Pelvic','Adipose'])else 'other')]
            for key,fs,role in groups:
                rows={}
                for i in np.unique(fs):
                    weight={}
                    for slot,w in zip(attrs.get('JOINTS_0',[])[i],attrs.get('WEIGHTS_0',[])[i]):
                        if w>0:weight[bones[int(slot)]]=weight.get(bones[int(slot)],0.)+float(w)
                    rows[int(i)]=(tuple(float(x)for x in attrs['POSITION'][i]),tuple(float(x)for x in attrs.get('NORMAL',np.zeros_like(attrs['POSITION']))[i]),tuple(float(x)for x in attrs['TEXCOORD_0'][i]),tuple(sorted(weight.items())))
                face_rows=[]
                for f in fs:
                    tri=tuple(rows[int(i)]for i in f);face_rows.append(min(tri,tri[1:]+tri[:1],tri[2:]+tri[:2]))
                records.setdefault(key,[]).extend(face_rows)
    rig=[]
    for skin in d.get('skins',[]):
        ib=arrays(d,b,skin['inverseBindMatrices'])
        rig.append([(d['nodes'][i].get('name',''),tuple(ib[k]),{a:d['nodes'][i].get(a)for a in ['translation','rotation','scale','matrix']})for k,i in enumerate(skin['joints'])])
    anim=[]
    for clip in d.get('animations',[]):
        channels=[]
        for ch in clip['channels']:
            s=clip['samplers'][ch['sampler']];target=ch['target'];channels.append((d['nodes'][target['node']].get('name',''),target['path'],s.get('interpolation','LINEAR'),arrays(d,b,s['input']).tobytes().hex(),arrays(d,b,s['output']).tobytes().hex()))
        anim.append((clip.get('name',''),sorted(channels)))
    return {'parts':records,'rig':repr(rig),'animation':repr(anim),'textures':textures,'materials':d.get('materials'),'samplers':d.get('samplers'),'triangles':sum(sum(len(x)for x in [v])for v in records.values())}
