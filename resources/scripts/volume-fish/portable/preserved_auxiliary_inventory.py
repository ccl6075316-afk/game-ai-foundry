"""Narrow 077 inventory adapter: exact retained eyes/barbels over a complete body."""
import hashlib,json,sys,io
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from preserved_part_signatures import unpack
from glb_io import read_glb,arrays,sha

def digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()

def material_contract(material):
    result=dict(material);result.setdefault('alphaMode','OPAQUE');result.setdefault('alphaCutoff',.5);result.setdefault('doubleSided',False)
    return result

def sampler_contract(sampler):
    result=dict(sampler);result.setdefault('wrapS',10497);result.setdefault('wrapT',10497)
    return result

def contract(model):
    doc,blob=read_glb(model);parts=doc.get('extras',{}).get('geometry_parts');result={}
    images=[]
    for image in doc.get('images',[]):
        assert 'bufferView'in image and 'uri'not in image,'Embedded original texture identity required'
        view=doc['bufferViews'][image['bufferView']];start=view.get('byteOffset',0);rgba=Image.open(io.BytesIO(blob[start:start+view['byteLength']])).convert('RGBA')
        images.append(dict(size=list(rgba.size),rgba_sha256=hashlib.sha256(rgba.tobytes()).hexdigest()))
    def texture_contract(material):
        refs=[]
        for group,prefix in [(material,''),(material.get('pbrMetallicRoughness',{}),'pbrMetallicRoughness.')]:
            for name,ref in group.items():
                if name.endswith('Texture')and isinstance(ref,dict):
                    texture=doc['textures'][ref['index']];sampler=doc.get('samplers',[])[texture['sampler']]if 'sampler'in texture else {}
                    refs.append(dict(semantic=prefix+name,image=images[texture['source']],sampler=sampler_contract(sampler)))
        return sorted(refs,key=lambda r:r['semantic'])
    parents={c:i for i,n in enumerate(doc['nodes'])for c in n.get('children',[])}
    def chain(i):
        rows=[]
        while True:
            n=doc['nodes'][i];rows.append((n.get('name',''),{k:n.get(k)for k in ['translation','rotation','scale','matrix']}))
            if i not in parents:break
            i=parents[i]
        return rows
    rigs=[]
    for skin in doc['skins']:
        ib=arrays(doc,blob,skin['inverseBindMatrices'])
        rigs.append(sorted((doc['nodes'][j]['name'],chain(j),ib[k].tolist())for k,j in enumerate(skin['joints'])))
    for ni,node in enumerate(doc['nodes']):
        if 'mesh'not in node:continue
        for si,prim in enumerate(doc['meshes'][node['mesh']]['primitives']):
            if parts:
                groups=[((p['source_node'],int(p.get('source_surface',0))),p)for p in parts]
            else:groups=[((node['name'],si),None)]
            for key,part in groups:
                result[key]=dict(material=material_contract(doc['materials'][prim['material']]),referenced_textures=texture_contract(doc['materials'][prim['material']]),node_chain=chain(ni) if not parts else None,attributes=sorted(prim['attributes']),mode=prim.get('mode',4))
    return result,rigs

