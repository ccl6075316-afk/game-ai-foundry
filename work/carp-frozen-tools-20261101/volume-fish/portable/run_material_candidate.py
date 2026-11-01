"""One bounded command: author offline material, freeze source, capture local views.

Config supplies species source/authoring script/parameters, parts, full authored
roots, rename receipt and own review settings. No shape inference or acceptance.
"""
import argparse,json,subprocess,sys,time
from pathlib import Path
from fish_asset_spec import ROOT,artifact_output
from parts import read,sha
from task_power import keep_system_awake
from candidate_profile_binding import check_profiles
from material_reference_review import check_reference_review
HERE=Path(__file__).resolve().parent
def run(a):
    config=read(a.config);inputs={k:(ROOT/config[k]).resolve()for k in ['input_blend','authoring_script','authoring_config','parts_file','root_plan','rename_report','review_settings']}
    assert all(p.is_file()for p in inputs.values());binding=check_profiles(inputs['authoring_config'],inputs['root_plan'],inputs['review_settings']);material_review=check_reference_review(inputs['authoring_config']);out=artifact_output(a.output,[a.config,*inputs.values()]);assert not out.exists();out.mkdir(parents=True)
    review_inputs=[Path(material_review['report']['path'])]if material_review else[]
    source_hashes={str(p):sha(p)for p in [a.config.resolve(),*inputs.values(),*review_inputs,Path(binding['profile']['path']),Path(__file__).resolve(),HERE/'candidate_profile_binding.py',HERE/'material_reference_review.py']};manifest={'ok':False,'kind':'portable_material_candidate_run','status':'running','next_action':'poll','source_inputs':source_hashes,'stages':[],'formal_acceptance':False};started=time.time()
    def save():manifest['elapsed_seconds']=time.time()-started;(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    manifest['authoring_profile_binding']=binding
    manifest['material_reference_review']=material_review
    def stage(name,argv,timeout=300):
        row={'name':name,'argv':[str(v)for v in argv],'status':'running'};manifest['stages'].append(row);save();proc=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=timeout);log=proc.stdout.decode('utf8',errors='replace')+proc.stderr.decode('utf8',errors='replace');(out/(name+'.log')).write_text(log,encoding='utf8');assert proc.returncode==0 and not any(s in log for s in ['Traceback','SCRIPT ERROR','ERROR:','Parse Error','Assertion failed']),name+': '+log[-1400:];row.update(status='done',ok=True);save();print(json.dumps({'stage':name,'ok':True}),flush=True)
    py=sys.executable;helper=str(HERE);blend=str(a.blender.resolve());godot=str(a.godot.resolve());review=read(inputs['review_settings']);game=(ROOT/review['game']).resolve()
    try:
        stage('author',[blend,'--background','--python-exit-code','1','--python',str(inputs['authoring_script']),'--','--blend',str(inputs['input_blend']),'--config',str(inputs['authoring_config']),'--output',str(out/'author')])
        stage('pack',[py,str(HERE.parent/'pack_fish_material_atlas.py'),'--model',str(out/'author/fish.glb'),'--output',str(out/'packing')])
        parts_file=inputs['parts_file']
        if config.get('use_author_surface_roles'):
            from material_parts import from_author_report
            parts_file=out/'parts-and-view.json'
            parts=from_author_report(read(inputs['parts_file']),read(out/'packing/packing.validation.json'),read(out/'author/authoring.validation.json'),read(inputs['authoring_config'])['body'],sha(out/'author/fish.glb'))
            parts_file.write_text(json.dumps(parts,indent=2)+'\n',encoding='utf8')
        stage('spec',[py,str(HERE/'prepare_spec.py'),'--source-blend',str(out/'author/fish.blend'),'--reference-glb',str(out/'packing/merged-mask.glb'),'--atlas',str(out/'packing/atlas.png'),'--packing-report',str(out/'packing/packing.validation.json'),'--parts',str(parts_file),'--output',str(out/'spec.json'),'--json'])
        stage('source',[py,str(HERE/'run_source.py'),'--spec',str(out/'spec.json'),'--blender',blend,'--output',str(out/'source-run'),'--execute','--json'])
        stage('part-plan',[py,str(HERE/'prepare_validation.py'),'--model',str(out/'source-run/fish.glb'),'--spec',str(out/'source-run/final-spec.json'),'--output',str(out/'plans'),'--json'])
        stage('fin-plan',[py,str(HERE/'prepare_fin_validation.py'),'--root-plan',str(inputs['root_plan']),'--spec',str(out/'source-run/final-spec.json'),'--parts-manifest',str(out/'plans/parts-manifest.json'),'--mesh-renames',str(inputs['rename_report']),'--root-collar-mm','0.5','--penetration-tolerance-mm','0.02','--output',str(out/'fin.plan.json')])
        review.update(final_spec=str((out/'source-run/final-spec.json').relative_to(ROOT)),fin_plan=str((out/'fin.plan.json').relative_to(ROOT)),ordinary_reference=str((out/'author/fish.glb').relative_to(ROOT)))
        settings=out/'review-config.json';settings.write_text(json.dumps(review,indent=2)+'\n',encoding='utf8')
        from run_delivery_checks import prepare
        local=out/'local';local.mkdir();prepare(settings,local)
        stage('local-views',[godot,'--path',str(game),'--rendering-method','gl_compatibility','--audio-driver','Dummy','--position','-3000,-3000','--disable-render-loop','--script',str(HERE/'capture_local_skin.gd'),'--',str(local/'review.plan.json'),str(local/'review')])
        receipt=read(local/'review/local-capture.validation.json');assert receipt['ok']
        assert all(sha(p)==h for p,h in source_hashes.items()),'Input changed during authoring'
        final=read(out/'source-run/final-spec.json');manifest.update(ok=True,status='done',next_action='human_review',model=final['model'],final_spec=str(out/'source-run/final-spec.json'),review_capture_sha256=sha(local/'review/local-capture.validation.json'),scope='Offline material/source/cold/local view technical chain only. Actual operator review and final full077/072/490/SOP remain required.')
    except Exception as e:manifest.update(status='failed',next_action='fix_input',failure={'kind':'validation','code':'material_candidate_failed','message':str(e)[:1800]})
    save();print(json.dumps({'ok':manifest['ok'],'manifest':str(out/'manifest.json'),'elapsed_seconds':manifest['elapsed_seconds'],'failure':manifest.get('failure')}));return 0 if manifest['ok']else 1
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['config','output','blender','godot']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--json',action='store_true')
    with keep_system_awake():
        raise SystemExit(run(p.parse_args()))
