"""Blender: actual packed body mesh only for independent original mouth BVH rays."""
import argparse,sys,json,hashlib
from pathlib import Path
import bpy,numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays
p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);assert not a.output.exists();d,b=read_glb(a.model);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);idx=arrays(d,b,pr['indices']);f=np.concatenate([idx[q['index_start']:q['index_start']+q['index_count']]for q in d['extras']['geometry_parts']if q['role']in['body_skin','mouth']]).reshape(-1,3)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);m=bpy.data.meshes.new('Exact current body triangles');m.from_pydata([(float(q[0]),float(-q[2]),float(q[1]))for q in v],[],f.tolist());ob=bpy.data.objects.new('Closed_body',m);bpy.context.collection.objects.link(ob);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()));a.output.with_suffix('.validation.json').write_text(json.dumps({'kind':'exact_packed_body_diagnostic_projection','model_sha256':hashlib.sha256(a.model.read_bytes()).hexdigest(),'positions_and_indices_exact':True,'scope':'Validation-only exact body triangles; not editable delivery source or a new source domain.'},indent=2)+'\n',encoding='utf8')