def auxiliary_proofs(plan,doc,blob):
    inventory=Path(plan['baseline_inventory']);assert inventory.is_absolute()and sha(inventory)==plan['baseline_inventory_sha256'],'Stale explicit baseline inventory'
    baseline=next(r for r in json.loads(inventory.read_text())['fish']if r['species']==plan['species'])
    expected_baseline_path=baseline['model']['path']
    if plan.get('baseline_snapshot_path'):
        expected_baseline_path=str(Path(plan['baseline_snapshot_root'])/plan['species']/'baseline.glb')
        assert plan['baseline_snapshot_path']==expected_baseline_path,'Unapproved baseline snapshot location'
    assert plan['baseline_model']==expected_baseline_path and plan['baseline_model_sha256']==baseline['model']['sha256']==sha(plan['baseline_model']), 'Incorrect or stale canonical baseline identity'
    finpath=Path(plan['fin_inventory_plan']);assert sha(finpath)==plan['fin_inventory_plan_sha256'],'Stale complete fin inventory'
    fin=json.loads(finpath.read_text())['items'][0]
    assert fin['model']==plan['model'] and fin['model_sha256']==plan['model_sha256'] and plan['body']==fin['body']=='Closed_body' and set(plan['fins'])==set(fin['fins']), 'Body/complete fin inventory altered'
    old=unpack(plan['baseline_model']);new=unpack(plan['model']);oc,orig_rig=contract(plan['baseline_model']);nc,new_rig=contract(plan['model'])
    serialization=None
    if plan.get('weight_serialization_proof'):
        proofpath=Path(plan['weight_serialization_proof']);assert sha(proofpath)==plan['weight_serialization_proof_sha256'],'Stale weight serialization proof'
        proof=json.loads(proofpath.read_text());assert proof['ok'];serialization=next(r for r in proof['records']if r['species']==plan['species'])
        assert serialization['baseline_model']==baseline['model'] and serialization['candidate_model']==dict(path=plan['model'],sha256=plan['model_sha256']),'Wrong frozen weight-serialization SHA pair'
        source=serialization['source_identity'];assert serialization['candidate_weights_exactly_predicted']and source['all_body_and_eye_source_vertex_groups_and_positions_exact']and source['baseline_mesh_signatures']==source['current_mesh_signatures']
        baseline_source=source['baseline_source']
        if plan.get('baseline_source_snapshot_path'):
            assert plan['baseline_source_snapshot_path']==str(Path(plan['baseline_snapshot_root'])/plan['species']/'baseline.blend'),'Unapproved baseline source snapshot location'
            baseline_source=dict(path=plan['baseline_source_snapshot_path'],sha256=baseline_source['sha256'])
        for ref in [baseline_source,source['current_source'],serialization['source_identity_report']]:assert sha(ref['path'])==ref['sha256'],'Stale exact source-group evidence'
        assert all(sha(p)==h for p,h in serialization['stock_exporter_dependencies'].items()),'Stock weight serialization changed'
    def static_match(key):
        a=old['parts'][key];b=new['parts'][key]
        if Counter(a)==Counter(b):return True
        assert serialization is not None,'Unexpected static attribute change without source-preserved export proof'
        proof=next((r for r in serialization['parts']if (r['name'],r['surface'])==key),None);assert proof and proof['geometry_normal_UV_directed_incidence_exact'],'No exact nonweight geometry proof'
        assert digest(sorted(a))==proof['original_weighted_directed_signature']and digest(sorted(b))==proof['candidate_weighted_directed_signature'],'Different weight bytes from the independently explained frozen export'
        geom=lambda faces:Counter(min(tuple(v[:3]for v in f),tuple(v[:3]for v in f[1:]+f[:1]),tuple(v[:3]for v in f[2:]+f[:2]))for f in faces)
        assert geom(a)==geom(b),'Geometry, normals, UV or directed topology changed'
        return False
    assert set(old['parts'])==set(new['parts']), 'Baseline/candidate complete surface inventory differs'
    assert old['rig']==new['rig'] and orig_rig==new_rig, 'Rig rests, hierarchy or inverse binds changed'
    assert old['animation']==new['animation'], 'Native animation changed'
    assert [material_contract(m)for m in old['materials']]==[material_contract(m)for m in new['materials']] and [sampler_contract(v)for v in old['samplers']]==[sampler_contract(v)for v in new['samplers']], 'Actual material/sampler contract changed'
    noncaudal_texture_proof=[]
    for key in sorted(old['parts']):
        if 'caudal'in key[0].lower():continue
        assert oc[key]['referenced_textures']==nc[key]['referenced_textures'],'Actual non-tail referenced RGBA/sampler changed: '+str(key)
        noncaudal_texture_proof.append(dict(part=list(key),referenced_textures=oc[key]['referenced_textures']))
    overlays=plan.get('decorative_overlays',{});proofs=[]
    for name,definition in overlays.items():
        assert definition==dict(kind='unchanged_baseline_auxiliary',underlying_body=plan['body'],baseline_name=name), 'Incorrect auxiliary baseline identity or unsupported declaration'
        assert ('eye'in name.lower() or 'barbel'in name.lower()) and name not in [plan['body'],*plan['fins']], 'Only explicit existing eye/barbel auxiliaries supported'
        node=next(n for n in doc['nodes']if n.get('name')==name and 'mesh'in n);assert 'skin'in node
        bones=[doc['nodes'][j]['name']for j in doc['skins'][node['skin']]['joints']];used=set();triangles=0
        for prim in doc['meshes'][node['mesh']]['primitives']:
            attrs=prim['attributes'];assert set(attrs)=={'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'},'Unexpected auxiliary attribute requires explicit proof'
            p=arrays(doc,blob,attrs['POSITION']);n=arrays(doc,blob,attrs['NORMAL']);uv=arrays(doc,blob,attrs['TEXCOORD_0']);w=arrays(doc,blob,attrs['WEIGHTS_0']);j=arrays(doc,blob,attrs['JOINTS_0']);tri=arrays(doc,blob,prim['indices']).reshape(-1,3)
            assert prim.get('mode',4)==4 and len(p)>0 and len(tri)>0 and np.isfinite(p).all() and np.isfinite(n).all() and np.isfinite(uv).all() and np.isfinite(w).all(), 'Empty or nonfinite auxiliary arrays'
            assert n.shape==p.shape and uv.shape==(len(p),2) and j.shape==w.shape==(len(p),4) and np.all(abs(np.linalg.norm(n,axis=1)-1)<1e-5), 'Incomplete auxiliary attributes'
            assert np.all(w>=0) and np.all(abs(w.sum(axis=1)-1)<1e-5) and j.min()>=0 and j.max()<len(bones), 'Invalid effective auxiliary skin support'
            assert tri.min()>=0 and tri.max()<len(p) and np.all(np.linalg.norm(np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]]),axis=1)>0), 'Invalid auxiliary oriented triangles'
            used.update(bones[int(jj)]for jr,wr in zip(j,w)for jj,ww in zip(jr,wr)if ww>0);triangles+=len(tri)
        keys=sorted(k for k in old['parts']if k[0]==name);assert keys and keys==sorted(k for k in new['parts']if k[0]==name),'Missing auxiliary surface identity'
        signatures=[]
        for key in keys:
            exact=static_match(key);assert oc[key]==nc[key], 'Auxiliary material/texture/node binding changed: '+name
            signatures.append(dict(surface=key[1],triangles=len(old['parts'][key]),baseline_signature=digest(sorted(old['parts'][key])),candidate_signature=digest(sorted(new['parts'][key])),weights_byte_exact=exact))
        assert sum(r['triangles']for r in signatures)==triangles,'Auxiliary inventory triangle count differs'
        proofs.append(dict(name=name,kind=definition['kind'],underlying_body=plan['body'],triangles=triangles,effective_bones=sorted(used),geometry_normal_UV_and_directed_triangles_exact=True,all_emitted_weights_byte_exact=all(r['weights_byte_exact']for r in signatures),surfaces=signatures))
    bodykeys=sorted(k for k in old['parts']if k[0]==plan['body'])
    assert len(bodykeys)==plan['expected_body_surfaces'] and bodykeys==sorted(k for k in new['parts']if k[0]==plan['body']),'Complete baseline body surface inventory differs'
    bodyproof=[]
    for key in bodykeys:
        exact=static_match(key);assert oc[key]==nc[key],'Underlying complete body material/texture/node binding changed'
        bodyproof.append(dict(surface=key[1],triangles=len(old['parts'][key]),unique_attribute_vertices=len(set(v for t in old['parts'][key]for v in t)),baseline_static_signature=digest(sorted(old['parts'][key])),candidate_static_signature=digest(sorted(new['parts'][key])),weights_byte_exact=exact,material_and_node_contract_signature=digest(oc[key])))
    assert set(k[0]for k in old['parts'])=={plan['body'],*plan['fins'],*overlays},'An original body/fin/auxiliary part was omitted'
    return dict(auxiliaries=proofs,body_surfaces=bodyproof,weight_serialization_evidence=serialization,baseline_model=plan['baseline_model'],baseline_model_sha256=plan['baseline_model_sha256'],candidate_model_sha256=plan['model_sha256'],rig_and_hierarchy_signature=digest((old['rig'],orig_rig)),animation_signature=digest(old['animation']),materials_and_samplers_signature=digest(([material_contract(m)for m in old['materials']],[sampler_contract(v)for v in old['samplers']])),raw_baseline_material_signature=digest(old['materials']),raw_candidate_material_signature=digest(new['materials']),material_default_equivalence='Only missing alphaMode=OPAQUE, alphaCutoff=0.5, doubleSided=false and sampler wrapS/wrapT=10497 are expanded. Actual min/mag filtering and every other field must match exactly.',embedded_texture_signatures=old['textures'],candidate_embedded_texture_signatures=new['textures'],full_embedded_texture_set_exact=old['textures']==new['textures'],all_noncaudal_referenced_texture_proofs=noncaudal_texture_proof,texture_scope='Every actual non-tail surface reference, including the complete body and all auxiliaries, resolves to exactly equal full RGBA payload and sampler. Tail-only image edits do not exempt any body or auxiliary donor.',retention='Signatures preserve the checked historical comparison, not a claim that the canonical baseline path remains replayable after installation. No old GLB package duplicated.')
