"""Project actual packed rows into the preserved source-domain validation template.

This is a diagnostic source only. Every old template point must match its exact
baseline body/fin part, and the resulting positions are checked independently
against the current final packed GLB by validate_authored_fin_volume.py.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read_parts(path):
    d,b=read_glb(path);p=d['meshes'][0]['primitives'][0];v=arrays(d,b,p['attributes']['POSITION']);result={}
    for q in d['extras']['geometry_parts']:
        vv=v[q['vertex_start']:q['vertex_start']+q['vertex_count']];result.setdefault(q['logical_name'],[]).extend(np.column_stack([vv[:,0],-vv[:,2],vv[:,1]]).tolist())
    return result
def main(a):
    out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not out.exists();old=read_parts(a.baseline);new=read_parts(a.model);assert set(old)==set(new)
    bpy.ops.wm.open_mainfile(filepath=str(a.template.resolve()));records=[]
    for ob in [o for o in bpy.data.objects if o.type=='MESH']:
        if ob.name not in old:
            ob.hide_render=True;continue
        before=np.array(old[ob.name]);after=np.array(new[ob.name]);assert before.shape==after.shape;tree=KDTree(len(before))
        for i,q in enumerate(before):tree.insert(q,i)
        tree.balance();errors=[]
        for v in ob.data.vertices:
            _,i,e=tree.find(v.co);assert e<2e-6,(ob.name,'Original template differs from exact installed baseline',e);errors.append(e);v.co=after[i]
        ob.data.update();records.append({'name':ob.name,'vertices':len(ob.data.vertices),'maximum_baseline_mapping_error_native':max(errors),'original_source_t_attributes_preserved':True})
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out));r={'ok':True,'kind':'actual_packed_to_original_domain_volume_projection','template_sha256':sha(a.template),'installed_baseline_sha256':sha(a.baseline),'model_sha256':sha(a.model),'projected_blend_sha256':sha(out),'objects':records,'scope':'Validation-only source-domain projection; actual final packed positions assigned. No candidate mutation, no root/source_t/UV changes; final bidirectional correspondence is separately checked.'};out.with_suffix('.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'ok':True,'meshes':len(records)}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['template','baseline','model','output']:p.add_argument('--'+k,required=True,type=Path)
    main(p.parse_args(sys.argv[sys.argv.index('--')+1:]))
