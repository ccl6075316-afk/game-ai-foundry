"""The standalone branch of 077: full exported model, no installed factory.

Plan paths are absolute. Required keys: species, model/model_sha256, body, fins,
motion_profile/motion_profile_sha256, motion_runtime/motion_runtime_sha256,
frozen_inputs (absolute path -> SHA256), expected_triangles/body_surfaces.
The plan cannot exempt body surfaces or relax the zero-missing-pixel gate.
"""
import hashlib, io, json, subprocess
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from freeze_surface_ownership import read_glb, accessor


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_inputs(plan):
    inputs=dict(plan['frozen_inputs'])
    for key in ['model','motion_profile','motion_runtime']:
        path=Path(plan[key]);assert path.is_absolute(), 'Plan paths must be absolute'
        expected=plan[key+'_sha256']
        assert str(path) not in inputs or inputs[str(path)]==expected, 'Conflicting frozen hash'
        inputs[str(path)]=expected
    if plan.get('packed_parts_manifest'):
        inputs[plan['packed_parts_manifest']]=plan['packed_parts_manifest_sha256']
    assert inputs and all(Path(p).is_absolute() and sha(p)==h for p,h in inputs.items()), 'Stale standalone dependency'
    return inputs


def inspect_model(plan):
    packed=bool(plan.get('packed_parts_manifest'))
    opacity=None
    if packed:
        from packed_fish_parts import logical_document
        assert sha(plan['packed_parts_manifest'])==plan['packed_parts_manifest_sha256'], 'Stale packed partition manifest'
        canonical=json.loads(Path(plan['packed_parts_manifest']).read_text());assert canonical['model_sha256']==sha(plan['model'])
        doc,blob,opacity=logical_document(plan['model'],plan['body'],plan['fins'])
    else:doc,blob=read_glb(Path(plan['model']))
    mesh_nodes=[n for n in doc['nodes'] if 'mesh' in n]
    assert len(plan['fins'])==7 and len(set(plan['fins']))==7 and plan['body'] not in plan['fins'], 'Explicit seven-fin inventory required'
    assert {n['name'] for n in mesh_nodes}=={plan['body'],*plan['fins']} and len(mesh_nodes)==8, 'Unexpected/empty body or fin inventory'
    bodies=[n for n in mesh_nodes if n['name']==plan['body']];assert len(bodies)==1
    body=bodies[0];assert 'skin' in body and doc.get('skins') and doc.get('animations'), 'Missing actual rig/animation'
    primitives=doc['meshes'][body['mesh']]['primitives'];assert len(primitives)==plan['expected_body_surfaces']>0
    edges=Counter();directions=Counter();surfaces=[];triangle_count=0
    for node in mesh_nodes:
        for prim in doc['meshes'][node['mesh']]['primitives']:
            assert prim.get('mode',4)==4, 'Non-triangle primitive'
            triangle_count+=len(accessor(doc,blob,prim['indices']))//3
    assert triangle_count==plan['expected_triangles'] and triangle_count>0, 'Unexpected complete model triangle count'
    for si,prim in enumerate(primitives):
        attrs=prim['attributes'];assert {'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'}<=attrs.keys(), 'Incomplete skinned body arrays'
        pos=accessor(doc,blob,attrs['POSITION']);normal=accessor(doc,blob,attrs['NORMAL']);tri=accessor(doc,blob,prim['indices']).reshape(-1,3)
        assert len(pos)>0 and len(tri)>0 and normal.shape==pos.shape and np.isfinite(pos).all() and np.isfinite(normal).all(), 'Empty/nonfinite body arrays'
        normal_lengths=np.linalg.norm(normal,axis=1)
        assert np.all(np.abs(normal_lengths-1)<1e-5), 'Nonunit/zero body normal'
        assert tri.min()>=0 and tri.max()<len(pos), 'Body index out of range'
        for key in ['TEXCOORD_0','WEIGHTS_0']:
            values=accessor(doc,blob,attrs[key]);assert len(values)==len(pos) and np.isfinite(values).all(), 'Invalid body '+key
        weights=accessor(doc,blob,attrs['WEIGHTS_0']);joints=accessor(doc,blob,attrs['JOINTS_0'])
        assert joints.shape==weights.shape==(len(pos),4), 'Skin attribute counts differ'
        assert np.all(weights>=0) and np.all(np.abs(weights.sum(axis=1)-1)<1e-5) and joints.max()<len(doc['skins'][body['skin']]['joints']), 'Invalid skin weights/joints'
        pts=[tuple(round(float(x),7) for x in v) for v in pos]
        area=np.linalg.norm(np.cross(pos[tri[:,1]]-pos[tri[:,0]],pos[tri[:,2]]-pos[tri[:,0]]),axis=1)
        assert np.all(area>0), 'Zero-area body triangle'
        face_normals=np.cross(pos[tri[:,1]]-pos[tri[:,0]],pos[tri[:,2]]-pos[tri[:,0]])
        assert np.all(np.sum(face_normals*normal[tri].mean(axis=1),axis=1)>0), 'Body normals disagree with winding'
        for face in tri:
            q=[pts[x] for x in face];assert len(set(q))==3, 'Degenerate welded body triangle'
            for x,y in zip(q,q[1:]+q[:1]):
                edge=tuple(sorted([x,y]));edges[edge]+=1;directions[edge]+=1 if x<y else -1
        mat=doc['materials'][prim['material']];pbr=mat.get('pbrMetallicRoughness',{})
        assert (mat.get('alphaMode','OPAQUE') in ('OPAQUE','MASK') if packed else mat.get('alphaMode','OPAQUE')=='OPAQUE') and pbr.get('baseColorFactor',[1,1,1,1])[3]==1, 'Nonopaque body material'
        if packed:assert opacity['ok'], 'Packed body sampled regions must all be opaque'
        # Specular controls shading only; transmission/volume/custom extensions
        # would need their own opacity semantics and are not silently accepted.
        assert set(mat.get('extensions',{}))<={'KHR_materials_specular'}, 'Unsupported body material extension'
        texture=pbr.get('baseColorTexture');image_info=None
        if texture is not None:
            tex=doc['textures'][texture['index']];image=doc['images'][tex['source']]
            assert 'bufferView' in image and 'uri' not in image, 'Body donor must be embedded'
            view=doc['bufferViews'][image['bufferView']];start=view.get('byteOffset',0);raw=blob[start:start+view['byteLength']]
            rgba=np.array(Image.open(io.BytesIO(raw)).convert('RGBA'));assert rgba.size and (opacity['ok'] if packed else np.all(rgba[:,:,3]==255)), 'Transparent embedded body donor'
            image_info={'embedded_sha256':hashlib.sha256(raw).hexdigest(),'rgba_sha256':hashlib.sha256(rgba.tobytes()).hexdigest(),'size':[rgba.shape[1],rgba.shape[0]]}
        surfaces.append({'surface':si,'triangles':len(tri),'vertices':len(pos),'material':mat.get('name',''),'opaque':True,'unit_normals_and_winding_agree':True,'texture':image_info})
    assert edges and all(n==2 for n in edges.values()), 'Open/nonmanifold welded body'
    assert all(n==0 for n in directions.values()), 'Inconsistent body winding'
    return {'triangles':triangle_count,'welded_edges':len(edges),'surfaces':surfaces,**({'packed_body_opacity':opacity,'analysis_projection_only':True} if packed else {})}


