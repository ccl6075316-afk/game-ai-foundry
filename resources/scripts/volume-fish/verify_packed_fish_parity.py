"""Read-only complete packed fish GLB semantic parity, including material/rig/clips."""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image
from pack_fish_material_atlas import read_glb,arrays

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def skin_rows(d,b,pr,node):
    names=[d['nodes'][i]['name']for i in d['skins'][node['skin']]['joints']];j=arrays(d,b,pr['attributes']['JOINTS_0']);w=arrays(d,b,pr['attributes']['WEIGHTS_0'])
    return [{names[int(i)]:float(v)for i,v in zip(jj,ww)if v>1e-7}for jj,ww in zip(j,w)]
def material_semantics(d):
    assert len(d['materials'])==1 and len(d['textures'])==1 and len(d['images'])==1
    m=d['materials'][0];p=m.get('pbrMetallicRoughness',{});t=p['baseColorTexture'];tex=d['textures'][t['index']];sampler=d['samplers'][tex.get('sampler',0)]
    return {'alphaMode':m.get('alphaMode','OPAQUE'),'alphaCutoff':m.get('alphaCutoff',.5),'doubleSided':m.get('doubleSided',False),'roughnessFactor':p.get('roughnessFactor',1),'metallicFactor':p.get('metallicFactor',1),'baseColorFactor':p.get('baseColorFactor',[1,1,1,1]),'texture_texCoord':t.get('texCoord',0),'magFilter':sampler.get('magFilter',9729),'minFilter':sampler.get('minFilter',9729),'wrapS':sampler.get('wrapS',10497),'wrapT':sampler.get('wrapT',10497),'specularFactor':m.get('extensions',{}).get('KHR_materials_specular',{}).get('specularFactor',1),'emissiveFactor':m.get('emissiveFactor',[0,0,0])}
def image_pixels(d,b):
    image=d['images'][0];v=d['bufferViews'][image['bufferView']];payload=b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
    return np.asarray(Image.open(io.BytesIO(payload)).convert('RGBA')),hashlib.sha256(payload).hexdigest()
def clips(d,b):
    result={}
    for clip in d.get('animations',[]):
        channels={}
        for c in clip['channels']:
            s=clip['samplers'][c['sampler']];key=d['nodes'][c['target']['node']]['name']+'/'+c['target']['path'];assert key not in channels
            channels[key]=(arrays(d,b,s['input']),arrays(d,b,s['output']),s.get('interpolation','LINEAR'))
        result[clip.get('name','unnamed')]=channels
    return result
def canonical_cycle(row):return min(tuple(row[i:])+tuple(row[:i])for i in range(3))
def node_rest_parity(d,e):
    def inventory(doc):
        names=[n['name']for n in doc['nodes']];assert len(names)==len(set(names)),'Unique node names required'
        parents={}
        for i,node in enumerate(doc['nodes']):
            for child in node.get('children',[]):assert child not in parents;parents[child]=i
        return {n['name']:(i,n)for i,n in enumerate(doc['nodes'])},parents
    old,op=inventory(d);new,np_=inventory(e);assert set(old)<=set(new)
    extras=set(new)-set(old);assert extras<= {'Body-only side reference'},'Unexpected extra node'
    animated={c['target']['node']for a in e.get('animations',[])for c in a['channels']};rig_ancestors=set()
    for skin in e['skins']:
        for joint in skin['joints']:
            while joint is not None:rig_ancestors.add(joint);joint=np_.get(joint)
    for name in extras:
        i,node=new[name];assert i not in animated and i not in rig_ancestors
        assert not node.get('children')and not any(k in node for k in ('mesh','skin','camera','weights'))and not node.get('extensions'),'Extra editor node cannot own render/rig resources'
    maximum=0.
    for name,(i,x)in old.items():
        j,y=new[name]
        old_parent=d['nodes'][op[i]]['name']if i in op else None;new_parent=e['nodes'][np_[j]]['name']if j in np_ else None
        assert old_parent==new_parent,(name,'Rest parent changed')
        for key,default in [('translation',[0,0,0]),('rotation',[0,0,0,1]),('scale',[1,1,1]),('matrix',None)]:
            a=x.get(key,default);b=y.get(key,default)
            if a is None or b is None:assert a==b
            else:assert len(a)==len(b);maximum=max(maximum,max(abs(u-v)for u,v in zip(a,b)))
        assert ('mesh'in x)==('mesh'in y)and ('skin'in x)==('skin'in y),(name,'Mesh/skin ownership changed')
        if 'skin'in x:
            def skeleton(doc,node):
                value=doc['skins'][node['skin']].get('skeleton');return doc['nodes'][value]['name']if value is not None else None
            assert skeleton(d,x)==skeleton(e,y),(name,'Skin skeleton reference changed')
    assert maximum<=1e-6,('Rest transform changed',maximum)
    return {'original_named_nodes':len(old),'max_rest_component_error':maximum,'parents_and_skin_skeleton_references_equal':True,'allowed_editor_empty_nodes':sorted(extras)}

