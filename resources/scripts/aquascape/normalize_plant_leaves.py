"""Replace forced curled variants with normal leaves from the SAME source art.

No new leaf count, no repainted bitmap, no added triangles. Existing attachment
points and plant identity remain; native binds are retargeted to compact normal
leaf postures. Selection is based on measured source silhouettes, not a fixed
list of leaf variants. Numerical controls here constrain the mesh, not prompts.
"""
import argparse,copy,json
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial.transform import Rotation
from skimage.morphology import medial_axis
from build_from_art import Glb,split_leaves,foreground
from clean_plant_material_edges import source_parts
from rig_plant_current import read_glb,array,append
from optimize_scenery import load,save,sha,metrics,compact,primitive,budget_type

def straightness(mask):
    sk=medial_axis(mask,rng=0);yy,xx=np.nonzero(sk)
    ids=np.full(mask.shape,-1,dtype=int);ids[yy,xx]=np.arange(len(xx));rows=[];cols=[];weights=[]
    for dy,dx in [(0,1),(1,-1),(1,0),(1,1)]:
        y2=yy+dy;x2=xx+dx;valid=(y2>=0)&(y2<mask.shape[0])&(x2>=0)&(x2<mask.shape[1]);src=np.arange(len(xx))[valid];dst=ids[y2[valid],x2[valid]];ok=dst>=0
        rows.extend(src[ok]);cols.extend(dst[ok]);weights.extend([np.hypot(dy,dx)]*int(ok.sum()))
    graph=coo_matrix((weights+weights,(rows+cols,cols+rows)),shape=(len(xx),len(xx))).tocsr()
    root=int(np.argmax(yy));dist=dijkstra(graph,indices=root);dist[~np.isfinite(dist)]=0;tip=int(np.argmax(dist))
    return float(np.hypot(xx[tip]-xx[root],yy[tip]-yy[root])/max(dist[tip],1))

def leaf_data(doc,binary,mesh):
    p=mesh['primitives'][0];attrs=p['attributes'];j=array(doc,binary,attrs['JOINTS_0']);w=array(doc,binary,attrs['WEIGHTS_0']);chain=np.unique(j[w>0]).astype(int)
    node=doc['nodes'][doc['skins'][0]['joints'][int(chain[0])]];basis=Rotation.from_quat(node['rotation']).as_matrix();anchor=np.array(node['translation'])
    last=doc['nodes'][doc['skins'][0]['joints'][int(chain[-1])]]
    # Source joints are uniformly spaced along the original leaf's extent.
    length=sum(np.linalg.norm(doc['nodes'][doc['skins'][0]['joints'][int(k)]]['translation']) for k in chain[1:])/.8
    return {'primitive':p,'v':array(doc,binary,attrs['POSITION']),'uv':array(doc,binary,attrs['TEXCOORD_0']),'basis':basis,'anchor':anchor,'chain':chain,'length':float(length)}

