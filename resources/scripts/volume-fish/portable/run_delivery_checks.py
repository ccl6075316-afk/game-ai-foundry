"""Execute explicit species-inventory delivery gates; stop on the first failure.

Config contains final_spec, fin_plan, ordinary_reference, geometry_profile,
head_stations, head_tolerance, pose_time, details and review_sources. All input
paths resolve against the repository. No anatomical acceptance is automated.
"""
import argparse,copy,hashlib,importlib.util,json,os,struct,subprocess,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(ROOT/'cli'))
from fish_budget import check_triangle_budget
from fish_asset_spec import load_spec,resolve_ref,artifact_output
from glb_io import read_glb,arrays
from parts import read,sha
from task_power import keep_system_awake

def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf8')
def path(v):return (ROOT/v).resolve()
def dump_glb(p,doc,blob):
    j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*(-len(j)%4);blob+=b'\0'*(-len(blob)%4)
    p.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(j)+len(blob))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(blob),b'BIN\0')+blob)

def check_fin_inventory(body, manifest, authored, profile):
    expected={f['name']+suffix for f in profile['fins'] for suffix in (['_left','_right'] if f['paired'] else [''])}
    actual=manifest['fin_names']
    assert expected and len(actual)==len(set(actual)) and body not in actual
    assert manifest['body_names']==[body] and set(actual)==set(authored['fins'])
    # author_trial_pbr's explicit collision-avoidance rename only. Do not infer
    # species anatomy from a fixed seven-fin count or silently omit adipose fins.
    original=[n if n in expected else n.removesuffix('_mesh') for n in actual]
    assert len(original)==len(set(original)) and set(original)==expected, 'Fin inventory differs from own species profile'

