"""Independently compare the full attachment section and free-tail transform.

This is not visual acceptance, nor a substitute for actual skinned contact.
The rejected paper-thin basal section must fail the section-width criterion.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb,accessor
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    cli=argparse.ArgumentParser();cli.add_argument('--before',type=Path,required=True);cli.add_argument('--after',type=Path,required=True);cli.add_argument('--parameters',type=Path,required=True);cli.add_argument('--output',type=Path,required=True);a=cli.parse_args()
    old=json.loads(a.before.read_text())['items'];new=json.loads(a.after.read_text())['items'];params=json.loads(a.parameters.read_text())['species'];rows=[]
    for before,after in zip(old,new):
        sp=before['species'];assert sp==after['species'];d,b=read_glb(Path(before['model']));nd,nb=read_glb(Path(after['model']))
        def prim(doc,name):return doc['meshes'][next(n['mesh'] for n in doc['nodes'] if n.get('name')==name and 'mesh' in n)]['primitives']
        p=prim(d,'Caudal')[0];q=prim(nd,'Caudal')[0];v=accessor(d,b,p['attributes']['POSITION']);w=accessor(nd,nb,q['attributes']['POSITION'])
        body=np.concatenate([accessor(d,b,r['attributes']['POSITION']) for r in prim(d,before['body'])]);rear=body[:,0].min();cap=body[np.abs(body[:,0]-rear)<1e-6];yc=(cap[:,1].min()+cap[:,1].max())/2
        order=np.argsort(cap[:,1]);cap=cap[order];ys=np.unique(np.round(cap[:,1],7));width=np.array([np.abs(cap[np.abs(cap[:,1]-y)<1.1e-7,2]).max() for y in ys])
        ids=np.array(before['fins']['Caudal']['ids']);assert list(ids)==after['fins']['Caudal']['ids'];target=np.interp(v[ids,1],ys,width);selected=target>.001
        old_error=float(np.max(np.abs(np.abs(v[ids,2][selected])-target[selected])));new_error=float(np.max(np.abs(np.abs(w[ids,2][selected])-target[selected])))
        assert old_error>.003 and new_error<.0001,'Section width must distinguish rejected flat root'
        assert np.max(np.abs(v[ids,:2]-w[ids,:2]))<1e-7
        free=rear-v[:,0]>=params[sp]['collar_native'];expected=v[free].copy();scale=params[sp]['free_tail_scale'];expected[:,0]=rear+(expected[:,0]-rear)*scale;expected[:,1]=yc+(expected[:,1]-yc)*scale
        error=float(np.max(np.abs(expected-w[free])));assert error<1e-7
        assert d['nodes']==nd['nodes'] and d['skins']==nd['skins'] and d['animations']==nd['animations'] and d['images']==nd['images'] and d['materials']==nd['materials']
        for name in p['attributes']:
            if name not in ['POSITION','NORMAL']:assert np.array_equal(accessor(d,b,p['attributes'][name]),accessor(nd,nb,q['attributes'][name]))
        assert np.array_equal(accessor(d,b,p['indices']),accessor(nd,nb,q['indices']))
        for n in d['nodes']:
            if 'mesh' not in n or n.get('name')=='Caudal':continue
            for bp,ap in zip(d['meshes'][n['mesh']]['primitives'],nd['meshes'][n['mesh']]['primitives']):
                shift=params[sp].get('clearance_offsets',{}).get(n.get('name'))
                if shift:
                    assert bp['indices']==ap['indices']
                    for key,index in bp['attributes'].items():
                        actual=accessor(nd,nb,ap['attributes'][key]);expected=accessor(d,b,index)
                        if key=='POSITION':expected+=np.array(shift,dtype=np.float32)
                        assert np.array_equal(expected,actual)
                    assert before['fins'][n['name']]['ids']==after['fins'][n['name']]['ids']
                else:
                    assert bp==ap
                    for index in list(bp['attributes'].values())+[bp['indices']]:assert np.array_equal(accessor(d,b,index),accessor(nd,nb,index))
        assert nb[:len(b)]==b,'Embedded source/rig/animation binary changed'
        rows.append({'species':sp,'ok':True,'before_sha256':sha(before['model']),'model_sha256':sha(after['model']),'root_count':len(ids),'complete_root_ids_and_xy_preserved':True,'old_max_section_error_native':old_error,'new_max_section_error_native':new_error,'old_flat_root_negative_control_failed':True,'free_tail_scale':scale,'free_vertices':int(free.sum()),'free_transform_max_error':error,'UV_indices_skin_source_and_other_meshes_identical':True,'explicit_noncaudal_position_offsets_native':params[sp].get('clearance_offsets',{})})
    a.output.write_text(json.dumps({'ok':all(r['ok'] for r in rows),'parameters_sha256':sha(a.parameters),'checker_sha256':sha(__file__),'records':rows,'limits':'Rest-space assembly constraints only. Artist review and full dynamic root/membrane/opacity gates remain required.'},indent=2),encoding='utf8')
    print(json.dumps(rows))
if __name__=='__main__':main()
