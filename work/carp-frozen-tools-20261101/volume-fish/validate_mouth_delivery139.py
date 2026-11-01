"""Bind actual resources, reviewed-source provenance and per-fish139 gates."""
import argparse,hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['plan','game','root','runtime','media','controls','review','output']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();rows=[]
    try:
        plan=read(a.plan);cfg=read(a.game/'assets/models/fish/motion/mouth-repair139.json');assert cfg==plan['config'];cfg_hash=sha(a.game/'assets/models/fish/motion/mouth-repair139.json')
        runtime=read(a.runtime/'completion.validation.json');body=read(a.runtime/'body-integrity/completion.validation.json');assert runtime['ok'] and body['ok'] and body['candidate_plan_sha256']==sha(a.plan)
        assert len(body['records'])==14 and {r['species'] for r in body['records']}==set(cfg['profiles'])
        videos=read(a.media/'video.validation.json');capture=read(a.media/'capture.validation.json');assert videos['ok'] and capture['ok'] and capture['config_sha256']==cfg_hash and videos['capture_sha256']==sha(a.media/'capture.validation.json')
        assert len(capture['rows'])==14 and all(r['binding']['ok'] for r in capture['rows'])
        controls=read(a.controls);assert controls['ok'] and controls['config_sha256']==cfg_hash and len(controls['checks'])==14
        review=read(a.review);assert review['mouth_delta_reviewed'] and set(review['records'])==set(cfg['profiles'])
        assert read(a.root/'source-package139/completion.validation.json')['ok']
        for item in plan['items']:
            s=item['species'];spec=item['profile'];assert sha(a.game/f'assets/models/fish/{s}.glb')==spec['source_model_sha256']
            for source,rel in item['copies'].items():assert sha(source)==sha(a.game/rel),'Staged resource differs from frozen candidate'
            base=a.root/s
            if s=='black_seabream':fin_plan=base/'localized/actual-fin139.plan.json';root_report=base/'localized/actual-root177139/completion.validation.json';full_report=base/'localized/actual-full-fin139/completion.validation.json';export=base/'localized/actual-full-fin139/black_seabream/export.validation.json'
            elif s=='peacock_bass':fin_plan=base/'repaired-parts139-v3.plan.json';root_report=base/'repaired-root177139-v3/completion.validation.json';full_report=base/'repaired-parallel-fin139-v3/completion.validation.json';export=base/'repaired-full-fin139-v3/peacock_bass/export.validation.json'
            else:fin_plan=base/'fin.plan.json';root_report=base/'fin-root177/completion.validation.json';full_report=base/'full-fin490/completion.validation.json';export=base/f'full-fin490/{s}/export.validation.json'
            root=read(root_report);full=read(full_report);exp=read(export);fp=read(fin_plan)['items'][0]
            assert root['ok'] and root['plan_sha256']==sha(fin_plan) and full['ok'] and full['poses']==490 and full['plan_sha256']==sha(fin_plan)
            expected={item['geometry']['path']:item['geometry']['sha256'],item['skinning_report']['path']:item['skinning_report']['sha256']}
            if 'fin_geometry' in item:expected[item['fin_geometry']['path']]=item['fin_geometry']['sha256']
            assert exp['candidate_input_sha256']==expected==fp['mouth_candidate']['frozen_inputs']
            assert exp['model_sha256']==spec['source_model_sha256'] and exp['exhibit_sha256']==sha(a.game/'scripts/aquarium/VolumeFishExhibit.gd') and exp['controller_sha256']==sha(a.game/exp['controller_source'].removeprefix('res://'))
            count=sum(len(part['triangles'])//3 for part in read(item['geometry']['path'])['parts']);assert exp['body_triangles']==count,'Fin gate used a different body'
            for check in full['checks']:assert check['ok'] and sha(check['report'])==check['sha256']
            record=review['records'][s];assert record['mouth_delta_ready']
            rows.append({'species':s,'ok':True,'root_report':str(root_report),'root_sha256':sha(root_report),'full_fin_report':str(full_report),'full_fin_sha256':sha(full_report),'body_resource_sha256':spec['body']['sha256'],'source_provenance':str(a.root/f'source-package139/{s}/provenance.validation.json')})
        result={'ok':len(rows)==14,'mouth_delta_ready':len(rows)==14,'whole_fish_acceptance':False,'install_plan_sha256':sha(a.plan),'records':rows,'runtime_sha256':sha(a.runtime/'completion.validation.json'),'media_sha256':sha(a.media/'capture.validation.json'),'controls_sha256':sha(a.controls),'review_sha256':sha(a.review),'checker_sha256':sha(__file__),'scope':'Authorized mouth/head repairs and accepted135 integration only. Required current technical gates and operator mouth review; no user visual acceptance or claim that all historical body-art observations are resolved.'}
    except Exception as e:result={'ok':False,'mouth_delta_ready':False,'error':str(e),'records':rows}
    a.output.write_text(json.dumps(result,indent=2));print(json.dumps({'ok':result['ok'],'error':result.get('error'),'fish':len(rows)}));return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
