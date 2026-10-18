"""Freeze explicit basal selections for existing exports; diagnose native rest contact.

Not a new-fish build/acceptance. Species root polylines are reviewable input data.
Run in Blender: -- inventory.json plan071.json output.json
"""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def nearline(p, lines):
 return min((p-(a+(b-a)*max(0,min(1,(p-a).dot(b-a)/max((b-a).length_squared,1e-20))))).length for a,b in zip(lines,lines[1:]))

def select_roots(o, sp, e, body_bones, fin=None):
 points=[o.matrix_world@v.co for v in o.data.vertices]
 nonbody=[sum(g.weight for g in v.groups if o.vertex_groups[g.group].name not in body_bones) for v in o.data.vertices]
 mapping=e['pixel_mapping'];s=mapping['pixels_per_unit'];cx=mapping['center_x'];cy=mapping['center_y']
 pixels=[(p.x*s+cx,cy-p.z*s) for p in points];lines=[];rule='body-only authored proximal band plus complete source basal polyline'
 if fin:
  poly=fin['polygon'];name=fin['name'];indices=[]
  if sp=='mahi_mahi':indices=[len(poly)-1,0]
  elif sp=='arapaima':indices={'Dorsal':[9,10,11,12,13,0],'Anal':[0,1,2,3,4],'Caudal':[len(poly)-1,0],'Pectoral':[len(poly)-1,0,1],'Pelvic':[len(poly)-1,0,1]}[name]
  elif sp=='blacktip_reef_shark':indices={'FirstDorsal':[11,12,0],'SecondDorsal':[8,0],'CaudalUpper':[16,0],'CaudalLower':[11,0],'Pectoral':[10,0],'Pelvic':[6,7,8,0],'Anal':[9,10,0]}[name]
  elif sp=='peacock_bass':indices={'Dorsal_soft':[18,19,20,21],'Dorsal_spiny':[45,46,47,48,49],'Anal':[1,2,3,4,5],'Caudal':[len(poly)-1,0],'Pectoral':[len(poly)-1,0],'Pelvic':[len(poly)-1,0,1]}[name]
  else:
   # Traced hammerhead fins have an explicit flat basal edge at the body-facing extreme.
   axis=0 if name.startswith('Caudal') else 1;val=(max if name.startswith(('Caudal','FirstDorsal','SecondDorsal')) else min)(p[axis] for p in poly)
   indices=[i for i,p in enumerate(poly) if abs(p[axis]-val)<.000001]
   if len(indices)<2:indices=[len(poly)-1,0]
  lines=[Vector(((poly[i][0]-.5),(.5-(fin['anchor'][1]+(poly[i][1]-fin['anchor'][1])*fin.get('vertical_scale',1)))*mapping['height']/mapping['width'])) for i in indices]
  tol=1.6/mapping['width']
  if name.startswith('Caudal'):
   # A scalar anchor-to-tip weight can be zero on an entire free lobe.
   # The caudal attachment is the anterior stem, not those free lobe margins.
   mx=max(p.x for p in points)
   ids=[i for i,p in enumerate(points) if p.x>=mx-.008 and abs((cy-p.z*s)/mapping['height']-fin['anchor'][1])<=.14]
  else:ids=[i for i,p in enumerate(points) if nonbody[i]<1e-7 or nearline(Vector((p.x,p.z)),lines)<=tol]
 elif sp=='silver_arowana':
  if o.name in ['Dorsal','Anal']:ids=[i for i,w in enumerate(nonbody) if w<1e-7]
  elif o.name.startswith('Caudal'):ids=[i for i,(x,y) in enumerate(pixels) if x>=276]
  else:
   a,b=((1390,384),(1118,490)) if o.name.startswith('Pectoral') else ((991,425),(852,501))
   delta=Vector(b)-Vector(a);ids=[i for i,p in enumerate(pixels) if (Vector(p)-Vector(a)).dot(delta)/delta.length_squared<=.061]
  rule='Native longitudinal t<=1/18 for paired fins; complete t=0 dorsal/anal row; caudal basal stem x>=276px'
 elif sp=='hairtail':
  if 'Dorsal' in o.name:
   ids=[v.index for v in o.data.vertices if sum(g.weight for g in v.groups if o.vertex_groups[g.group].name.endswith('_Tip'))<1e-6]
  else:ids=[i for i,(x,y) in enumerate(pixels) if x<=1592 and y<=110]
  rule='Native dorsal root row (Tip weight=0), paired basal source stem x<=1592,y<=110'
 else:
  if o.name=='Tail_Fin':ids=[i for i,(x,y) in enumerate(pixels) if x>=240 and 365<=y<=530]
  elif o.name=='Adipose_Fin':ids=[i for i,(x,y) in enumerate(pixels) if y>=345]
  elif o.name.startswith('Pectoral'):ids=[i for i,w in enumerate(nonbody) if w<=.15]
  elif o.name=='Pelvic_Fin':ids=[i for i,(x,y) in enumerate(pixels) if y<=770]
  else:ids=[i for i,w in enumerate(nonbody) if w<1e-7]
  rule='Native body-only dorsal/anal base; paired proximal hinge own weight<=.15; pelvic basal y<=770; tail x>=240; adipose y>=345 pixels'
 assert ids, (sp,o.name,'empty base')
 return ids,rule

