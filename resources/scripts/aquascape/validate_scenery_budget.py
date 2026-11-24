"""Blocking complete-instance budgets, closed topology, roots and apertures."""
import argparse,json
from pathlib import Path
import numpy as np
from optimize_scenery import load,save,sha,metrics,budget_type
from rig_plant_current import read_glb,array
from validate_art_models import inspect
from validate_plant_current import pose,deform
from build_decor_ten import source_image,source_for,semantic_checks

def validate_rooted_current(doc, binary, options):
    from validate_shader_shells import points

    low = np.asarray(options['anchor_min'], dtype=float)
    size = np.asarray(options['anchor_size'], dtype=float)
    amplitude = float(options['amplitude'])
    if low.shape != (3,) or size.shape != (3,) or not np.isfinite([low, size]).all() or (size <= 0).any() or not 0 < amplitude <= .35:
        return {}, ['Invalid rooted-current shader parameters']
    if doc.get('skins') or doc.get('animations'):
        return {}, ['Rooted-current mesh carries unexpected skeletal animation']
    roots = 0
    root_error = 0.
    loop_error = 0.
    displacement = 0.
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            attrs = primitive['attributes']
            if not {'TEXCOORD_1', 'COLOR_0'} <= attrs.keys():
                return {}, ['Missing root weight or pivot vertex channel']
            v, flow, color = (array(doc,binary,attrs[name]) for name in ('POSITION','TEXCOORD_1','COLOR_0'))
            if not np.isfinite(flow).all() or not np.isfinite(color).all() or (flow < 0).any() or (flow > 1).any():
                return {}, ['Invalid root weights or pivot vertex colors']
            pinned = flow[:,0] <= .08
            roots += int(pinned.sum())
            rest = points(v,flow,color,low,size,0.,amplitude=amplitude)
            end = points(v,flow,color,low,size,10.,amplitude=amplitude)
            loop_error = max(loop_error, float(np.linalg.norm(end-rest,axis=1).max()))
            for seconds in np.linspace(0,10,41):
                posed = points(v,flow,color,low,size,seconds,amplitude=amplitude)
                if pinned.any():
                    root_error = max(root_error,float(np.linalg.norm((posed-v)[pinned],axis=1).max()))
                displacement = max(displacement,float(np.linalg.norm(posed-rest,axis=1).max()))
    data = {'root_pinned_vertices':roots,'root_motion_m':root_error,'loop_seam_m':loop_error,'max_tip_motion_m':displacement,'current_samples':41}
    failed = not roots or max(root_error,loop_error)>1e-6 or displacement<.0003
    return data, ['Root, loop or tip-motion failure'] if failed else []

