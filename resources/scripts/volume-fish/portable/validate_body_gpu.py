"""Check discrete actual GPU body alpha coverage for arbitrary declared surfaces.

Cold GLTFDocument import, actual-array diagnostic probes, two native phases and
8 matching views. This is not mesh closure, anatomy, full077 or full490.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image
from parts import freeze, fresh_output, read, require, sha

def reject_engine_errors(log):
    require(not any(marker in log for marker in ('ERROR:', 'SCRIPT ERROR', 'Parse Error', 'Assertion failed')), 'GPU engine logged an error: '+log[-1800:])

def missing_pixels(actual, reference):
    actual=np.asarray(Image.open(actual).convert('RGBA'));reference=np.asarray(Image.open(reference).convert('RGBA'))
    require(actual.shape==reference.shape,'Coverage image dimensions differ')
    mask=reference[:,:,3]>128
    require(int(mask.sum())>30,'Empty reference body')
    return int((mask & (actual[:,:,3]<128)).sum()),int(mask.sum())

def validate(manifest_path, godot, project, clip, output, dotnet=None):
    manifest_path=Path(manifest_path).resolve();godot=Path(godot).resolve();project=Path(project).resolve();output=fresh_output(output)
    manifest=read(manifest_path)
    require(manifest.get('kind')=='fish_portable_part_manifest' and manifest.get('ok'),'Portable part manifest required')
    # Recompute source ownership/opacity; do not trust a hand-edited manifest's pass.
    spec={'parts':[{'name':p['source_name'],'role':p['role'],'source_node':p['source_node'],'source_surface':p['source_surface'],'logical_name':p['name'],'opaque_uv':p['opaque_uv']} for p in manifest['parts']],'expected':manifest['expected']}
    require(freeze(manifest['model'],spec)==manifest,'Stale or altered canonical part manifest')
    require(godot.is_file() and (project/'project.godot').is_file(),'Existing Godot and project required')
    require(isinstance(clip,str) and bool(clip),'Explicit native clip required')
    helper=Path(__file__).resolve().parent; capture=helper/'capture_body_gpu.gd'
    inputs={str(p):sha(p) for p in [manifest_path,Path(manifest['model']),Path(__file__).resolve(),capture,helper/'parts.py',helper/'PackedFishParts.gd',helper/'glb_io.py']}
    output.mkdir(parents=True)
    plan={'model':manifest['model'],'model_sha256':manifest['model_sha256'],'packed_parts_manifest':str(manifest_path),'packed_parts_manifest_sha256':sha(manifest_path),'poses':[{'clip':clip,'fraction':0.0},{'clip':clip,'fraction':0.37}],'frozen_inputs':inputs}
    plan_path=output/'capture-plan.json';plan_path.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf8')
    result={'ok':False,'kind':'body_gpu_coverage_discrete','formal_acceptance':False,'model_sha256':manifest['model_sha256'],'manifest_sha256':sha(manifest_path),'plan_sha256':sha(plan_path),'source_dependencies':inputs,'failures':[],'scope':'Two discrete native poses/eight views each; 0 missing body pixels and transparent negative control. Does not prove closed mesh, anatomy, full077/full490, controllers or continuous-time coverage.'}
    try:
        env=dict(os.environ)
        if dotnet:env['DOTNET_ROOT']=str(Path(dotnet).resolve())
        command=[str(godot),'--path',str(project),'--rendering-method','gl_compatibility','--audio-driver','Dummy','--windowed','--position','-3000,-3000','--resolution','64x64','--disable-render-loop','--log-file',str(output/'godot.log'),'--script',str(capture),'--',str(plan_path),str(output)]
        run=subprocess.run(command,text=True,capture_output=True,timeout=120,env=env)
        log=run.stdout+run.stderr;(output/'capture.log').write_text(log,encoding='utf8')
        reject_engine_errors(log)
        require(run.returncode==0 and (output/'capture.validation.json').is_file(),'GPU capture failed: '+log[-1800:])
        data=read(output/'capture.validation.json');require(data.get('ok'),str(data.get('failures')))
        require(data['model_sha256']==manifest['model_sha256'] and data['plan_sha256']==sha(plan_path) and data['frozen_inputs']==inputs,'Stale GPU bindings')
        require(data['body_surfaces']==sum(p['opaque_uv'] for p in manifest['parts']),'Body surface inventory mismatch')
        require(data['runtime_meshes_after_cleanup']==1,'Diagnostic probes were not cleared')
        require(data['source_donor_rgba_sha256']==data['actual_donor_rgba_sha256']==manifest['body_opacity']['rgba_sha256'],'Actual GPU donor changed')
        require(len(data['pose_digests'])==2 and data['pose_digests'][0]!=data['pose_digests'][1],'Native poses did not change actual rig; select an animated clip')
        records=data['records'];require(len(records)==16 and {(r['pose'],r['view']) for r in records}=={(p,v) for p in range(2) for v in range(8)},'Incomplete discrete view inventory')
        for row in records:
            require(row['pose_before']==row['pose_after'] and row['camera_before']==row['camera_after'],'Actual/reference pose or camera changed')
            for key in ('actual','reference'):require(sha(output/row[key])==row[key+'_sha256'],'Changed GPU capture')
            row['missing_body_pixels'],row['reference_pixels']=missing_pixels(output/row['actual'],output/row['reference'])
        negative=data['negative'];require(sha(output/negative['actual'])==negative['actual_sha256'],'Changed transparent negative')
        negative['missing_body_pixels'],negative['reference_pixels']=missing_pixels(output/negative['actual'],output/negative['reference'])
        require(negative['missing_body_pixels']>0,'Transparent negative was not rejected')
        require(all(sha(p)==digest for p,digest in inputs.items()),'Dependencies changed during GPU comparison')
        require(all(r['missing_body_pixels']==0 for r in records),'Missing actual body pixels in discrete views')
        result.update(ok=True,records=records,negative_control=negative,pose_digests=data['pose_digests'],body_surfaces=data['body_surfaces'],body_triangles=data['body_triangles'],actual_donor_rgba_sha256=data['actual_donor_rgba_sha256'],partition_proof=data['partition_proof'],engine=data['engine'])
    except (ValueError,AssertionError,KeyError,IndexError,TypeError,OSError,subprocess.TimeoutExpired) as error:
        result['failures']=[{'kind':'validation','code':'body_gpu_coverage_discrete_failed','message':str(error)[:2200]}]
    result.update(command='portable.validate_body_gpu',status='done' if result['ok'] else 'failed',next_action='none' if result['ok'] else 'fix_input')
    report=output/'completion.validation.json';report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result,report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('manifest','godot','project','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--clip',required=True);p.add_argument('--dotnet',type=Path);p.add_argument('--json',action='store_true');args=p.parse_args()
    try:
        result,report=validate(args.manifest,args.godot,args.project,args.clip,args.output,args.dotnet)
        receipt={'ok':result['ok'],'command':result['command'],'status':result['status'],'next_action':result['next_action'],'outputs':[str(report)],'summary':{'kind':result['kind'],'formal_acceptance':False},'failures':result['failures']}
    except (ValueError,AssertionError,KeyError,IndexError,TypeError,OSError) as error:
        receipt={'ok':False,'command':'portable.validate_body_gpu','status':'failed','next_action':'fix_input','outputs':[],'failures':[{'kind':'validation','code':'body_gpu_input_invalid','message':str(error)[:1200]}]}
    print(json.dumps(receipt));return 0 if receipt['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
