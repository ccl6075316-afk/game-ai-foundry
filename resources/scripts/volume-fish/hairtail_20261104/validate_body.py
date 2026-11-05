"""Hairtail-only auxiliary inventory for standalone 077. No runtime factory.

The body inspector below retains the upstream body guards. Only the auxiliary
branch differs: two explicitly closed mixed-skin eyes and six closed tooth
components, never relabelled as rigid lenses/fins. GPU capture uses original GLB.
This gate does not prove dynamic attachment of eyes/teeth.
"""
import argparse
import subprocess
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
PORTABLE=HERE.parent/'portable'
sys.path[:0]=[str(PORTABLE),str(HERE.parent)]
import validate_standalone_body as base
from freeze_surface_ownership import read_glb,accessor
sha=base.sha
frozen_inputs=base.frozen_inputs
missing_pixels=base.missing_pixels
EXPECTED_BODY='Hairtail_Ribbon_Body'
EXPECTED_FINS={'Hairtail_Continuous_Dorsal','Hairtail_Pectoral_Far','Hairtail_Pectoral_Near'}
EXPECTED_AUX={**{f'Eye_native_{s}':'closed_mixed_skin_eye_lens' for s in [-1,1]},
              **{f'Oral_tooth_{s}_{i}':'closed_mixed_skin_upper_tooth' for s in [-1,1] for i in range(3)}}


def opaque_triangle_pixels(rgba,uv,triangles):
    """Conservative triangle/pixel-cell SAT, including exact edge contacts."""
    height,width=rgba.shape[:2]
    assert np.isfinite(uv).all() and np.all(uv>=0) and np.all(uv<=1),'UV outside embedded donor'
    tested=0
    for triangle in triangles:
        p=uv[triangle]*[width,height]
        low=np.maximum(0,np.floor(p.min(0)).astype(int)-1)
        high=np.minimum([width-1,height-1],np.floor(p.max(0)).astype(int))
        xx,yy=np.meshgrid(np.arange(low[0],high[0]+1),np.arange(low[1],high[1]+1))
        cells=np.column_stack([xx.ravel(),yy.ravel()]);centers=cells+.5
        hit=np.ones(len(cells),dtype=bool)
        axes=[np.array([1.,0.]),np.array([0.,1.])]
        for a,b in zip(p,np.roll(p,-1,axis=0)):
            edge=b-a
            if np.linalg.norm(edge)>1e-14:axes.append(np.array([-edge[1],edge[0]]))
        for axis in axes:
            project=p@axis;mid=centers@axis;radius=.5*np.abs(axis).sum()
            hit &= (mid+radius>=project.min()-1e-9)&(mid-radius<=project.max()+1e-9)
        cells=cells[hit];tested+=len(cells)
        assert len(cells) and np.all(rgba[cells[:,1],cells[:,0],3]==255),'Transparent pixels intersect actual auxiliary UV triangle'
    return tested


