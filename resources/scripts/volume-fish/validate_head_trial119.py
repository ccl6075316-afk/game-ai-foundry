"""Validate local transverse trials against the frozen source and complete eye-support triangles.

This checks preservation and declared trial scope, not biological correctness.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb,accessor
from revise_head_width import gain_at


def ellipse_hits(tri,center,radius):
    q=(tri-np.asarray(center))/np.asarray(radius)
    hit=np.any(np.sum(q*q,axis=2)<=1+1e-10,axis=1)
    cross=[]
    for k in range(3):
        a=q[:,k];b=q[:,(k+1)%3];e=b-a
        t=np.clip(-np.sum(a*e,axis=1)/np.maximum(np.sum(e*e,axis=1),1e-30),0,1)
        hit|=np.sum((a+t[:,None]*e)**2,axis=1)<=1+1e-10
        cross.append(e[:,0]*(-a[:,1])-e[:,1]*(-a[:,0]))
    cross=np.array(cross).T
    area=(q[:,1,0]-q[:,0,0])*(q[:,2,1]-q[:,0,1])-(q[:,1,1]-q[:,0,1])*(q[:,2,0]-q[:,0,0])
    hit|=(np.abs(area)>1e-12)&(np.all(cross>=0,axis=1)|np.all(cross<=0,axis=1))
    return hit


def eye_regions(profile,species):
    pts=np.concatenate([np.array(c['base_surface_points']) for c in profile['caps']])[:,:2]
    mi=pts.min(0);ma=pts.max(0)
    regions=[{'name':'chart112_eye_support_and_full_fade','space':'XY','center':((mi+ma)/2).tolist(),'radius':((ma-mi)*.55*1.35).tolist()}]
    if species=='red_seabream':
        regions.append({'name':'active_friendly_eye_scale80_support','space':'UV','center':[.886,.438],'radius':[.04*1.5,.079*1.5]})
    return regions


def guards(doc,blob,profile,species):
    node=next(n for n in doc['nodes'] if n.get('name')=='Closed_body')
    prim=doc['meshes'][node['mesh']]['primitives'][0]
    pos=accessor(doc,blob,prim['attributes']['POSITION']);uv=accessor(doc,blob,prim['attributes']['TEXCOORD_0']);idx=accessor(doc,blob,prim['indices']).reshape(-1,3)
    result=[]
    for region in eye_regions(profile,species):
        values=pos[:,:2] if region['space']=='XY' else uv
        hit=ellipse_hits(values[idx].astype(float),region['center'],region['radius'])
        ids=np.unique(idx[hit]);assert len(ids),'Empty eye support'
        result.append({**region,'vertex_indices':ids.tolist(),'triangles':int(hit.sum()),'maximum_source_u':float(pos[ids,0].max()+.5)})
    return result


def validate(row,eye):
    sd,sb=read_glb(Path(row['source']));td,tb=read_glb(Path(row['target']));assert hashlib.sha256(Path(row['source']).read_bytes()).hexdigest()==row['source_sha256']
    for key in ('nodes','skins','animations','images','textures','materials'):
        assert sd.get(key)==td.get(key),'Changed '+key
    assert len(sd['meshes'])==len(td['meshes'])
    for sm,tm in zip(sd['meshes'],td['meshes']):
        assert {k:v for k,v in sm.items() if k!='primitives'}=={k:v for k,v in tm.items() if k!='primitives'}
        assert len(sm['primitives'])==len(tm['primitives'])
        for sp,tp in zip(sm['primitives'],tm['primitives']):
            assert {k:v for k,v in sp.items() if k!='attributes'}=={k:v for k,v in tp.items() if k!='attributes'}
    assert tb[:len(sb)]==sb,'Original BIN prefix changed'
    gs=guards(sd,sb,eye,row['species']);changed=0;checks=[]
    for sn,tn in zip(sd['nodes'],td['nodes']):
        if 'mesh' not in sn:continue
        for si,(sp,tp) in enumerate(zip(sd['meshes'][sn['mesh']]['primitives'],td['meshes'][tn['mesh']]['primitives'])):
            aa={k:accessor(sd,sb,v) for k,v in sp['attributes'].items()};bb={k:accessor(td,tb,v) for k,v in tp['attributes'].items()}
            assert aa.keys()==bb.keys();assert np.array_equal(accessor(sd,sb,sp['indices']),accessor(td,tb,tp['indices']))
            for key in aa:
                if sn['name'] not in row['mesh_allowlist'] or key not in ('POSITION','NORMAL','TANGENT'):assert np.array_equal(aa[key],bb[key]),'Unexpected '+sn['name']+'/'+key
            if sn['name'] not in row['mesh_allowlist']:continue
            p=aa['POSITION'];q=bb['POSITION'];mask=np.any(p!=q,axis=1)
            field=np.array([gain_at(row['stations'],float(v[0])+.5) for v in p]);g=field[:,0];derivative=field[:,1];active=g>1+1e-9
            assert np.array_equal(q[:,2],(p[:,2]*g).astype('<f4')),'Incorrect f32 transverse field'
            expected=aa['NORMAL'].astype(float).copy()
            expected[:,0]-=p[:,2]*derivative/g*expected[:,2]
            expected[:,2]/=g
            expected/=np.maximum(np.linalg.norm(expected,axis=1),1e-12)[:,None]
            expected[~active]=aa['NORMAL'][~active]
            assert np.max(abs(bb['NORMAL']-expected))<2e-6,'Incorrect normal inverse transpose'
            assert np.array_equal(p[:,:2],q[:,:2]),'Side XY changed'
            assert np.all(p[mask,0]+.5>row['stations'][0][0]),'Domain escaped'
            for key in ('POSITION','NORMAL','TANGENT'):
                if key in aa:assert np.array_equal(aa[key][p[:,0]+.5<=row['stations'][0][0]],bb[key][p[:,0]+.5<=row['stations'][0][0]]),'Frozen domain changed'
            assert np.isfinite(q).all();changed+=int(mask.sum())
            if si==0:
                for g in gs:
                    ids=g['vertex_indices'];assert np.array_equal(p[ids],q[ids]),'Eye support triangle moved: '+g['name']
            idx=accessor(td,tb,tp['indices']).reshape(-1,3)
            on=np.cross(p[idx[:,1]]-p[idx[:,0]],p[idx[:,2]]-p[idx[:,0]])
            nn=np.cross(q[idx[:,1]]-q[idx[:,0]],q[idx[:,2]]-q[idx[:,0]])
            assert np.all(np.sum(on*nn,axis=1)>0),'Triangle flipped or degenerated'
            assert np.isfinite(bb['NORMAL']).all() and np.max(abs(np.linalg.norm(bb['NORMAL'],axis=1)-1))<2e-5
            checks.append({'surface':si,'changed_vertices':int(mask.sum()),'side_XY_exact':True,'eye_triangles_frozen':si==0,'finite_normals_and_no_face_flips':True})
    assert changed>0,'No local trial change'
    return {'species':row['species'],'ok':True,'source_sha256':row['source_sha256'],'model_sha256':hashlib.sha256(Path(row['target']).read_bytes()).hexdigest(),'checks':checks,'eye_supports':[{k:v for k,v in g.items() if k!='vertex_indices'} for g in gs]}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--eyes',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rows=[]
    try:
        eyes=json.loads(a.eyes.read_text())['profiles']
        for row in json.loads(a.plan.read_text())['items']:rows.append(validate(row,eyes[row['species']]))
        result={'ok':True,'items':rows,'limits':'Frozen local scope, triangle orientation and eye preservation only. Need visual/full fin/body validation; not anatomical acceptance.'}
    except Exception as e:result={'ok':False,'items':rows,'error':str(e)}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':result['ok'],'error':result.get('error'),'species':[x['species'] for x in rows]}));return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
