extends RefCounted
## Art-directed, finite behavior study. Offsets are in fish lengths, not biology measurements.
static func state(seconds:float, config:Dictionary, length_m:float)->Dictionary:
    var ends:Array=config.phase_ends
    var t:float=clampf(seconds,0.0,float(ends[-1]))
    var stage:=0
    while stage<5 and t>=float(ends[stage]):stage+=1
    var start:float=0.0 if stage==0 else float(ends[stage-1])
    var u:float=clampf((t-start)/(float(ends[stage])-start),0.0,1.0)
    var eased:float=smoothstep(0.0,1.0,u)
    var x:float;var z:=0.0;var yaw:=0.0;var amplitude:float;var frequency:float
    var burst:float=config.burst_amplitude;var glide:float=config.glide_amplitude
    var fast:float=config.burst_frequency;var slow:float=config.glide_frequency
    match stage:
        0:
            x=lerpf(-.20,-.0667,eased);amplitude=lerpf(.45*burst,burst,eased);frequency=fast
        1:
            x=lerpf(-.0667,.0833,1.0-pow(1.0-u,1.5));amplitude=lerpf(burst,glide,eased);frequency=lerpf(fast,slow,eased)
        2:
            x=lerpf(.0833,.1167,eased);z=lerpf(0.,.12,eased);yaw=lerpf(0.,float(config.observe_yaw),eased);amplitude=glide;frequency=slow
        3:
            x=.1167;z=.12;yaw=lerpf(float(config.observe_yaw),float(config.observe_yaw)*.4,eased);amplitude=glide;frequency=slow
        4:
            x=.1167;z=.12;yaw=lerpf(float(config.observe_yaw)*.4,.35,eased);amplitude=lerpf(glide,.9*burst,eased);frequency=lerpf(slow,fast*.9,eased)
        _:
            x=lerpf(.1167,.4,eased);z=lerpf(.12,-.15,eased);yaw=.35;amplitude=burst;frequency=fast*.9
    return {"offset":Vector3(x,float(config.height_tl),z)*length_m,"yaw":yaw,"stage":stage,
        "label":["摆尾启动","滑行","侧身靠近","短暂观察","侧转离开","游开"][stage],
        "controls":{"body_amplitude":amplitude,"body_frequency":frequency,"fin_amplitude":float(config.fin_amplitude)*(.9 if stage>0 and stage<5 else 1.),"fin_frequency":float(config.fin_frequency)}}

static func validate(config:Dictionary)->bool:
    if config.phase_ends.size()!=6 or config.shape_scale.size()!=3:return false
    var previous:=0.0
    for value in config.phase_ends:
        if not is_finite(float(value)) or float(value)<=previous:return false
        previous=float(value)
    if not is_equal_approx(float(config.shape_scale[0]),1.0):return false
    for value in config.shape_scale:
        if not is_finite(float(value)) or float(value)<.8 or float(value)>1.2:return false
    for key in ["burst_amplitude","burst_frequency","glide_amplitude","glide_frequency","fin_amplitude","fin_frequency"]:
        if not is_finite(float(config[key])) or float(config[key])<=0.0 or float(config[key])>2.5:return false
    return config.eye_scale>=.5 and config.eye_scale<=1.0 and config.eye_radius[0]>0.0 and config.eye_radius[1]>0.0
