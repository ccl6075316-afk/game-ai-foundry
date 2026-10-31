"""Blender diagnostic: freeze current root-to-finite-body barycentric targets.

This records the ENTIRE selected root band. It never chooses a nearest-body
subset, changes geometry, relaxes contact tolerances or certifies animation.
"""
import argparse,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));from glb_io import sha
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def skin(row,matrices):
 p=np.c_[row['vertices_native'],np.ones(len(row['vertices_native']))];js=np.array(row['joints'],int).reshape(-1,4);ws=np.array(row['weights']).reshape(-1,4);return(np.einsum('nsij,nj->nsi',matrices[js],p)*ws[:,:,None]).sum(1)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--compact',type=Path,required=True);p.add_argument('--fins',nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);rest=read(a.compact/'rest-skin.json');static=read(a.compact/'matrices-000.json');assert static['action']=='Static';mat=np.array(static['joint_matrices_m_per_native']);vertices=[];triangles=[];offset=0
 for row in rest['surfaces']:
  if not row['body']:continue
  xyz=skin(row,mat);vertices.extend(xyz);tris=np.array(row['triangles'],int).reshape(-1,3);triangles.extend(tris+offset);offset+=len(xyz)
 vertices=np.array(vertices);triangles=np.array(triangles,int);volume=np.einsum('ij,ij->i',vertices[triangles[:,0]],np.cross(vertices[triangles[:,1]],vertices[triangles[:,2]])).sum()/6
 if volume<0:triangles=triangles[:,[0,2,1]]
 tree=BVHTree.FromPolygons(vertices.tolist(),triangles.tolist(),all_triangles=True);records=[]
 for row in rest['surfaces']:
  if row['name']not in a.fins:continue
  xyz=skin(row,mat);points=[]
  for i in row['root_ids']:
   hit,normal,face,distance=tree.find_nearest(Vector(xyz[i]));t=triangles[face];bary=barycentric_transform(hit,*[Vector(vertices[j])for j in t],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));beta=np.maximum(np.array(bary),0);beta/=beta.sum();signed=float(np.dot(xyz[i]-np.array(hit),np.array(normal)));points.append({'vertex':i,'body_triangle':t.tolist(),'barycentric':beta.tolist(),'static_signed_offset_m':signed,'nearest_distance_m':distance})
  records.append({'name':row['name'],'complete_root_ids':row['root_ids'],'roots':points})
 assert len(records)==len(a.fins)and all(r['roots']for r in records);report={'ok':True,'kind':'complete_frozen_root_body_binding_diagnostic','compact_rest':str((a.compact/'rest-skin.json').resolve()),'compact_rest_sha256':sha(a.compact/'rest-skin.json'),'body_triangles_outward':triangles.tolist(),'fins':records,'formal_acceptance':False,'scope':'Actual current finite-body nearest triangles, complete frozen root IDs, convex barycentric coordinates and measured static signed offsets. Fitting and fresh posed gates remain separate.'};assert not a.output.exists();a.output.write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({'ok':True,'fins':len(records),'roots':sum(len(r['roots'])for r in records)}))
if __name__=='__main__':main()
