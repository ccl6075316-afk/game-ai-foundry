"""Splice a reviewed anterior surface into its original rigged body.

Only for a frozen pair of single, star-shaped cross-section loops. Refuses
nonmanifold results. The explicit cut planes are species/candidate parameters.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb, accessor


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def clip(part, plane, anterior):
    keys = ['vertices','normals','uv','uv2','reference_positions','reference_normals','joints','weights','chart']
    data = {k:np.asarray(part[k],dtype=float) for k in keys}
    result = {k:[] for k in keys}
    faces, cache = [], {}
    p = data['vertices']
    keep = p[:,0]>=plane if anterior else p[:,0]<=plane

    def vertex(a, b=None):
        key = (a,) if b is None else tuple(sorted((a,b)))
        if key in cache:
            return cache[key]
        idx = len(result['vertices']); cache[key] = idx
        if b is None:
            for k in keys:result[k].append(data[k][a].tolist())
        else:
            t = (plane-p[a,0])/(p[b,0]-p[a,0])
            for k in keys:
                if k in ['joints','weights']:continue
                x = data[k][a]*(1-t)+data[k][b]*t
                if k=='vertices':x[0]=plane
                if k in ['normals','reference_normals']:x/=max(np.linalg.norm(x),1e-20)
                result[k].append(x.tolist())
            weights={}
            for i, factor in [(a,1-t),(b,t)]:
                for joint,w in zip(data['joints'][i],data['weights'][i]):
                    weights[int(joint)]=weights.get(int(joint),0)+float(w*factor)
            ordered=sorted(weights.items(),key=lambda x:(-x[1],x[0]))
            assert sum(x[1] for x in ordered[4:])<1e-5
            ordered=ordered[:4]+[(0,0.)]*max(0,4-len(ordered))
            total=sum(x[1] for x in ordered)
            result['joints'].append([j for j,w in ordered])
            result['weights'].append([w/total for j,w in ordered])
        return idx

    for triangle in np.asarray(part['triangles']).reshape(-1,3):
        polygon=[]
        for a,b in zip(triangle,np.roll(triangle,-1)):
            if keep[a]:polygon.append(vertex(int(a)))
            if keep[a]!=keep[b]:polygon.append(vertex(int(a),int(b)))
        for i in range(1,len(polygon)-1):faces.append([polygon[0],polygon[i],polygon[i+1]])
    result['triangles']=faces
    result['source_surface']=part['source_surface']
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    args=parser.parse_args()
    plan=json.loads(args.plan.read_text(encoding='utf8'))
    for p,h in plan['frozen_inputs'].items():assert sha(p)==h,p
    candidate=json.loads(Path(plan['candidate_body']).read_text(encoding='utf8'))
    charts=json.loads(Path(plan['candidate_skin_records']).read_text(encoding='utf8')) if plan.get('candidate_skin_records') else np.zeros((len(candidate['parts'][0]['vertices']),4)).tolist()
    doc,binary=read_glb(Path(plan['source_model']))
    node=next(n for n in doc['nodes'] if n.get('name')==plan['mesh'])
    originals=[]
    for si,prim in enumerate(doc['meshes'][node['mesh']]['primitives']):
        attrs=prim['attributes']
        p=accessor(doc,binary,attrs['POSITION']);n=accessor(doc,binary,attrs['NORMAL'])
        part={'source_surface':si,'vertices':p.tolist(),'normals':n.tolist(),
              'reference_positions':p.tolist(),'reference_normals':n.tolist(),
              'uv':accessor(doc,binary,attrs['TEXCOORD_0']).tolist(),
              'uv2':accessor(doc,binary,attrs['TEXCOORD_1']).tolist() if 'TEXCOORD_1' in attrs else np.zeros((len(p),2)).tolist(),
              'joints':accessor(doc,binary,attrs['JOINTS_0']).tolist(),
              'weights':accessor(doc,binary,attrs['WEIGHTS_0']).tolist(),
              'chart':np.zeros((len(p),4)).tolist(),
              'triangles':accessor(doc,binary,prim['indices']).reshape(-1,3)[:,[0,2,1]].tolist()}
        originals.append(part)
    parts=[]
    for si,part in enumerate(candidate['parts']):
        part['chart']=charts if si==0 else np.zeros((len(part['vertices']),4)).tolist()
        left=clip(originals[si],plan['posterior_cut_x'],False)
        right=clip(part,plan['anterior_cut_x'],True)
        assert left['vertices'] or si!=0
        if not left['vertices']:
            right['triangles']=np.asarray(right['triangles']).reshape(-1).tolist();parts.append(right);continue
        offset=len(left['vertices'])
        for key in left:
            if key in ['triangles','source_surface']:continue
            left[key].extend(right[key])
        left['triangles'].extend((np.asarray(right['triangles'])+offset).tolist())
        v=np.asarray(left['vertices'])
        rings=[]
        for plane in [plan['posterior_cut_x'],plan['anterior_cut_x']]:
            ids=np.flatnonzero(abs(v[:,0]-plane)<1e-9)
            unique={tuple(np.round(v[i],8)):int(i) for i in ids}
            ids=list(unique.values());assert len(ids)>8
            center=np.mean(v[ids,1:],axis=0)
            angles=np.arctan2(v[ids,2]-center[1],v[ids,1]-center[0])
            order=np.argsort(angles)
            rings.append([(float(angles[i]),ids[i]) for i in order])
        a,b=rings
        # Start both rings at the same angular seam and zipper monotonically.
        a=a+[(a[0][0]+2*np.pi,a[0][1])]
        b=b+[(b[0][0]+2*np.pi,b[0][1])]
        i=j=0;bridge=[]
        while i<len(a)-1 or j<len(b)-1:
            if j==len(b)-1 or (i<len(a)-1 and a[i+1][0]<=b[j+1][0]):
                face=[a[i][1],a[i+1][1],b[j][1]];i+=1
            else:
                face=[a[i][1],b[j+1][1],b[j][1]];j+=1
            xyz=v[face];normal=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0])
            ref=np.asarray(left['normals'])[face].mean(axis=0)
            # Godot clockwise triangles have inward cross-products.
            if normal@ref>0:face=[face[0],face[2],face[1]]
            bridge.append(face)
        left['triangles'].extend(bridge)
        left['triangles']=np.asarray(left['triangles']).reshape(-1).tolist()
        parts.append(left)
    # Enforce the same 1e-7 native position identity used by the body gate.
    # Remeshing can create sub-identity sliver edges at a material boundary.
    # Collapse those positions, remove only their collapsed faces, and require
    # the complete welded shell to remain manifold afterwards.
    all_positions=np.concatenate([np.asarray(p['vertices']) for p in parts])
    _,first,inverse=np.unique(np.round(all_positions,7),axis=0,return_index=True,return_inverse=True)
    canonical=all_positions[first][inverse]
    weld_distance=float(np.linalg.norm(canonical-all_positions,axis=1).max())
    assert weld_distance<1e-7
    offset=0;collapsed_faces=0
    for part in parts:
        count=len(part['vertices']);pos=canonical[offset:offset+count];offset+=count
        tri=np.asarray(part['triangles']).reshape(-1,3)
        keys=np.round(pos,7)
        valid=np.any(keys[tri[:,0]]!=keys[tri[:,1]],axis=1)&np.any(keys[tri[:,1]]!=keys[tri[:,2]],axis=1)&np.any(keys[tri[:,0]]!=keys[tri[:,2]],axis=1)
        collapsed_faces+=int((~valid).sum())
        part['vertices']=pos.tolist();part['triangles']=tri[valid].ravel().tolist()
    edges=Counter();triangles=0
    for part in parts:
        pos=np.asarray(part['vertices']);tri=np.asarray(part['triangles']).reshape(-1,3)
        for face in tri:
            points=[tuple(np.round(pos[i],7)) for i in face]
            assert len(set(points))==3,('Degenerate splice triangle',part['source_surface'],pos[face].tolist())
            for a,b in zip(points,points[1:]+points[:1]):edges[tuple(sorted((a,b)))]+=1
        triangles+=len(tri)
    assert edges and all(n==2 for n in edges.values()),Counter(edges.values())
    output=Path(plan['output']);output.mkdir(parents=True,exist_ok=True)
    skin_records=parts[0]['chart']
    for part in parts:
        del part['chart']
        part['joints']=np.asarray(part['joints'],dtype=int).tolist()
    body_path=output/'body.bound.json';chart_path=output/'skin.records.json'
    body_path.write_text(json.dumps({'parts':parts},separators=(',',':')),encoding='utf8')
    chart_path.write_text(json.dumps(skin_records,separators=(',',':')),encoding='utf8')
    report={'schema_version':1,'ok':True,'command':'fish.localize-mouth-study','status':'done','next_action':'human_review','inputs':plan['frozen_inputs'],
            'outputs':[{'path':str(p),'sha256':sha(p)} for p in [body_path,chart_path]],
            'summary':{'triangles':triangles,'watertight_position_welded':True,'posterior_cut_x':plan['posterior_cut_x'],
                       'position_identity_native':1e-7,'maximum_position_weld_native':weld_distance,'collapsed_sub_identity_faces_removed':collapsed_faces,
                       'anterior_cut_x':plan['anterior_cut_x'],'scope':'Candidate splice. New collar, real skinned fin distances, materials and motion still require validation.'},'failures':[]}
    (output/'localize.validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report['summary']))


if __name__=='__main__':main()