def normalize(root,row,source,out,policy):
    d,b=read_glb(source);g=Glb();g.doc=copy.deepcopy(d);g.bin=bytearray(b)
    parts_path=source_parts(root,row['id']);images=split_leaves(parts_path);scores=np.array([straightness(foreground(im)) for im in images])
    reviewed=load(root/'resources/aquascape/normal-leaf-sources.json')
    if row['id'] not in reviewed['plants']:raise ValueError('Review this species normal source leaves first; do not impose a common leaf template: '+row['id'])
    if reviewed.get('source_sha256',{}).get(row['id'])!=sha(parts_path):raise ValueError('Normal leaf reference review is stale for this source artwork: '+row['id'])
    healthy=np.asarray(reviewed['plants'][row['id']],dtype=int)
    meshes=[m for m in d['meshes'] if m['name'].startswith('traced_leaf_')];data=[leaf_data(d,b,m) for m in meshes]
    by_part={i%len(images):i for i in range(len(meshes))};healthy=np.array([i for i in healthy if i in by_part],dtype=int)
    if not len(healthy):raise ValueError('No ordinary source leaf available: '+row['id'])
    kind=budget_type(row,policy);rhizome=row['id'] in ['anubias','bucephalandra','lagenandra_red'];changes=[]
    for index,(mesh,old) in enumerate(zip(meshes,data)):
        part=index%len(images);chosen=part if part in healthy else int(healthy[index%len(healthy)]);donor=data[by_part[chosen]]
        local=(donor['v']-donor['anchor'])@donor['basis'];uv=donor['uv'];t=np.clip(1-uv[:,1],0,1)
        # Keep leaf thickness while removing the old uniformly exaggerated
        # out-of-plane bulge. Paint/UV samples remain unchanged.
        _,group=np.unique(uv,axis=0,return_inverse=True);center_z=np.zeros(len(local))
        for group_id in np.unique(group):
            ix=group==group_id;center_z[ix]=np.median(local[ix,2])
        local[:,2]=local[:,2]-center_z+center_z*.18
        local*=old['length']/max(donor['length'],1e-8)
        up=old['basis'][:,1].copy()
        # Constrain the existing source headings to a coherent rooted clump;
        # no shared per-leaf angle array or repeated 'special leaf' slot.
        up[[0,2]]*=.55 if kind=='ribbon_plant' else (.85 if rhizome else .7)
        up[1]=max(up[1],.55 if rhizome else .8);up/=np.linalg.norm(up)
        old_up=old['basis'][:,1];axis=np.cross(old_up,up);axis_length=float(np.linalg.norm(axis))
        alignment=Rotation.from_rotvec(axis/max(axis_length,1e-12)*np.arctan2(axis_length,float(np.dot(old_up,up)))).as_matrix()
        # Parallel-transport the SOURCE leaf plane. Do not face every blade
        # towards the viewer or replace source depth with a flat generic fan.
        basis=alignment@old['basis']
        v=(local@basis.T+old['anchor']).astype('float32');faces=np.arange(len(v)).reshape(-1,3)
        knots=np.array([.08,.28,.48,.68,.88]);lo=np.clip(np.searchsorted(knots,t,side='right')-1,0,3);alpha=np.clip((t-knots[lo])/.2,0,1)
        joints=np.zeros((len(v),4),dtype='uint16');weights=np.zeros((len(v),4),dtype='float32');joints[:,0]=old['chain'][lo];joints[:,1]=old['chain'][lo+1];weights[:,0]=1-alpha;weights[:,1]=alpha
        target=next(m for m in g.doc['meshes'] if m['name']==mesh['name']);target['primitives']=[primitive(g,v,faces,uv,donor['primitive']['material'],{'JOINTS_0':(joints,'VEC4',5123),'WEIGHTS_0':(weights,'VEC4',5126)})]
        base_node=g.doc['nodes'][d['skins'][0]['joints'][int(old['chain'][0])]];base_node['rotation']=Rotation.from_matrix(basis).as_quat().tolist()
        # Each bone chain follows the new normal leaf; original authored motion
        # samples are retained, with fresh inverse binds for the changed rest.
        for k,joint in enumerate(old['chain'][1:],1):g.doc['nodes'][d['skins'][0]['joints'][int(joint)]]['translation']=[0,old['length']*.2,0]
        changes.append({'mesh':mesh['name'],'old_source_part':part,'normal_source_part':chosen,'old_part_score':float(scores[part]),'normal_part_score':float(scores[chosen]),'triangles':len(faces),'attachment_m':old['anchor'].tolist()})
    parents={c:i for i,n in enumerate(g.doc['nodes']) for c in n.get('children',[])};world={}
    for i,node in enumerate(g.doc['nodes']):
        mat=np.eye(4);mat[:3,:3]=Rotation.from_quat(node.get('rotation',[0,0,0,1])).as_matrix();mat[:3,3]=node.get('translation',[0,0,0]);world[i]=world[parents[i]]@mat if i in parents else mat
    inverse=np.stack([np.linalg.inv(world[i]).flatten(order='F') for i in g.doc['skins'][0]['joints']]).astype('float32');g.doc['skins'][0]['inverseBindMatrices']=append(g,inverse,'MAT4')
    g.doc.setdefault('extras',{})['leaf_revision']='natural-leaf-v10';g.doc['asset']['generator']='Foundry normal source leaves, compact rooted posture, retargeted native binds'
    compact(g);out.parent.mkdir(parents=True,exist_ok=True);g.save(out)
    after=metrics(out)
    if after['triangles']>policy['types'][kind]['hard_limit']:raise ValueError('Natural leaf version exceeds existing budget: '+row['id'])
    if after['triangles']>metrics(source)['triangles']:raise ValueError('This leaf correction may not add triangles: '+row['id'])
    return {'id':row['id'],'source':str(source),'source_sha256':sha(source),'source_parts':str(parts_path),'source_parts_sha256':sha(parts_path),'normal_source_review_sha256':sha(root/'resources/aquascape/normal-leaf-sources.json'),'output':str(out),'sha256':sha(out),'triangles':after['triangles'],'source_part_scores':scores.tolist(),'ordinary_source_parts':healthy.tolist(),'leaf_changes':changes,'original_image_bytes_retained':True,'original_animation_samples_retained':True,'attachment_points_retained':True,'rig_rest_retargeted':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--deploy',action='store_true');a=p.parse_args();root=a.root.resolve();game=root/'projects/fishing-2d/game';policy=load(root/'resources/aquascape/geometry-budgets.json');catalog=load(a.input);rows=[]
    species={r['id']:r for r in load(root/'resources/aquascape/catalog-20-v5.json')['plants']}
    for row in catalog['assets']:
        if not row.get('animated'):continue
        source=game/row.get('pre_natural_leaf_model',row['model']).removeprefix('res://');out=a.output/'plants'/(row['id']+'.glb');result=normalize(root,row,source,out,policy);rows.append(result)
        row.update(pre_natural_leaf_model=row.get('pre_natural_leaf_model',row['model']),model='res://'+out.resolve().relative_to(game).as_posix(),geometry_revision='natural-leaf-v10',natural_leaf_build_report=str(a.report.resolve()),shader_model='res://'+(a.output/'shader-plants'/(row['id']+'.glb')).resolve().relative_to(game).as_posix(),shader_metadata='res://'+(a.output/'shader-plants/shader-plants.validation.json').resolve().relative_to(game).as_posix())
        row.pop('leaf_count',None)
        if row['id'] in species:row['morphology']=species[row['id']]['morphology']
        row['plant_art_policy']='A natural clump of the named species; no prescribed leaf count, special curl/unfolding slot, or spread/bend angle.'
        print(json.dumps({'id':row['id'],'triangles':result['triangles'],'ordinary_parts':result['ordinary_source_parts']}),flush=True)
    save(a.output/'catalog.json',catalog);save(a.report,{'schema_version':1,'command':'aquascape.normal-source-leaves','ok':True,'status':'done','next_action':'human_review','outputs':rows,'failures':[],'user_acceptance':'pending','scope':'Existing native-resolution normal leaf donors and plant identity; no bitmap repainting, new leaf count or added detail budget.'})
    if a.deploy:
        from validate_scenery_budget import validate
        report=validate(root,[a.output/'catalog.json'],a.report.with_name('deployment.validation.json'))
        if not report['ok']:raise ValueError(report['failures'])
        save(a.input,catalog)
if __name__=='__main__':main()
