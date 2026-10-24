"""Blender: build complete native source cutouts on a rigged 3D fin surface."""
import bpy,json,sys,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt,barycentric_transform
sys.path.insert(0,str(Path(__file__).parent))
from closed_body_index140 import build as closed_sign_index
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def nearest_line(q,line):
 best=(1e9,None)
 for a,b in zip(line,line[1:]):
  edge=b-a;t=max(0.,min(1.,(q-a).dot(edge)/max(edge.length_squared,1e-12)));p=a+edge*t;dist=(p-q).length
  if dist<best[0]:best=(dist,p)
 return best
def inside(q,poly):
 odd=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a.y>q.y)!=(b.y>q.y) and q.x<(b.x-a.x)*(q.y-a.y)/(b.y-a.y)+a.x:odd=not odd
 return odd
def smooth(t):t=max(0.,min(1.,t));return t*t*(3-2*t)
def main():
 args=sys.argv[sys.argv.index('--')+1:];p=read(args[0]);assert sha(p['source_mesh'])==p['source_mesh_sha256'];assert sha(p['source_annotations'])==p['source_annotations_sha256'];src=read(p['source_mesh']);out=Path(p['output']);out.mkdir(parents=True,exist_ok=True);(out/'build.plan.json').write_text(json.dumps(p,indent=2));w,h=p['source_size'];aspect=w/h
 mapping=p.get('pixel_mapping',{});ppu=float(mapping.get('pixels_per_unit',w));cx=float(mapping.get('center_x',w/2));cy=float(mapping.get('center_y',h/2));native_width=w/ppu
 positions=[];triangles=[];bodyweights=[];body_names=src['body'][0]['skin_joint_names']
 bodies=src['body']
 if p.get('body_geometry_override'):
  override=p['body_geometry_override'];assert sha(override['path'])==override['sha256'];data=read(override['path']);jointmap=[next(i for i,n in enumerate(body_names) if n==name or n==name+'_2') for name in override['skin_joint_names']];parts=[]
  for part in data['parts']:parts.append({**part,'rest_vertices':part['vertices'],'joints':[[jointmap[j] for j in row] for row in part['joints']]})
  bodies=[{'skin_joint_names':body_names,'parts':parts}]
 for obj in bodies:
  assert obj['skin_joint_names']==body_names
  for part in obj['parts']:
   offset=len(positions);positions.extend(Vector(q) for q in part['rest_vertices']);ids=part['triangles'];triangles.extend(tuple(offset+v for v in ids[k:k+3]) for k in range(0,len(ids),3));bodyweights.extend(dict(zip(j,v)) for j,v in zip(part['joints'],part['weights']))
 bvh=BVHTree.FromPolygons(positions,triangles,all_triangles=True);inside_body=closed_sign_index([list(v) for v in positions],triangles);old={f['name']:f for f in src['fins']};output=[];reports=[];frozen={}
 for spec in p['fins']:
  name=spec['name'];f=old[name];assert sha(spec['texture'])==spec['texture_sha256'] and sha(spec['source_mask'])==spec['source_mask_sha256'];raw_poly=[Vector(q) for q in spec['polygon_px']];base=[Vector(q) for q in spec['baseline_px']];poly=[]
  # The actual constrained basal BORDER must also be split: interior grids do
  # not split a long boundary chord after it bends onto a curved body.
  for a,b in zip(raw_poly,raw_poly[1:]+raw_poly[:1]):
   near=min(nearest_line(q,base)[0] for q in [a,b,(a+b)*.5])<spec['root_band_px']+spec['root_blend_px']+2;step=spec['root_dense_px'] if near else spec['grid_px'];count=max(1,math.ceil((b-a).length/step));poly.extend(a.lerp(b,k/count) for k in range(count))
  points=poly[:];spacing=spec['grid_px'];minx=min(q.x for q in poly);maxx=max(q.x for q in poly);miny=min(q.y for q in poly);maxy=max(q.y for q in poly)
  for y in range(math.floor(miny),math.ceil(maxy)+1,round(spacing)):
   for x in range(math.floor(minx),math.ceil(maxx)+1,round(spacing)):
    q=Vector((x+.31,y+.17))
    if inside(q,poly):points.append(q)
  # One uniform basal grid avoids many overlapping grids on curved polylines.
  # Coverage and physical root/membrane limits are unchanged.
  dense=spec['root_dense_px'];near_band=spec['root_band_px']+spec['root_blend_px']+2;bx0=max(minx,min(q.x for q in base)-near_band);bx1=min(maxx,max(q.x for q in base)+near_band);by0=max(miny,min(q.y for q in base)-near_band);by1=min(maxy,max(q.y for q in base)+near_band)
  for yi in range(math.floor(by0/dense),math.ceil(by1/dense)+1):
   for xi in range(math.floor(bx0/dense),math.ceil(bx1/dense)+1):
    q=Vector((xi*dense,yi*dense))
    if nearest_line(q,base)[0]<near_band and inside(q,poly):points.append(q)
  for a,b in zip(base,base[1:]):
   count=max(2,math.ceil((b-a).length/dense))
   for k in range(count+1):
    q=a.lerp(b,k/count)
    if inside(q,poly) or nearest_line(q,poly+[poly[0]])[0]<1e-5:points.append(q)
  scaled=[Vector((q.x/w,q.y/w)) for q in points];dv,_,df,*_=delaunay_2d_cdt(scaled,[(i,(i+1)%len(poly)) for i in range(len(poly))],[list(range(len(poly)))],1,1e-8);assert df
  # CDT can retain coincident constrained/grid endpoints. Weld in the same
  # native1e-7 identity used by the finite-shell gate before thickening.
  canonical={};mapped=[];clean=[]
  for q in dv:
   key=(round(float(q.x),7),round(float(q.y),7))
   if key not in canonical:canonical[key]=len(clean);clean.append(q)
   mapped.append(canonical[key])
  next_faces=[];seen=set()
  for face in df:
   face=[mapped[i] for i in face]
   if len(set(face))<3:continue
   key=tuple(sorted(face))
   if key not in seen:next_faces.append(face);seen.add(key)
  dv=clean;df=next_faces;used=sorted({i for face in df for i in face});remap={old:i for i,old in enumerate(used)};dv=[dv[i] for i in used];df=[[remap[i] for i in face] for face in df]
  source=[Vector((q.x*w,q.y*w)) for q in dv];distances=[nearest_line(q,base)[0] for q in source];maxdist=max(distances);paired=name.startswith(('Pectoral','Pelvic'));dorsal='Dorsal' in name or 'Adipose' in name;ventral='Anal' in name;tail='Caudal' in name or 'Tail_Fin' in name;side=1 if name.endswith(('_left','_+1','_Near')) else -1;names=f['skin_joint_names'];bodymap=[names.index(n) for n in body_names];finbone=next((i for i,n in enumerate(names) if n in [name,name+'_2']),None);vertices=[];weights=[];joints=[];rootids=[];displacements=[]
  uv_index=None;uv_vertices=[];uv_triangles=[];uv_weights=[]
  if spec.get('fin_weight_mode')=='source_uv_interpolation':
   for part in f['parts']:
    offset=len(uv_vertices);uv_vertices.extend(Vector((u*w,v*h,0)) for u,v in part['uv']);uv_weights.extend(dict(zip(j,v)) for j,v in zip(part['joints'],part['weights']));ids=part['triangles'];uv_triangles.extend(tuple(offset+v for v in ids[k:k+3]) for k in range(0,len(ids),3))
   uv_index=BVHTree.FromPolygons(uv_vertices,uv_triangles,all_triangles=True)
  else:assert finbone is not None,('Explicit multi-bone transport required',name)
  for i,(q,distance) in enumerate(zip(source,distances)):
   xy=Vector(((q.x-cx)/ppu,(cy-q.y)/ppu,0.));_,basal=nearest_line(q,base);bp=Vector(((basal.x-cx)/ppu,(cy-basal.y)/ppu,0.));direction=Vector((0,0,side)) if paired else Vector((0,1 if dorsal else -1,0)) if not tail else Vector((-1,0,0));origin=bp+direction*2*native_width;hit,normal,face,_=bvh.ray_cast(origin,-direction,4.*native_width)
   if hit is None:hit,normal,face,_=bvh.find_nearest(bp)
   assert hit is not None
   if normal.dot(direction)<0:normal=-normal
   if not paired and spec.get('transport_median_relative_to_base',False):
    # Preserve source fin extent relative to its own basal curve. Clamping
    # every absolute source ordinate to a larger curved body flattens whole
    # rows onto one edge. The body itself is retained; placement displacement
    # remains explicit in the source-camera comparison.
    if tail:xy.x+=float(spec.get('tail_uniform_transport_native',hit.x-bp.x))
    else:xy.y+=hit.y-bp.y
   gain=1.-smooth((distance-spec['root_band_px'])/spec['root_blend_px'])
   segment=min(zip(base,base[1:]),key=lambda pair:nearest_line(basal,list(pair))[0]);st=(segment[1]-segment[0]).normalized();source_tangent=Vector((st.x,-st.y,0));source_delta=Vector(((q.x-basal.x)/ppu,-(q.y-basal.y)/ppu,0));tangent=(source_tangent-normal*source_tangent.dot(normal)).normalized();cross=normal.cross(tangent).normalized();source_perp=Vector((-source_tangent.y,source_tangent.x,0));perp=source_delta.dot(source_perp)
   if paired and cross.dot(source_perp)<0:cross=-cross
   root_probe=hit+tangent*source_delta.dot(source_tangent)+cross*perp*.75;root_hit,root_normal,_,_=bvh.find_nearest(root_probe)
   if root_normal.dot(direction)<0:root_normal=-root_normal
   # A finite tangent collar must not collapse at a closest-triangle corner.
   # Keep the transported 2D patch finite; actual signed-distance gates still
   # reject any resulting gap or excessive burial against the real surface.
   basal_target=(root_probe-normal*spec['root_inset_native']) if spec.get('finite_tangent_collar',False) else root_hit-root_normal*spec['root_inset_native']
   if spec.get('root_project_normal_only',False):basal_target=root_probe-root_normal*((root_probe-root_hit).dot(root_normal)+spec['root_inset_native'])
   if paired:
    sh,sn,sface,_=bvh.ray_cast(Vector((xy.x,xy.y,side*2)),Vector((0,0,-side)),4.)
    depth=abs(sh.z) if sh is not None else abs(hit.z)
    xy.z=side*(depth+spec['free_clearance_native']+spec['spread_native']*smooth(distance/maxdist))
   # A finite source basal strip wraps onto the local body tangent surface.
   # Collapsing that whole strip onto one line would create zero-area faces.
   point=xy.lerp(basal_target,gain)
   if distance<=spec['root_band_px']+1e-6:point=basal_target;rootids.append(i)
   else:
    half=spec['thickness_native']/2;minimum=half+spec.get('minimum_outer_clearance_native',.00035)+spec['free_clearance_native']*smooth((distance-spec['root_band_px'])/12.);clearance=minimum
    if paired:
     sh,sn,sface,_=bvh.ray_cast(Vector((point.x,point.y,side*2)),Vector((0,0,-side)),4.)
     if sh is not None:point.z=side*max(side*point.z,side*sh.z+clearance)
    elif tail:
     sh,sn,sface,_=bvh.ray_cast(Vector((-2,point.y,point.z)),Vector((1,0,0)),4.)
     if sh is not None:point.x=min(point.x,sh.x-clearance)
    else:
     vertical=1 if dorsal else -1;sh,sn,sface,_=bvh.ray_cast(Vector((point.x,vertical*2,point.z)),Vector((0,-vertical,0)),4.)
     if sh is not None:point.y=vertical*max(vertical*point.y,vertical*sh.y+clearance)
    near,nn,_,separation=bvh.find_nearest(point);point_inside=inside_body(point)
    if point_inside or separation<minimum:
     outward=(near-point) if point_inside else (point-near)
     if outward.length<1e-10:
      outward=nn
      if inside_body(near+outward*.001):outward=-outward
     point=near+outward.normalized()*minimum
   vertices.append(point);displacements.append(math.hypot(point.x-(q.x-cx)/ppu,point.y-(cy-q.y)/ppu)*ppu)
   near,nn,fi,_=bvh.find_nearest(point);aa,bb,cc=triangles[fi];bary=barycentric_transform(near,positions[aa],positions[bb],positions[cc],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={};influence=float(spec.get('fin_influence_scale',1.));assert 0.<influence<=1.;finweight=smooth((distance-spec['root_band_px']-8)/max(20,maxdist*.7))*influence
   for bi,bw in zip([aa,bb,cc],bary):
    for j,v in bodyweights[bi].items():mix[bodymap[j]]=mix.get(bodymap[j],0)+max(0,bw)*v*(1-finweight)
   if uv_index is not None:
    near_uv,_,face_uv,_=uv_index.find_nearest(Vector((q.x,q.y,0)));ia,ib,ic=uv_triangles[face_uv];bw_uv=barycentric_transform(near_uv,uv_vertices[ia],uv_vertices[ib],uv_vertices[ic],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    if not all(math.isfinite(float(z)) for z in bw_uv) or sum(max(0,float(z)) for z in bw_uv)<1e-10:
     # A degenerate legacy UV seam has no barycentric area. Its nearest
     # original UV vertex retains the original multi-bone weights.
     nearest_vi=min([ia,ib,ic],key=lambda j:(uv_vertices[j]-near_uv).length_squared);bw_uv=Vector(tuple(1. if j==nearest_vi else 0. for j in [ia,ib,ic]))
    for vi,bw in zip([ia,ib,ic],bw_uv):
     for joint,weight in uv_weights[vi].items():mix[joint]=mix.get(joint,0)+max(0,bw)*weight*finweight
   else:mix[finbone]=mix.get(finbone,0)+finweight
   ww=sorted(mix.items(),key=lambda z:-z[1])[:4]
   while len(ww)<4:ww.append((0,0.))
   total=sum(v for j,v in ww);joints.append([j for j,v in ww]);weights.append([v/total for j,v in ww])
  assert len(rootids)>=2,(name,len(rootids));faces=[]
  for face in df:
   for k in range(1,len(face)-1):faces.append([face[0],face[k],face[k+1]])
  normals=[Vector() for q in vertices]
  for aa,bb,cc in faces:
   n=(vertices[bb]-vertices[aa]).cross(vertices[cc]-vertices[aa])
   for j in [aa,bb,cc]:normals[j]+=n
  for i,n in enumerate(normals):normals[i]=n.normalized() if n.length>1e-12 else Vector((0,0,1))
  n=len(vertices);half=spec['thickness_native']/2;solid=[q+normals[i]*half for i,q in enumerate(vertices)]+[q-normals[i]*half for i,q in enumerate(vertices)];allfaces=faces+[[n+c,n+b,n+a] for a,b,c in faces];edges={}
  for face in faces:
   for a,b in zip(face,face[1:]+face[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
  for es in edges.values():
   if len(es)==1:
    a,b=es[0];allfaces.extend([[a,n+a,n+b],[a,n+b,b]])
  roots=rootids+[i+n for i in rootids];uv=[[q.x/w,q.y/h] for q in source];part={'surface':0,'vertices':[list(q) for q in solid],'normals':[list(q) for q in normals]+[list(-q) for q in normals],'uv':uv+uv,'joints':joints+joints,'weights':weights+weights,'triangles':[j for face in allfaces for j in face]};output.append({'name':name,'skin_joint_names':names,'parts':[part],'texture':spec['texture'],'texture_sha256':spec['texture_sha256']});frozen[name]={'ids':roots,'rest_points_gltf':[list(solid[i]) for i in roots],'vertices':len(solid),'rule':'Full independently annotated source basal neighborhood, before 3D surface transport','source_baseline':[[q[0]/w,q[1]/h] for q in spec['baseline_px']],'source_t_max':spec['root_band_px']/maxdist};reports.append({'name':name,'vertices':len(solid),'root_vertices':len(roots),'source_contour_vertices':len(poly),'max_projection_displacement_px':max(displacements),'grid_px':spacing,'source_texture_sha256':spec['texture_sha256']})
 data={'species':p['species'],'source_model_sha256':src['source_model_sha256'],'fins':output};(out/'fins.bound.json').write_text(json.dumps(data));(out/'root-selection.json').write_text(json.dumps(frozen));(out/'build.validation.json').write_text(json.dumps({'ok':len(output)==len(p['fins']),'plan_sha256':sha(args[0]),'source_model_sha256':src['source_model_sha256'],'fins_sha256':sha(out/'fins.bound.json'),'root_selection_sha256':sha(out/'root-selection.json'),'records':reports,'scope':'New source-cut fin geometry; technical build only. Actual engine UV, root/full membrane and visual/source gates remain required.'},indent=2));print('SOURCE_FINS141',json.dumps(reports))
if __name__=='__main__':main()
