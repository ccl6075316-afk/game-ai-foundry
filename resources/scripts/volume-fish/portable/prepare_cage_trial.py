"""Prepare a source cage from explicit species data, reusing accepted archive gates.

Original sections and full source fin polygons remain authoritative; a declared
same-species transverse target is an artistic hypothesis, not a biological fit.
"""
import argparse,copy,json
from pathlib import Path
import numpy as np
from fish_asset_spec import ROOT,artifact_output
from parts import read,sha
def prepare(config_path,out):
    config=read(config_path);accepted=(ROOT/config['accepted_handoff']).resolve();old=read(accepted);original=(ROOT/config['original_profile']).resolve();profile=copy.deepcopy(read(original));assert old['style_visual_review']=='accepted'and profile['species']==config['species']
    source=(ROOT/config['source']).resolve();assert sha(source)==old['source']['sha256']
    artifact_dir=accepted.parent/(accepted.stem+'-artifacts');reference=ROOT/profile['style']['reference_image'].removeprefix('repo://')
    archive={'accepted_handoff':str(accepted),'profile':str(original),'blend':str(artifact_dir/'fish.blend'),'glb':str(artifact_dir/'fish.glb'),'source':str(source),'reference':str(reference),'review_images':{key:str(artifact_dir/'review'/({'style_comparison':'style-comparison.png','master_comparison':'master-comparison.png'}.get(key,key+'.png')))for key in old['style_review']['hashes']['review_images']}}
    assert all(Path(v).is_file()for k,v in archive.items()if k!='review_images')and all(Path(v).is_file()for v in archive['review_images'].values())
    envelope=config['head_envelope'];sections=profile['body']['sections'];extra=config.get('additional_stations',[])
    assert all(isinstance(u,(int,float))and not isinstance(u,bool)and sections[0][0]<=u<=sections[-1][0]for u in extra),'Additional stations must stay within this species body'
    positions=sorted({s[0]for s in sections}|{s[0]for s in envelope}|{s[0]for s in profile['oral_jaws']['slit_path']}|set(extra));assert min(positions)==sections[0][0]and max(positions)==sections[-1][0]
    new=[]
    for u in positions:
        row=[u]+[float(np.interp(u,[s[0]for s in sections],[s[i]for s in sections]))for i in [1,2,3]]
        if u>=envelope[0][0]:row[3]=float(np.interp(u,[s[0]for s in envelope],[s[1]for s in envelope]))
        new.append(row)
    profile['body'].update(sections=new,ring_positions=positions,rings=len(positions),radial=config['radial']);profile['oral_jaws']['lip_bevel']=0;profile['native_fin_cutouts']=True
    if 'oral_boolean_solver' in config:
        assert config['oral_boolean_solver'] in ('EXACT','MANIFOLD')
        profile['oral_jaws']['boolean_solver']=config['oral_boolean_solver']
    for fin in profile['fins']:
        fin['interior_grid']=config['fin_interior_grid'];fin['root_attachment']['baseline_spacing']=config['baseline_spacing']
    profile['notes'].append(config['scope'])
    target=(ROOT/config['output_profile']).resolve();assert target.is_relative_to(ROOT/'resources/volume-fish')and not target.exists()
    out=artifact_output(out,[config_path,source,accepted,original]);assert not out.exists();out.mkdir(parents=True)
    target.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(out/'archive-inputs.json').write_text(json.dumps(archive,indent=2)+'\n',encoding='utf8')
    receipt={'ok':True,'kind':'explicit_cage_trial_preparation','species':profile['species'],'status':'pending','next_action':'run','source_sha256':sha(source),'profile':str(target),'profile_sha256':sha(target),'config_sha256':sha(config_path),'rings':len(positions),'radial':config['radial'],'installed':False,'user_acceptance':False,'scope':'Preparation only; volume replan must independently verify full historical acceptance and archive before build.'}
    (out/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--json',action='store_true');a=p.parse_args()
    try:r=prepare(a.config,a.output);print(json.dumps({'ok':True,'rings':r['rings'],'profile':r['profile']}))
    except (ValueError,AssertionError,OSError,KeyError)as e:print(json.dumps({'ok':False,'next_action':'fix_input','error':str(e)}));raise SystemExit(1)
