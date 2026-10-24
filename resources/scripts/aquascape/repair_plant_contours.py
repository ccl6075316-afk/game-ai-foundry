"""Remesh leaf surfaces around intact source polygons; retain the existing pose.

The original parametric surface is recovered from exported positions and UVs,
then sampled on constrained polygon triangles. Roots, materials, bones and clips
are retained. New surface vertices receive the same fixed-base weight profile.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from build_from_art import Glb,split_leaves,foreground
from rig_plant_current import read_glb,array,append
from clean_plant_material_edges import source_parts
from leaf_polygon import triangulate,cross

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def features(uv):
    t=1-uv[:,1]
    return np.c_[uv[:,0],t,t*t,np.sin(np.pi*t),np.ones(len(t))]

def remesh(source,parts,output,static):
    doc,binary=read_glb(source);g=Glb();g.doc=copy.deepcopy(doc);g.bin=bytearray(binary)
    leaves=split_leaves(parts);reports=[]
    for mesh in g.doc['meshes']:
        if not mesh['name'].startswith('traced_leaf_'):continue
        leaf_id=int(mesh['name'].rsplit('_',1)[1])-1;image=leaves[leaf_id%6];mask=foreground(image);h,w=mask.shape
        old=mesh['primitives'][0];attrs=old['attributes'];uv=array(doc,binary,attrs['TEXCOORD_0']);position=array(doc,binary,attrs['POSITION'])
        triangle_uv=uv.reshape(-1,3,2);signed=cross(triangle_uv[:,1]-triangle_uv[:,0],triangle_uv[:,2]-triangle_uv[:,0])
        front=np.repeat(signed<-.00000001,3);back=np.repeat(signed>.00000001,3)
        front_fit=np.linalg.lstsq(features(uv[front]),position[front],rcond=None)[0]
        back_fit=np.linalg.lstsq(features(uv[back]),position[back],rcond=None)[0]
        residual=max(float(np.linalg.norm(features(uv[front])@front_fit-position[front],axis=1).max()),float(np.linalg.norm(features(uv[back])@back_fit-position[back],axis=1).max()))
        if residual>2e-7:raise ValueError(mesh['name']+': source surface cannot be recovered accurately')
        p,faces,detail=triangulate(mask)
        original_uv=p/np.array([w-1,h-1]);F=features(original_uv)
        # Validate in the actual serialized float32 coordinates: very thin
        # clipped slivers can collapse after casting even when float64 is valid.
        v=np.r_[F@front_fit,F@back_fit].astype('float32').astype(float);count=len(p)
        # Pixel-center UVs stop nearest sampling from rounding onto a neighbor.
        tex=np.tile(np.clip((p+.5)/np.array([w,h]),0,1),(2,1))
        # Ear clipping is CCW in image coordinates; reverse on the front face.
        front_faces=faces[:,[0,2,1]];back_faces=faces+count
        closed=[*map(tuple,front_faces),*map(tuple,back_faces)];edges={}
        for f in front_faces:
            for a,b in zip(f,np.roll(f,-1)):
                edges.setdefault(tuple(sorted((int(a),int(b)))),[]).append((int(a),int(b)))
        for uses in edges.values():
            if len(uses)==1:
                a,b=uses[0];closed.extend([(a,a+count,b+count),(a,b+count,b)])
        closed=np.asarray(closed);tri=v[closed]
        normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);length=np.linalg.norm(normals,axis=1)
        good=length>1e-20;closed=closed[good];tri=tri[good];normals=np.repeat(normals[good]/length[good,None],3,axis=0)
        positions=tri.reshape(-1,3);uvs=tex[closed].reshape(-1,2)
        old_j=array(doc,binary,attrs['JOINTS_0']);old_w=array(doc,binary,attrs['WEIGHTS_0']);joints=np.unique(old_j[old_w>0])
        if len(joints)!=5:raise ValueError('Unexpected existing native leaf joint chain')
        t=np.clip(1-uvs[:,1],0,1);knots=np.array([.08,.28,.48,.68,.88]);low=np.clip(np.searchsorted(knots,t,side='right')-1,0,3);high=low+1;blend=np.clip((t-knots[low])/(knots[high]-knots[low]),0,1)
        ids=np.zeros((len(positions),4),dtype='uint16');weights=np.zeros((len(positions),4),dtype='float32');ids[:,0]=joints[low];ids[:,1]=joints[high];weights[:,0]=1-blend;weights[:,1]=blend
        mesh['primitives']=[{'attributes':{'POSITION':g.accessor(positions,'VEC3'),'NORMAL':g.accessor(normals,'VEC3'),'TEXCOORD_0':g.accessor(uvs,'VEC2'),'JOINTS_0':append(g,ids,'VEC4',5123,34962),'WEIGHTS_0':append(g,weights,'VEC4',5126,34962)},'material':old['material'],'mode':4}]
        reports.append({'mesh':mesh['name'],'source_surface_fit_error_m':residual,'triangles':len(closed),'source_part':leaf_id%6+1,**detail})
    g.doc.setdefault('extras',{})['leaf_uv_pixel_centers']=True
    g.doc['asset']['generator']='Foundry intact leaf polygon reconstruction'
    output.parent.mkdir(parents=True,exist_ok=True);g.save(output)
    # A matching unskinned rest reference supplies fresh CPU motion validation.
    for node in g.doc['nodes']:node.pop('skin',None)
    for mesh in g.doc['meshes']:
        for prim in mesh['primitives']:
            prim['attributes'].pop('JOINTS_0',None);prim['attributes'].pop('WEIGHTS_0',None)
    g.doc.pop('skins',None);g.doc.pop('animations',None);static.parent.mkdir(parents=True,exist_ok=True);g.save(static)
    new,newbin=read_glb(output)
    preserved=all(doc.get(k)==new.get(k) for k in ['nodes','skins','animations','images','materials','textures','samplers']) and newbin[:len(binary)]==binary
    if not preserved:raise ValueError('Source rig or artwork changed')
    return {'id':source.stem,'source':str(source),'source_sha256':sha(source),'output':str(output),'sha256':sha(output),'static':str(static),'source_parts':str(parts),'source_parts_sha256':sha(parts),'materials_rig_animation_preserved':preserved,'leaves':reports}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.root.resolve();catalog=json.loads(a.input.read_text(encoding='utf-8'));rows=[]
    for row in catalog['assets']:
        if not row['animated']:continue
        original=row.get('pre_contour_repair_model',row['model']);source=root/'projects/fishing-2d/game'/original.removeprefix('res://')
        result=remesh(source,source_parts(root,row['id']),a.output/'plants'/(row['id']+'.glb'),a.output/'plant-static'/(row['id']+'.glb'));rows.append(result)
        row['pre_contour_repair_model']=original;row['model']='res://'+str((a.output/'plants'/(row['id']+'.glb')).resolve().relative_to(root/'projects/fishing-2d/game')).replace('\\','/');row['geometry_revision']='intact-leaf-contours-v7'
    a.output.mkdir(parents=True,exist_ok=True)
    source_cfg=json.loads((root/'projects/fishing-2d/game/assets/aquascape-v5/plant-motion.json').read_text(encoding='utf-8'));old_cfg=json.loads((root/'resources/aquascape/plant-current-v4.json').read_text(encoding='utf-8'))
    source_cfg['plants']=old_cfg['plants']+source_cfg['plants'];source_cfg['source_models']=str((a.output/'plant-static').resolve().relative_to(root));(a.output/'plant-motion.json').write_text(json.dumps(source_cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    data={'schema_version':1,'command':'aquascape.repair-plant-contours','ok':True,'status':'done','next_action':'human_review','outputs':rows,'failures':[],'visual_review':'pending','user_acceptance':'pending','scope':'Continuous source outline with 0.65 native-pixel simplification and constrained ear triangulation; no eroded silhouette or replacement artwork. Original leaf pose, thickness, bone graph and animation retained. New surface weights use the same fixed-base profile.'}
    (a.output/'build.validation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');a.input.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'ok':True,'plants':len(rows),'leaf_shells':sum(len(r['leaves']) for r in rows)}))

if __name__=='__main__':main()
