"""Local transverse thickening on the current editable skin; topology stays fixed."""
import bpy,math,json
from mathutils import Vector

def modify_arms(root,out):
 build=json.loads((root/'motion-r3/rest/gray-build.validation.json').read_text());paths=build['control_paths'];labels=build['arm_labels']
 roots=[Vector(p[0])for p in paths];dirs=[(Vector(p[-1])-Vector(p[0])).normalized()for p in paths];lengths=[(Vector(p[-1])-Vector(p[0])).length for p in paths]
 def smooth(x):x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
 def scale(f):return 1+.06*smooth((f-.35)/.30)+.39*smooth((f-.92)/.08)
 def locate(p):
  candidates=[]
  for i in range(8):
   s=(p-roots[i]).dot(dirs[i]);off=p-roots[i]-s*dirs[i];candidates.append((off.length,i,s,off))
  return min(candidates,key=lambda x:x[0])
 skin=bpy.data.objects['Octopus_gray_skin'];cups=bpy.data.objects['Paired_sucker_rows_512_cups'];counts={};maximum=0;protected_changes=0
 for v in skin.data.vertices:
  dist,i,s,off=locate(v.co);f=s/lengths[i]
  if f<=.35 or dist>.22:continue
  # Preserve the old rounded cap topology; shorten only the last 0.06 ML and broaden its cross section.
  shorten=.012*smooth((s-(lengths[i]-.060))/.060)
  delta=off*(scale(f)-1)-dirs[i]*shorten
  v.co+=delta;maximum=max(maximum,delta.length);counts[labels[i]]=counts.get(labels[i],0)+1
 skin.data.update()
 # Translate each full cup to its enlarged support instead of stretching the cup bowl.
 adjacency=[set()for v in cups.data.vertices]
 for edge in cups.data.edges:
  a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
 unseen=set(range(len(adjacency)));cup_changes=0
 while unseen:
  stack=[unseen.pop()];ids=[]
  while stack:
   a=stack.pop();ids.append(a)
   for b in adjacency[a]:
    if b in unseen:unseen.remove(b);stack.append(b)
  center=sum((cups.data.vertices[i].co for i in ids),Vector())/len(ids);dist,i,s,off=locate(center);f=s/lengths[i]
  if f<=.35:continue
  delta=off*(scale(f)-1)-dirs[i]*(.012*smooth((s-(lengths[i]-.060))/.060))
  for j in ids:cups.data.vertices[j].co+=delta
  cup_changes+=1
 cups.data.update()
 report={'kind':'octopus_local_arm_thickening','changed_skin_vertices_by_arm':counts,'max_skin_vertex_shift_ML':maximum,'translated_cup_components':cup_changes,'cross_section_scale':{'proximal_0_35':1,'fraction_0_65_to_0_92':1.06,'at_end':1.45},'tip_shortening_max_ML':.012,'tip_transition_length_ML':.060,'topology_uv_weights_rest_bones':'preserved','scope':'Distal arms and their cup support only; head/mantle/web/proximal arms protected','limits':['Authored local form adjustment, not a specimen-measured width profile']}
 (out/'geometry-change.validation.json').write_text(json.dumps(report,indent=2)+'\n')
