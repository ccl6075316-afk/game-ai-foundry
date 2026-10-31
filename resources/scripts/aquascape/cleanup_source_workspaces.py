"""Retain source-art workflows, remove only their unused generated game shells.

Default is a recorded dry run. Every deletion is a checked literal path under
projects/aquascape-expansion-v11-*, after terminal manifest/job verification.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
REVIEW=ROOT/'projects/fishing-2d/plans/reviews/aquascape-expansion-v11'

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    projects=sorted((ROOT/'projects').glob('aquascape-expansion-v11-*'));targets=[];sources=[]
    tracked_result=subprocess.run(['git','-C',str(ROOT),'ls-files','-z','--','projects'],capture_output=True,check=True)
    tracked_paths=set(tracked_result.stdout.decode('utf-8').split('\0'))
    for project in projects:
        manifest=load(project/'pipeline/manifest.json')
        if any(t['status'] not in ['done','skipped'] for t in manifest['tasks']):raise RuntimeError('Source workflow is not finished: '+str(project))
        jobs=[load(p) for p in (project/'pipeline/jobs').glob('*.json')]
        if not jobs or any(j.get('status') not in ['done','failed'] for j in jobs):raise RuntimeError('Source job still active or unknown: '+str(project))
        # Assets manifest points to original output images/plans, not these
        # generated 2D background display games. Original inputs remain intact.
        for row in load(project/'output/assets-manifest.json')['assets'].values():
            if row.get('review',{}).get('status')=='replaced':continue
            for stage in row.get('stages',[]):
                if stage.get('status')!='done' or not stage.get('path_repo'):continue
                original=(ROOT/stage['path_repo']).resolve()
                if not original.exists():raise RuntimeError('Missing source artifact: '+str(original))
                if original.is_relative_to(project/'game'):raise RuntimeError('Game folder contains an authoritative source: '+str(original))
        for p in project.rglob('*'):
            if p.is_file() and (p.is_relative_to(project/'game') or p.suffix=='.log'):
                absolute=p.resolve()
                if not absolute.is_relative_to(project.resolve()) or not project.resolve().is_relative_to(ROOT/'projects'):raise RuntimeError('Cleanup target escaped the explicit source project')
                if p.relative_to(ROOT).as_posix() in tracked_paths:raise RuntimeError('Refusing tracked source deletion: '+str(p))
                targets.append({'path':str(absolute),'bytes':p.stat().st_size,'sha256':sha(p)})
        sources.append({'project':str(project),'manifest':str(project/'pipeline/manifest.json'),'retained_original_images':len(list((project/'output').glob('*_raw.png')))})
    report={'schema_version':1,'command':'aquascape.source-workspace-cleanup','ok':True,'status':'done' if args.apply else 'pending','next_action':'human_review','applied':False,'targets':targets,'bytes':sum(t['bytes'] for t in targets),'source_workflows':sources,'retained':'Frozen and draft briefs; production/progress; workflow manifests and terminal job receipts; prompt plans; original raw images; assets manifests; all current aquarium assets and review evidence.','removed_scope':'Unused standalone background-display game templates, copied background textures, per-source Godot/.NET caches, and terminal source-job logs. None is part of the fishing-2d runtime or a source-art stage input.','reproduction':'The source game shells are ordinary Foundry workflow-init/import scaffolds. The final aquarium models rebuild from the retained raw artwork with build_expansion_v11.py; they do not need these shells.'}
    output=REVIEW/'source-workspace-cleanup.validation.json';save(output,report)
    if args.apply:
        # One filesystem runtime handles literal deletions; each absolute path
        # has already been whitelisted and checked against tracked source files.
        for item in targets:Path(item['path']).unlink()
        for project in projects:
            directories=sorted([p for p in project.rglob('*') if p.is_dir()],key=lambda p:len(p.parts),reverse=True)
            for directory in directories:
                if directory.resolve().is_relative_to(project.resolve()) and not any(directory.iterdir()):directory.rmdir()
        report['applied']=True;report['remaining_source_bytes']=sum(p.stat().st_size for d in projects for p in d.rglob('*') if p.is_file());save(output,report)
    print(json.dumps({'ok':True,'applied':report['applied'],'files':len(targets),'removed_mb':round(report['bytes']/1048576,2),'retained_projects':len(projects)}))
if __name__=='__main__':main()
