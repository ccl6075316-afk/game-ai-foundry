"""Summarize completed controlled actual-GPU cases; never infer FPS or pure GPU time.

The aggregate manifest is explicitly assembled AFTER actual per-case execution.
No rendering, fish repair, production installation or acceptance occurs here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
EXPERIMENT=ROOT/'projects/fishing-2d/experiments/nile-dorsal-route-trial/round10-material-performance'
VARIANTS=('baseline9','merged-mask','merged-opaque')
TIMES=('motion_call_ms','engine_refresh_wait_ms','forced_draw_readback_ms','controlled_step_ms')
FIELDS=TIMES+('draw_calls','primitives')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def artifact(p):return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def distribution(values):
    assert values and all(math.isfinite(float(v))and v>=0 for v in values),'Invalid raw metric'
    a=sorted(values);n=len(a)
    return {'samples':n,'p50':a[int((n-1)*.5)],'p95':a[int((n-1)*.95)],'min':a[0],'max':a[-1],'mean':sum(a)/n}
def normalize_frozen(inputs):
    result={}
    for p,h in inputs.items():
        name=str(Path(p).resolve());assert name not in result or result[name]==h,'Conflicting input aliases';result[name]=h
    return result

def check_samples(report,count,animated,variant):
    """Minimized own window is expected; validate the actual explicit GPU work."""
    assert report['protocol']=='controlled-v1'and report['kind']=='fish_material_controlled_case'
    raw=report['raw_samples'];assert len(raw)==60
    assert report['explicit_draw_signals_total']==75
    assert report['actual_pose_changed']is bool(animated)and report['actual_GPU_image_changed']is bool(animated)
    assert (report['first_pose_sha256']!=report['last_pose_sha256'])==animated
    assert (report['first_image_RGBA_sha256']!=report['last_image_RGBA_sha256'])==animated
    assert report['gpu_timer_available']is False
    for key in ('first_window_state','last_window_state'):
        state=report[key]
        assert state['minimized']is True and state['can_draw']is False and state['always_on_top']is False
        assert state['root_visible']is True and state['viewport_rid_valid']is True
        assert state['viewport_size']==[1280,720]and state['viewport_update_mode']==4
    for row in raw:
        assert row['explicit_draw_signals']==1
        assert row['draw_calls']==count*(9 if variant=='baseline9'else 1)
        assert row['primitives']==count*1710
        for field in TIMES:assert math.isfinite(row[field])and row[field]>=0
        assert abs(row['controlled_step_ms']-sum(row[k]for k in TIMES[:3]))<=.005,'Inconsistent component timings'
    measured={field:distribution([x[field]for x in raw])for field in FIELDS}
    for field,metrics in measured.items():
        for key in ('p50','p95','min','max','mean'):assert abs(report[field][key]-metrics[key])<=1e-8*max(1,abs(metrics[key])),(field,key)
    return measured

def validate_case(path,count,animated,variant,model):
    ep=path/'controlled-execution.validation.json';rp=path/'controlled.validation.json';execution=read(ep);report=read(rp)
    assert execution['ok']and execution['kind']=='fish_material_controlled_execution'and execution['protocol']=='controlled-v1'
    assert execution['returncode']==0 and not execution['timed_out']and execution['inputs_unchanged']and execution['errors']==[]
    assert Path(execution['report']).resolve()==rp.resolve()and execution['report_sha256']==sha(rp)
    assert '--disable-render-loop'in execution['command']and '--headless'not in execution['command']
    assert report['ok']and report['direct_GLTFDocument']and report['runtime_static_build_calls']==0
    assert Path(report['model']).resolve()==model.resolve()and report['model_sha256']==sha(model)
    files=[model,ROOT/'resources/scripts/volume-fish/benchmark_fish_materials_controlled.gd',ROOT/'resources/scripts/volume-fish/benchmark_fish_materials.gd',ROOT/'resources/scripts/volume-fish/run_fish_material_controlled_case.py',ROOT/'projects/fishing-2d/game/project.godot',ROOT/'projects/fishing-2d/game/scripts/aquarium/FoundryFishMotion.gd',ROOT/'resources/volume-fish/motion/nile_tilapia-082.json']
    bound=normalize_frozen(execution['frozen_inputs']);assert bound=={str(p.resolve()):sha(p)for p in files}
    render_bound=normalize_frozen(report['frozen_inputs']);assert render_bound and all(bound.get(k)==v for k,v in render_bound.items())
    expected={'count':count,'animated':bool(animated),'samples':60,'warmup':15,'viewport':[1280,720],'rendering_method':'gl_compatibility','rendering_driver':'opengl3','automatic_render_loop':False,'explicit_force_draws_per_step':1,'swap_buffers':False,'readback_every_step':True,'hidden_own_window':False,'own_window_minimized':True,'always_on_top':False,'shadow':False,'water_AI_collision':False,'automatic_LOD':False,'real_length_cm':40}
    for key,value in expected.items():assert report['settings'][key]==value,(path.name,key)
    assert abs(report['settings']['fixed_simulation_delta_seconds']-1/60)<1e-14
    assert report['settings']['display_server']!='headless'
    gpu=report['settings']['gpu'].lower();assert gpu and not any(x in gpu for x in ('dummy','llvmpipe','swiftshader','software'))
    for key,value in {'bones':18,'triangles':1710,'vertices':1465,'surfaces':9 if variant=='baseline9'else 1,'meshes':8 if variant=='baseline9'else 1}.items():assert report['per_fish'][key]==value
    assert len(report['images'])==2
    for image in report['images']:assert Path(image['path']).resolve().parent==path.resolve()and sha(image['path'])==image['sha256']
    return {'report':report,'metrics':check_samples(report,count,animated,variant),'initialization_ms':report['initialization_ms'],'frozen_inputs':bound,'execution':artifact(ep),'report_artifact':artifact(rp),'execution_file_mtime_ns':ep.stat().st_mtime_ns}

def capture_evidence(models):
    p=EXPERIMENT/'captures-v3/comparison/comparison.validation.json';d=read(p);assert d['ok']
    for path,h in d['frozen_inputs'].items():
        assert sha(path)==h;report=read(path);variant=Path(path).parent.name
        assert report['ok']and report['model_sha256']==sha(models[variant])and len(report['captures'])==48
        for image in report['captures']:assert sha(image['path'])==image['sha256']
    for sheet in d['sheets']:assert sha(sheet['path'])==sheet['sha256']
    source=EXPERIMENT/'evidence-sources/benchmark_fish_materials-capture-29df7105.gd'
    assert sha(source)=='29df7105c94f51f7bc9b172aa33ef40abe02d8c8910b93b34409de50bed4f088'
    return {'comparison':artifact(p),'summary':d['summary'],'archived_capture_source':artifact(source),'scope':'Actual29df captures retain their original source, models, materials and pose/camera records. Later benchmark script hashes differ; old reports are not rebound. Hash validation does not perform visual acceptance.'}

def compare(rows,field):
    lookup={(x['count'],x['animated'],x['variant']):x for x in rows};result=[]
    for count in (100,300,1000):
        for animated in (False,True):
            for old,new,label in [('baseline9','merged-mask','material_packing'),('merged-mask','merged-opaque','alpha_mode_same_geometry')]:
                a=lookup[count,animated,old];b=lookup[count,animated,new];before=a['metrics'][field]['p50'];after=b['metrics'][field]['p50']
                gains=[100*(x['metrics'][field]['p50']-y['metrics'][field]['p50'])/x['metrics'][field]['p50']for x,y in zip(a['per_round'],b['per_round'])]
                result.append({'count':count,'animated':animated,'comparison':label,'metric':field,'from':old,'to':new,'pooled_P50_reduction_percent':100*(before-after)/before,'per_round_P50_reduction_percent':gains,'both_rounds_positive':all(x>0 for x in gains),'scope':'Controlled microbenchmark, not normal FPS or isolated GPU duration.'})
    return result

def summarize(matrix,output):
    matrix=Path(matrix).resolve();output=Path(output).resolve()
    assert matrix==EXPERIMENT.resolve()/'benchmark/controlled-v1'and output==EXPERIMENT.resolve()
    plan=read(matrix/'matrix-manifest.json')
    assert plan['protocol']=='controlled-v1'and plan['settings']['expected_cases']==36
    expected_names={f'r{r}-{n}-'+('motion-'if a else 'static-')+v for r in (1,2)for n in (100,300,1000)for a in (False,True)for v in VARIANTS}
    resolved=plan.get('resolved_case_directories',{})
    assert set(resolved)<= {f'r2-1000-motion-{v}'for v in VARIANTS},'Only explicitly authorized final-block retries supported'
    directories={name:Path(resolved.get(name,str(matrix/name))).resolve()for name in expected_names}
    for name,path in directories.items():
        assert path.parent==matrix and path.name in (name,name+'-retry2'),'Invalid explicit retry directory'
    actual_directories={p.resolve()for p in matrix.iterdir()if p.is_dir()}
    assert set(directories.values())<=actual_directories,'Incomplete adopted36-case matrix'
    rejected_extra=actual_directories-set(directories.values());rejected=[]
    for path in sorted(rejected_extra):
        assert path.name in resolved and path==matrix/path.name,'Unexpected case directory'
        execution=path/'controlled-execution.validation.json';value=read(execution)
        assert value['ok']is False,'A valid original case cannot be silently replaced by a faster retry'
        rejected.append({'directory':str(path),'execution':artifact(execution),'errors':value.get('errors',[]),'reason':'Explicit prespecified complete final-block retry after window-postcondition failure; invalid original excluded, not selected by speed.'})
    models={'baseline9':EXPERIMENT.parent/'round9-fin-clearance/final-B-artifacts/fish.glb','merged-mask':EXPERIMENT/'candidates-v2/merged-mask.glb','merged-opaque':EXPERIMENT/'candidates-v2/merged-opaque.glb'}
    cases=[];groups={};environment=None;frozen={}
    for repeat in (1,2):
        for count in (100,300,1000):
            for animated in (False,True):
                order=VARIANTS if repeat==1 else tuple(reversed(VARIANTS));ordered=[]
                for variant in order:
                    name=f'r{repeat}-{count}-'+('motion-'if animated else 'static-')+variant
                    value=validate_case(directories[name],count,animated,variant,models[variant]);report=value.pop('report')
                    current={k:report['settings'][k]for k in ('gpu','gpu_api','engine','display_server','model_scale','camera_size','layout')}
                    if environment is None:environment=current
                    assert environment==current
                    for p,h in value['frozen_inputs'].items():assert p not in frozen or frozen[p]==h;frozen[p]=h
                    row={'round':repeat,'variant':variant,'count':count,'animated':animated,'planned_case':name,'resolved_directory':str(directories[name]),**value};cases.append(row);ordered.append(row);groups.setdefault((count,animated,variant),[]).append(report)
                assert [x['variant']for x in sorted(ordered,key=lambda x:x['execution_file_mtime_ns'])]==list(order),'Per-group actual completion order differs'
    pooled=[]
    for (count,animated,variant),reports in groups.items():
        rounds=[{'round':i+1,'metrics':{k:distribution([x[k]for x in r['raw_samples']])for k in FIELDS}}for i,r in enumerate(reports)]
        pooled.append({'count':count,'animated':animated,'variant':variant,'pooled_raw_samples':120,'metrics':{k:distribution([x[k]for r in reports for x in r['raw_samples']])for k in FIELDS},'per_round':rounds,'controlled_step_P50_round_range':[min(r['metrics']['controlled_step_ms']['p50']for r in rounds),max(r['metrics']['controlled_step_ms']['p50']for r in rounds)]})
    visual=capture_evidence(models);failures=[]
    for old in ('matrix-v2','matrix-v3'):
        directory=EXPERIMENT/'benchmark'/old/'r1-100-motion-baseline9';witnesses=[]
        for p in directory.glob('*.validation.json'):
            d=read(p);state=d.get('window_state',{})
            if state.get('can_draw')is False or state.get('minimized')is True:witnesses.append(artifact(p))
        assert witnesses,'Missing original invalid-window witness for '+old
        failures.append({'matrix':old,'evidence':witnesses,'reason':'Entire automatic-window partial matrix rejected; no cases mixed into controlled data.'})
    settings={'protocol':'controlled-v1','counts':[100,300,1000],'animated':[False,True],'variants':list(VARIANTS),'rounds':2,'samples_per_case':60,'warmup_per_case':15,'viewport':[1280,720],'automatic_render_loop':False,'force_draw_per_step':1,'swap_buffers':False,'synchronous_readback_per_step':True,'own_window_minimized':True,'expected_cases':36,'scope':'Post-execution aggregation of real independently frozen cases; not a pre-run manifest or another benchmark invocation.'}
    assert normalize_frozen(plan['frozen_inputs'])==frozen,'Inputs differ from the running plan snapshot'
    assert {Path(x['directory']).name for x in plan['planned_cases']}==expected_names
    manifest=dict(plan)
    manifest.update(ok=True,status='done',next_action='human_review',final_aggregate_kind='post_execution_case_validation',cases=[{'round':x['round'],'count':x['count'],'animated':x['animated'],'variant':x['variant'],'resolved_directory':x['resolved_directory'],'execution':x['execution'],'report':x['report_artifact']}for x in cases],rejected_original_case_directories=rejected,validated_case_count=36,final_scope=settings['scope'])
    write(matrix/'matrix-manifest.json',manifest)
    aggregate={'ok':True,'kind':'fish_material_controlled_matrix_validation','protocol':'controlled-v1','expected_cases':36,'validated_cases':36,'raw_samples':2160,'manifest':artifact(matrix/'matrix-manifest.json'),'analyzer_sha256':sha(__file__),'checks':{'current_case_input_hashes':True,'successful_execution_and_reports':True,'each60_measured15_warmup75_signals':True,'one_actual_draw_per_step':True,'actual_draws_and_primitives_exact':True,'pose_and_GPU_change_match_mode':True,'own_window_minimized_no_focus_claim':True,'all_first_last_images_current':True,'two_opposite_variant_orders':True},'scope':settings['scope']}
    write(matrix/'matrix.validation.json',aggregate)
    comparisons=compare(pooled,'controlled_step_ms')+compare(pooled,'forced_draw_readback_ms')
    limitations=['Baseline-to-merged comparison includes mesh/surface packing, atlas/texture bindings and a common alpha pipeline; it measures that combined optimization, not a pure draw-call-only effect.','Controlled step includes motion, normal engine-frame/deferred wait, one forced draw and full-image synchronous readback/allocation; not regular FPS, frame latency or pureGPU time.','Forced_draw_readback includes CPU/driver submission and GPU synchronization/readback; its delta is not isolated alpha-shader cost.','Motion direct-call timing excludes deferred engine skeleton/skin/render work.','No water/AI/collision/shadows/automaticLOD. Fixed slots andcamera; increasing population increases screen coverage.','Existing user applications were not closed. Opposite-order repeats reduce but do not eliminate background load and thermal drift.','No added-face model exists: same1710face MASK/OPAQUE cannot compare addingNfaces with retainingcutout.','v1white mouth was caused by ignoredCOLOR0. v2sRGB8 mouth quantization and4near-texel-boundaryUVprobe differences mean near parity, not absolute losslessness.','OPAQUE reveals original cutout regions andisnot an equal-quality accepted replacement.','R9remains reviewed/current; R10has no newblend/SOP approval, production installation or whole-fish user acceptance.','No PI/DeepSeek/Kimi call this round: PI runtime notlocated in three explicit localroots. No measuredCodex token saving claimed.']
    report={'ok':True,'kind':'nile_material_controlled_performance_review','status':'measured_experiment_not_installed','formal_asset_acceptance':False,'matrix_manifest':artifact(matrix/'matrix-manifest.json'),'matrix_validation':artifact(matrix/'matrix.validation.json'),'analyzer_sha256':sha(__file__),'environment':environment,'settings':settings,'models':{k:artifact(p)for k,p in models.items()},'validated_cases':cases,'rejected_original_case_directories':rejected,'pooled_results':pooled,'paired_comparisons':comparisons,'quantile_method':'Lower empirical floor((n-1)*q), matchingGodot. Pool120realrawsamples/tworounds, do not averagepercentiles.','gpu_timer_available':False,'GPU_time_ms':None,'visual_evidence':visual,'rejected_window_matrices':failures,'limitations':limitations}
    write(output/'validation-report.json',report)
    lookup={(x['count'],x['animated'],x['variant']):x for x in pooled}
    lines=['# 尼罗罗非鱼材质合并：受控GPU实验','',f"{environment['gpu']}，Godot {environment['engine']['string']}，OpenGL Compatibility，1280×720。36有效案例，每案例15次预热、60次实测，两轮顺序反转。每组两轮120原始样本合并P50/P95，单位ms。",'', '**受控时间包含强制绘制和整图同步读回，不能换算正常游戏FPS，也不是纯GPU时间。**','']
    for field,label in [('controlled_step_ms','受控总步骤'),('forced_draw_readback_ms','强制绘制＋同步读回'),('motion_call_ms','控制器直接调用'),('engine_refresh_wait_ms','引擎帧/延后工作等待')]:
        lines+=['',label+'：','', '|数量|状态|原9组 P50/P95|合1组裁切 P50/P95|合1组不透明 P50/P95|','|---:|---|---:|---:|---:|']
        for count in (100,300,1000):
            for animated in (False,True):lines.append('|'+str(count)+'|'+('游动'if animated else '静止')+'|'+'|'.join(f"{lookup[count,animated,v]['metrics'][field]['p50']:.3f} / {lookup[count,animated,v]['metrics'][field]['p95']:.3f}"for v in VARIANTS)+'|')
    lines+=['','两轮总步骤P50范围：','', '|数量|状态|原9组|合1组裁切|合1组不透明|','|---:|---|---:|---:|---:|']
    for count in (100,300,1000):
        for animated in (False,True):lines.append('|'+str(count)+'|'+('游动'if animated else '静止')+'|'+'|'.join('–'.join(f'{x:.3f}'for x in lookup[count,animated,v]['controlled_step_P50_round_range'])for v in VARIANTS)+'|')
    lines+=['','实测解释：','']
    for count in (100,300,1000):
        c=next(x for x in comparisons if x['count']==count and x['animated']and x['comparison']=='material_packing'and x['metric']=='controlled_step_ms')
        change=c['pooled_P50_reduction_percent'];word='下降'if change>=0 else '增加'
        lines.append(f"- {count}条游动，9组→1组裁切的受控总步骤P50{word}{abs(change):.1f}%；两轮耗时降幅（正值更快）分别为"+' / '.join(f'{x:.1f}%'for x in c['per_round_P50_reduction_percent'])+'，结合波动范围解读。')
    alpha=next(x for x in comparisons if x['count']==1000 and x['animated']and x['comparison']=='alpha_mode_same_geometry'and x['metric']=='controlled_step_ms')
    lines.append(f"- 1000条游动，MASK→OPAQUE的受控总步骤P50合并样本降幅仅{alpha['pooled_P50_reduction_percent']:.2f}%；两轮分别为"+' / '.join(f'{x:+.2f}%'for x in alpha['per_round_P50_reduction_percent'])+'。本次未测得关闭裁切的稳定收益，现阶段不支持为此盲目增面；这不是证明增面一定更贵。')
    lines+=['- 实际逐样本核对每鱼9→1次绘制；1710面/1465顶点/18骨不变。1000条为9000→1000次绘制，同为171万三角面。','- 合并材质不会消除逐鱼动作计算；动作直接调用、引擎延后工作与绘制应分别看。','- 当前不透明版只是同几何控制：有原透明区域显露。没有增面版本，不能宣称增面比裁切更划算。','', '外观和失败边界：','', '- v1白口内被真实图像阻断：COLOR_0有数组，Godot却未启用顶点色作为albedo。v2只将口内常色编码成sRGB8图块，不改身体/鳍原像素。量化与有限UV边界误差明确保留。','- captures-v3每变体48张同姿态图使用29df归档捕获源码；模型/材质/姿态/相机证据保留，未把后来计时代码哈希伪装成旧捕获来源。','- 自动窗口matrix-v2/v3被macOS不可绘制/最小化拒绝，全部部分结果排除。受控模式自有窗口最小化是预期，以真实GPU图像、每步drawsignal和计数验证工作，不再抢用户焦点。','', '限制：','']
    lines+=['- '+x for x in limitations]
    if rejected:lines+=['','最后一组重试说明：原r2-1000-motion-merged-opaque触发自有窗口被恢复的后置断言，执行失败，不解释为测得很慢。保留原失败证据；按预先明确映射，以完全相同冻结代码重跑该最后三变体配对组，不选择快结果、不重跑此前33成功案例。']
    lines+=['','原R9成品保留；本轮没有安装替换、新blend固化或完整SOP完成声明。逐案例实际命令、哈希、60raw、首尾GPU图片与聚合来源见 validation-report.json 和 benchmark/controlled-v1/。']
    (output/'performance-review.md').write_text('\n'.join(lines)+'\n');return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--matrix',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--replace-summary',action='store_true');a=p.parse_args()
    if not a.replace_summary:assert not any((a.output/name).exists()for name in ('validation-report.json','performance-review.md')),'Explicit --replace-summary required'
    r=summarize(a.matrix,a.output);print(json.dumps({'ok':r['ok'],'cases':len(r['validated_cases']),'raw_samples':2160}))
if __name__=='__main__':main()
