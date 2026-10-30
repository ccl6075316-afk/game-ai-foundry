"""Preflight, author, cold export and compare one portable packed source.

Defaults to a read-only plan. --execute writes a fresh isolated output directory.
Technical parity is not fish acceptance; final specialized and visual gates remain.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from fish_asset_spec import ROOT,artifact_output,input_paths,load_spec,preflight,sha
from verify_parity import verify


def run(args):
    spec=load_spec(args.spec);inputs=input_paths(spec);baseline=preflight(args.spec)
    output=artifact_output(args.output,list(inputs.values())+[args.spec])
    source=output/'source';model=output/'fish.glb';here=Path(__file__).resolve().parent
    stages=[('author',[str(args.blender),'--background','--python-exit-code','1','--python',str(here/'build_source.py'),'--','--spec',str(args.spec.resolve()),'--output',str(source),'--json']),
            ('cold_export',[str(args.blender),'--background','--python-exit-code','1','--python',str(here/'export_source.py'),'--','--blend',str(source/'fish.blend'),'--output',str(model),'--report',str(output/'cold-export.validation.json')])]
    planned={'ok':True,'kind':'portable_source_run_plan','dry_run':not args.execute,'spec':str(args.spec.resolve()),'output':str(output),'inventory':baseline['summary']['inventory'],'stages':[{'name':name,'argv':argv}for name,argv in stages],'after_processes':['verify full1e-6 GLB semantic parity','bind finalmodel hash into final spec','write validation report and manifest']}
    if not args.execute:return planned
    if not args.blender.is_file():raise ValueError('Configured Blender executable missing')
    output.mkdir(parents=True);manifest={'kind':'portable_source_manifest','version':1,'status':'running','next_action':'poll','input_spec':{'path':str(args.spec.resolve()),'sha256':sha(args.spec)},'input_files':spec['inputs'],'stages':[],'scope':'Technical portable source run only, no fish acceptance.'};manifest_path=output/'manifest.json'
    def save():manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    save();before={key:sha(path)for key,path in inputs.items()};started=time.time()
    try:
        for name,argv in stages:
            log=output/(name+'.stdout.txt')
            try:
                result=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=args.timeout)
            except subprocess.TimeoutExpired as error:
                def decoded(value):return value.decode(errors='replace')if isinstance(value,bytes)else value or ''
                log.write_text(decoded(error.stdout)+'\n'+decoded(error.stderr))
                manifest['stages'].append({'name':name,'argv':argv,'timeout_seconds':args.timeout,'log':str(log.relative_to(ROOT)),'log_sha256':sha(log)})
                save();raise
            log.write_text(result.stdout+'\n'+result.stderr)
            entry={'name':name,'argv':argv,'returncode':result.returncode,'log':str(log.relative_to(ROOT)),'log_sha256':sha(log)};manifest['stages'].append(entry);save()
            if result.returncode or 'Traceback (most recent call last)'in result.stdout+result.stderr:raise RuntimeError(name+' failed; see '+str(log))
        proof=verify(inputs['reference_glb'],model,spec,baseline['summary']['parts'])
        if before!={key:sha(path)for key,path in inputs.items()}or sha(args.spec)!=manifest['input_spec']['sha256']:raise RuntimeError('Read-only authoring input changed')
        if sha(model)!=sha(source/'fish.glb'):raise RuntimeError('Cold source export bytes differ from initial source export')
        final_spec={**spec,'model':{'path':str(model.relative_to(ROOT)),'sha256':sha(model)},'model_role':'final'};final_path=output/'final-spec.json';final_path.write_text(json.dumps(final_spec,indent=2)+'\n')
        proof.update(input_spec_sha256=manifest['input_spec']['sha256'],final_spec={'path':str(final_path.relative_to(ROOT)),'sha256':sha(final_path)},cold_export_bytes_equal=True,original_inputs_unchanged=True)
        report=output/'validation-report.json';report.write_text(json.dumps(proof,indent=2)+'\n');manifest.update(status='done',next_action='human_review',model=final_spec['model'],final_spec=proof['final_spec'],validation_report={'path':str(report.relative_to(ROOT)),'sha256':sha(report)},elapsed_seconds=time.time()-started);save()
        return {'ok':True,'status':'done','next_action':'human_review','manifest':str(manifest_path),'final_spec':str(final_path),'model':str(model),'report':str(report)}
    except Exception as error:
        manifest.update(status='failed',next_action='fix_input',failure={'kind':'validation','code':'portable_source_run_failed','message':str(error)},elapsed_seconds=time.time()-started);save();raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,required=True);parser.add_argument('--blender',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group();mode.add_argument('--execute',action='store_true');mode.add_argument('--dry-run',action='store_true')
    parser.add_argument('--timeout',type=float,default=300,help='Per Blender stage timeout in seconds');parser.add_argument('--json',action='store_true');args=parser.parse_args()
    try:
        if args.timeout<=0:raise ValueError('Timeout must be positive')
        result=run(args)
    except (ValueError,AssertionError,KeyError,OSError,subprocess.SubprocessError,RuntimeError)as error:
        result={'ok':False,'status':'blocked','next_action':'fix_input','failures':[{'kind':'validation','code':'portable_source_run_failed','message':str(error)}]}
    print(json.dumps(result,indent=2));return 0 if result['ok']else 1

if __name__=='__main__':raise SystemExit(main())
