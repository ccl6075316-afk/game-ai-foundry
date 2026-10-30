"""Read-only Blender rig and animation snapshot for the authoring invariant."""
def rig_action_snapshot():
    import bpy
    def matrix(m): return [list(row) for row in m]
    def curve(f):
        return {'path':f.data_path,'index':f.array_index,'extrapolation':f.extrapolation,
                'keys':[(list(k.co),list(k.handle_left),list(k.handle_right),k.handle_left_type,k.handle_right_type,k.interpolation,k.easing,k.amplitude,k.back,k.period) for k in f.keyframe_points],
                'samples':[list(k.co) for k in f.sampled_points],
                'modifiers':[(m.type,repr(m.bl_rna.identifier)) for m in f.modifiers]}
    actions=[]
    for a in bpy.data.actions:
        channels=[]
        if hasattr(a,'fcurves'):
            channels.extend(curve(f) for f in a.fcurves)
        layers=[]
        for layer in getattr(a,'layers',[]):
            strips=[]
            for strip in layer.strips:
                bags=[]
                for bag in getattr(strip,'channelbags',[]):
                    bags.append({'slot_handle':bag.slot_handle,'curves':[curve(f) for f in bag.fcurves]})
                strips.append({'type':strip.type,'channelbags':bags})
            layers.append({'name':layer.name,'strips':strips})
        actions.append({'name':a.name,'frame_range':list(a.frame_range),'legacy_curves':channels,'layers':layers,'slots':[(s.identifier,s.target_id_type) for s in getattr(a,'slots',[])]})
    rigs=[]
    for rig in bpy.data.objects:
        if rig.type!='ARMATURE':continue
        ad=rig.animation_data
        rigs.append({'name':rig.name,'matrix_world':matrix(rig.matrix_world),'bones':[(b.name,b.parent.name if b.parent else None,matrix(b.matrix_local),b.use_deform)for b in rig.data.bones],
                     'pose':[(b.name,list(b.location),list(b.rotation_quaternion),list(b.rotation_euler),list(b.scale),b.rotation_mode)for b in rig.pose.bones],
                     'active_action':ad.action.name if ad and ad.action else None,
                     'tracks':[(t.name,t.mute,t.is_solo,[(s.name,s.action.name if s.action else None,s.frame_start,s.frame_end,s.action_frame_start,s.action_frame_end,s.scale,s.repeat,s.blend_type,s.extrapolation,s.influence)for s in t.strips])for t in ad.nla_tracks]if ad else []})
    return {'rigs':rigs,'actions':actions}
