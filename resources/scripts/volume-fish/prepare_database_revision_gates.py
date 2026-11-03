"""Bind current source-owned candidate to complete original root domains and gates."""
import argparse,copy,hashlib,json,struct,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.interpolate import PchipInterpolator
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE/'portable'),str(HERE)]
from glb_io import read_glb,arrays
from parts import freeze
from logical_document import logical_document
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def glb(p,d,b):
    j=json.dumps(d,separators=(',',':')).encode();j+=b' '*(-len(j)%4);b+=b'\0'*(-len(b)%4);p.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(j)+len(b))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(b),b'BIN\0')+b)
def main(a):
    out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not out.exists();out.mkdir(parents=True)
    baseline=ROOT/f'output/five-fish-database-20261103/restored/{a.species}/frozen';model=a.model.resolve();blend=model.with_suffix('.blend');assert blend.exists();spec=read(baseline/'source-run/final-spec.json');old=Path(spec['model']['path']);installed=ROOT/f'projects/fishing-2d/game/assets/models/fish/{a.species}.glb';assert sha(installed)==spec['model']['sha256']
    spec['model']={'path':str(model),'sha256':sha(model)};spec['inputs']['source_blend']={'path':str(blend),'sha256':sha(blend)};spec['inputs']['reference_glb']=dict(spec['model']);spec['inputs']['atlas']={'path':str(a.atlas.resolve()),'sha256':sha(a.atlas)};spec['inputs']['packing_report']={'path':str((model.parent/'source-authoring.validation.json').resolve()),'sha256':sha(model.parent/'source-authoring.validation.json')};spec['motion']['runtime']={'path':str(ROOT/'projects/fishing-2d/game/scripts/aquarium/FoundryFishMotion.gd'),'sha256':sha(ROOT/'projects/fishing-2d/game/scripts/aquarium/FoundryFishMotion.gd')}
    spec.pop('production',None) # A new review will bind the current candidate; old review is historical.
    write(out/'spec.json',spec);manifest=freeze(model,spec,out/'parts-manifest.json')
    oldd,oldb=read_glb(installed);d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);ov=arrays(oldd,oldb,oldd['meshes'][0]['primitives'][0]['attributes']['POSITION']);assert v.shape==ov.shape
    plan=read(baseline/'fin.plan.json');item=plan['items'][0];root_counts={};root_errors={}
    for name,r in item['fins'].items():
        part=next(p for p in oldd['extras']['geometry_parts'] if p['logical_name']==name);start=part['vertex_start'];end=start+part['vertex_count'];distance,ids=cKDTree(ov[start:end]).query(r['rest_points_gltf']);assert float(distance.max())<1e-6,(name,'Original complete root bank does not map to exact installed baseline')
        root_counts[name]=len(r['rest_points_gltf']);root_errors[name]=float(distance.max());r['rest_points_gltf']=v[start+ids].tolist()
    runtime=ROOT/spec['motion']['runtime']['path'];motion=ROOT/spec['motion']['profile']['path'];helper=HERE/'portable/PackedFishParts.gd';canon=HERE/'portable/parts.py';exporter=HERE/'portable/export_fin_poses.gd'
    item.update(model=str(model),model_sha256=sha(model),packed_parts_manifest=str(out/'parts-manifest.json'),packed_parts_manifest_sha256=sha(out/'parts-manifest.json'),packed_helper_script=str(helper),packed_canonicalizer=str(canon),motion_runtime=str(runtime),controller_script=str(runtime),motion_profile=str(motion),motion_profile_sha256=sha(motion),motion_runtime_sha256=sha(runtime))
    dependencies=[model,blend,a.atlas.resolve(),baseline/'fin.plan.json',installed,out/'spec.json',out/'parts-manifest.json',helper,canon,exporter,runtime,motion]
    item['frozen_inputs']={str(p):sha(p) for p in dependencies};item['scope']='Complete original root bank mapped by exact installed rest vertices, all original root points retained. New actual candidate and runtime; no historical pass transferred.';write(out/'fin.plan.json',plan)
    write(out/'root-domain-preservation.validation.json',{'ok':True,'species':a.species,'original_plan_sha256':sha(baseline/'fin.plan.json'),'installed_baseline_sha256':sha(installed),'candidate_sha256':sha(model),'original_root_counts':root_counts,'new_root_counts':{k:len(r['rest_points_gltf']) for k,r in item['fins'].items()},'maximum_original_bank_to_installed_error_native':root_errors,'membrane_clearance_unchanged':item['membrane_clearance']})
    ld,lb,_=logical_document(model,item['body'],list(item['fins']),out/'parts-manifest.json');glb(out/'ordinary-reference.glb',ld,lb)
    config=read(baseline/'delivery-config.json');profile=read(ROOT/config['geometry_profile']);comparison=read(a.comparison);rr=comparison['sections']['reference'];target=PchipInterpolator([r['s'] for r in rr],[r['width_over_body_axis'] for r in rr]);bodyidx=np.concatenate([arrays(d,b,pr['indices']).reshape(-1)[p['index_start']:p['index_start']+p['index_count']] for p in d['extras']['geometry_parts'] if p['role'] in ['body_skin','mouth']]);lo,hi=v[bodyidx,0].min(),v[bodyidx,0].max();L=hi-lo
    # Insert actual requested measurement planes before interpolating. Sparse
    # construction controls are not the independently sampled reference curve.
    original=np.array(profile['body']['sections'],float)
    us=sorted(set(original[:,0].tolist()+config['head_stations']))
    profile['body']['sections']=[[u,*[float(np.interp(u,original[:,0],original[:,i])) for i in [1,2,3]]] for u in us]
    accepted_path=ROOT/f'output/five-fish-database-20261103/restored/{a.species}/accepted-head-envelope.profile.json'
    accepted=np.array(read(accepted_path)['body']['sections'],float) if accepted_path.exists() else None
    fallbacks=[]
    for row in profile['body']['sections']:
        t=float((hi-(row[0]-.5))/L)
        if .005<=t<=.82:row[3]=float(target(t)*L/2)
        elif row[0] in config['head_stations']:
            assert accepted is not None,'Unsupported library head plane needs exact previous accepted outer envelope, not construction-cage fallback'
            row[3]=float(np.interp(row[0],accepted[:,0],accepted[:,3]));fallbacks.append({'u':row[0],'reference_body_s':t,'half_width_native':row[3],'source':str(accepted_path),'source_sha256':sha(accepted_path),'reason':'Outside finite library sampling range; preserve previous accepted independent outer envelope, not the construction cage or current candidate measurements.'})
    write(out/'head-reference-coverage.validation.json',{'ok':True,'species':a.species,'independent_reference':{'path':str(a.comparison.resolve()),'sha256':sha(a.comparison)},'unsupported_planes':fallbacks,'no_extrapolation_or_candidate_fit_target':True})
    profile['notes']=profile.get('notes',[])+['Anterior transverse desired outer envelope independently from inspected library bind geometry, matched body nose-to-peduncle axis. Not biological measurement; project XY/fin domains retained.']
    write(out/'head-envelope.profile.json',profile)
    config.update(final_spec=str(out/'spec.json'),fin_plan=str(out/'fin.plan.json'),ordinary_reference=str(out/'ordinary-reference.glb'),head_envelope_profile=str(out/'head-envelope.profile.json'),geometry_profile=str(out/'head-envelope.profile.json'),fin_pose_exporter=str(exporter),review_capture_script=str(HERE/'portable/capture_fish_review.gd'))
    config['review_sources']=[str(ROOT/config['review_sources'][0]),str(ROOT/f'projects/fishing-2d/experiments/{a.species.replace("_","-")}-portable-trial-20261031/body-generated.png')]
    assert all(Path(p).exists() for p in config['review_sources']);config.pop('production',None);write(out/'delivery-config.json',config)
    print(json.dumps({'ok':True,'species':a.species,'root_counts':root_counts,'output':str(out)}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--species',required=True)
    for k in ['model','atlas','comparison','output']:p.add_argument('--'+k,required=True,type=Path)
    main(p.parse_args())
