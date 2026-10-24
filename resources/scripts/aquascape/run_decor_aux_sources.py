"""Bounded CLI orchestration reading only official source workflow state.

No alternate queue, status file or copied task state. Every decision is derived
from the ten authoritative manifests/jobs and immutable ornament catalogue.
"""
import argparse,json,time
from pathlib import Path
from catalog_workflows import call
from prepare_full_views_catalog import plans

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--init',action='store_true');p.add_argument('--parallel-projects',type=int,default=2);a=p.parse_args();root=a.root.resolve();specs=json.loads((root/'resources/aquascape/decor-10-v1.json').read_text(encoding='utf-8'))['assets'];projects=[root/f'projects/aquascape-decor-{s["id"]}-views-v1' for s in specs]
    if a.init:
        for project in projects:
            if (project/'pipeline/manifest.json').exists():continue
            call(root,['brief','freeze','--input',str(project/'brief.draft.json'),'-o',str(project/'brief.json'),'--json'])
            call(root,['workflow','context','--brief',str(project/'brief.json'),'--json'])
            valid=call(root,['workflow','validate','--brief',str(project/'brief.json'),'--json'])
            if valid['next_action']=='derive_production':call(root,['workflow','init','--brief',str(project/'brief.json'),'--json'])
            plans(root,project)
    previous={}
    while True:
        rows=[]
        for project in projects:
            manifest=project/'pipeline/manifest.json';args=['workflow','status','--manifest',str(manifest)]
            jobs=sorted((project/'pipeline/jobs').glob('*.json'),key=lambda p:p.stat().st_mtime)
            if jobs:
                job=json.loads(jobs[-1].read_text(encoding='utf-8'))
                if not job.get('finished_at'):args+=['--job-id',job['job_id']]
            status=call(root,[*args,'--json']);rows.append((project,status))
            key=(status['status'],status['next_action'])
            if previous.get(project.name)!=key:print(json.dumps({'project':project.name,'status':key[0],'next_action':key[1]}),flush=True);previous[project.name]=key
        if any(s['status'] in ['failed','blocked','paused'] for _,s in rows):raise RuntimeError('Source workflow needs repair; read failures/manifest before retry.')
        if all(s['status']=='done' and s['next_action']=='human_review' for _,s in rows):return 0
        active=sum(s['next_action']=='poll' for _,s in rows)
        for project,status in rows:
            if active>=a.parallel_projects:break
            if status['status']=='pending' and status['next_action']=='run':
                result=call(root,['workflow','run','--manifest',str(project/'pipeline/manifest.json'),'--stage','assets','--jobs','2','--detach','--json']);active+=1
                print(json.dumps({'project':project.name,'job_id':result['summary']['job_id'],'status':result['status']}),flush=True)
        time.sleep(15)

if __name__=='__main__':raise SystemExit(main())