def verify(reference,candidate):
    reference=Path(reference).resolve();candidate=Path(candidate).resolve();d,b=read_glb(reference);e,c=read_glb(candidate)
    assert len(d['meshes'])==len(e['meshes'])==1 and len(d['meshes'][0]['primitives'])==len(e['meshes'][0]['primitives'])==1
    p=d['meshes'][0]['primitives'][0];q=e['meshes'][0]['primitives'][0];node=next(n for n in d['nodes']if 'mesh'in n);other=next(n for n in e['nodes']if 'mesh'in n)
    rest=node_rest_parity(d,e)
    assert set(p['attributes'])==set(q['attributes'])=={'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'}
    attrs={};maximum=0.
    for key in ('POSITION','NORMAL','TEXCOORD_0'):
        x=arrays(d,b,p['attributes'][key]);y=arrays(e,c,q['attributes'][key]);assert x.shape==y.shape and np.isfinite(y).all();error=float(np.max(np.abs(x-y)));assert error<=1e-6,(key,error);attrs[key]={'rows':len(x),'max_component_error':error};maximum=max(maximum,error)
    old_skin=skin_rows(d,b,p,node);new_skin=skin_rows(e,c,q,other);assert len(old_skin)==len(new_skin);skin_error=0.
    for x,y in zip(old_skin,new_skin):assert x.keys()==y.keys();skin_error=max(skin_error,max(abs(x[k]-y[k])for k in x))
    assert skin_error<=1e-6;attrs['JOINTS_WEIGHTS_by_bone_name']={'rows':len(old_skin),'max_component_error':skin_error}
    ix=arrays(d,b,p['indices']).reshape(-1,3).tolist();iy=arrays(e,c,q['indices']).reshape(-1,3).tolist();assert len(ix)==len(iy)==1710
    assert Counter(canonical_cycle(t)for t in ix)==Counter(canonical_cycle(t)for t in iy),'Directed triangles changed'
    assert material_semantics(d)==material_semantics(e),'Material semantics changed'
    material=material_semantics(e);assert material['alphaMode']=='MASK'and material['alphaCutoff']==.5 and material['roughnessFactor']==1 and material['metallicFactor']==0 and material['specularFactor']==0 and material['magFilter']==material['minFilter']==9728
    pixels,old_png=image_pixels(d,b);new_pixels,new_png=image_pixels(e,c);assert pixels.shape==new_pixels.shape and np.array_equal(pixels,new_pixels),'Atlas RGBA differs'
    parts=e.get('extras',{}).get('geometry_parts',[]);assert len(parts)==9
    covered_vertices=set();covered_indices=set();body_parts=[]
    uv=arrays(e,c,q['attributes']['TEXCOORD_0']);flat_indices=arrays(e,c,q['indices']).reshape(-1)
    for part in parts:
        vs=part['vertex_start'];ve=vs+part['vertex_count'];start=part['index_start'];end=start+part['index_count'];assert not covered_vertices.intersection(range(vs,ve))and not covered_indices.intersection(range(start,end));covered_vertices.update(range(vs,ve));covered_indices.update(range(start,end))
        assert all(vs<=i<ve for i in flat_indices[start:end]),'Actual index stream escapes logical part'
        if part['role']in ('body_skin','mouth'):
            coords=uv[vs:ve]*[new_pixels.shape[1],new_pixels.shape[0]];lo=np.floor(coords.min(axis=0)).astype(int);hi=np.floor(coords.max(axis=0)).astype(int)+1;alpha=new_pixels[lo[1]:hi[1],lo[0]:hi[0],3];assert alpha.size and (alpha==255).all(),'Body alpha not fully opaque in its actual UV domain';body_parts.append(part['index_count']//3)
    assert covered_vertices==set(range(len(uv)))and covered_indices==set(range(len(flat_indices)))and sorted(body_parts)==[64,840]
    assert len(d['skins'])==len(e['skins'])==1
    a_skin,z_skin=d['skins'][0],e['skins'][0];a_names=[d['nodes'][i]['name']for i in a_skin['joints']];z_names=[e['nodes'][i]['name']for i in z_skin['joints']];assert set(a_names)==set(z_names)and len(z_names)==18
    am=arrays(d,b,a_skin['inverseBindMatrices']);zm=arrays(e,c,z_skin['inverseBindMatrices']);ibm_error=max(float(np.max(np.abs(am[i]-zm[z_names.index(name)])))for i,name in enumerate(a_names));assert ibm_error<=1e-6
    old_clips,new_clips=clips(d,b),clips(e,c);assert old_clips.keys()==new_clips.keys();clip_report={}
    for name,channels in old_clips.items():
        assert channels.keys()==new_clips[name].keys();time_error=value_error=0.
        for key,(times,vals,interp)in channels.items():
            t,v,i=new_clips[name][key];assert times.shape==t.shape and vals.shape==v.shape and interp==i;time_error=max(time_error,float(np.max(np.abs(times-t))));value_error=max(value_error,float(np.max(np.abs(vals-v))))
        assert time_error<=1e-6 and value_error<=1e-6;clip_report[name]={'channels':len(channels),'max_time_error':time_error,'max_value_error':value_error}
    assert sum(x['channels']for x in clip_report.values())==54
    for i,_ in enumerate(e['accessors']):assert np.isfinite(arrays(e,c,i)).all(),'Nonfinite exported accessor'
    return {'ok':True,'kind':'packed_fish_complete_GLB_semantic_parity','reference':{'path':str(reference),'sha256':sha(reference)},'candidate':{'path':str(candidate),'sha256':sha(candidate)},'checker_sha256':sha(__file__),'triangles':len(iy),'vertices':len(uv),'bones':len(z_names),'single_mesh_single_surface':True,'attributes':attrs,'directed_triangles_equal':True,'node_rest_and_hierarchy':rest,'material_semantics':material,'atlas_RGBA_exact':True,'atlas_size':[new_pixels.shape[1],new_pixels.shape[0]],'PNG_bytes_equal':old_png==new_png,'reference_PNG_sha256':old_png,'candidate_PNG_sha256':new_png,'body_and_mouth_UV_domain_alpha_255':True,'logical_parts':parts,'IBMs_by_bone_name_max_component_error':ibm_error,'native_clips':clip_report,'finite_all_exported_accessors':True,'scope':'Complete raw GLB semantics at existing1e-6component limit; same source vertex identities, directed triangles, original node rest/parents and skin skeleton references. Does not replace actual Godot cold load/pose profile binding, specialized fin/body gates or visual review.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('reference','candidate','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[3];output=a.output.resolve();assert output.is_relative_to(root/'work')or output.is_relative_to(root/'output')or output.is_relative_to(root/'projects/fishing-2d/experiments');assert len({output,a.reference.resolve(),a.candidate.resolve()})==3 and not output.exists()and output.suffix=='.json';r=verify(a.reference,a.candidate);output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'ok':True,'max_geometry_error':max(x['max_component_error']for x in r['attributes'].values()),'IBMs_error':r['IBMs_by_bone_name_max_component_error'],'native_clips':r['native_clips'],'RGBA_exact':True}))
if __name__=='__main__':main()
