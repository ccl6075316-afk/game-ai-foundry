"""Plan/execute exact hash-verified cleanup for one completed database revision.

Protects every current SOP candidate/evidence file. No archive is constructed.
Only explicitly regenerable samples, duplicate captures and superseded source
outputs in this one experiment directory are eligible.
"""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main(a):
    root=a.directory.resolve();assert root.is_relative_to(ROOT/'projects/fishing-2d/experiments/five-fish-database-20261103') and root.name==a.species
    sop=read(root/'sop.validation.json');assert sop['ok'];review=read(root/'production-review.json');protected={Path(x['path']).resolve() for x in [*review['candidate_files'].values(),*review['evidence'].values()]};protected|={root/'production-review.json',root/'sop.validation.json'}
    assert a.prefix.replace('-','').isalnum()
    planfile=root/(a.prefix+'.plan.json');receipt=root/(a.prefix+'-execution.json')
    if a.execute:
        plan=read(planfile);assert plan['root']==str(root) and plan['model_sha256']==review['candidate_files']['model']['sha256'] and plan['sop_sha256']==sha(root/'sop.validation.json')
        for row in plan['delete']:
            p=Path(row['path']);assert p.resolve().is_relative_to(root) and p.resolve()==p and p not in protected and not p.is_symlink();assert all(not q.is_symlink() for q in p.parents if q.is_relative_to(root));assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
        removed=[]
        for row in plan['delete']:
            Path(row['path']).unlink();removed.append(row)
        result={'ok':True,'scope':plan['scope'],'removed_files':len(removed),'removed_bytes':sum(r['bytes'] for r in removed),'exact_deleted_files':removed,'retained_files':sum(1 for p in root.rglob('*') if p.is_file()),'retained_bytes_before_receipt':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),'current_model_sha256':review['candidate_files']['model']['sha256'],'sop_sha256':sha(root/'sop.validation.json'),'new_archives_created':0};write(receipt,result);print(json.dumps({k:v for k,v in result.items() if k!='exact_deleted_files'}));return
    targets=set();keep_samples={0,1,2,250,489};current_delivery=Path(read(root/'current-evidence.validation.json')['actual_capture']['path']).parent.parent;export=current_delivery/f'fin490/{a.species}/export.validation.json'
    if export.exists():
        roots=read(current_delivery/f'fin490/{a.species}/roots.validation.json')
        if roots['samples']:
            keep_samples.add(max(range(len(roots['samples'])),key=lambda i:max(r['max_signed_distance_cm'] for r in roots['samples'][i]['fins'].values())))
            keep_samples.add(min(range(len(roots['samples'])),key=lambda i:min(r['min_signed_distance_cm'] for r in roots['samples'][i]['fins'].values())))
        for i,row in enumerate(read(export)['samples']):
            p=Path(row['posed_mesh_json']);assert p.is_relative_to(root)
            if i not in keep_samples and p.exists():targets.add(p)
    keep_frames={0,24,48,96,144,192,240,252,264,276}
    for p in (current_delivery/'review/frames').glob('frame-*.jpg'):
        if int(p.stem.split('-')[-1]) not in keep_frames:targets.add(p)
    retained_old={
      'width-r1/review/before-head-bottom-texture.png','width-r1/review/before-whole-top-clay.png','width-r1/review/before-head-oblique-texture.png','material-r1/review/after-head-top-clay.png',
      'width-r2/review/after-head-oblique-texture.png','width-r2/review/after-head-bottom-texture.png','width-r2/review/after-head-top-clay.png','width-r2/review/after-whole-top-clay.png','width-r2/review/after-whole-left-texture.png',
      'unlit-review/after-whole-left-texture.png','unlit-review/after-whole-right-texture.png','unlit-review/after-head-bottom-texture.png','unlit-review/before-head-bottom-texture.png'}
    for folder in ['width-r1/review','material-r1/review','width-r2/review','unlit-review']:
        for p in (root/folder).glob('*.png'):
            if p.relative_to(root).as_posix() not in retained_old:targets.add(p)
    for folder in ['delivery-r1/body077','delivery-r2/body077']:
        for p in (root/folder).glob('p*-v*-*.png'):
            if folder.startswith('delivery-r1') or p.name not in ['p0-v0-actual.png','p0-v0-closed.png','p1-v0-actual.png','p1-v0-closed.png']:targets.add(p)
    for filename in ['width-r1/fish.blend','width-r1/fish.glb','material-r1/fish.blend','material-r1/cold-fish.glb','width-r2/cold-fish.glb','delivery-r1/negative-narrow-head.glb']:
        p=root/filename
        if p.exists():targets.add(p)
    # Other fish may need more iterations. Preserve current sources and reports,
    # one failed candidate GLB per revision, and representative superseded views.
    if a.species!='rainbow_trout':
        for folder in root.glob('delivery-*'):
            if folder!=current_delivery:
                for q in (folder/'review').glob('*.png'):
                    if q.name not in ['head-top-clay.png','head-bottom-texture.png','mouth-front-texture.png']:targets.add(q)
                targets.update(folder.glob(f'fin490/{a.species}/poses/*.json'))
                for e in folder.glob(f'fin490/{a.species}/export.validation.json'):
                    sampled=read(e).get('samples',[]);keep_failed={0}
                    mr=e.parent/'membranes.validation.json'
                    if mr.exists():
                        for value in read(mr).get('summary',{}).values():
                            pose=value.get('worst_pose')
                            if value.get('failed_poses',0) and pose:
                                keep_failed.update(i for i,row in enumerate(sampled) if row['action']==pose['action'] and abs(row['seconds']-pose['seconds'])<1e-6)
                    for i,row in enumerate(sampled):
                        q=Path(row['posed_mesh_json'])
                        if q.exists() and i not in keep_failed:targets.add(q)
                targets.update((folder/'review/frames').glob('*.jpg'))
                targets.update((folder/'body077').glob('p*-v*-*.png'))
            else:
                for q in (folder/'body077').glob('p*-v*-*.png'):
                    if q.name not in ['p0-v0-actual.png','p0-v0-closed.png','p1-v0-actual.png','p1-v0-closed.png']:targets.add(q)
        for folder in root.glob('width-*'):
            for q in folder.glob('*.blend'):targets.add(q)
            targets.update(folder.glob('cold-fish.glb'))
            for q in (folder/'review').glob('*.png'):
                if q.name not in ['before-head-bottom-texture.png','after-head-bottom-texture.png','after-whole-top-clay.png']:targets.add(q)
        for q in (root/'skin-fit/compact').rglob('matrices-*.json'):
            if int(q.stem.split('-')[-1]) not in [0,382,489]:targets.add(q)
        for q in root.glob('gates-*/volume-source.blend'):
            if q not in protected:targets.add(q)
    current_gates=Path(review['candidate_files']['final_spec']['path']).parent
    for q in root.glob('gates-*/ordinary-reference.glb'):
        if q.parent!=current_gates:targets.add(q)
    for q in root.glob('delivery-*/negative-narrow-head.glb'):
        if q.parent!=current_delivery:targets.add(q)
    targets-=protected
    rows=[{'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(targets)]
    plan={'kind':'exact_single_fish_experiment_cleanup','root':str(root),'scope':'Passing dense490 cache except static/extreme/representative samples; duplicate video frames except10 phases; superseded captures, redundant cold export, replaced source intermediates. Current source/model, actual failure GLB, required raw inputs, all current SOP evidence, complete numeric reports, full movie and critical views retained. Historical captures may refer to intentionally retired rebuildable caches; no complete old author-chain byte replay promised.','model_sha256':review['candidate_files']['model']['sha256'],'sop_sha256':sha(root/'sop.validation.json'),'protected_current_files':[str(p) for p in sorted(protected)],'retained_pose_indices':sorted(keep_samples),'retained_movie_frames':sorted(keep_frames),'delete':rows,'delete_bytes':sum(r['bytes'] for r in rows),'delete_files':len(rows)};write(planfile,plan);print(json.dumps({'ok':True,'planned_files':len(rows),'planned_bytes':plan['delete_bytes'],'plan':str(planfile)}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True,type=Path);p.add_argument('--species',required=True);p.add_argument('--prefix',default='cleanup');p.add_argument('--execute',action='store_true');main(p.parse_args())