def missing_pixels(actual,reference):
    x=np.array(Image.open(actual).convert('RGBA'));y=np.array(Image.open(reference).convert('RGBA'))
    assert x.shape==y.shape, 'Coverage image dimensions differ'
    mask=y[:,:,3]>128;assert mask.sum()>30, 'Empty reference body'
    return int((mask&(x[:,:,3]<128)).sum())


def validate(game,godot,plan_path,output):
    output.mkdir(parents=True,exist_ok=True);result={'ok':False,'kind':'standalone_body_integrity_077','formal_acceptance':False};capture=Path(__file__).with_name('capture_standalone_body.gd')
    validation_dependencies={str(p.resolve()):sha(p) for p in [Path(__file__),capture,Path(__file__).with_name('freeze_surface_ownership.py'),Path(__file__).with_name('validate_body_integrity.py')]}
    try:
        plan=json.loads(plan_path.read_text());inputs=frozen_inputs(plan);geometry=inspect_model(plan)
        if plan.get('packed_parts_manifest'):
            for dependency in [Path(__file__).with_name('packed_fish_parts.py'),Path(__file__).with_name('PackedFishValidation.gd')]:validation_dependencies[str(dependency.resolve())]=sha(dependency)
        receipt=output/'capture.validation.json'
        if receipt.exists():receipt.unlink()
        run=subprocess.run([str(godot),'--path',str(game),'--log-file',str(output/'godot.log'),'--rendering-method','gl_compatibility','--script',str(capture),'--',str(plan_path),str(output)],capture_output=True,text=True,timeout=180)
        log=run.stdout+run.stderr;(output/'capture.log').write_text(log)
        assert run.returncode==0 and 'ERROR:' not in log and receipt.exists(), 'Standalone GPU capture failed'
        data=json.loads(receipt.read_text());assert data['model_sha256']==plan['model_sha256'] and data['plan_sha256']==sha(plan_path), 'Stale GPU capture'
        assert data['frozen_inputs']==inputs and data['body']==plan['body'], 'Runtime bindings differ'
        actual_materials=data['motion']['materials'];assert len(actual_materials)==len(geometry['surfaces']), 'Actual material count differs'
        for expected,actual in zip(geometry['surfaces'],actual_materials):
            assert expected['surface']==actual['surface'], 'Actual surface order differs'
            assert actual['texture']==bool(expected['texture']), 'Actual body texture binding differs'
            if expected['texture']:assert actual['rgba_sha256']==expected['texture']['rgba_sha256'], 'Actual GPU donor RGBA differs from embedded model'
        assert len(data['records'])==16 and {(r['pose'],r['view']) for r in data['records']}=={(p,v) for p in range(2) for v in range(8)}, 'Incomplete coverage inventory'
        for row in data['records']:
            assert row['pose_before']==row['pose_after'] and row['camera_before']==row['camera_after'], 'Actual/reference pose or camera differs'
            for key in ['actual','reference']:assert sha(output/row[key])==row[key+'_sha256'], 'Changed capture image'
            row['missing_body_pixels']=missing_pixels(output/row['actual'],output/row['reference'])
        negative=data['negative'];assert sha(output/negative['actual'])==negative['actual_sha256'], 'Changed negative image'
        negative['missing_body_pixels']=missing_pixels(output/negative['actual'],output/negative['reference'])
        assert negative['missing_body_pixels']>0, 'Transparent material negative control was not rejected'
        assert frozen_inputs(plan)==inputs, 'Standalone dependency changed during capture'
        assert all(sha(p)==h for p,h in validation_dependencies.items()), 'Validation helper changed during capture'
        assert data['records'][0]['pose_before']!=data['records'][8]['pose_before'], 'Maximum-motion pose did not change actual rig'
        result.update(ok=all(r['missing_body_pixels']==0 for r in data['records']),model_sha256=plan['model_sha256'],species=plan['species'],geometry=geometry,records=data['records'],negative_control=negative,frozen_inputs=inputs,motion=data['motion'],method='Welded closed body, opaque embedded donors; exact same posed body with opaque double-sided reference, zero missing pixels. No mouth exemption.',limits='Two discrete poses, eight views each; maximum amplitude control at one declared runtime phase, not exhaustive continuous coverage.')
    except Exception as error:result['error']=str(error)
    result.update(plan_sha256=sha(plan_path),checker_sha256=sha(__file__),capture_script_sha256=sha(capture),validation_dependencies=validation_dependencies)
    (output/'completion.validation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
