"""Actual replacement-body variant of the077 integrity gate.

The GLB is checked only for unchanged auxiliaries, never as evidence for the
replacement body. That body comes from the freshly exported active ArrayMesh.
"""
import hashlib,json,re,traceback
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from freeze_surface_ownership import read_glb,accessor

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def closed(parts):
    edges=Counter();count=0
    for part in parts:
        v=np.asarray(part['vertices'],float);t=np.asarray(part['triangles'],int).reshape(-1,3)
        assert v.ndim==2 and v.shape[1]==3 and np.isfinite(v).all() and len(t),'Invalid/empty actual body arrays'
        assert t.min()>=0 and t.max()<len(v)
        points=[tuple(round(float(x),7) for x in p) for p in v]
        for face in t:
            q=[points[i] for i in face];assert len(set(q))==3,'Degenerate actual body triangle'
            for x,y in zip(q,q[1:]+q[:1]):edges[tuple(sorted([x,y]))]+=1
        count+=len(t)
    assert edges and all(n==2 for n in edges.values()),'Open/nonmanifold actual body shell'
    return {'triangles':count,'edges':len(edges),'all_edge_valences':2,'native_position_identity_decimals':7}
def binding_matches(active,expected,names):
    mapping=[]
    for name in names:
        matches=[i for i,n in enumerate(active['skin_bind_names']) if n==name or n==name+'_2'];assert len(matches)==1,'Ambiguous actual bone mapping';mapping.append(matches[0])
    assert len(active['parts'])==len(expected)
    for part,ref in zip(active['parts'],expected):
        assert np.array_equal(np.asarray(part['vertices'],np.float32),np.asarray(ref['vertices'],np.float32)),'Runtime mesh differs from fin-gate geometry'
        assert np.array_equal(np.asarray(part['triangles']).ravel(),np.asarray(ref['triangles']).ravel())
        assert np.array_equal(np.asarray(part['bones']).reshape(-1,4),np.asarray(mapping)[np.asarray(ref['joints'],int)]),'Runtime skin differs from fin-gate binding'
        weights=np.asarray(part['weights'],np.float32).reshape(-1,4);source_weights=np.asarray(ref['weights'],np.float32)
        # Both the renderer and posed-fin exporter use Godot's exact UNORM16
        # floor encoder. Compare integer codes, not an enlarged float tolerance.
        expected_codes=(source_weights*np.float32(65535)).astype(np.uint16);actual_codes=np.rint(weights*np.float32(65535)).astype(np.uint16)
        assert np.array_equal(actual_codes,expected_codes),'Runtime packed skin weights differ from fin-gate binding'
        assert np.isfinite(weights).all() and np.min(weights)>=0 and np.max(abs(source_weights.sum(1)-1))<1e-6
        assert np.max(abs(weights.sum(1)-1))<=4/65535+1e-7
