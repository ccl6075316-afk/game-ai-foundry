"""Loft a measured open-reference mandible and corner webs, then inverse-bind it.

The authored reference is an open silhouette; closed rest vertices are obtained
by inverse linear-blend skinning so the target opening reconstructs that shape.
"""
import bpy,bmesh,math
from mathutils import Vector,Matrix
from volume_mouth import slit_v

def build_reference_jaw(body,settings,aspect,weights,body_section,side_patches):
    lower=settings['separate_lower'];ref=lower['reference_shape'];rows=ref['sections'];motion=settings['articulation']
    skin=body.data.materials[0];inside=next(m for m in body.data.materials if m.name.startswith('Oral interior'))
    def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
    def sample(u):
        if u<=rows[0][0]:return rows[0][1:]
        if u>=rows[-1][0]:return rows[-1][1:]
        for a,b in zip(rows,rows[1:]):
            if a[0]<=u<=b[0]:
                t=(u-a[0])/(b[0]-a[0]);return [x+(y-x)*t for x,y in zip(a[1:],b[1:])]
    def influence(u):return smooth((u-motion['fixed_root_u'])/(motion['rigid_start_u']-motion['fixed_root_u']))
    def join_width(u,z,width):
        bt,bb,bd=body_section(u);cz=(.5-(bt+bb)/2)*aspect;rz=(bb-bt)*aspect/2
        body_y=bd*math.sqrt(max(0,1-((z-cz)/rz)**2))
        mix=1-smooth((u-settings['corner'][0])/.035)
        return width*(1-mix)+body_y*mix
    hinge=Vector((motion['hinge'][0]-.5,0,(.5-motion['hinge'][1])*aspect))
    rotation=Matrix.Rotation(math.radians(ref['open_degrees']),4,'Y')
    opening=Matrix.Translation(hinge)@rotation@Matrix.Translation(-hinge)
    def finish(name,verts,faces,materials,jaw_weights):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(skin);mesh.materials.append(inside)
        for poly,mi in zip(mesh.polygons,materials):poly.material_index=mi;poly.use_smooth=True
        uv=mesh.uv_layers.new(name='SourceReferenceUV')
        for poly in mesh.polygons:
            for li in poly.loop_indices:
                co=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(co.x+.5,.5+co.z/aspect)
        source_u=mesh.attributes.new('reference_source_u','FLOAT','POINT');weight=mesh.attributes.new('reference_jaw_weight','FLOAT','POINT')
        for vertex,w in zip(mesh.vertices,jaw_weights):
            source_u.data[vertex.index].value=vertex.co.x+.5;weight.data[vertex.index].value=w
            blend=Matrix.Identity(4)
            for i in range(4):
                for j in range(4):blend[i][j]=(1-w)*(1 if i==j else 0)+w*opening[i][j]
            vertex.co=blend.inverted()@vertex.co
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        if not all(e.is_manifold for e in bm.edges):raise ValueError(name+' reference loft not closed manifold')
        if bm.calc_volume(signed=True)<=0:raise ValueError(name+' nonpositive volume')
        bm.to_mesh(mesh);bm.free();mesh.update()
        obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj);return obj
    # Longitudinal loops carry the original outer contour, rather than a global oval plate.
    us=sorted(set([row[0] for row in rows]+[rows[0][0]+(rows[-1][0]-rows[0][0])*i/144 for i in range(145)]))
    n=96;verts=[];faces=[];mat=[];jw=[]
    for u in us:
        top,bottom,width=sample(u);zt=(.5-top)*aspect;zb=(.5-bottom)*aspect
        for j in range(n):
            angle=math.tau*j/n;co=math.cos(angle);si=math.sin(angle)
            z=zt-lower['cup_depth']*co*co if co>=0 else zt+(zb-zt)*(-co)
            join=1-smooth((u-settings['corner'][0])/.035)
            y=join_width(u,zt,width)*si if co>=0 else math.copysign((1-join)*width*abs(si)+join*join_width(u,z,width)*abs(si)**.15,si)
            # Posterior rings are attachment tissue inside the intact head.
            # Do not let their independent ellipse emboss a plate-shaped rim.
            inset=.0015*(1-smooth((u-(settings['corner'][0]-.012))/.010))
            if inset>0:
                bt,bb,bd=body_section(u);cz=(.5-(bt+bb)/2)*aspect;rz=(bb-bt)*aspect/2
                z=max(cz-rz+inset,min(cz+rz-inset,z))
                allowed=max(.0001,bd*math.sqrt(max(0,1-((z-cz)/rz)**2))-inset)
                y=max(-allowed,min(allowed,y))
            verts.append((u-.5,y,z));jw.append(influence(u))
    for i in range(len(us)-1):
        for j in range(n):
            faces.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j));mat.append(1 if math.cos(math.tau*(j+.5)/n)>.5 else 0)
    faces.extend([tuple(range(n-1,-1,-1)),tuple((len(us)-1)*n+j for j in range(n))]);mat.extend([0,0])
    jaw=finish('Lower_jaw_separate',verts,faces,mat,jw)
    webs=[]
    for side in [-1,1]:
        verts=[];faces=[];jw=[];nu=48;nv=10
        for layer in range(2):
            for i in range(nu+1):
                u=settings['corner'][0]+(ref['web_end_u']-settings['corner'][0])*i/nu
                roof=(.5-slit_v(settings,u))*aspect+settings['gap']/2+.0005
                floor=(.5-sample(u)[0])*aspect-.0005
                top,bottom,depth=body_section(u);center=(.5-(top+bottom)/2)*aspect;rad=(bottom-top)*aspect/2
                upper_y=depth*math.sqrt(max(.02,1-((roof-center)/rad)**2))
                lower_y=join_width(u,(.5-sample(u)[0])*aspect,sample(u)[2])
                for j in range(nv+1):
                    t=j/nv;y=side*((1-t)*upper_y+t*lower_y+(.0006 if layer else -.0006))
                    verts.append((u-.5,y,roof+(floor-roof)*t));jw.append(influence(u)*t)
        stride=nv+1;sheet=(nu+1)*stride
        for layer in range(2):
            for i in range(nu):
                for j in range(nv):
                    q=layer*sheet+i*stride+j;faces.append((q,q+1,q+stride+1,q+stride))
        for i in range(nu):
            for j in [0,nv]:
                q=i*stride+j;faces.append((q,q+stride,q+stride+sheet,q+sheet))
        for i in [0,nu]:
            for j in range(nv):
                q=i*stride+j;faces.append((q,q+1,q+1+sheet,q+sheet))
        webs.append(finish('Oral_corner_web_'+('left' if side<0 else 'right'),verts,faces,[0]*len(faces),jw))
    jaw['oral_web_names']=[o.name for o in webs]
    # Use the native side donor on lateral head faces. Existing eye-clearing UV
    # patches are preserved by sampling the same donor polygon/offset rules.
    def inside_poly(point,poly):
        x,y=point;odd=False;j=len(poly)-1
        for i in range(len(poly)):
            xi,yi=poly[i];xj,yj=poly[j]
            if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi:odd=not odd
            j=i
        return odd
    # Source-side donor coordinates are already authored in the body UV layer
    # before the atlas; recover them using declared patches passed in settings.
    for poly in body.data.polygons:
        u=sum(body.data.vertices[i].co.x+.5 for i in poly.vertices)/len(poly.vertices)
        if u<ref['side_projection_start_u'] or abs(poly.normal.y)<.35:continue
        poly.material_index=0
        for li in poly.loop_indices:
            co=body.data.vertices[body.data.loops[li].vertex_index].co;uvp=[co.x+.5,.5-co.z/aspect]
            for patch in side_patches:
                if inside_poly(uvp,patch['polygon']):uvp=[uvp[0]+patch['offset'][0],uvp[1]+patch['offset'][1]];break
            body.data.uv_layers.active.data[li].uv=(uvp[0],1-uvp[1])
    return jaw,{'method':'Source-open longitudinal jaw loft with closed corner webs; inverse LBS binds target reference pose to closed rest.','reference_shape':ref,'reference_open_degrees':ref['open_degrees'],'lower_jaw_vertices':len(jaw.data.vertices),'lower_jaw_object':jaw.name,'oral_web_objects':[o.name for o in webs],'articulated_jaw':False,'source_projection':True}
