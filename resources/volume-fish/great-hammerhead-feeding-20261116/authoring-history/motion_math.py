"""Reference evaluator for the isolated Godot controls; native Blender axes."""
import json,math,os
from pathlib import Path
from mathutils import Quaternion,Vector
W=Path(__file__).resolve().parent
config_file=os.environ.get('FISH_FEEDING_CONFIG','motion.json')
cfg=json.loads((W/config_file).read_text(encoding='utf-8-sig'))
def smooth(a,b,t):
 u=max(0,min(1,(t-a)/(b-a)));return u*u*(3-2*u)
def bend(t):
 for a,b in zip(cfg['bend_keys'],cfg['bend_keys'][1:]):
  if t<=b[0]:return a[1]+(b[1]-a[1])*smooth(a[0],b[0],t)
 return cfg['bend_keys'][-1][1]
def curve(t):
 v=cfg['keyframes'][-1].copy()
 for a,b in zip(cfg['keyframes'],cfg['keyframes'][1:]):
  if t<=b['t']:
   dt=b['t']-a['t'];u=max(0,min(1,(t-a['t'])/dt));f=u*u*(3-2*u)
   v={k:a[k]+(b[k]-a[k])*f for k in ['gape','protrusion','head']}
   v['travel']=(2*u**3-3*u*u+1)*a['travel']+(u**3-2*u*u+u)*dt*a['travel_speed']+(-2*u**3+3*u*u)*b['travel']+(u**3-u*u)*dt*b['travel_speed']
   break
 v['shake']=bend(t);v['body_yaw']=0
 w=cfg['blend_window'];v['body_blend']=smooth(w[0],w[1],t)*(1-smooth(w[2],w[3],t))
 absolute=[d*bend(t-delay) for d,delay in zip(cfg['body_degrees'],cfg['body_delay'])]
 v['body_angles']=[a-(absolute[i-1] if i else 0) for i,a in enumerate(absolute)]
 return v
def apply(rig,v):
 for i,angle in enumerate(v.get('body_angles',[])):
  b=rig.pose.bones[f'body_{i:02d}'];b.rotation_mode='QUATERNION'
  axis=b.bone.matrix_local.to_3x3().inverted()@Vector((0,0,1))
  b.rotation_quaternion=b.rotation_quaternion.slerp(Quaternion(axis,math.radians(angle)),v['body_blend'])
 amount=v['protrusion']*min(1,v['gape']/.25)
 upper=math.radians(cfg['upper_max_degrees'])*amount
 for n,angle in [('jaw_lower',math.radians(cfg['jaw_max_degrees'])*v['gape']-upper),('jaw_upper',upper),('feeding_head',math.radians(-cfg['head_max_degrees'])*v['head'])]:
  b=rig.pose.bones[n];b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion((0,1,0),angle)
  if n=='feeding_head':b.rotation_quaternion=Quaternion((0,0,1),math.radians(cfg['shake_degrees'])*v.get('shake',0))@b.rotation_quaternion
 for n,shift,f in [('jaw_upper',cfg['upper_translation_native'],amount),('oral_floor',cfg['floor_translation_native'],v['gape'])]:
  b=rig.pose.bones[n];b.location=b.bone.matrix_local.to_3x3().inverted()@Vector(shift)*f