def prepare(config_file,out):
    config=read(config_file);spec=load_spec(path(config['final_spec']));fin_path=path(config['fin_plan']);fin=read(fin_path)['items'][0]
    model=resolve_ref(spec['model']);manifest_path=Path(fin['packed_parts_manifest']);manifest=read(manifest_path)
    assert sha(model)==fin['model_sha256']==manifest['model_sha256'] and sha(manifest_path)==fin['packed_parts_manifest_sha256']
    profile=read(path(config['geometry_profile']))
    check_fin_inventory(config['body'],manifest,fin,profile)
    motion=read(resolve_ref(spec['motion']['profile']))
    assert abs(motion['real_length_cm']-profile['real_length_cm'])<1e-6,'Display length differs between geometry and motion'
    budget=check_triangle_budget(manifest['triangles'],motion['real_length_cm'])
    p={k:copy.deepcopy(fin[k])for k in ('species','model','model_sha256','motion_profile','motion_profile_sha256','motion_runtime','packed_parts_manifest','packed_parts_manifest_sha256','frozen_inputs')}
    scale=spec['viewer']['model_scale'];assert isinstance(scale,(int,float)) and scale>0
    packed,buffer=read_glb(model);primitive=packed['meshes'][0]['primitives'][0];positions=arrays(packed,buffer,primitive['attributes']['POSITION'])
    assert abs(float(positions[:,0].max()-positions[:,0].min())*scale-motion['real_length_cm']/100)<1e-5,'Actual viewer length differs from declared display length'
    write(out/'budget.validation.json',dict(budget,model_sha256=sha(model),actual_viewer_length_checked=True))
    p.update(motion_runtime_sha256=sha(p['motion_runtime']),model_scale=scale,body=config['body'],fins=list(fin['fins']),expected_triangles=manifest['triangles'],expected_body_surfaces=sum(x['opaque_uv']for x in manifest['parts']),maximum_amplitude=2.5,pose_time=config['pose_time'])
    dependencies=[config_file,fin_path,path(config['final_spec']),Path(__file__),ROOT/'cli/fish_budget.py',HERE/'logical_document.py',HERE/'validate_standalone_body.py',HERE/'capture_standalone_body.gd',HERE/'validate_motion_controls.gd']
    p['frozen_inputs'].update({str(x.resolve()):sha(x)for x in dependencies});write(out/'body-motion.plan.json',p)
    # A Boolean opening can remove the widest latitude of a construction cage.
    # Keep the independently frozen desired outer envelope distinct from the
    # cage used to produce it; do not fit the target to measured output or relax
    # its tolerance. Legacy recipes use their geometry profile as before.
    envelope_path=path(config.get('head_envelope_profile',config['geometry_profile']))
    envelope_profile=read(envelope_path)
    assert envelope_profile['species']==profile['species'] and envelope_profile['real_length_cm']==profile['real_length_cm'],'Head envelope species/display length differs'
    p['frozen_inputs'][str(envelope_path)]=sha(envelope_path)
    sections=envelope_profile['body']['sections']
    target=[[u,float(np.interp(u,[s[0]for s in sections],[s[3]for s in sections]))]for u in config['head_stations']]
    ordinary=path(config['ordinary_reference']);doc,blob=read_glb(ordinary);blob=bytearray(blob);node=next(n for n in doc['nodes']if n.get('name')==p['body']and'mesh'in n)
    for prim in doc['meshes'][node['mesh']]['primitives']:
        aid=prim['attributes']['POSITION'];a=doc['accessors'][aid];v=doc['bufferViews'][a['bufferView']];values=arrays(doc,blob,aid);values[:,2]*=.1
        offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',12)
        for i,row in enumerate(values):struct.pack_into('<3f',blob,offset+i*stride,*row)
    negative=out/'negative-narrow-head.glb';dump_glb(negative,doc,blob)
    write(out/'head.plan.json',{'items':[dict(species=p['species'],target=str(model),target_sha256=sha(model),source=str(negative),source_sha256=sha(negative),body=p['body'],fins=p['fins'],packed_parts_manifest=str(manifest_path),packed_parts_manifest_sha256=sha(manifest_path),target_half_width_envelope=target,envelope_halfwidth_tolerance_native=config['head_tolerance'])],'basis':{'profile':str(envelope_path),'sha256':sha(envelope_path),'geometry_profile':str(path(config['geometry_profile'])),'geometry_profile_sha256':sha(path(config['geometry_profile'])),'scope':'Independently frozen own-species artistic outer envelope; may differ from uncut construction cage. Synthetic90% width negative. Not a biological measurement or a visual verdict.'}})
    p.update(whole_camera_size=config['whole_camera_size'],details=config['details'],review_sources=[])
    for ref in config['review_sources']:
        q=path(ref);p['review_sources'].append({'path':str(q),'sha256':sha(q)})
    p['frozen_inputs'].update({str(HERE/name):sha(HERE/name)for name in ['capture_fish_review.gd','ReviewCaptureBase.gd']});write(out/'review.plan.json',p)
    return config,p

