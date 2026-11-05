"""Explicit operator review of surviving pixels, without invented generation jobs.

This is a separate source gate. Historical generation/model acceptance is never
reconstructed; the reviewed pixel hash must still match an accepted historical
source. Every build rechecks the new receipt and all surviving inputs.
"""
from pathlib import Path
from datetime import datetime


def snapshot(review: Path, profile: Path, output: Path) -> dict:
    import volume_fish as v
    r = v.read_json(review)
    v.keys(r, {'kind','schema_version','species','real_length_cm','source','style_reference','review','provenance'},
           {'kind','schema_version','species','real_length_cm','source','style_reference','review','provenance'}, 'existing pixels receipt')
    v.require(r['kind']=='fish_existing_pixels_review' and type(r['schema_version']) is int and r['schema_version']==1,
              'Unsupported existing pixels receipt')
    def text(value, label):
        v.require(isinstance(value,str) and bool(value.strip()), label+' must be nonempty')
    text(r['species'],'Species')
    p, ref = v.validate_profile(v.read_json(profile), profile)
    v.require(p['species']==r['species'] and type(r['real_length_cm']) in (int,float)
              and p['real_length_cm']==r['real_length_cm'], 'Review species/length differs from profile')
    files={'review':review,'profile':profile}
    for role in ('source','style_reference'):
        entry=v.keys(r[role], {'path','sha256'}, {'path','sha256'}, role)
        files[role]=v.resolve_file(entry['path'],review.parent)
        v.require(v.sha(files[role])==entry['sha256'], role+' pixels changed')
    source=v.image_info(files['source'],transparent=True)
    v.require(ref['sha256']==r['style_reference']['sha256'] and ref['path']==str(files['style_reference']),
              'Reviewed style reference differs from profile')
    v.require(abs(p['source_aspect_ratio']/(source['width']/source['height'])-1)<=.02, 'Source/profile aspect mismatch')
    rv=v.keys(r['review'], {'status','reviewer','reviewed_at','observations','evidence'}, {'status','reviewer','reviewed_at','observations','evidence'}, 'operator source review')
    v.require(rv['status']=='accepted', 'Existing pixels require an accepted operator source/style review')
    text(rv['reviewer'],'Reviewer');text(rv['reviewed_at'],'Review timestamp')
    try:
        stamp=datetime.fromisoformat(rv['reviewed_at'].replace('Z','+00:00'))
        v.require(stamp.tzinfo is not None, 'Review timestamp requires timezone')
    except ValueError as exc:
        raise v.VolumeError('Invalid review timestamp') from exc
    observations=v.keys(rv['observations'], {'source','style','species','limitations'}, {'source','style','species','limitations'}, 'source review observations')
    for key,value in observations.items():text(value,'Observation '+key)
    evidence=v.keys(rv['evidence'], {'source','style'}, {'source','style'}, 'actual source/style image review evidence')
    for role,item in evidence.items():
        v.keys(item, {'path','sha256','observation'}, {'path','sha256','observation'}, 'review evidence '+role)
        text(item['observation'],'Evidence observation '+role)
        ep=v.resolve_file(item['path'],review.parent)
        v.image_info(ep)
        v.require(v.sha(ep)==item['sha256'],'Actual review evidence changed: '+role)
        files['evidence_'+role]=ep
    prov=v.keys(r['provenance'], {'kind','description','historical_handoff','historical_profile'}, {'kind','description','historical_handoff','historical_profile'}, 'existing pixel provenance')
    v.require(prov['kind']=='existing_pixels','Must declare existing_pixels, not generation pipeline')
    text(prov['description'],'Existing source provenance description')
    oldref=v.keys(prov['historical_handoff'], {'path','sha256'}, {'path','sha256'}, 'historical source receipt')
    files['historical_handoff']=v.resolve_file(oldref['path'],review.parent)
    v.require(v.sha(files['historical_handoff'])==oldref['sha256'],'Historical receipt changed')
    old=v.read_json(files['historical_handoff'])
    v.require(old.get('kind')=='fish_volume_handoff' and old.get('source_review',{}).get('status')=='accepted',
              'Historical source was not accepted')
    v.require(old.get('source',{}).get('sha256')==source['sha256'], 'Surviving pixels differ from historical accepted source')
    # Resolve surviving profile bytes explicitly; a filename substring is not identity.
    hp=v.keys(prov['historical_profile'], {'path','sha256'}, {'path','sha256'}, 'historical species profile')
    files['historical_profile']=v.resolve_file(hp['path'],review.parent)
    raw=files['historical_profile'].read_bytes()
    import hashlib
    v.require(v.sha(files['historical_profile'])==hp['sha256'], 'Historical profile changed')
    hashes={hp['sha256'],hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()}
    v.require(old.get('profile_snapshot',{}).get('sha256') in hashes,'Historical profile snapshot mismatch')
    identity=v.read_json(files['historical_profile'])
    v.require(identity.get('species')==r['species'] and identity.get('real_length_cm')==r['real_length_cm']
              and old.get('real_length_cm')==r['real_length_cm'], 'Historical species/length mismatch')
    v.require(not any(k in p for k in ('head_projection','dorsal_projection','ventral_projection','rest_shape_revision')),
              'Auxiliary inputs require their own independently reviewed source gate')
    inputs=set(files.values())
    v.require(output not in inputs and not any(Path(x) in inputs for x in v.expected_outputs(output).values()), 'Outputs must not overwrite review inputs')
    source['provenance_kind']='operator_existing_pixel_review'
    return {'schema_version':1,'kind':'fish_volume_handoff','status':'pending','next_action':'run',
            'asset':r['species']+'_reviewed_pixels','source_image':source['path'],'source':source,
            'source_review':{'status':'accepted','source':'operator_existing_pixel_review','updated_at':rv['reviewed_at'],
                             'reviewer':rv['reviewer'],'observations':observations},
            'profile':str(profile),'profile_snapshot':{'path':str(profile),'sha256':v.sha(profile)},
            'real_length_cm':p['real_length_cm'],'outputs':v.expected_outputs(output),
            'style_contract':{'pixel_art':True,'source_sha256':source['sha256'],'style_reference_image':ref['path'],
                              'style_reference_sha256':ref['sha256'],'texture_filter':'nearest','roughness':1.0},
            'style_visual_review':'pending','failures':[],
            'reviewed_source_receipt':{'path':str(review),'sha256':v.sha(review),'fingerprint':{k:v.sha(path) for k,path in files.items()},
                                      'scope':'New operator review of surviving existing pixels only. No generation pipeline, historical missing file, model approval, or user acceptance claimed.'}}


def plan_reviewed_source(review: Path, profile: Path, output: Path) -> dict:
    import volume_fish as v
    from volume_sop import start_production
    review,profile,output=(Path(x).resolve() for x in (review,profile,output))
    v.require(not output.exists(), 'Choose a fresh handoff output')
    ledger=output.with_name(output.stem+'-sop-review.json')
    v.require(not ledger.exists(),'Choose a fresh production ledger; do not inherit a prior review')
    data=snapshot(review,profile,output)
    data['production']=start_production(output,v.read_json(profile)['species'],'rebuild',{'source_image':data['source_image'],'species_profile':profile})
    v.write_json(output,data)
    return data


def fresh_reviewed_source(data: dict, path: Path) -> dict:
    import volume_fish as v
    receipt=data['reviewed_source_receipt']
    review=v.resolve_file(receipt['path'],path.parent)
    v.require(v.sha(review)==receipt['sha256'],'Existing pixel review changed after plan')
    expected=snapshot(review,v.resolve_file(data['profile'],path.parent),path)
    for key,value in expected.items():
        if key not in {'status','next_action','style_visual_review','failures'}:
            v.require(data.get(key)==value,'Reviewed source input changed after plan: '+key)
    return data
