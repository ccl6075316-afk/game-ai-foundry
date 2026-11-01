"""Blender: ray-test actual side opening against independent source lip traces.

Tests new and rejected old source meshes; no construction coordinates are read
from the meshes, no visual/biological acceptance is inferred.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser()
for name in ['config','current','rejected','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cfg=json.loads(a.config.read_text(encoding='utf8'));W,H=cfg['source_size'];upper=np.asarray(cfg['upper_inner_edge_px'],float);lower=np.asarray(cfg['lower_inner_edge_px'],float)
results={}
for label,path in [('rejected',a.rejected),('current',a.current)]:
    bpy.ops.wm.open_mainfile(filepath=str(path.resolve()));body=bpy.data.objects[cfg['body']];body.data.calc_loop_triangles();verts=[body.matrix_world@v.co for v in body.data.vertices];faces=[tuple(t.vertices)for t in body.data.loop_triangles];tree=BVHTree.FromPolygons(verts,faces,all_triangles=True);rows=[]
    for i,(px,hi)in enumerate(upper):
        x=px+1 if i==0 else px;up=float(np.interp(x,upper[:,0],upper[:,1]));lo=float(np.interp(x,lower[:,0],lower[:,1]));ys=np.arange(up-12,lo+12.25,.25);hit=np.asarray([tree.ray_cast(Vector((x/W-.5,-2.,(.5-y/H)*H/W)),Vector((0,1,0)),4.)[0]is not None for y in ys]);middle=int(np.argmin(abs(ys-(up+lo)/2)));start=middle;end=middle
        if not hit[middle]:
            while start>0 and not hit[start-1]:start-=1
            while end+1<len(ys)and not hit[end+1]:end+=1
        valid=not hit[middle]and start>0 and end+1<len(ys);observed=[float(ys[start]-.125),float(ys[end]+.125)]if valid else None;error=max(abs(observed[0]-up),abs(observed[1]-lo))if observed else None;ok=valid and error<=1.25
        rows.append({'x_source_px':float(x),'expected_upper_lower_px':[up,lo],'actual_ray_gap_px':observed,'max_boundary_error_px':error,'skin_hits_above_and_below':valid,'ok':bool(ok)})
    results[label]={'ok':all(r['ok']for r in rows),'source_blend':str(path.resolve()),'sha256':sha(path),'rows':rows}
report={'ok':results['current']['ok']and not results['rejected']['ok'],'kind':'independent_actual_source_mouth_opening_regression','config_sha256':sha(a.config),'source_sha256':cfg['source_sha256'],'results':results,'scope':'Side orthographic actual-body BVH rays at own frozen upper/lower source traces,0.25px sampling/1.25px tolerance. Requires hit skin above and below. Reject old slit negative. Does not approve frontal shape,lip colors,animation or biological width.'};assert not a.output.exists();a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':report['ok'],'current':results['current']['ok'],'rejected':results['rejected']['ok'],'current_rows':results['current']['rows']}));raise SystemExit(0 if report['ok']else 1)
