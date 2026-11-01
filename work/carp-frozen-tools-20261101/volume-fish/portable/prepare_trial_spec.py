"""Bind actual native clip/bones/inventory to explicitly declared anatomical roles.

No source-form inference: caller supplies body surface roles, every fin node and
an explicit old-to-actual bone alias map. One unambiguous native clip is required.
"""
import argparse,copy,json
from pathlib import Path
from parts import read,sha,require,fresh_output
from glb_io import read_glb,arrays
from fish_asset_spec import ROOT

def prepare(model,packing_file,role_file,motion_template,species,length_cm,runtime,motion_output,output):
    model=Path(model).resolve();packing_file=Path(packing_file).resolve();role_file=Path(role_file).resolve();runtime=Path(runtime).resolve()
    packing=read(packing_file);roles=read(role_file);doc,blob=read_glb(model)
    require(packing['ok'] and packing['candidates']['merged-mask']['sha256']==sha(model),'Stale packing/model')
    require(len(doc['animations'])==1 and bool(doc['animations'][0].get('name')),'Select one unambiguous named native clip')
    require(length_cm>0 and len(doc['skins'])==1 and runtime.is_file(),'Positive length, one skin and existing controller required')
    clips=doc['animations'][0]['name'];joint_names={doc['nodes'][i]['name']for i in doc['skins'][0]['joints']}
    template=read(motion_template);profile=copy.deepcopy(template['profiles'][species]if'profiles'in template else template)
    require(profile['species']==species,'Species mismatch')
    aliases=roles.get('bone_aliases',{});require(all(k not in joint_names and v in joint_names for k,v in aliases.items()),'Aliases must explicitly resolve only missing old bones to actual source bones')
    profile['body_bones']=[aliases.get(k,k)for k in profile['body_bones']]
    profile['fin_motion_constraints']={aliases.get(k,k):v for k,v in profile.get('fin_motion_constraints',{}).items()}
    require(set(profile['body_bones'])|set(profile['fin_motion_constraints'])<=joint_names,'Unresolved native bones; declare exact aliases')
    require(len(profile['body_bones'])==len(set(profile['body_bones'])),'Aliased duplicate body bones')
    profile.update(base_clip=clips,real_length_cm=length_cm)
    body=roles['body'];surfaces={int(k):v for k,v in roles['body_surfaces'].items()};fins=roles['fin_nodes']
    require(len(fins)==len(set(fins)) and body not in fins,'Unique explicit anatomical inventory required')
    parts=[];seen=set()
    for row in packing['parts']:
        node=row['node'];surface=row['surface'];seen.add((node,surface))
        require(node==body or node in fins,'Unlisted anatomical node: '+node)
        role=surfaces[surface]if node==body else'fin'
        parts.append({'name':node+'_'+str(surface),'logical_name':node,'role':role,'source_node':node,'source_surface':surface})
    require({n for n,s in seen}=={body,*fins} and {s for n,s in seen if n==body}==set(surfaces),'Incomplete anatomical inventory')
    primitive=doc['meshes'][0]['primitives'][0];pos=arrays(doc,blob,primitive['attributes']['POSITION']);span=float(pos[:,0].max()-pos[:,0].min());require(span>0,'Zero whole-fish length')
    motion_output=Path(motion_output).resolve();require(motion_output.is_relative_to(ROOT/'resources/volume-fish')and not motion_output.exists(),'Fresh explicit motion profile under resources/volume-fish required')
    output=fresh_output(output);require(not output.exists(),'Fresh output directory required')
    result={'species':species,'game':roles['game'],'parts':parts,'motion':{'api':'foundry_motion_v1','runtime':{'path':str(runtime.relative_to(ROOT)),'sha256':sha(runtime)},'profile':{'path':str(motion_output.relative_to(ROOT)),'sha256':''},'action':'Swim'},'viewer':{'model_scale':length_cm/100/span,'native_clip':clips,'focuses':roles.get('focuses',{}),'captures':[{'name':name,'yaw_degrees':yaw,'pitch_degrees':pitch,'time_seconds':0}for name,yaw,pitch in [('side',0,0),('reverse',180,0),('front',90,0),('oblique',35,15),('top',0,85),('bottom',0,-85)]]}}
    motion_output.parent.mkdir(parents=True,exist_ok=True);motion_output.write_text(json.dumps(profile,indent=2)+'\n',encoding='utf8');result['motion']['profile']['sha256']=sha(motion_output)
    output.mkdir(parents=True);(output/'parts-and-view.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    receipt={'ok':True,'kind':'explicit_trial_inputs','source_inputs':{str(p):sha(p)for p in [model,packing_file,role_file,Path(motion_template),runtime]},'parts':len(parts),'native_clip':clips,'native_joint_names':sorted(joint_names),'explicit_bone_aliases':aliases,'model_scale':result['viewer']['model_scale'],'motion_profile':str(motion_output),'motion_profile_sha256':sha(motion_output),'visual_review':'pending','scope':'Native binding/configuration only; no anatomy, root, color or acceptance inferred.'}
    (output/'preparation.validation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['model','packing-report','roles','motion-template','runtime','motion-profile-output','output']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--species',required=True);p.add_argument('--real-length-cm',type=float,required=True);p.add_argument('--json',action='store_true');a=p.parse_args()
    try:
        r=prepare(a.model,a.packing_report,a.roles,a.motion_template,a.species,a.real_length_cm,a.runtime,a.motion_profile_output,a.output);print(json.dumps({'ok':True,'parts':r['parts'],'native_clip':r['native_clip'],'model_scale':r['model_scale']}))
    except (ValueError,AssertionError,KeyError,TypeError,OSError)as e:print(json.dumps({'ok':False,'status':'failed','next_action':'fix_input','failures':[{'kind':'validation','code':'trial_input_invalid','message':str(e)}]}));raise SystemExit(1)
