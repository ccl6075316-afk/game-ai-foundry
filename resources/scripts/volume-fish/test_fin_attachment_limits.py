"""Small parser/real-runner contract tests; no Blender, Godot or fish export."""
import argparse,contextlib,hashlib,io,json,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode=True
import validate_fin_completion as completion
import validate_fin_membrane_clearance as membrane
from fin_attachment_limits import attachment_limits_cm,require_report_limits

SCRIPTS=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[3]
    assert output.is_relative_to(root/'output') or output.is_relative_to(root/'work'), 'Use a repository output/work directory'
    records=[]
    def record(name,details):records.append(dict(name=name,ok=True,details=details))
    assert attachment_limits_cm({})==(.10,.60)
    assert attachment_limits_cm({'attachment_limits':{'outer_gap_mm':.5,'max_embedding_mm':.5}})==(.05,.05)
    assert attachment_limits_cm({'attachment_limits':{'outer_gap_cm':.05,'max_embedding_cm':.05}})==(.05,.05)
    assert attachment_limits_cm({'attachment_limits':{'outer_gap_mm':0,'max_embedding_mm':0}})==(0.,0.)
    bad=[None,False,[],{}, {'outer_gap_mm':.5},{'max_embedding_mm':.5},
         {'outer_gap_mm':.5,'max_embedding_cm':.05},
         {'outer_gap_mm':.5,'max_embedding_mm':.5,'outer_gap_cm':.05,'max_embedding_cm':.05},
         {'tolerance_cm':.05,'max_penetration_cm':.05}]
    for unit in ['mm','cm']:
        for key in ['outer_gap_'+unit,'max_embedding_'+unit]:
            for v in [True,False,'0.5',None,[],{},float('nan'),float('inf'),-float('inf'),-.01,10**400]:
                d={'outer_gap_'+unit:.5,'max_embedding_'+unit:.5};d[key]=v;bad.append(d)
    for limits in bad:
        try:attachment_limits_cm({'attachment_limits':limits})
        except ValueError:pass
        else:raise AssertionError('Accepted invalid declaration '+repr(limits))
    for limits in [True,'0.1',None,float('nan'),float('inf'),-.1]:
        try:require_report_limits({'tolerance_cm':limits,'max_penetration_cm':.6},{})
        except ValueError:pass
        else:raise AssertionError('Accepted invalid report limits')
    record('parser_units_and_fail_closed',{'invalid_declarations_rejected':len(bad),'legacy_cm':[.10,.60],'declared_0_5mm_cm':[.05,.05],'cm_fields':['outer_gap_cm','max_embedding_cm']})
    with tempfile.TemporaryDirectory(prefix='fixture-',dir=output) as temp:
        base=Path(temp);game=base/'game';model=base/'fish.glb';model.write_bytes(b'synthetic fixture, no actual fish')
        runtime=['scripts/aquarium/FoundryFishMotion.gd','scripts/aquarium/VolumeFishExhibit.gd','assets/models/fish/motion/motion.json']
        for name in runtime:
            p=game/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(name)
        exporter=SCRIPTS/'export_runtime_fin_roots.gd';calls=[];active={};serial=0
        def export_data():
            return dict(ok=True,fin_membrane_revision=1,samples=[{}]*490,export_script_sha256=sha(exporter),model_sha256=sha(model),controller_sha256=sha(game/runtime[0]),exhibit_sha256=sha(game/runtime[1]),motion_config_sha256=sha(game/runtime[2]))
        def fake_subprocess(cmd,**kwargs):
            calls.append(cmd)
            if '--script' in cmd:
                q=active['out']/'test';q.mkdir(exist_ok=True);(q/'export.validation.json').write_text(json.dumps(export_data()))
            else:
                checker=Path(cmd[cmd.index('--python')+1]);target=Path(cmd[cmd.index('--output')+1]);export=Path(cmd[cmd.index('--export')+1]);d=export_data()
                d.update(checker_sha256=sha(checker),coverage_checker_sha256=sha(SCRIPTS/'runtime_pose_coverage.py'),export_report=str(export),export_report_sha256=sha(export),summary={'Fin':{'failed_contact_samples':0,'maximum_signed_distance_cm':0.,'minimum_signed_distance_cm':0.}})
                if checker.name=='check_runtime_fin_attachment.py':
                    d.update(tolerance_cm=float(cmd[cmd.index('--tolerance-cm')+1]),max_penetration_cm=float(cmd[cmd.index('--max-penetration-cm')+1]))
                    if active.get('lie'):d.update(tolerance_cm=.10,max_penetration_cm=.60)
                target.write_text(json.dumps(d))
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        def invoke(module,plan,extra=(),reuse_export=False,lie=False):
            nonlocal serial
            serial+=1;out=base/f'out-{serial}';out.mkdir();active.update(out=out,lie=lie)
            if reuse_export:
                d=out/'test';d.mkdir();(d/'export.validation.json').write_text(json.dumps(export_data()))
            argv=['test','--plan',str(plan),'--game',str(game),'--godot','fake-godot','--blender','fake-blender','--output',str(out),'--species','test',*extra]
            with patch.object(sys,'argv',argv),patch('subprocess.run',side_effect=fake_subprocess),contextlib.redirect_stdout(io.StringIO()):code=module.main()
            return code,json.loads((out/'completion.validation.json').read_text()),out
        for declaration,label,expected in [(None,'legacy',[.10,.60]),({'outer_gap_mm':.5,'max_embedding_mm':.5},'strict-mm',[.05,.05]),({'outer_gap_cm':.05,'max_embedding_cm':.05},'strict-cm',[.05,.05])]:
            spec=dict(species='test',model=str(model),model_sha256=sha(model),fins={'Fin':{}},membrane_clearance={'root_collar_mm':.5,'penetration_tolerance_mm':.02})
            if declaration is not None:spec['attachment_limits']=declaration
            plan=base/(label+'.json');plan.write_text(json.dumps({'items':[spec]}));start=len(calls)
            code,result,_=invoke(completion,plan);assert code==0 and result['ok']
            normal=calls[-1];assert [float(normal[normal.index(k)+1])for k in ['--tolerance-cm','--max-penetration-cm']]==expected
            code,result,fullout=invoke(membrane,plan,['--reuse-export'],reuse_export=True);assert code==0 and result['ok']
            rootcmd=calls[-2];memcmd=calls[-1];assert [float(rootcmd[rootcmd.index(k)+1])for k in ['--tolerance-cm','--max-penetration-cm']]==expected
            assert memcmd[memcmd.index('--root-collar-mm')+1]=='0.5' and memcmd[memcmd.index('--penetration-tolerance-mm')+1]=='0.02'
            assert all('--script' not in cmd for cmd in calls[-2:]),'Reused export must not launch Godot'
            full=fullout/'completion.validation.json';before=len(calls);code,reused,_=invoke(completion,plan,['--reuse-full490-completion',str(full)]);assert code==0 and reused['ok'] and len(calls)==before
            record(label+'_real_runner_commands_and_reuse',{'normal_072_root_cm':expected,'full490_root_cm':expected,'membrane_mm':[.5,.02],'exact_490_reuse_ok':True,'reuse_launched_processes':0})
            if declaration is not None:
                proof=next(x for x in result['checks']if x['check']=='roots');path=Path(proof['report']);old=path.read_text();wrong=json.loads(old);wrong.update(tolerance_cm=.10,max_penetration_cm=.60);path.write_text(json.dumps(wrong));proof['sha256']=sha(path);full.write_text(json.dumps(result))
                code,rejected,_=invoke(completion,plan,['--reuse-full490-completion',str(full)]);assert code==1 and not rejected['ok'] and 'Different root attachment limits' in rejected['error'];path.write_text(old)
                code,rejected,_=invoke(completion,plan,lie=True);assert code==1 and not rejected['ok']
                code,rejected,_=invoke(membrane,plan,['--reuse-export'],reuse_export=True,lie=True);assert code==1 and not rejected['ok']
                record(label+'_reject_legacy_limit_receipts',{'072_reuse_rejected':True,'fresh_072_wrong_limits_rejected':True,'fresh_490_wrong_limits_rejected':True})
        spec['attachment_limits']={'outer_gap_mm':.5};plan.write_text(json.dumps({'items':[spec]}))
        for module in [completion,membrane]:
            before=len(calls);code,result,_=invoke(module,plan);assert code==1 and not result['ok'] and len(calls)==before
        record('malformed_plan_fails_before_export',{'both_runners':True,'subprocesses':0})
        removed=[{'path_relative_to_fixture':str(p.relative_to(base)),'bytes':p.stat().st_size}for p in sorted(base.rglob('*'))if p.is_file()]
        cleanup={'fixture_root':str(base),'files':removed,'deleted_files':len(removed),'deleted_bytes':sum(p['bytes']for p in removed)}
    files=[Path(__file__),SCRIPTS/'fin_attachment_limits.py',SCRIPTS/'validate_fin_completion.py',SCRIPTS/'validate_fin_membrane_clearance.py']
    assert not base.exists()
    report=dict(ok=True,scope='Real runner mains with synthetic hashed fixture and intercepted subprocesses; parser, command units, report reuse only. No fish/geometry/exporter/kernel or490 sample evaluation.',checks=records,inputs={str(p):sha(p)for p in files},fixture_cleaned=True,cleanup=cleanup)
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'checks':len(records)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);run(parser.parse_args().output)