def validate(game,receipt,output,candidate_plan):
    records=[]
    try:
        data=json.loads(receipt.read_text());assert data['ok'] and data['checks']
        assert data['checker_sha256']==sha(Path(__file__).with_name('validate_mouth_runtime139.gd')),'Stale GPU checker'
        assert data.get('checker_dependencies'),'Missing inherited GPU checker bindings'
        for path,digest in data['checker_dependencies'].items():assert sha(path)==digest,'Stale inherited checker: '+path
        cfg_path=game/'assets/models/fish/motion/mouth-repair139.json';cfg=json.loads(cfg_path.read_text());assert data['config_sha256']==sha(cfg_path)
        frozen=json.loads(candidate_plan.read_text());assert frozen['config']==cfg,'Candidate/resource plan differs from actual configuration'
        frozen_rows={r['species']:r for r in frozen['items']}
        assert data['helper_sha256']==sha(game/'scripts/aquarium/MouthRepair139.gd')
        assert data.get('runtime_dependencies'),'Missing actual runtime binding inventory'
        for path,digest in data['runtime_dependencies'].items():assert sha(game/path.removeprefix('res://'))==digest,'Stale actual runtime: '+path
        own=json.loads((game/'assets/models/fish/motion/surface-ownership.json').read_text())['profiles']
        opacity=json.loads((game/'assets/models/fish/motion/body-opacity.json').read_text())['profiles']
        for row in data['checks']:
            sp=row['species'];assert not sp.endswith('hammerhead')
            p=cfg['profiles'][sp];assert row['ok'] and row['fin_resources_verified'] and row['auxiliary_unchanged']
            assert row['fins_unchanged']==(not p.get('fins'))
            for kind in ['body','lips']:
                if kind in p:assert sha(game/p[kind]['path'].removeprefix('res://'))==p[kind]['sha256']==row[kind+'_sha256']
            folder=receipt.parent/sp;mesh=folder/'runtime-body.mesh.json';assert sha(mesh)==row['runtime_body_sha256']
            active=json.loads(mesh.read_text());shell=closed(active['parts'])
            frozen_row=frozen_rows[sp]
            for key in ['geometry','skinning_report']:assert sha(frozen_row[key]['path'])==frozen_row[key]['sha256'],'Stale frozen geometry/binding'
            expected=json.loads(Path(frozen_row['geometry']['path']).read_text())['parts']
            names=json.loads(Path(frozen_row['skinning_report']['path']).read_text())['summary']['skin_joint_names']
            binding_matches(active,expected,names)
            if p.get('fins'):
                assert 'fin_geometry' in frozen_row and sha(frozen_row['fin_geometry']['path'])==frozen_row['fin_geometry']['sha256']
                fin_file=folder/'runtime-fins.mesh.json';assert sha(fin_file)==row['runtime_fin_binding_sha256'];actual_fins=json.loads(fin_file.read_text())
                expected_fins=json.loads(Path(frozen_row['fin_geometry']['path']).read_text())['fins'];assert set(actual_fins)==set(p['fins'])=={f['name'] for f in expected_fins}
                for fin in expected_fins:
                    resource=p['fins'][fin['name']];assert sha(game/resource['path'].removeprefix('res://'))==resource['sha256']
                    binding_matches(actual_fins[fin['name']],fin['parts'],fin['skin_joint_names'])
            materials=row['materials'];assert len(materials)==len(active['parts'])
            for mat in materials:
                if mat['kind']=='opaque_standard':
                    assert mat['transparency_disabled'] and mat['albedo_alpha']==1
                    if mat['texture_present']:
                        texture=mat['texture'];assert min(texture['size'])>0 and len(texture['base_data_sha256'])==64
                    else:assert not mat.get('texture')
                    continue
                assert mat['kind']=='opaque_shader'
                path=Path(mat['shader']);assert sha(path)==mat['shader_sha256'];code=path.read_text()
                code=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/','',code)
                assert not re.search(r'\b(?:ALPHA|ALPHA_SCISSOR_THRESHOLD|ALPHA_HASH_SCALE|discard)\b',code),'Coverage-changing actual body shader'
                for tex in mat['textures']:
                    assert min(tex['size'])>0 and tex['base_data_sha256']
                    if tex['name'] in ['opaque_skin','original_opaque']:assert tex['opaque_checked'] and tex['opaque']
            assert {(v['pose'],v['view']) for v in row['coverage']}=={(p,v) for p in range(2) for v in range(8)}
            for v in row['coverage']:
                stem=folder/'coverage'/f"p{v['pose']}-v{v['view']}";actual=stem.with_name(stem.name+'-actual.png');ref=stem.with_name(stem.name+'-closed.png')
                assert sha(actual)==v['actual_sha256'] and sha(ref)==v['reference_sha256']
                a=np.asarray(Image.open(actual).convert('RGBA'));b=np.asarray(Image.open(ref).convert('RGBA'));assert a.shape==b.shape
                mask=b[:,:,3]>128;assert mask.sum()>30 and int(mask.sum())==v['covered_pixels']
                assert int((mask&(a[:,:,3]<128)).sum())==v['missing_pixels']==0,'Actual GPU body hole'
            source=game/f'assets/models/fish/{sp}.glb';assert sha(source)==row['model_sha256']==p['source_model_sha256']==opacity[sp]['model_sha256']
            d,b=read_glb(source);aux=[]
            declared={x['node']:x for x in frozen_row.get('static_overlays',[])}
            found_overlays=set()
            for node in d['nodes']:
                if 'mesh' not in node or node['name']=='Closed_body' or node['name'] in own[sp]['fins'] or node['name'] in opacity[sp]['suppressed_auxiliary']:continue
                if node['name'] in declared:
                    layer=declared[node['name']];assert layer['underlying_body']=='Closed_body' and ('Source_lips139'==node['name'] or node['name'].startswith('Eye_relief112_')),'Unrecognized static overlay'
                    ref=layer['geometry'];assert sha(ref['path'])==ref['sha256'],'Stale static overlay source';geometry=json.loads(Path(ref['path']).read_text())
                    if layer['kind']=='lips':parts=geometry['parts']
                    else:
                        assert layer['kind']=='eye';caps=geometry['profiles'][sp]['caps'];parts=[next(c for c in caps if float(c['side'])==float(layer['side']))]
                    actual=d['meshes'][node['mesh']]['primitives'];assert len(actual)==len(parts),'Static overlay surface count changed'
                    for prim,part in zip(actual,parts):
                        for key,field in [('POSITION','vertices'),('NORMAL','normals'),('TEXCOORD_0','uv'),('JOINTS_0','joints'),('WEIGHTS_0','weights')]:
                            got=accessor(d,b,prim['attributes'][key]);want=np.asarray(part[field],dtype=got.dtype);assert np.array_equal(got,want),'Static overlay geometry/UV/skin differs: '+node['name']+'/'+field
                        ids=np.asarray(part['triangles']if layer['kind']=='lips'else part['indices']).reshape(-1,3)
                        if layer['kind']=='lips':ids=ids[:,[0,2,1]]
                        assert np.array_equal(accessor(d,b,prim['indices']).ravel(),ids.ravel()),'Static overlay topology differs'
                    found_overlays.add(node['name']);aux.append({'name':node['name'],'decorative_overlay':True,'underlying_closed_body':'Closed_body','exact_frozen_geometry_uv_skin':True});continue
                parts=[]
                for si,prim in enumerate(d['meshes'][node['mesh']]['primitives']):
                    parts.append({'vertices':accessor(d,b,prim['attributes']['POSITION']),'triangles':accessor(d,b,prim['indices'])})
                    mat=d['materials'][prim['material']]
                    if mat.get('pbrMetallicRoughness',{}).get('baseColorTexture') is not None:
                        donor=opacity[sp]['surfaces'][node['name']][str(si)];path=game/donor['texture'].removeprefix('res://');assert sha(path)==donor['texture_sha256']
                        assert np.all(np.asarray(Image.open(path).convert('RGBA'))[:,:,3]==255),'Transparent auxiliary donor'
                aux.append({'name':node['name'],'closed':closed(parts)})
            assert found_overlays==set(declared),'Declared static overlay missing from GLB'
            assert len(row['samples'])==16 and {v['action'] for v in row['samples']}=={'Swim','Turn','Ascend','Dive'}
            assert len(row['transitions'])==36 and len({(v['from'],v['to']) for v in row['transitions']})==12
            assert len(row['distances'])==3
            for v in row['samples']+row['transitions']+row['distances']:assert sha(v['file'])==v['sha256']
            records.append({'species':sp,'ok':True,'body_resource_sha256':p['body']['sha256'],'geometry_and_actual_bone_binding_match_frozen_candidate':True,'actual_shell':shell,'unchanged_auxiliaries':aux,'gpu_views':16,'missing_body_pixels':0,'actual_body_lod_counts':row['actual_body_lod_counts']})
        result={'ok':True,'records':records,'runtime_report':str(receipt),'runtime_report_sha256':sha(receipt),'candidate_plan_sha256':sha(candidate_plan),'checker_sha256':sha(__file__),'scope':'Active139 body closure, exact geometry/bone/weight match to frozen fin-gate candidate, actual per-surface materials and opaque donors, identical-pose GPU coverage, unchanged source auxiliaries. Original GLB is only a rig/fin/auxiliary donor. Discrete visibility, not continuous-time proof or visual acceptance.'}
    except Exception as e:result={'ok':False,'error':str(e),'traceback':traceback.format_exc(),'records':records}
    output.mkdir(parents=True,exist_ok=True);(output/'completion.validation.json').write_text(json.dumps(result,indent=2));return result
