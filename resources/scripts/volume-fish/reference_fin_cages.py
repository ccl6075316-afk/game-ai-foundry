"""Sparse image-outline fin cages attached to an already authored body.

No source fin mesh connectivity, UV, or skinning is used. Species parameters
and tissue thickness/camber remain in the explicit trial plan.
"""
import bpy,bmesh,math
import numpy as np
from collections import Counter,defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform,delaunay_2d_cdt

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)

def nearline(p,line):
    best=(float('inf'),None)
    for a,b in zip(line,line[1:]):
        e=b-a;t=max(0.,min(1.,(p-a).dot(e)/max(e.length_squared,1e-12)));q=a+e*t
        if (p-q).length<best[0]:best=((p-q).length,q)
    return best

def simplify(poly,line,target):
    locked={min(range(len(poly)),key=lambda i:(poly[i]-q).length) for q in line}
    for axis in (0,1):
        locked.add(min(range(len(poly)),key=lambda i:poly[i][axis]))
        locked.add(max(range(len(poly)),key=lambda i:poly[i][axis]))
    assert len(locked)<target
    live=list(range(len(poly)))
    while len(live)>target:
        costs=[]
        for j,i in enumerate(live):
            if i in locked:continue
            a,b,c=(poly[live[(j+k)%len(live)]] for k in (-1,0,1))
            costs.append((abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)),j))
        live.pop(min(costs)[1])
    return [poly[i] for i in live]

