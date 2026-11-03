"""Bind a source-owned transverse revision to its own complete root bank.

Only prepares inputs; no historical physical pass is transferred. Requires an exactly enumerated XY authoring receipt and
unchanged packed vertex/part identity. Topology-changing revisions need their
own audited root mapping instead of silently using this adapter.
"""
import argparse,copy,hashlib,io,json,struct,sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from scipy.spatial import cKDTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE/'portable'),str(HERE)]
from glb_io import read_glb,arrays
from parts import freeze
from logical_document import logical_document
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def path(value):
    if isinstance(value,dict):value=value['path']
    p=Path(value);return (ROOT/p).resolve()if not p.is_absolute()else p.resolve()
def ref(p):p=path(p);return {'path':str(p),'sha256':sha(p)}
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def write_glb(p,d,b):
    j=json.dumps(d,separators=(',',':')).encode();j+=b' '*(-len(j)%4);b+=b'\0'*(-len(b)%4)
    p.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(j)+len(b))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(b),b'BIN\0')+b)
def main(a):
    out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir(parents=True)
    spec=read(a.baseline_spec);oldmodel=path(a.baseline_model);model=path(a.model);blend=path(a.blend);atlas=path(a.atlas)
    oldd,oldb=read_glb(oldmodel);d,b=read_glb(model)
    assert len(d['meshes'])==len(oldd['meshes'])==1 and len(d['meshes'][0]['primitives'])==1
    pr=d['meshes'][0]['primitives'][0];opr=oldd['meshes'][0]['primitives'][0]
    v=arrays(d,b,pr['attributes']['POSITION']);ov=arrays(oldd,oldb,opr['attributes']['POSITION'])
    assert v.shape==ov.shape,'Packed vertex identity changed'
    assert a.xy_delta_receipt,'Independent own-mouth XY authoring receipt required'
    xyproof=read(a.xy_delta_receipt)
    assert xyproof['ok'] and xyproof['model_sha256']==sha(model)
    changed=np.flatnonzero(np.any(v[:,:2]!=ov[:,:2],axis=1));records=xyproof['vertices']
    assert len(records)==len(changed) and {int(x['vertex'])for x in records}==set(changed.tolist()),'Incomplete XY delta enumeration'
    for x in records:
        i=int(x['vertex'])
        assert np.array_equal(ov[i,:2],np.array(x['old_XY'],dtype=ov.dtype)) and np.array_equal(v[i,:2],np.array(x['new_XY'],dtype=v.dtype)),('XY receipt differs',i)
    assert d['extras']['geometry_parts']==oldd['extras']['geometry_parts'],'Part identity changed; cannot transport old roots blindly'
    author=path(a.authoring_report)if a.authoring_report else model.parent/'source-authoring.validation.json'
    ar=read(author);assert ar['ok'] and ar['model_sha256']==sha(model),'Current source authoring receipt required'
    unchanged={}
    for name in ['TEXCOORD_0','JOINTS_0','WEIGHTS_0']:
        unchanged[name]=np.array_equal(arrays(d,b,pr['attributes'][name]),arrays(oldd,oldb,opr['attributes'][name]))
    unchanged['indices']=np.array_equal(arrays(d,b,pr['indices']),arrays(oldd,oldb,opr['indices']))
    assert all(unchanged.values()),'UV/packing/skin/index change needs an independent current packing recipe'
    assert len(d['images'])==1
    imageview=d['bufferViews'][d['images'][0]['bufferView']];png=b[imageview.get('byteOffset',0):imageview.get('byteOffset',0)+imageview['byteLength']]
    assert np.array_equal(np.array(Image.open(io.BytesIO(png)).convert('RGBA')),np.array(Image.open(atlas).convert('RGBA'))),'Atlas file differs from actual embedded pixels'
    packing=out/'packing-continuity.validation.json'
    write(packing,{'ok':True,'kind':'unchanged_packing_identity_for_transverse_revision','model':ref(model),'baseline_model':ref(oldmodel),'editable_source':ref(blend),'authoring':ref(author),'atlas':ref(atlas),'actual_embedded_png_sha256':hashlib.sha256(png).hexdigest(),'embedded_decoded_RGBA_equal':True,'unchanged_arrays':unchanged,'scope':'No repacking inferred: actual unchanged UV/index/skin and actual embedded RGBA measured; source authoring and complete new physical gates separate.'})
    spec=copy.deepcopy(spec);spec.pop('production',None);spec.update(model=ref(model),species=a.species)
    spec['inputs']={'source_blend':ref(blend),'reference_glb':ref(model),'atlas':ref(atlas),'packing_report':ref(packing)}
    for role in ['runtime','profile']:spec['motion'][role]=ref(spec['motion'][role])
    if a.game:spec['game']=str(path(a.game))
    write(out/'spec.json',spec);freeze(model,spec,out/'parts-manifest.json')
    plan=read(a.baseline_plan);assert len(plan['items'])==1;item=plan['items'][0];assert item['species']==a.species
    assert item['model_sha256']==sha(oldmodel),'Baseline root bank does not bind supplied old model'
    root_counts={};mapping={}
    for name,r in item['fins'].items():
        part=next(p for p in oldd['extras']['geometry_parts']if p['logical_name']==name)
        start=part['vertex_start'];stop=start+part['vertex_count'];distance,ids=cKDTree(ov[start:stop]).query(r['rest_points_gltf'])
        assert len(distance)>0 and distance.max()<1e-6,(name,'Incomplete or foreign old root bank')
        root_counts[name]=len(distance);mapping[name]=float(distance.max());r['rest_points_gltf']=v[start+ids].tolist()
    motion=path(spec['motion']['profile']);runtime=path(spec['motion']['runtime']);helper=HERE/'portable/PackedFishParts.gd';canon=HERE/'portable/parts.py';exporter=HERE/'portable/export_fin_poses.gd'
    item.update(model=str(model),model_sha256=sha(model),packed_parts_manifest=str(out/'parts-manifest.json'),packed_parts_manifest_sha256=sha(out/'parts-manifest.json'),packed_helper_script=str(helper),packed_canonicalizer=str(canon),motion_profile=str(motion),motion_profile_sha256=sha(motion),motion_runtime=str(runtime),motion_runtime_sha256=sha(runtime),controller_script=str(runtime))
    deps=[model,blend,atlas,oldmodel,a.baseline_spec,a.baseline_plan,out/'spec.json',out/'parts-manifest.json',packing,author,helper,canon,exporter,runtime,motion,Path(__file__),a.xy_delta_receipt]
    item['frozen_inputs']={str(path(p)):sha(path(p))for p in deps};item['scope']='Original complete own-species root bank mapped by unchanged vertex/part identity. All original root points retained, new candidate needs actual current posed gates.'
    write(out/'fin.plan.json',plan)
    write(out/'root-domain-preservation.validation.json',{'ok':True,'species':a.species,'baseline_model':ref(oldmodel),'original_plan':ref(a.baseline_plan),'model':ref(model),'root_counts_before':root_counts,'root_counts_after':{k:len(x['rest_points_gltf'])for k,x in item['fins'].items()},'maximum_root_mapping_errors':mapping,'membrane_clearance':item['membrane_clearance'],'scope':'Domain transport only, no physical pass inferred.'})
    ld,lb,_=logical_document(model,item['body'],list(item['fins']),out/'parts-manifest.json');write_glb(out/'ordinary-reference.glb',ld,lb)
    if a.baseline_config:config=read(a.baseline_config)
    else:
        assert a.baseline_review_plan and a.baseline_head_plan
        review=read(a.baseline_review_plan);head=read(a.baseline_head_plan)['items'][0]
        config={'body':review['body'],'head_stations':[x[0]for x in head['target_half_width_envelope']],'head_tolerance':head['envelope_halfwidth_tolerance_native'],'pose_time':review['pose_time'],'whole_camera_size':review['whole_camera_size'],'details':review['details'],'review_sources':[x['path']for x in review['review_sources']],'game':spec['game']}
    profile=read(a.geometry_profile);assert profile['species']==a.species
    original=np.array(profile['body']['sections'],float);us=sorted(set(original[:,0].tolist()+config['head_stations']))
    profile['body']['sections']=[[u,*[float(np.interp(u,original[:,0],original[:,i]))for i in [1,2,3]]]for u in us]
    comparison=read(a.comparison);assert comparison['species']==a.species;rr=comparison['sections']['reference'];target=PchipInterpolator([x['s']for x in rr],[x['width_over_body_axis']for x in rr])
    idx=arrays(oldd,oldb,opr['indices']).reshape(-1);bodyids=np.concatenate([idx[p['index_start']:p['index_start']+p['index_count']]for p in oldd['extras']['geometry_parts']if p['role']in ['body_skin','mouth']]);lo,hi=ov[bodyids,0].min(),ov[bodyids,0].max();length=hi-lo;coverage=[]
    for row in profile['body']['sections']:
        t=float((hi-(row[0]-.5))/length)
        if .005<=t<=.82:row[3]=float(target(t)*length/2)
        if row[0]in config['head_stations']:
            assert .005<=t<=.82,'Head station outside finite reference; provide an independently accepted envelope instead of extrapolating'
            coverage.append({'u':row[0],'reference_body_s':t,'target_halfwidth':row[3]})
    profile['notes']=profile.get('notes',[])+['Transverse outer envelope from independently inspected library body sections, excluding fins/eyes; fixed old own-body axis registration, project XY preserved. Third-party art, not biological measurement.']
    write(out/'head-envelope.profile.json',profile);write(out/'head-reference-coverage.validation.json',{'ok':True,'species':a.species,'independent_reference':ref(a.comparison),'old_axis_model':ref(oldmodel),'head_stations':coverage,'no_candidate_fit_or_extrapolation':True})
    config.pop('production',None);config.update(final_spec=str(out/'spec.json'),fin_plan=str(out/'fin.plan.json'),ordinary_reference=str(out/'ordinary-reference.glb'),geometry_profile=str(out/'head-envelope.profile.json'),head_envelope_profile=str(out/'head-envelope.profile.json'),fin_pose_exporter=str(exporter),review_capture_script=str(HERE/'portable/capture_fish_review.gd'))
    if a.game:config['game']=str(path(a.game))
    for key in ['game']:config[key]=str(path(config[key]))
    config['review_sources']=[str(path(x))for x in config['review_sources']];assert all(Path(p).is_file()for p in config['review_sources'])
    write(out/'delivery-config.json',config);print(json.dumps({'ok':True,'species':a.species,'output':str(out),'root_counts':root_counts,'physical_gates_not_run':True}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--species',required=True)
    for key in ['baseline-spec','baseline-plan','baseline-model','model','blend','atlas','geometry-profile','comparison','output']:p.add_argument('--'+key,required=True,type=Path)
    for key in ['baseline-config','baseline-review-plan','baseline-head-plan','game','authoring-report','xy-delta-receipt']:p.add_argument('--'+key,type=Path)
    main(p.parse_args())