def inspect_auxiliaries(plan,doc,blob,mesh_nodes):
    assert plan['species']=='hairtail' and plan['body']==EXPECTED_BODY
    assert set(plan['fins'])==EXPECTED_FINS,'Hairtail complete three-fin inventory required'
    overlays=plan.get('decorative_overlays',{})
    assert set(overlays)==set(EXPECTED_AUX),'Exactly two native eyes and six declared tooth components required'
    body=next(n for n in mesh_nodes if n['name']==plan['body'])
    proofs=[]
    for name,definition in overlays.items():
        assert definition.get('kind')==EXPECTED_AUX[name] and definition.get('underlying_body')==plan['body'],'Explicit actual auxiliary kind/body required'
        assert 'rigid_bone' not in definition,'Mixed-skin auxiliaries must not claim rigid support'
        node=next(n for n in mesh_nodes if n['name']==name)
        assert node.get('skin')==body.get('skin') and 'skin'in body,'Auxiliary must use actual body skin'
        joints_count=len(doc['skins'][body['skin']]['joints'])
        edges=Counter();directions=Counter();triangle_count=0;covered_pixels=0;used_bones=set()
        for prim in doc['meshes'][node['mesh']]['primitives']:
            assert prim.get('mode',4)==4
            attrs=prim['attributes'];assert {'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'}<=attrs.keys()
            pos=accessor(doc,blob,attrs['POSITION']);normal=accessor(doc,blob,attrs['NORMAL']);uv=accessor(doc,blob,attrs['TEXCOORD_0'])
            tri=accessor(doc,blob,prim['indices']).reshape(-1,3);weights=accessor(doc,blob,attrs['WEIGHTS_0']);joints=accessor(doc,blob,attrs['JOINTS_0'])
            assert len(pos)>0 and len(tri)>0 and tri.min()>=0 and tri.max()<len(pos)
            assert np.isfinite(pos).all() and normal.shape==pos.shape and np.isfinite(normal).all()
            assert np.all(abs(np.linalg.norm(normal,axis=1)-1)<1e-5),'Auxiliary nonunit normal'
            assert weights.shape==joints.shape==(len(pos),4) and np.isfinite(weights).all() and np.all(weights>=0)
            assert np.all(abs(weights.sum(1)-1)<1e-5) and joints.min()>=0 and joints.max()<joints_count,'Invalid auxiliary skin'
            used_bones.update(int(j) for js,ws in zip(joints,weights) for j,w in zip(js,ws) if w>1e-7)
            face_normals=np.cross(pos[tri[:,1]]-pos[tri[:,0]],pos[tri[:,2]]-pos[tri[:,0]])
            assert np.all(np.linalg.norm(face_normals,axis=1)>0),'Zero-area auxiliary triangle'
            assert np.all((face_normals*normal[tri].mean(1)).sum(1)>0),'Auxiliary normals disagree with winding'
            pts=[tuple(round(float(x),7)for x in v)for v in pos]
            for face in tri:
                q=[pts[i]for i in face];assert len(set(q))==3,'Degenerate welded auxiliary triangle'
                for a,b in zip(q,q[1:]+q[:1]):
                    edge=tuple(sorted([a,b]));edges[edge]+=1;directions[edge]+=1 if a<b else -1
            mat=doc['materials'][prim['material']];pbr=mat.get('pbrMetallicRoughness',{})
            assert mat.get('alphaMode','OPAQUE')=='OPAQUE' and pbr.get('baseColorFactor',[1,1,1,1])[3]==1,'Auxiliary must be OPAQUE'
            assert set(mat.get('extensions',{}))<={'KHR_materials_specular'},'Unsupported auxiliary material opacity semantics'
            texture=pbr.get('baseColorTexture') or mat.get('emissiveTexture');assert texture is not None,'Native auxiliary donor missing'
            image=doc['images'][doc['textures'][texture['index']]['source']];assert 'bufferView'in image and 'uri'not in image
            view=doc['bufferViews'][image['bufferView']];offset=view.get('byteOffset',0)
            rgba=np.array(Image.open(io.BytesIO(blob[offset:offset+view['byteLength']])).convert('RGBA'))
            covered_pixels+=opaque_triangle_pixels(rgba,uv,tri);triangle_count+=len(tri)
        assert edges and all(n==2 for n in edges.values()) and all(n==0 for n in directions.values()),'Auxiliary not an oriented closed mesh'
        proofs.append(dict(name=name,kind=definition['kind'],triangles=triangle_count,closed_opaque=True,actual_body_skin=node['skin'],used_joint_indices=sorted(used_bones),conservative_uv_pixel_cells=covered_pixels,support_scope='normalized shared body skin only; anatomical/dynamic attachment requires separate evidence'))
    return proofs

def inspect_model(plan):
    packed=bool(plan.get('packed_parts_manifest'))
    opacity=None
    if packed:
        from logical_document import logical_document
        assert sha(plan['packed_parts_manifest'])==plan['packed_parts_manifest_sha256'], 'Stale packed partition manifest'
        canonical=json.loads(Path(plan['packed_parts_manifest']).read_text(encoding='utf8'));assert canonical['model_sha256']==sha(plan['model'])
        doc,blob,opacity=logical_document(plan['model'],plan['body'],plan['fins'],plan['packed_parts_manifest'])
    else:doc,blob=read_glb(Path(plan['model']))
    mesh_nodes=[n for n in doc['nodes'] if 'mesh' in n]
    assert plan['fins'] and len(set(plan['fins']))==len(plan['fins']) and plan['body'] not in plan['fins'], 'Explicit complete species fin inventory required'
    overlays=plan.get('decorative_overlays',{})
    assert isinstance(overlays,dict) and not set(overlays)&{plan['body'],*plan['fins']}, 'Ambiguous decorative overlay inventory'
    assert {n['name'] for n in mesh_nodes}=={plan['body'],*plan['fins'],*overlays} and len(mesh_nodes)==1+len(plan['fins'])+len(overlays), 'Unexpected/empty body, fin or declared overlay inventory'
    overlay_proofs=inspect_auxiliaries(plan,doc,blob,mesh_nodes)
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
        texture=pbr.get('baseColorTexture') or mat.get('emissiveTexture');image_info=None
        donor_role='albedo' if pbr.get('baseColorTexture') is not None else 'emission'
        if texture is not None:
            tex=doc['textures'][texture['index']];image=doc['images'][tex['source']]
            assert 'bufferView' in image and 'uri' not in image, 'Body donor must be embedded'
            view=doc['bufferViews'][image['bufferView']];start=view.get('byteOffset',0);raw=blob[start:start+view['byteLength']]
            rgba=np.array(Image.open(io.BytesIO(raw)).convert('RGBA'));assert rgba.size and (opacity['ok'] if packed else np.all(rgba[:,:,3]==255)), 'Transparent embedded body donor'
            image_info={'donor_role':donor_role,'embedded_sha256':hashlib.sha256(raw).hexdigest(),'rgba_sha256':hashlib.sha256(rgba.tobytes()).hexdigest(),'size':[rgba.shape[1],rgba.shape[0]]}
        surfaces.append({'surface':si,'triangles':len(tri),'vertices':len(pos),'material':mat.get('name',''),'opaque':True,'unit_normals_and_winding_agree':True,'texture':image_info})
    assert edges and all(n==2 for n in edges.values()), 'Open/nonmanifold welded body'
    assert all(n==0 for n in directions.values()), 'Inconsistent body winding'
    return {'triangles':triangle_count,'welded_edges':len(edges),'surfaces':surfaces,'decorative_overlay_proofs':overlay_proofs,**({'packed_body_opacity':opacity,'analysis_projection_only':True} if packed else {})}


