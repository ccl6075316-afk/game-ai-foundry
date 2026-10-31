"""Consolidate current evidence and clean only explicitly reproducible files."""
import argparse,json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from expand_catalog_v11 import ROOT,CFG,REVIEW
from build_expansion_v11 import GAME,OUT
from optimize_scenery import load,save,sha,metrics
from validate_scenery_budget import validate
from catalog_workflows import call

def sheets(cfg):
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
    for kind,views in [('plants',['tank']),('solids',['front','right','back','top','gray'])]:
        for view in views:
            sheet=Image.new('RGB',(2000,1000),'#dce5e0');draw=ImageDraw.Draw(sheet)
            for i,s in enumerate(cfg[kind]):
                path=REVIEW/'plant-final'/f'{s["id"]}-0.0.png' if kind=='plants' else REVIEW/'solids-native'/f'{s["id"]}-{view}.png'
                im=Image.open(path).convert('RGB');im=im.crop((0,90,1125,810));im.thumbnail((395,445));x=(i%5)*400;y=(i//5)*500;sheet.paste(im,(x,y+40));draw.text((x+10,y+8),s['name_zh'],font=font,fill='black')
            sheet.save(REVIEW/('plants-in-tank.jpg' if kind=='plants' else f'solids-{view}.jpg'),quality=92)

def main():
    p=argparse.ArgumentParser();p.add_argument('--clean',action='store_true');a=p.parse_args();cfg=load(CFG);sheets(cfg)
    checks=validate(ROOT,[GAME/'assets/aquascape-v5/catalog.json',GAME/'assets/aquascape-decor-v1/catalog.json'],REVIEW/'all-assets-budget.validation.json')
    required=[REVIEW/'shader.validation.json',REVIEW/'live-motion/motion.validation.json',REVIEW/'plant-final/tank.validation.json',REVIEW/'solids-native/viewer.validation.json',REVIEW/'placement/placement.validation.json']
    if not checks['ok'] or not all(load(path)['ok'] for path in required):raise RuntimeError('Current validation gate failed')
    workflows=[]
    for project in sorted((ROOT/'projects').glob('aquascape-expansion-v11-*')):
        manifest=project/'pipeline/manifest.json'
        if not manifest.exists():continue
        jobs=sorted((project/'pipeline/jobs').glob('*.json'),key=lambda f:f.stat().st_mtime);job=load(jobs[-1])['job_id']
        result=call(ROOT,['workflow','status','--manifest',str(manifest),'--job-id',job,'--json'])
        if result['status']!='done' or result['next_action']!='human_review':raise RuntimeError('Source workflow is not finished: '+project.name)
        workflows.append({'manifest':str(manifest),'job_id':job,'status':result['status'],'next_action':result['next_action']})
    outputs=[]
    for row in load(OUT/'catalog.json')['assets']:
        path=GAME/row['model'].removeprefix('res://');outputs.append(dict(id=row['id'],name_zh=row['name_zh'],category=row['category'],path=str(path),**metrics(path),budget=row['geometry_budget']))
    history=[
      'Initial auxiliary art often repeated oblique fronts; the second camera round improved hints but is still not calibrated orthographic data. These illustrations are appearance references; native geometry is an artistic inference, with actual multiview and aperture review.',
      'Aggressive intermediate QEM left 1-2 nonmanifold edges on three solids. Direct topology-preserving reduction removed them; disconnected root fragments were removed before final reduction. Current fifty-asset gate passes.',
      'Transparent carrier corners extended below the authored plant root and initially caused floating placement. Placement now uses the authored zero-height root; the full twenty-species tank envelope and fixed-root checks pass.',
      'Oblique roof/end drawings projected a doorway/open mouth onto solid top/side surfaces. Native unscaled source roof/skin crops remove these painted false openings; final geometry still has its actual tunnel.',
      'The frozen source briefs inherited generic legacy batch description text mentioning four reused assets. No old asset was counted as a new item: the twenty explicit asset IDs and generated art are all additional designs.'
    ]
    summary={'new_plants':10,'new_scenery':10,'current_plants':20,'current_scenery':30,'current_total':50,'new_complete_instance_triangles':sum(r['triangles'] for r in outputs),'current_complete_instance_triangles':sum(r['triangles'] for r in checks['outputs']),'new_plant_triangle_range':[min(r['triangles'] for r in outputs if r['category']=='plant'),max(r['triangles'] for r in outputs if r['category']=='plant')],'new_plant_runtime':'one source-resolution atlas/surface per species; separate alpha-masked thin sprig shells; rooted vertex shader; no skeleton, clips, vertex-frame bake or animation textures'}
    handoff={'schema_version':1,'command':'aquascape.expansion-v11-delivery','ok':True,'status':'done','next_action':'human_review','summary':summary,'outputs':outputs,'source_workflows':workflows,'research':cfg['research'],'research_scope':cfg['research_scope'],'checks':[str(path) for path in [REVIEW/'all-assets-budget.validation.json',*required]],'performance':load(REVIEW/'instancing/render.validation.json')['performance'],'performance_scope':'1000 instances of these ten additional plants at 1920x1080 on RTX 5080/OpenGL Compatibility. This is an isolated populated-plant path, not a fish/water/whole-aquarium performance measurement. GPU timing availability and memory counters are driver-specific.','operator_visual_review':'Viewed all source art, all ten plants in the native tank at different phases, actual front/right/back/top/gray solid views, roof/end donors, and native selection/placement/save/restore. Technical and operator review do not substitute for user acceptance.','failure_history_and_resolutions':history,'reproduction':{'source':'expand_catalog_v11.py + catalog_workflows.py; context/validate/init/run/status --json on each frozen source brief; review actual artwork before accept','geometry':'build_expansion_v11.py extract; plants; solids; registry; deploy (deploy blocks on current budget/geometry/root/cavity failures)','layouts':'expansion_source_layouts.py creates reviewed construction annotations, never image prompt counts or angles','runtime':'open-shader-plant-tank.cmd; open-current-scenery.cmd; aquascape_decor_v1.tscn has all 30 static props','source_policy':'Do not rerun the historical v5 twenty-item producer over the expanded live registries; this additional batch has its own frozen source/workflow and budgeted builder.'},'failures':[],'user_acceptance':'pending'}
    save(REVIEW/'production.handoff.json',handoff)
    if a.clean:
        targets=[]
        for folder in [REVIEW/'intermediate-solids',REVIEW/'plant-native',REVIEW/'instancing/motion-frames']:
            if folder.exists():targets.extend(p for p in folder.rglob('*') if p.is_file() and p.suffix in ['.png','.glb'])
        targets.extend((REVIEW/'instancing').glob('compare-*.png'))
        for pattern in ['closeup-*-5.0.png','closeup-*-7.5.png']:
            targets.extend((REVIEW/'instancing').glob(pattern))
        targets.extend(p for p in REVIEW.glob('*.log'))
        approved=[]
        for path in sorted(set(targets)):
            path=path.resolve()
            if not path.is_relative_to(REVIEW.resolve()) or not path.is_file():raise RuntimeError('Cleanup escaped review workspace')
            relative=path.relative_to(GAME.parent).as_posix();tracked=subprocess.run(['git','-C',str(GAME.parent),'ls-files','--error-unmatch','--',relative],capture_output=True)
            if tracked.returncode==0:raise RuntimeError('Refuse to remove tracked evidence: '+str(path))
            approved.append({'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)})
        cleanup={'command':'aquascape.expansion-artifact-cleanup','ok':True,'status':'done','next_action':'human_review','deleted':approved,'deleted_bytes':sum(r['bytes'] for r in approved),'retained':'Current GLB/PNG/catalog resources; every original source and workflow-referenced artwork; source-layout annotations; final ten-plant dual-phase tank captures; all ten solid five-view captures; exact GPU loop/quarter-phase and MultiMesh population evidence; live pause/resume images; placement roundtrip; authoritative reports.','rebuildable_intermediates':'Dense solid meshes and full donor copies are rebuilt from protected source projects by build_expansion_v11.py solids. The complete native donors for roof/skin crops can be recreated from their recorded original image + pixel bounds.','superseded_evidence':'plant-native is replaced by plant-final; identical-model budget comparison pictures by the final tank views; discarded phase images by exact 0/2.5/10 loop images plus the retained encoded GPU motion video.','outputs':[str(REVIEW/'production.handoff.json'),str(REVIEW/'plants-in-tank.jpg'),str(REVIEW/'solids-front.jpg')]}
        save(REVIEW/'cleanup.validation.json',cleanup)
        for entry in approved:Path(entry['path']).unlink()
        for folder in [REVIEW/'intermediate-solids',REVIEW/'instancing/motion-frames']:
            if folder.exists() and not any(folder.iterdir()):folder.rmdir()
        cleanup['remaining_review_bytes']=sum(p.stat().st_size for p in REVIEW.rglob('*') if p.is_file());cleanup['remaining_runtime_asset_bytes']=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file());save(REVIEW/'cleanup.validation.json',cleanup)
        handoff['cleanup']=str(REVIEW/'cleanup.validation.json');handoff['artifact_lifecycle']='Paths of removed intermediate/source-donor copies and superseded captures remain as provenance in older reports; cleanup.validation.json records hashes and retained replacements/rebuild commands. Current runtime/source/unique evidence references remain available.'
    save(REVIEW/'production.handoff.json',handoff);save(REVIEW/'validation-report.json',handoff)
    print(json.dumps({'ok':True,**summary,'deleted_files':len(approved) if a.clean else 0,'user_acceptance':'pending'},ensure_ascii=False))
if __name__=='__main__':main()
