from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[3];base=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ref=lambda p:{'path':str(p.relative_to(root)),'sha256':sha(p)}
profile={'species':'synthetic_controller_fixture','real_length_cm':60,'head_sign':-1,'base_clip':'Clip0','body_bones':['Joint0','Joint1','Joint2','Joint3'],'tank_size_m':[20,20,20],'path_radii_m':[.5,.3],'vertical_amplitude_m':.1,'envelope_radius_m':3,'period_seconds':4,'transition_seconds':.3,'body_delay_seconds':.2,'base_body_gain':.5,'actions':{'Swim':{'vertical_sign':1,'radius_scale':1,'bend_radians':.1,'clip_speed':1}}}
(base/'motion.json').write_text(json.dumps(profile,indent=2)+'\n')
spec={'kind':'fish_asset_finalization_spec','version':1,'species':'synthetic_controller_fixture','game':str((root/'work/fish-portable-tools/viewer-smoke/game').relative_to(root)),'model':ref(base/'unpacked.glb'),'motion':{'runtime':ref(root/'resources/runtime/godot/VolumeFishMotion.gd'),'profile':ref(base/'motion.json'),'action':'Swim'},'viewer':{'native_clip':'Clip0','captures':[{'name':'overview','time_seconds':0}]}}
(base/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
