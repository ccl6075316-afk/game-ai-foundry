"""Closed shells for this batch's manually traced aquatic growth forms.

Run in background Blender. Coordinates in the layout are normalized to the
desired complete-asset dimensions; the exported GLB uses Y up and +Z front.
"""
from pathlib import Path
import argparse
import json
import math
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import intersect_ray_tri, tessellate_polygon

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("subject", type=Path)
parser.add_argument("atlas", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gray", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
row = json.loads(args.subject.read_text())
size = Vector(row["nominal_xyz_m"])
layout = row["layout"]
verts = []
faces = []
loop_art = []
flow = []
regions = {}
bank_triangles = []
contacts = []
motion = layout.get("motion",0.0)
atlas_size = Vector((256.0,256.0))

def world(point):
    return Vector((point[0]*size.x,point[1]*size.y,point[2]*size.z))

def section_frames(points, angles, rolls):
    for index,(angle,roll) in enumerate(zip(angles,rolls)):
        vertical = points[min(index+1,len(points)-1)] - points[max(index-1,0)]
        vertical.normalize()
        width = Vector((math.cos(angle),0,math.sin(angle)))
        width -= vertical * width.dot(vertical)
        if width.length < 0.01:
            width = vertical.cross(Vector((0,1,0)))
        width.normalize()
        normal = width.cross(vertical).normalized()
        yield width*math.cos(roll)+normal*math.sin(roll), normal*math.cos(roll)-width*math.sin(roll)

def atlas_uv(patch,u,v,reverse=False):
    index = layout["patches"].index(patch)
    x,y = (index%4)*64, (index//4)*128 + 64*reverse
    return ((x+2.0+60.0*u)/atlas_size.x,1.0-(y+2.0+60.0*(1-v))/atlas_size.y)

def add_face(indices,uvs):
    faces.append(tuple(indices))
    loop_art.extend(uvs)

def shell(item):
    stations = item["profile"]
    points = [world(r[:3]) for r in stations]
    if item.get("ground_contact"):
        ray_start=Vector((points[0].x,size.y*2,points[0].z))
        down=Vector((0,-1,0))
        hits=[p.y for face in bank_triangles if (p:=intersect_ray_tri(*face,down,ray_start)) is not None]
        if not hits:
            raise ValueError(f"{item['name']}: ground contact is outside mud bank")
        surface=max(hits)
        lift=surface-points[0].y-size.y*.022
        for point in points:
            point.y+=lift
        assert points[0].y < surface < points[-1].y
        contacts.append(dict(name=item["name"],buried_depth_m=float(surface-points[0].y),
                             visible_height_m=float(points[-1].y-surface)))
    sides = item.get("sides",4)
    patch = item.get("patch","blade")
    count = len(points)
    point_tip = item.get("point_tip", False)
    tangential = item.get("radial", False)
    pitch = item.get("phase",0.0)
    start = len(verts)
    frames = section_frames(points, [math.radians(r[5]) if len(r)>5 else 0 for r in stations],
                            [math.radians(r[6]) if len(r)>6 else 0 for r in stations])
    arc = [0]
    for a,b in zip(points,points[1:]):
        arc.append(arc[-1]+(b-a).length)
    pivot = world(item.get("pivot",stations[0][:3]))
    rings = count - int(point_tip)
    for index, ((width,normal), center, station) in enumerate(zip(frames,points,stations)):
        u = min(1.0, max(0.0,(center.y / size.y + item.get("flow_bias",0)) * motion)) if item.get("sway",True) else 0.0
        if index == 0 and item.get("pin_base",True):
            u = 0.0
        if station[1] <= 0.02:
            u = 0.0
        if point_tip and index == count-1:
            verts.append(center)
            flow.append((u,pitch,pivot))
            continue
        for n in range(sides):
            angle = 2*math.pi*n/sides
            edge=math.cos(angle)
            corrugation=item.get("ruffle",0.)*math.sin(index*1.65+n*1.85)*(abs(edge)**3)
            verts.append(center + size.x*(width*(station[3]*edge) + normal*(station[4]*math.sin(angle)+station[3]*corrugation)))
            flow.append((u, pitch, pivot))
    def ring_index(level,n):
        return start+level*sides+n%sides
    def rail(n):
        if tangential:
            return n/sides
        spoke = n%sides
        return min(spoke,sides-spoke)/(sides//2)
    for level in range(rings-1):
        for n in range(sides):
            where = [(level,n),(level,n+1),(level+1,n+1),(level+1,n)]
            reverse = n >= sides//2 and not tangential
            add_face([ring_index(j,k) for j,k in where], [atlas_uv(patch,rail(k),arc[j]/arc[-1],reverse) for j,k in where])
    if point_tip:
        tip = len(verts)-1
        for n in range(sides):
            reverse = n >= sides//2 and not tangential
            fraction = arc[rings-1]/arc[-1]
            add_face([ring_index(rings-1,n),ring_index(rings-1,n+1),tip],
                     [atlas_uv(patch,rail(n),fraction,reverse),atlas_uv(patch,rail(n+1),fraction,reverse),
                      atlas_uv(patch,.5,1.,reverse)])
    for level,invert in ([(0,True)] if point_tip else [(0,True),(count-1,False)]):
        indices = list(range(sides))
        if invert:
            indices.reverse()
        add_face([ring_index(level,n) for n in indices],[atlas_uv(patch,0.4+0.2*math.cos(n*math.tau/sides),.05+.02*math.sin(n*math.tau/sides),True) for n in indices])
    regions[item.get("name",str(start))] = {"first_vertex":start,"vertices":len(verts)-start}

def ground_bank(item):
    """Rim, eroded contact sole, and an irregular ring of raised mud."""
    n = len(item["outline"])
    xz = item["outline"]
    patch = item.get("patch","mud")
    rise = item.get("rise",1.0)
    start = len(verts)
    face_start=len(faces)
    rings=item.get("rings",[(.78,0.0,0.0),(1,.08,1.0),(.66,.29,1.7),(.34,.37,1.1)])
    for shrink,y,shifts in rings:
        for j,(x,z) in enumerate(xz):
            height = rise*(y+shifts*(.026*math.sin(j*2.31)+.013*math.cos(j*4.27)+.09*(-x)-.055*z))
            offset=item.get("upper_bias",[0,0])
            verts.append(world((x*shrink+offset[0]*y,height,z*shrink+offset[1]*y)))
            flow.append((0.,0.,Vector((0,0,0))))
    for k in range(len(rings)-1):
        for j in range(n):
            corners = ((k,j),(k,(j+1)%n),(k+1,(j+1)%n),(k+1,j))
            indices = [start+nk*n+nj for nk,nj in corners]
            add_face(indices,[atlas_uv(patch,verts[b].x/size.x+.5,verts[b].z/size.z+.5) for b in indices])
    for k in [0,len(rings)-1]:
        order = list(range(n)) if k else list(reversed(range(n)))
        indices = [start+k*n+j for j in order]
        add_face(indices,[atlas_uv(patch,verts[b].x/size.x+.5,verts[b].z/size.z+.5,reverse=k==0) for b in indices])
    for face in faces[face_start:]:
        local=[verts[i] for i in face]
        for tri in tessellate_polygon([local]):
            bank_triangles.append(tuple(local[i] for i in tri))

def plate(item):
    # Non-circular calcified plate with a pinched stem and two rounded lobes.
    a,b=map(world,item["axis"])
    direction=(b-a).normalized()
    width_axis=Vector((math.cos(item["yaw"]),0,math.sin(item["yaw"])))
    width_axis-=direction*width_axis.dot(direction)
    width_axis.normalize()
    normal=width_axis.cross(direction).normalized()
    edge=[(-.15,.00),(.14,.01),(.38,.23),(.61,.57),(.57,.78),(.34,.97),(.02,.88),
          (-.31,1.),(-.58,.81),(-.63,.56),(-.41,.25)]
    n=len(edge)
    start=len(verts)
    thickness=item["thickness"]*size.x
    pivot=world(item["pivot"])
    def add_vertex(point):
        verts.append(point)
        weight=min(1.,max(0.,point.y/size.y)*motion)
        flow.append((weight,item["phase"],pivot))
    for side in (-1,1):
        for u,v in edge:
            point=a.lerp(b,v)+size.x*item["width"]*u*width_axis+normal*side*thickness*.35
            add_vertex(point)
        add_vertex(a.lerp(b,.57)+normal*side*thickness)
    for side in (0,1):
        base=start+side*(n+1)
        for i in range(n):
            j=(i+1)%n
            uv=[atlas_uv(item["patch"],edge[k][0]*.74+.5,edge[k][1],bool(side)) for k in (i,j)]
            add_face([base+i,base+j,base+n],uv+[atlas_uv(item["patch"],.5,.57,bool(side))])
    for i in range(n):
        j=(i+1)%n
        add_face([start+i,start+j,start+n+1+j,start+n+1+i],
                 [atlas_uv("rim",i/n,.5),atlas_uv("rim",(i+1)/n,.5),
                  atlas_uv("rim",(i+1)/n,.55),atlas_uv("rim",i/n,.55)])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
for item in layout["parts"]:
    if item.get("kind","shell") == "bank":
        ground_bank(item)
    elif item.get("kind") == "plate":
        plate(item)
    else:
        shell(item)
points = list(zip(*verts))
anchor_min = Vector([min(coords) for coords in points])
anchor_size = Vector([max(coords)-min(coords) for coords in points])
center_ground = Vector((anchor_min.x+anchor_size.x/2,anchor_min.y,anchor_min.z+anchor_size.z/2))
ratios = Vector([length/span for length,span in zip(size,anchor_size)])
# Exact nominal dimensions refer to the complete instance, including roots.
verts = [Vector([(x-o)*s for x,o,s in zip(v,center_ground,ratios)]) for v in verts]
flow = [(u,phase,Vector([(x-o)*s for x,o,s in zip(p,center_ground,ratios)])) for u,phase,p in flow]
def blender(v):
    return (v.x,-v.z,v.y)

mesh = bpy.data.meshes.new(row["id"]+" · closed natural shells")
mesh.from_pydata([blender(v) for v in verts],[],faces)
mesh.update()
uv = mesh.uv_layers.new(name="Pixel artwork")
# Waterflow XY: convert glTF V back to exported convention.
sway = mesh.uv_layers.new(name="Water flow")
for i,loop in enumerate(mesh.loops):
    uv.data[i].uv = loop_art[i]
    u,phase,_ = flow[loop.vertex_index]
    sway.data[i].uv = (u,1-phase)
lo = Vector((min(p.x for _,_,p in flow)-.0001,-.0001,min(p.z for _,_,p in flow)-.0001))
span = Vector([max(p[i] for _,_,p in flow)-lo[i]+.0001 for i in range(3)])
colors = mesh.color_attributes.new(name="Water pivots",type="FLOAT_COLOR",domain="POINT")
for i,(_,_,p) in enumerate(flow):
    colors.data[i].color = tuple((p[a]-lo[a])/span[a] for a in range(3))+(1.0,)
mesh.uv_layers.active_index = 0
graph = bmesh.new()
graph.from_mesh(mesh)
bmesh.ops.recalc_face_normals(graph,faces=list(graph.faces))
bmesh.ops.triangulate(graph,faces=list(graph.faces))
assert not any(not e.is_manifold for e in graph.edges)
graph.to_mesh(mesh)
graph.free()
for p in mesh.polygons:
    p.use_smooth = True
mesh.update()
obj = bpy.data.objects.new(row["id"],mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
material = bpy.data.materials.new(row["id"]+" · nearest pixel artwork")
material.use_nodes=True
obj.data.materials.append(material)
shader=material.node_tree.nodes.get("Principled BSDF")
shader.inputs["Roughness"].default_value=.95
shader.inputs["Specular IOR Level"].default_value=.18
if args.gray:
    shader.inputs["Base Color"].default_value=(0.39,0.46,0.48,1)
else:
    paint=material.node_tree.nodes.new("ShaderNodeTexImage")
    paint.image=bpy.data.images.load(str(args.atlas))
    paint.image.pack()
    paint.interpolation="Closest"
    paint.extension="EXTEND"
    material.node_tree.links.new(paint.outputs["Color"],shader.inputs["Base Color"])
obj["geometry_budget_type"]=row["budget_type"]
obj["nominal_xyz_m"]=list(size)
obj["waterflow_uv"]="UV2.x root-to-tip; UV2.y phase; COLOR_0 RGB author pivot; static when no shader bound"
obj["anchor_min"]=list(lo)
obj["anchor_size"]=list(span)
obj["source_board_sha256"]=row["source_board_sha256"]
obj["intent_layout"]=" / ".join(layout["notes"])
args.output.parent.mkdir(parents=True,exist_ok=True)
if not args.gray:
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.with_suffix(".blend")),compress=True)
bpy.ops.export_scene.gltf(filepath=str(args.output),export_format="GLB",export_texcoords=True,
                          export_vertex_color="ACTIVE",export_animations=False,export_extras=True)
triangles=len(mesh.polygons)
proof=dict(triangles=triangles,anchor_min=list(lo),anchor_size=list(span),pinned_vertices=sum(u<=.08 for u,_,_ in flow),
           moving_vertices=sum(u>.08 for u,_,_ in flow),source_parts=regions,
           bank_contacts=[dict(c,buried_depth_m=c["buried_depth_m"]*ratios.y,visible_height_m=c["visible_height_m"]*ratios.y) for c in contacts])
args.output.with_suffix(".build.json").write_text(json.dumps(proof,indent=2)+"\n")
