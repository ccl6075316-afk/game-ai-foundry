"""Small CLI orchestration over authoritative workflow manifests, no shadow queue."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def call(root,args):
    # Detached Windows children may inherit pipe handles. File capture waits only
    # for the CLI parent, not for unrelated EOF from the whole detached subtree.
    with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
        result=subprocess.run([str(root/'.venv/Scripts/python.exe'),str(root/'cli/gamefactory.py'),*args],cwd=root,stdout=stdout,stderr=stderr)
        stdout.seek(0);out=stdout.read().decode('utf-8');stderr.seek(0);err=stderr.read().decode('utf-8')
    try:data=json.loads(out)
    except json.JSONDecodeError:raise RuntimeError(out[-1000:]+err[-1000:])
    if result.returncode or not data.get('ok',True):raise RuntimeError(json.dumps(data,ensure_ascii=False))
    return data


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--project',type=Path,action='append',required=True);p.add_argument('--mode',choices=['init','start','status'],required=True);p.add_argument('--jobs',type=int,default=2);a=p.parse_args()
    for project in a.project:
        project=project if project.is_absolute() else a.root/project;brief=project/'brief.json';manifest=project/'pipeline/manifest.json'
        if a.mode=='init':
            if not brief.exists():call(a.root,['brief','freeze','--input',str(project/'brief.draft.json'),'-o',str(brief),'--json'])
            context=call(a.root,['workflow','context','--brief',str(brief),'--json'])
            valid=call(a.root,['workflow','validate','--brief',str(brief),'--json'])
            if context.get('status')=='done':raise RuntimeError('Project already done; do not reinitialize: '+str(project))
            if valid['next_action']=='derive_production':call(a.root,['workflow','init','--brief',str(brief),'--json'])
            from prepare_full_views_catalog import plans
            plans(a.root,project)
            print(json.dumps({'project':project.name,'ok':True,'status':'pending','next_action':'run'}),flush=True)
        elif a.mode=='start':
            status=call(a.root,['workflow','status','--manifest',str(manifest),'--json'])
            if status['next_action'] in ['poll','human_review']:
                print(json.dumps({'project':project.name,'status':status['status'],'next_action':status['next_action'],'run_skipped':True}),flush=True)
                continue
            if status['next_action']!='run':raise RuntimeError('Not pending/run: '+json.dumps(status))
            data=call(a.root,['workflow','run','--manifest',str(manifest),'--stage','assets','--jobs',str(a.jobs),'--detach','--json'])
            print(json.dumps({'project':project.name,'status':data['status'],'job_id':data['summary']['job_id']}),flush=True)
        else:
            jobs=sorted((project/'pipeline/jobs').glob('*.json'),key=lambda f:f.stat().st_mtime)
            args=['workflow','status','--manifest',str(manifest)]
            if jobs:args+=['--job-id',json.loads(jobs[-1].read_text(encoding='utf-8'))['job_id']]
            data=call(a.root,[*args,'--json']);print(json.dumps({'project':project.name,'ok':data['ok'],'status':data['status'],'next_action':data['next_action'],'counts':data['summary']['manifest']['counts'],'failed':data['summary']['manifest']['failed_ids'],'failures':data['failures']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