BASE_CHECKER_SHA256 = "1a73badcd756005eb10e5e70530ea3bcc084c5db2f084d0cb16843cb65ab4fd7"


def run_gpu(game,godot,plan_path,output):
    output.mkdir(parents=True,exist_ok=True);result={'ok':False,'kind':'standalone_body_integrity_077','formal_acceptance':False};capture=Path(__file__).with_name('capture_standalone_body.gd')
    validation_dependencies={str(p.resolve()):sha(p) for p in [Path(__file__),capture,Path(__file__).parent.parent/'freeze_surface_ownership.py',Path(__file__).parent.parent/'validate_body_integrity.py']}
    try:
        plan=json.loads(plan_path.read_text(encoding='utf8'));inputs=frozen_inputs(plan);geometry=inspect_model(plan)
        if plan.get('packed_parts_manifest'):
            for dependency in [Path(__file__).with_name('logical_document.py'),Path(__file__).with_name('PackedFishParts.gd')]:validation_dependencies[str(dependency.resolve())]=sha(dependency)
        receipt=output/'capture.validation.json'
        if receipt.exists():receipt.unlink()
        run=subprocess.run([str(godot),'--path',str(game),'--log-file',str(output/'godot.log'),'--rendering-method','gl_compatibility','--script',str(capture),'--',str(plan_path),str(output)],capture_output=True,text=True,timeout=180)
        log=run.stdout+run.stderr;(output/'capture.log').write_text(log,encoding='utf8')
        assert run.returncode==0 and 'ERROR:' not in log and receipt.exists(), 'Standalone GPU capture failed'
        data=json.loads(receipt.read_text(encoding='utf8'));assert data['model_sha256']==plan['model_sha256'] and data['plan_sha256']==sha(plan_path), 'Stale GPU capture'
        assert data['frozen_inputs']==inputs and data['body']==plan['body'], 'Runtime bindings differ'
        actual_materials=data['motion']['materials'];assert len(actual_materials)==len(geometry['surfaces']), 'Actual material count differs'
        for expected,actual in zip(geometry['surfaces'],actual_materials):
            assert expected['surface']==actual['surface'], 'Actual surface order differs'
            assert actual['texture']==bool(expected['texture']), 'Actual body texture binding differs'
            if expected['texture']:
                assert actual['donor_role']==expected['texture']['donor_role'],'Actual donor role differs'
                assert actual['rgba_sha256']==expected['texture']['rgba_sha256'], 'Actual GPU donor RGBA differs from embedded model'
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
    (output/'completion.validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


def validate(game,godot,plan_path,output,geometry_only=False):
    assert sha(PORTABLE/'validate_standalone_body.py')==BASE_CHECKER_SHA256,'Base 077 inspector changed; audit the copied body guards before reuse'
    assert output.is_relative_to(HERE.parents[3]/'projects/fishing-2d/experiments/hairtail-static-merge') and not output.exists(),'New hairtail output required'
    plan=json.loads(plan_path.read_text(encoding='utf-8-sig'))
    assert not plan.get('packed_parts_manifest'),'This private adapter handles the original multi-mesh hairtail only'
    if geometry_only:
        output.mkdir(parents=True)
        result={'ok':False,'kind':'hairtail_geometry_preflight_not_077','formal_acceptance':False,'model_sha256':sha(plan['model'])}
        try:
            assert sha(plan['model'])==plan['model_sha256'],'Stale model'
            result.update(ok=True,geometry=inspect_model(plan))
        except Exception as error:result['error']=str(error)
        (output/'geometry.validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
        return result
    adapter=str(Path(__file__).resolve())
    assert plan['frozen_inputs'].get(adapter)==sha(adapter),'Freeze this private adapter in the actual plan'
    result=run_gpu(game,godot,plan_path,output)
    result['species_adapter']={'path':adapter,'sha256':sha(adapter),'base_checker_sha256':BASE_CHECKER_SHA256,'auxiliary_scope':'Two closed mixed-skin eyes and six closed upper-tooth components; no rigid support claim. Actual body GPU/closure/donor gates unchanged. Attachment is separately validated.'}
    result['validation_dependencies'][adapter]=sha(adapter)
    (output/'completion.validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['game','godot','plan','output']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--geometry-only',action='store_true')
    args=parser.parse_args();result=validate(args.game.resolve(),args.godot.resolve(),args.plan.resolve(),args.output.resolve(),args.geometry_only)
    print(json.dumps({'ok':result['ok'],'error':result.get('error'),'geometry_only':args.geometry_only}));raise SystemExit(0 if result['ok']else 1)
