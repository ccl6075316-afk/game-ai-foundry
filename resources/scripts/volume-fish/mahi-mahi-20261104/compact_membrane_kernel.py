"""Exact standard membrane loop, upstreamSHA efd93d9e2f3868f6e9de712e2d8ecd90012fd17e28133cdcef649eca710531fd; only d/sample injection and return row replace fileiteration."""
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
def measure_pose(d,sample,summary,a,export):
    verts=[Vector(v) for v in d['body_vertices_m']];faces=d['body_triangles'];volume=sum(verts[x].dot(verts[y].cross(verts[z])) for x,y,z in faces)/6.
    assert abs(volume)>1e-9
    if volume<0:faces=[list(reversed(f)) for f in faces]
    bvh=BVHTree.FromPolygons(verts,faces,all_triangles=True);row={'action':sample['action'],'seconds':sample['seconds'],'fins':{}}
    lower=[min(v[j] for v in verts) for j in range(3)];upper=[max(v[j] for v in verts) for j in range(3)];ray_direction=Vector((.231,.371,.899)).normalized()
    assert set(d['membranes'])==set(export['expected_fins'])
    for name,mem in d['membranes'].items():
        vs=[Vector(v) for v in mem['vertices_m']];tr=mem['triangles'];roots=d['roots'][name]['points_m'];kd=KDTree(len(roots))
        for i,pt in enumerate(roots):kd.insert(Vector(pt),i)
        kd.balance();root_ids={i for i,v in enumerate(vs) if kd.find(v)[2]<1e-8}
        root_faces=[tr[i:i+3] for i in range(0,len(tr),3) if all(j in root_ids for j in tr[i:i+3])]
        root_surface=BVHTree.FromPolygons(vs,root_faces,all_triangles=True) if root_faces else None
        points=list(vs);edges=set()
        for i in range(0,len(tr),3):
            ids=tr[i:i+3];x,y,z=[vs[j] for j in ids];points.extend([(x+y+z)/3,x*.6+y*.2+z*.2,x*.2+y*.6+z*.2,x*.2+y*.2+z*.6])
            for aa,bb in zip(ids,ids[1:]+ids[:1]):edges.add(tuple(sorted([aa,bb])))
        for aa,bb in edges:
            for fraction in [.25,.5,.75]:points.append(vs[aa].lerp(vs[bb],fraction))
        min_dist=1e9;count=0;worst=None;checked=0;exempt=0
        for pt in points:
            near,normal,_,dist=bvh.find_nearest(pt)
            # The nearest triangle's normal does not classify a point at a
            # shared edge/vertex (e.g. a tail behind the body's AABB). An
            # oriented non-axis-aligned ray classifies the closed body.
            outside=any(pt[j]<lower[j]-1e-8 or pt[j]>upper[j]+1e-8 for j in range(3))
            if outside:inside=False
            else:
                ray_hit,ray_normal,_,_=bvh.ray_cast(pt,ray_direction)
                inside=ray_hit is not None and ray_normal.dot(ray_direction)>0
            signed=-dist if inside else dist
            root_distance=kd.find(pt)[2]
            if root_surface:root_distance=min(root_distance,root_surface.find_nearest(pt)[3])
            # Exempt the complete frozen basal surface, but never allow it
            # to hide a penetration deeper than the frozen seam collar.
            if root_distance<=a.root_collar_mm/1000 and signed>=-a.root_collar_mm/1000:exempt+=1;continue
            checked+=1
            if signed<min_dist:min_dist=signed;worst=list(pt)
            if signed < -a.penetration_tolerance_mm/1000:count+=1
        assert checked>0,'Root collar excludes entire fin: '+name
        result={'samples':checked,'root_seam_samples':exempt,'inside_samples':count,'min_signed_distance_mm':min_dist*1000,'worst_point_m':worst};row['fins'][name]=result
        v=summary.setdefault(name,{'failed_poses':0,'worst_penetration_mm':0.,'worst_pose':None})
        if count:v['failed_poses']+=1
        if min_dist*1000<v['worst_penetration_mm']:v['worst_penetration_mm']=min_dist*1000;v['worst_pose']={'action':sample['action'],'seconds':sample['seconds'],'point_m':worst}
    return row
