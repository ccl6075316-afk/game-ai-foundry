"""Execute a frozen species-specific head study through rig/material transport.

Creates review candidates only. Does not accept or install fish.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--blender',type=Path,required=True)
    a=p.parse_args();plan=json.loads(a.plan.read_text(encoding='utf8'));scripts=Path(__file__).resolve().parent
    for row in plan['items']:
        dest=Path(row['output']).resolve();dest.mkdir(parents=True,exist_ok=True)
        assert sha(row['model'])==row['model_sha256']
        def run(name,args,blender=False):
            cmd=[str(a.blender),'-b','--python',str(scripts/name),'--',*args] if blender else [sys.executable,'-X','utf8',str(scripts/name),*args]
            r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=1200)
            (dest/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf8')
            assert r.returncode==0 and 'Traceback' not in r.stdout+r.stderr,(name,r.stdout[-2000:],r.stderr[-2000:])
        run('prepare_mouth_surface.py',['--model',row['model'],'--output',str(dest)])
        surface=dest/'surface.plan.json'
        save(surface,{'species':row['species'],'input':str(dest/'source-shell.npz'),'input_sha256':sha(dest/'source-shell.npz'),'surface':row['surface'],'constraints':row['constraints']})
        run('remesh_mouth_surface.py',[str(surface)],True)
        gray=dest/'whole-head-gray.mesh.json';transport=dest/'transport.plan.json'
        save(transport,{'base_gray_mesh':str(gray),'base_gray_sha256':sha(gray),'base_surface_plan':str(surface),'base_surface_plan_sha256':sha(surface),'source_attributes':str(dest/'source-attributes.npz'),'source_attributes_sha256':sha(dest/'source-attributes.npz')})
        run('transport_mouth_material.py',[str(transport)],True)
        body=dest/'textured-body.mesh.json';skin=dest/'skinning.plan.json'
        save(skin,{'species':row['species'],'source_model':row['model'],'mesh':'Closed_body','body':str(body),'output':str(dest),'maximum_discarded_weight':1e-5,'maximum_source_projection_distance':5e-6,'maximum_lip_projection_distance':.001,'frozen_inputs':{row['model']:sha(row['model']),str(body):sha(body)}})
        run('transfer_mouth_skinning.py',['--plan',str(skin)],True)
        local=dest/'localize.plan.json'
        save(local,{'source_model':row['model'],'mesh':'Closed_body','candidate_body':str(dest/'body.bound.json'),'posterior_cut_x':row['posterior_cut_x'],'anterior_cut_x':row['anterior_cut_x'],'output':str(dest/'localized'),'frozen_inputs':{row['model']:sha(row['model']),str(dest/'body.bound.json'):sha(dest/'body.bound.json')}})
        run('localize_mouth_study.py',['--plan',str(local)])
        result=dest/'localized/body.bound.json';receipt=dest/'skinning.validation.json'
        save(dest/'preview.plan.json',{'species':row['species'],'body':str(result),'body_sha256':sha(result),'model_sha256':row['model_sha256'],'skinning_report':str(receipt),'skinning_report_sha256':sha(receipt)})
        save(dest/'build.validation.json',{'ok':True,'status':'done','next_action':'human_review','species':row['species'],'plan_sha256':sha(a.plan),'outputs':[{'path':str(result),'sha256':sha(result)}],'production_installed':False,'full_fish_accepted':False})
        print('MOUTH_CANDIDATE_BUILT',row['species'],flush=True)

if __name__=='__main__':main()