def main():
 args=sys.argv[sys.argv.index('--')+1:];inventory=json.loads(Path(args[0]).read_text());plan=json.loads(Path(args[1]).read_text(encoding='utf8'));entries={e['species']:e for e in plan['items']};rows=[]
 for row in inventory:
  sp=row['species'];e=entries[sp];bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=row['before']);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.view_layer.update()
  meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];body=next(o for o in meshes if o.name.startswith(('Closed_body','Arowana_closed','Fish_Body','Hairtail_Ribbon')))
  body.data.calc_loop_triangles();bp=[body.matrix_world@v.co for v in body.data.vertices];tri=[tuple(t.vertices) for t in body.data.loop_triangles];bvh=BVHTree.FromPolygons(bp,tri,all_triangles=True)
  profile=json.loads(Path(e['profile']).read_text(encoding='utf8')) if e.get('profile') else {};fins={}
  length=max(v.x for o in meshes for v in [o.matrix_world@v.co for v in o.data.vertices])-min(v.x for o in meshes for v in [o.matrix_world@v.co for v in o.data.vertices]);real=json.loads(Path('E:/game-ai-foundry/projects/fishing-2d/game/assets/models/fish/motion/motion.json').read_text())['profiles'][sp]['real_length_cm'];scale_cm=real/length
  for o in meshes:
   if not any(k in o.name for k in ['Dorsal','Anal','Caudal','Pectoral','Pelvic','Tail_Fin','Adipose_Fin']):continue
   spec=next((f for f in profile.get('fins',[]) if o.name==f['name'] or o.name in [f['name']+'_left',f['name']+'_right']),None)
   ids,rule=select_roots(o,sp,e,row['body_bones'],spec);coords=[o.matrix_world@o.data.vertices[i].co for i in ids];dist=[]
   for p in coords:
    hit,n,_,d=bvh.find_nearest(p);dist.append(d*scale_cm*(1 if (p-hit).dot(n)>=0 else -1))
   fins[o.name]={'ids':ids,'rest_points_gltf':[[p.x,p.z,-p.y] for p in coords],'rule':rule,'rest_min_cm':min(dist),'rest_max_cm':max(dist),'vertices':len(o.data.vertices)}
  rows.append({'species':sp,'model':row['before'],'model_sha256':row['sha256'],'body':body.name,'body_bones':row['body_bones'],'length_native':length,'scale_cm':scale_cm,'fins':fins})
 Path(args[2]).write_text(json.dumps({'kind':'existing_fin_attachment_plan','scope':'Explicit basal fin inventory; absolute contact must be verified again on actual imported animated GLBs','items':rows},indent=2),encoding='utf8')
 print('ROOT_PLAN_DONE')
if __name__=='__main__':main()
