"""Restore a side-art caudal plane while retaining the complete attached base.

Refine in source space before narrowing the attachment transition. All original
basal vertices and their weights survive; new basal midpoints extend the frozen
selection. Source pixels, other meshes, rig and animation buffers are untouched.
"""
import argparse, copy, hashlib, json
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb, accessor
from patch_existing_fin_meshes import write
from subdivide_fin_contact import refine

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def repair(spec, profile, output, spacing=.006, collar=.006):
    source=Path(spec['model']); assert sha(source)==spec['model_sha256']
    d,blob=read_glb(source); before=copy.deepcopy(d); binary=bytearray(blob)
    node=next(n for n in d['nodes'] if n.get('name')=='Caudal' and 'mesh' in n)
    mesh=d['meshes'][node['mesh']]; assert len(mesh['primitives'])==1
    prim=mesh['primitives'][0]; attrs={k:accessor(d,blob,a) for k,a in prim['attributes'].items()}
    original=attrs['POSITION'].copy(); roots=np.asarray(spec['fins']['Caudal']['rest_points_gltf'])
    selected=np.min(np.linalg.norm(original[:,None]-roots[None],axis=2),axis=1)<spec['length_native']*.00002
    assert selected.sum()==len(roots), 'Complete original root selection must resolve uniquely'
    aspect=profile['source_aspect_ratio']; baseline=np.asarray(spec['fins']['Caudal']['source_baseline'])
    assert np.ptp(baseline[:,0])<1e-7, 'This posterior caudal method needs a vertical source baseline'
    base_x=float(baseline[0,0])
    rows=[]
    for i in range(len(original)):
        r={k:tuple(a[i]) for k,a in attrs.items()};r['root']=bool(selected[i]);r['_OLD']=r['POSITION']
        u,v=r['TEXCOORD_0'];r['POSITION']=(u-.5,(.5-v)/aspect,r['POSITION'][2]);rows.append(r)
    triangles=[tuple(map(int,t)) for t in accessor(d,blob,prim['indices']).reshape(-1,3)]
    rows,triangles,refinement=refine(rows,triangles,spacing,lambda p:True)
    for r in rows:
        p=np.array(r['POSITION']);old=np.array(r['_OLD'])
        distance=max(0.,base_x-r['TEXCOORD_0'][0]);t=np.clip(distance/collar,0,1);gain=t*t*(3-2*t)
        r['POSITION']=tuple(old if r['root'] else old*(1-gain)+p*gain)
        # A single continuous side-art chart; no stretched old broad collar.
        x,y,z=r['POSITION'];r['TEXCOORD_0']=(x+.5,.5-y*aspect)
    positions=np.asarray([r['POSITION'] for r in rows]);faces=np.asarray(triangles)
    normals=np.zeros_like(positions);face_normals=np.cross(positions[faces[:,1]]-positions[faces[:,0]],positions[faces[:,2]]-positions[faces[:,0]])
    assert np.min(np.linalg.norm(face_normals,axis=1))>1e-13,'Degenerate repaired triangle'
    for j in range(3):np.add.at(normals,faces[:,j],face_normals)
    normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-20)
    for r,n in zip(rows,normals):r['NORMAL']=tuple(n)
    def append(source_index,values):
        a=copy.deepcopy(d['accessors'][source_index]);dt={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]
        if a['type']=='SCALAR' and np.max(values)>65535:a['componentType']=5125;dt='<u4'
        values=np.asarray(values,dtype=dt);binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(values.tobytes())
        a.update(bufferView=len(d['bufferViews']),byteOffset=0,count=len(values));a.pop('min',None);a.pop('max',None)
        if a['type']=='VEC3':a.update(min=values.min(axis=0).tolist(),max=values.max(axis=0).tolist())
        d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':values.nbytes,'target':34963 if a['type']=='SCALAR' else 34962});d['accessors'].append(a);return len(d['accessors'])-1
    for k,a in list(prim['attributes'].items()):prim['attributes'][k]=append(a,[r[k] for r in rows])
    prim['indices']=append(prim['indices'],faces.reshape(-1,1))
    assert np.array_equal(positions[:len(original)][selected],original[selected])
    for i,m in enumerate(before['meshes']):
        if i!=node['mesh']:assert m==d['meshes'][i]
    for key in ['nodes','skins','animations','images','materials','textures']:assert before[key]==d[key]
    assert binary[:len(blob)]==blob
    output.mkdir(parents=True,exist_ok=True);dest=output/'fish.glb';write(dest,d,binary)
    report={'ok':True,'source':str(source),'source_sha256':sha(source),'output_sha256':sha(dest),'original_roots_preserved':int(selected.sum()),'complete_root_selection_retained':True,'noncaudal_meshes_rig_images_materials_animations_identical':True,'refinement':refinement,'transition_native':collar,'source_chart':'u=x+.5; v=.5-y*aspect','vertices':len(rows),'triangles':len(triangles)}
    root_ids=[i for i,r in enumerate(rows) if r['root']]
    spec=copy.deepcopy(spec);spec.update(model=str(dest.resolve()),model_sha256=sha(dest))
    spec['fins']['Caudal'].update(ids=root_ids,rest_points_gltf=positions[root_ids].tolist(),vertices=len(rows))
    (output/'repair.validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return spec,report

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--parameters',type=Path,default=Path(__file__).resolve().parents[2]/'volume-fish/hammer-caudal-source.json');a=p.parse_args()
    items=[];reports=[];repo=Path(__file__).resolve().parents[3];settings=json.loads(a.parameters.read_text(encoding='utf8'))['species']
    for spec in json.loads(a.plan.read_text(encoding='utf8'))['items']:
        if spec['species'] not in settings:continue
        option=settings[spec['species']]
        assert spec['model_sha256']==option['baseline_model_sha256'],'Unreviewed caudal baseline'
        profile=json.loads((repo/'resources/volume-fish'/f"{spec['species'].replace('_','-')}-121.profile.json").read_text(encoding='utf8'))
        item,report=repair(spec,profile,a.output/spec['species'],option['source_edge_spacing_native'],option['attachment_transition_native']);items.append(item);reports.append(report)
    (a.output/'candidate.plan.json').write_text(json.dumps({'items':items},indent=2),encoding='utf8');print(json.dumps(reports))
if __name__=='__main__':main()