def run(args):
    out=artifact_output(args.output);assert not out.exists();out.mkdir(parents=True)
    config,p=prepare(args.config.resolve(),out);game=path(config['game']);godot=str(args.godot.resolve());blender=str(args.blender.resolve())
    status={'ok':False,'kind':'portable_delivery_gate_manifest','species':p['species'],'model':p['model'],'model_sha256':p['model_sha256'],'status':'running','next_action':'poll','formal_acceptance':False,'user_acceptance':False,'config_sha256':sha(args.config),'stages':[{'name':'budget','ok':True,'status':'done','report':str(out/'budget.validation.json'),'report_sha256':sha(out/'budget.validation.json')}]};started=time.time()
    def save():status['elapsed_seconds']=time.time()-started;write(out/'manifest.json',status)
    def stage(name,cmd,report,expect=False,timeout=900):
        row={'name':name,'argv':[str(x)for x in cmd],'status':'running'};status['stages'].append(row);save()
        run=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);log=run.stdout.decode('utf8',errors='replace');(out/(name+'.log')).write_text(log,encoding='utf8')
        assert not any(s in log for s in ['ERROR:','SCRIPT ERROR','Parse Error','Assertion failed']),name+': '+log[-1800:]
        result=read(report);assert result.get('ok')is (not expect),name+': '+str(result.get('error',result.get('failures','')))
        assert (run.returncode!=0)if expect else run.returncode==0,name+' exit code mismatch'
        row.update(status='done',ok=True,report=str(report),report_sha256=sha(report),expected_rejection=expect);save();print(json.dumps({'stage':name,'ok':True}),flush=True)
    base=[godot,'--headless','--path',str(game),'--script']
    py=sys.executable
    try:
        stage('import',base+[str(HERE/'validate_import.gd'),'--',p['packed_parts_manifest'],str(out/'import.validation.json')],out/'import.validation.json')
        stage('motion',base+[str(HERE/'validate_motion_controls.gd'),'--',str(out/'motion.validation.json'),'--standalone-plan',str(out/'body-motion.plan.json')],out/'motion.validation.json')
        # Load by absolute file, avoiding legacy modules with identical basenames.
        modspec=importlib.util.spec_from_file_location('portable_body_gate',HERE/'validate_standalone_body.py');module=importlib.util.module_from_spec(modspec);modspec.loader.exec_module(module)
        sys.path.insert(0,str(HERE));result=module.validate(game,Path(godot),out/'body-motion.plan.json',out/'body077');assert result['ok'],'body077: '+str(result.get('error'))
        status['stages'].append({'name':'body077','ok':True,'status':'done','report':str(out/'body077/completion.validation.json'),'report_sha256':sha(out/'body077/completion.validation.json')});save();print('{"stage":"body077","ok":true}',flush=True)
        for negative in [False,True]:
            label='negative-head'if negative else'head';report=out/(label+'.validation.json')
            stage(label,[py,str(HERE/'check_head_form.py'),'--plan',str(out/'head.plan.json'),'--output',str(report)]+(['--baseline']if negative else[]),report,expect=negative)
        review=out/'review';review.mkdir()
        stage('review',[godot,'--path',str(game),'--rendering-method','gl_compatibility','--audio-driver','Dummy','--position','-3000,-3000','--disable-render-loop','--script',str(HERE/'capture_fish_review.gd'),'--',str(out/'review.plan.json'),str(review)],review/'review-capture.validation.json',timeout=180)
        stage('fin490',[py,str(HERE.parent/'validate_fin_membrane_clearance.py'),'--plan',str(path(config['fin_plan'])),'--game',str(game),'--godot',godot,'--blender',blender,'--output',str(out/'fin490'),'--species',p['species'],'--exporter',str(HERE/'export_fin_poses.gd'),'--checker-timeout','600','--export-timeout','300','--membrane-workers','4'],out/'fin490/completion.validation.json')
        stage('root072',[py,str(HERE.parent/'validate_fin_completion.py'),'--plan',str(path(config['fin_plan'])),'--game',str(game),'--godot',godot,'--blender',blender,'--output',str(out/'root072'),'--species',p['species'],'--exporter',str(HERE/'export_fin_poses.gd'),'--reuse-full490-completion',str(out/'fin490/completion.validation.json')],out/'root072/completion.validation.json')
        assert sha(p['model'])==p['model_sha256'];status.update(ok=True,status='done',next_action='human_review')
    except Exception as e:
        status.update(status='failed',next_action='fix_input',failure={'kind':'validation','code':'delivery_gate_failed','message':str(e)[:2400]})
    save();print(json.dumps({'ok':status['ok'],'manifest':str(out/'manifest.json'),'failure':status.get('failure')}));return 0 if status['ok']else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ['config','output','godot','blender']:parser.add_argument('--'+k,type=Path,required=True)
    with keep_system_awake():
        raise SystemExit(run(parser.parse_args()))