def validate(root,catalog_paths,output):
    game=root/'projects/fishing-2d/game';policy=load(root/'resources/aquascape/geometry-budgets.json');rows=[];failures=[]
    decor={s['id']:s for s in load(root/'resources/aquascape/decor-10-v1.json')['assets']}
    for catalog in catalog_paths:
        for row in load(catalog)['assets']:
            path=game/row['model'].removeprefix('res://');kind=budget_type(row,policy)
            shader_only=row.get('deformation')=='shader'
            masked=shader_only or row.get('material_mode')=='mask'
            data=inspect(path,allow_alpha_mask=masked);m=metrics(path);local=[]
            if m['triangles']>policy['types'][kind]['hard_limit']:local.append('Complete instance exceeds hard budget')
            if not data['ok'] or data['nonmanifold_edges']:local.append('Invalid geometry, open or nonmanifold edges')
            detail={};d,b=read_glb(path)
            if shader_only:
                from validate_shader_shells import validate as validate_shells
                detail=validate_shells(root,row,path)
                local.extend(detail.pop('failures'))
            elif row.get('rooted_current'):
                detail,current_failures=validate_rooted_current(d,b,row['rooted_current'])
                local.extend(current_failures)
                if row.get('geometry_revision')=='consolidated-vertex-current-v10':
                    from merge_plant_meshes import validate_merge

                    src=game/row['merge_source_model'].removeprefix('res://')
                    reference=game/row['shader_model'].removeprefix('res://')
                    try:
                        detail['merge']=validate_merge(src,reference,path,row['rooted_current'])
                    except (AssertionError, ValueError) as error:
                        local.append(f'Combined vertex-current plant verification failed: {error}')
            elif row.get('animated'):
                src=game/row['pre_budget_model'].removeprefix('res://');original,ob=read_glb(src)
                def payload(doc,binary,im):
                    v=doc['bufferViews'][im['bufferView']];off=v.get('byteOffset',0);return binary[off:off+v['byteLength']]
                same_images=len(d['images'])==len(original['images']) and all(payload(d,b,im)==payload(original,ob,old) for im,old in zip(d['images'],original['images']))
                same_rig=d['nodes']==original['nodes']
                authorized_retarget=False
                if row.get('geometry_revision')=='natural-leaf-v10':
                    proof=load(Path(row['natural_leaf_build_report']))
                    matched=next((r for r in proof['outputs'] if r['id']==row['id']),None)
                    normal_source=game/row['pre_natural_leaf_model'].removeprefix('res://')
                    authorized_retarget=bool(proof['ok'] and matched and matched['sha256']==sha(path) and matched['source_sha256']==sha(normal_source) and matched['rig_rest_retargeted'])
                same_clips=all(np.array_equal(array(d,b,s[key]),array(original,ob,t[key])) for an,oldan in zip(d['animations'],original['animations']) for s,t in zip(an['samplers'],oldan['samplers']) for key in ['input','output'])
                anchors=0;tips=0;anchor_error=0.;loop_error=0.;rest_error=0.;tip_motion=0.
                matrices=[pose(d,b,float(t)) for t in np.linspace(0,10,81)];rest=pose(d,b)
                for mesh in d['meshes']:
                    leaf=mesh['name'].startswith('traced_leaf_')
                    for prim in mesh['primitives']:
                        attrs=prim['attributes'];v=array(d,b,attrs['POSITION']);uv=array(d,b,attrs['TEXCOORD_0']);w=array(d,b,attrs['WEIGHTS_0'])
                        pinned=(1-uv[:,1]<=.08+1e-6) if leaf else np.ones(len(v),dtype=bool);tip=(1-uv[:,1]>.9) if leaf else np.zeros(len(v),dtype=bool)
                        if leaf and (not pinned.any() or not tip.any()):local.append(mesh['name']+': missing base/tip vertices')
                        if not np.allclose(w.sum(1),1,atol=1e-6) or (w<0).any():local.append('Invalid weights')
                        anchors+=int(pinned.sum());tips+=int(tip.sum());rest_error=max(rest_error,float(np.linalg.norm(deform(prim,d,b,rest)-v,axis=1).max()))
                        first=deform(prim,d,b,matrices[0]);last=deform(prim,d,b,matrices[-1]);loop_error=max(loop_error,float(np.linalg.norm(first-last,axis=1).max()))
                        for mat in matrices:
                            delta=deform(prim,d,b,mat)-v
                            if pinned.any():anchor_error=max(anchor_error,float(np.linalg.norm(delta[pinned],axis=1).max()))
                            if tip.any():tip_motion=max(tip_motion,float(np.linalg.norm(delta[tip],axis=1).max()))
                if max(anchor_error,loop_error,rest_error)>2e-6 or tip_motion<.0003:local.append('Native root, bind, loop or motion check failed')
                if not (same_images and (same_rig or authorized_retarget) and same_clips):local.append('Original artwork/rig/clip changed without current authorized retarget proof')
                detail={'native_poses':81,'anchor_vertices':anchors,'tip_vertices':tips,'anchor_error_m':anchor_error,'loop_error_m':loop_error,'rest_error_m':rest_error,'tip_motion_m':tip_motion,'original_images_byte_identical':same_images,'original_nodes_identical':same_rig,'authorized_natural_leaf_retarget':authorized_retarget,'original_clip_samples_identical':same_clips}
            elif row['id'] in decor:
                verts=np.vstack([array(d,b,p['attributes']['POSITION']) for mesh in d['meshes'] for p in mesh['primitives']]);faces=np.arange(len(verts)).reshape(-1,3)
                spec=decor[row['id']];bounds=row['projection_bounds'];fm=source_image(source_for(root,row['id'],'front'))[1]
                tests=semantic_checks(verts,faces,bounds['width'],bounds['height'],bounds['depth'],spec,fm)
                if any(not t['ok'] for t in tests):local.append('Original semantic aperture/floor check failed')
                detail={'semantic_checks':tests}
            elif row.get('geometry_revision')=='budget-first-v11':
                proof=load(root/'projects/fishing-2d/plans/reviews/aquascape-expansion-v11/solids.validation.json')
                current=next(r for r in proof['outputs'] if r['id']==row['id'])
                if current['sha256']!=sha(path):local.append('Current solid semantic proof is stale')
                if not current['source_build']['ok']:local.append('Source hull has disconnected components or invalid cavities')
                config=next(s for s in load(root/'resources/aquascape/expansion-v11.json')['solids'] if s['id']==row['id'])
                cavities={'bamboo_shelter':'pipe','slate_cave':'box_tunnel','ruined_tower':'arched_tunnel'}
                spec={**config,'cavity':cavities.get(row['id'],'none')};bounds=row['projection_bounds']
                verts=np.vstack([array(d,b,p['attributes']['POSITION']) for mesh in d['meshes'] for p in mesh['primitives']]);faces=np.arange(len(verts)).reshape(-1,3)
                from scipy.sparse import coo_matrix
                from scipy.sparse.csgraph import connected_components
                unique,indices=np.unique(verts,axis=0,return_inverse=True);ff=indices.reshape(-1,3);edges=np.concatenate([ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]]]);graph=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(unique),len(unique))).tocsr()
                components=connected_components(graph,directed=False,return_labels=False)
                if components!=1:local.append('Solid prop has detached geometry')
                fm=source_image(root/current['source_build']['materials']['front']['source'])[1]
                tests=semantic_checks(verts,faces,bounds['width'],bounds['height'],bounds['depth'],spec,fm)
                if any(not t['ok'] for t in tests):local.append('New prop aperture/floor check failed')
                detail={'semantic_checks':tests}
            result={'id':row['id'],'path':str(path),'ok':not local,'budget_type':kind,'budget':policy['types'][kind],**m,'open_edges':data['open_edges'],'nonmanifold_edges':data['nonmanifold_edges'],**detail,'failures':local};rows.append(result)
            failures.extend(row['id']+': '+f for f in local)
    report={'schema_version':1,'command':'aquascape.validate-scenery-budget','ok':not failures,'status':'done' if not failures else 'failed','next_action':'human_review' if not failures else 'fix_input','inputs':{'policy_sha256':sha(root/'resources/aquascape/geometry-budgets.json')},'outputs':rows,'failures':failures,'user_acceptance':'pending','limitations':['Discrete CPU poses and ray probes supplement actual multi-view native visual review.']};save(output,report);return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--input',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--json',action='store_true');a=p.parse_args();r=validate(a.root.resolve(),a.input,a.output)
    print(json.dumps({'ok':r['ok'],'models':len(r['outputs']),'triangles':sum(r['triangles'] for r in r['outputs']),'failures':r['failures']}));return 0 if r['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