def build(body,rig,plan,settings,directory,make_material):
    W,H=plan['source_size'];scale=settings['runtime_scale']
    points=[v.co.copy() for v in body.data.vertices]
    body_faces=[tuple(p.vertices) for p in body.data.polygons]
    assert all(len(face)==3 for face in body_faces)
    bvh=BVHTree.FromPolygons(points,body_faces,all_triangles=True)
    bw=[{body.vertex_groups[g.group].name:g.weight for g in v.groups} for v in body.data.vertices]
    xmin=min(v.x for v in points)
    tailpoints=[v for v in points if v.x<xmin+.002]
    zcenter=(min(v.z for v in tailpoints)+max(v.z for v in tailpoints))/2
    def hit_body(p,d):
        hit,no,fi,_=bvh.ray_cast(p+d*2,-d,4)
        if hit is None:hit,no,fi,_=bvh.find_nearest(p)
        if no.dot(d)<0:no=-no
        return hit,no
    def sample_weights(p):
        hit,_,fi,_=bvh.find_nearest(p);ids=body_faces[fi]
        bary=barycentric_transform(hit,*[points[i] for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        result=defaultdict(float)
        for i,w in zip(ids,bary):
            for key,value in bw[i].items():result[key]+=max(0,w)*value
        return result
    records=[];roots={}
    for spec in plan['fins']:
        name=spec['name'];original=[Vector(p) for p in spec['polygon_px']];line=[Vector(p) for p in spec['baseline_px']]
        outline=simplify(original,line,settings['fin_boundary_vertices'][name])
        center=sum(outline,Vector((0,0)))/len(outline);basal=sum(line,Vector((0,0)))/len(line)
        seeds=outline+[basal.lerp(center,f) for f in (.45,.8)]
        xy,_,ff,*_=delaunay_2d_cdt([p/W for p in seeds],[(i,(i+1)%len(outline)) for i in range(len(outline))],[list(range(len(outline)))],1,1e-8)
        tri=[tuple(f) for f in ff if len(f)==3];used=sorted({i for f in tri for i in f});remap={i:j for j,i in enumerate(used)}
        pixels=[xy[i]*W for i in used];tri=[tuple(remap[i] for i in f) for f in tri];n=len(pixels)
        distances=[nearline(p,line)[0] for p in pixels];maximum=max(distances)
        paired=name.startswith(('Pectoral','Pelvic'));tail=name=='Caudal';side=-1 if name.endswith('_left') else 1
        direction=Vector((0,side,0)) if paired else Vector((-1,0,0)) if tail else Vector((0,0,1 if name=='Dorsal' else -1))
        verts=[];weights=[];widths=[];root_ids=[];bone=name+'_2';assert rig.data.bones.get(bone)
        for i,(pixel,distance) in enumerate(zip(pixels,distances)):
            base=nearline(pixel,line)[1];bp=Vector((base.x/W-.5,0,(H*.5-base.y)/W))
            if tail:bp.z=zcenter+(bp.z-zcenter)*plan['tail']['end_height_scale']
            hit,no=hit_body(bp,direction);s=min(1.,distance/maximum);gain=1-smooth(distance/14.)
            p=Vector((pixel.x/W-.5,0,(H*.5-pixel.y)/W))
            if paired:p.y=side*(abs(hit.y)+spec['spread_native']*smooth(s)+spec['camber_mm']/1000/scale*math.sin(math.pi*s))
            elif tail:p.x+=xmin+.00015-(line[0].x/W-.5);p.y=spec['camber_mm']/1000/scale*math.sin(math.pi*s)
            else:p.z+=hit.z-bp.z;p.y=spec['camber_mm']/1000/scale*math.sin(math.pi*s)
            delta=Vector(((pixel.x-base.x)/W,0,-(pixel.y-base.y)/W));tangent=delta-no*delta.dot(no)
            if paired:tangent.y=side*abs(tangent.y)
            root=hit+tangent*.65-no*.00015
            if tail:root=Vector((xmin+.00015,0,bp.z+tangent.z*.65))
            p=p.lerp(root,gain);root_mm=spec['root_mm']
            if tail:
                sh,_,_,_=bvh.ray_cast(Vector((xmin+.0001,1,p.z)),Vector((0,-1,0)),2)
                root_mm=max(.4,2*abs(sh.y)*scale*1000-.08) if sh is not None else .4
            width=(spec['edge_mm']+(root_mm-spec['edge_mm'])*(1-s)**1.6)/1000/scale;widths.append(width)
            if distance<=4:root_ids.append(i)
            elif not tail:
                nearest,nn,_,_=bvh.find_nearest(p);clear=width*.5+.0003
                if (p-nearest).dot(nn)<clear:p=nearest+nn*clear
            mix=sample_weights(p);fw=smooth((distance-5)/max(10,maximum*.65))*spec['fin_influence']
            mix={k:v*(1-fw) for k,v in mix.items()};mix[bone]=mix.get(bone,0)+fw
            mix=dict(sorted(mix.items(),key=lambda v:-v[1])[:4]);amount=sum(mix.values());assert amount>0
            weights.append({k:v/amount for k,v in mix.items()});verts.append(p)
        assert root_ids
        mid=bpy.data.meshes.new(name+'_mid');mid.from_pydata(verts,[],tri);mid.update()
        bm=bmesh.new();bm.from_mesh(mid);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mid);bm.free()
        tri=[tuple(f.vertices) for f in mid.polygons];normals=[v.normal.copy() for v in mid.vertices]
        solid=[p+normals[i]*widths[i]*.5 for i,p in enumerate(verts)]+[p-normals[i]*widths[i]*.5 for i,p in enumerate(verts)]
        faces=tri+[tuple(i+n for i in reversed(t)) for t in tri]
        counts=Counter(tuple(sorted((f[j],f[(j+1)%3]))) for f in tri for j in range(3))
        for a,b,c in tri:
            for x,y in ((a,b),(b,c),(c,a)):
                if counts[tuple(sorted((x,y)))]==1:faces.extend(((x,x+n,y+n),(x,y+n,y)))
        mesh=bpy.data.meshes.new(name+'_reference_cage');mesh.from_pydata(solid,[],faces);mesh.update()
        ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);ob.parent=rig;mod=ob.modifiers.new('Swim skin','ARMATURE');mod.object=rig
        uv=mesh.uv_layers.new(name='UVMap');safe=np.load(directory/spec['wall_donor_field'])
        for face in mesh.polygons:
            face.use_smooth=True
            for li in face.loop_indices:
                pixel=pixels[mesh.loops[li].vertex_index%n]
                if face.index>=len(tri)*2:
                    x=max(0,min(W-1,round(pixel.x)));y=max(0,min(H-1,round(pixel.y)));pixel=Vector((float(safe['x'][y,x])+.5,float(safe['y'][y,x])+.5))
                uv.data[li].uv=(pixel.x/W,1-pixel.y/H)
        for i,row in enumerate(weights+weights):
            for key,value in row.items():
                group=ob.vertex_groups.get(key) or ob.vertex_groups.new(name=key);group.add([i],value,'REPLACE')
        mesh.materials.append(make_material('fin_'+name,directory/spec['image'],True))
        bm=bmesh.new();bm.from_mesh(mesh);closed=all(e.is_manifold for e in bm.edges);zero=sum(f.calc_area()<=1e-13 for f in bm.faces);bm.free();assert closed and zero==0
        roots[name]={'ids':root_ids+[i+n for i in root_ids],'source_baseline':spec['baseline_px'],'source_size':[W,H]}
        records.append({'name':name,'triangles':len(faces),'closed':closed,'zero_area':zero,'root_vertices':len(root_ids)*2,'old_fin_mesh_read':False})
        bpy.data.meshes.remove(mid)
    return records,roots
