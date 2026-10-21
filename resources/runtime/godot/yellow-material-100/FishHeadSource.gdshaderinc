// Source-coordinate repair: preserve the native lateral artwork and continue
// the same lip strip across the widened front. No flat palette replacement.
uniform bool head_source_repair=false;
uniform vec4 source_eye;
uniform vec2 eye_gap_native;
uniform float eye_donor_u;
uniform float eye_donor_v;
uniform bool mouth_source_projection=false;
uniform float mouth_shift_native_u=0.018;
uniform vec2 mouth_donor_window;
uniform vec3 mouth_source_edges[32];
uniform int mouth_edge_count=0;
uniform int model_path_count=0;
uniform vec2 model_path[8];
uniform float model_tangents[8];
uniform float model_aspect;
uniform float model_gap;
uniform float model_lip_roll;
uniform vec4 upper_skin_patch;
uniform vec4 lower_skin_patch;
uniform int mouth_path_count=0;
uniform vec2 mouth_path[8];
uniform float mouth_tangents[8];
uniform int source_width_count=0;
uniform vec2 source_width_path[32];
uniform int head_eye_debug=0;
uniform bool secondary_feature_enabled=false;
uniform vec4 secondary_feature;

float source_mouth_v(float u){
    if(u<=mouth_path[0].x)return mouth_path[0].y+(u-mouth_path[0].x)*mouth_tangents[0];
    for(int i=1;i<mouth_path_count;i++){
        vec2 a=mouth_path[i-1];vec2 b=mouth_path[i];
        if(u<=b.x){float w=b.x-a.x;float t=(u-a.x)/w;
            return (2.0*t*t*t-3.0*t*t+1.0)*a.y+(t*t*t-2.0*t*t+t)*w*mouth_tangents[i-1]+(-2.0*t*t*t+3.0*t*t)*b.y+(t*t*t-t*t)*w*mouth_tangents[i];}
    }
    int last=mouth_path_count-1;return mouth_path[last].y+(u-mouth_path[last].x)*mouth_tangents[last];
}
float source_halfwidth(float u){
    if(u<=source_width_path[0].x)return source_width_path[0].y;
    for(int i=1;i<source_width_count;i++)if(u<=source_width_path[i].x){
        vec2 a=source_width_path[i-1];vec2 b=source_width_path[i];return mix(a.y,b.y,(u-a.x)/(b.x-a.x));}
    return source_width_path[source_width_count-1].y;
}
float model_slit_v(float u){
    if(u<=model_path[0].x)return model_path[0].y+(u-model_path[0].x)*model_tangents[0];
    for(int i=1;i<model_path_count;i++){
        vec2 a=model_path[i-1];vec2 b=model_path[i];
        if(u<=b.x){float w=b.x-a.x;float t=(u-a.x)/w;
            return (2.0*t*t*t-3.0*t*t+1.0)*a.y+(t*t*t-2.0*t*t+t)*w*model_tangents[i-1]+(-2.0*t*t*t+3.0*t*t)*b.y+(t*t*t-t*t)*w*model_tangents[i];}
    }
    int last=model_path_count-1;return model_path[last].y+(u-model_path[last].x)*model_tangents[last];
}
float source_lip_v(float u,float upper){
    vec3 a=mouth_source_edges[0];
    if(u<=a.x)return mix(a.z,a.y,upper);
    for(int i=1;i<mouth_edge_count;i++){
        vec3 b=mouth_source_edges[i];
        if(u<=b.x)return mix(mix(a.z,a.y,upper),mix(b.z,b.y,upper),(u-a.x)/(b.x-a.x));
        a=b;
    }
    return mix(a.z,a.y,upper);
}
float head_front_weight(vec3 pos){
    float u=pos.x+0.5;
    float width=max(0.00001,source_halfwidth(u));
    float lateral=1.0-smoothstep(0.55,0.95,abs(pos.z)/width);
    return smoothstep(0.95,0.985,u)*max(lateral,smoothstep(0.985,0.994,u));
}
vec2 head_source_uv(vec2 uv,vec3 pos,float upper){
    if(!mouth_source_projection)return uv;
    float width=max(0.00001,source_halfwidth(pos.x+0.5));
    float across=clamp(abs(pos.z)/width,0.0,1.0);
    upper=step(0.5,upper);
    float mix_amount=head_front_weight(pos);
    float donor_u=mix(uv.x,mix(mouth_donor_window.x,mouth_donor_window.y,across),mix_amount);
    float fade=smoothstep(model_path[0].x,model_path[0].x+0.012,pos.x+0.5);
    float model_edge=(0.5-model_slit_v(pos.x+0.5))*model_aspect+(upper*2.0-1.0)*(model_gap*0.5+model_lip_roll*fade);
    float margin=(upper>0.5?-3.0:3.0)/source_size.y;
    float donor_v=source_lip_v(donor_u,upper)+margin-(pos.y-model_edge)/model_aspect;
    return vec2(donor_u,mix(uv.y,donor_v,mix_amount));
}
vec3 source_opaque_color(vec2 uv){
    vec4 c=texture(source_texture,uv);
    if(c.a<0.95 && mouth_source_projection && uv.x>mouth_path[0].x){
        for(int i=1;i<=64;i++){
            float u=uv.x-float(i)/source_size.x;
            vec2 donor=vec2(u,uv.y+source_mouth_v(u)-source_mouth_v(uv.x));
            vec4 sample_color=texture(source_texture,donor);
            if(sample_color.a>0.95)return sample_color.rgb;
        }
    }
    return c.a>0.95?c.rgb:texture(opaque_skin,uv).rgb;
}
float source_eye_footprint(vec2 uv){return 1.0-smoothstep(1.0,1.25,length((uv-source_eye.xy)/source_eye.zw));}
float source_eye_keep(vec3 pos){return smoothstep(eye_gap_native.x,eye_gap_native.y,abs(pos.z));}
// 090 single-species prototype: explicit spatial rim and lateral eye chart.
uniform bool rim_local_source=false;
uniform bool yellow_source_trial=false;
uniform int local_rim_count=0;
uniform vec4 local_rim_start[160];
uniform vec4 local_rim_end[160];
uniform int local_cross_count=0;
uniform vec4 local_cross[32];
uniform vec4 local_eye_chart;
uniform int local_lip_debug=0;

vec2 local_rim_distance(vec3 pos){
    float best=100.0;float upper=0.0;
    for(int i=0;i<local_rim_count;i++){
        vec3 a=local_rim_start[i].xyz;vec3 ab=local_rim_end[i].xyz-a;
        float t=clamp(dot(pos-a,ab)/max(dot(ab,ab),1e-12),0.0,1.0);
        float d=length(pos-a-t*ab);
        if(d<best){best=d;upper=mix(local_rim_start[i].w,local_rim_end[i].w,t);}
    }
    return vec2(best,step(.5,upper));
}
vec4 local_head_section(float x){
    vec4 a=local_cross[0];
    if(x<=a.x)return a;
    for(int i=1;i<local_cross_count;i++){
        vec4 b=local_cross[i];
        if(x<=b.x)return mix(a,b,(x-a.x)/max(b.x-a.x,1e-7));
        a=b;
    }
    return a;
}
vec3 local_head_color(vec2 uv,vec3 pos,vec3 base){
    vec3 c=base;
    if(local_lip_debug==1){
        vec2 rim=local_rim_distance(pos);
        return mix(vec3(.12,.18,.22),mix(vec3(.1,1.,.2),vec3(1.,.2,.1),rim.y),1.-smoothstep(.0025,.003,rim.x));
    }
    if(pos.x>.470){
        vec2 rim=local_rim_distance(pos);
        float anterior=smoothstep(.470,.487,pos.x);
        float outside_lip=smoothstep(.003,.009,rim.x);
        vec4 patch=mix(lower_skin_patch,upper_skin_patch,rim.y);
        vec2 local_grain=fract(vec2(abs(pos.z),pos.y)*source_size.x/7.0);
        vec2 donor=mix(patch.xy,patch.zw,local_grain);
        c=mix(c,source_opaque_color(donor),anterior*outside_lip);
    }
    // 091: preserve native lateral eye coordinates. Only clear the footprint
    // where a side projection would repeat it over the dorsal midline.
    vec4 section=local_head_section(pos.x);
    float across=abs(pos.z)/max(section.w,1e-6);
    float flank=smoothstep(.45,.78,across);
    // Continue the source's dorsal skin beneath its silhouette ink. A planar
    // side outline must not become a black ladder across the whole forehead.
    float dorsal=(1.-smoothstep(.35,.70,across))*smoothstep(section.y,section.y+section.z*.35,pos.y)*smoothstep(.29,.34,pos.x);
    float dorsal_v=.5-(section.y+section.z)/model_aspect;
    vec2 dorsal_uv=vec2(uv.x,max(uv.y,dorsal_v+10./source_size.y));
    c=mix(c,source_opaque_color(dorsal_uv),dorsal);
    float original_eye=1.0-smoothstep(1.08,1.25,length((uv-source_eye.xy)/source_eye.zw));
    vec2 clean=vec2(eye_donor_u+(uv.x-source_eye.x)*.15,eye_donor_v+(uv.y-source_eye.y)*.25);
    c=mix(c,source_opaque_color(clean),original_eye*(1.-flank));
    float front_upper=(.5-source_lip_v(.994,1.))*model_aspect;
    float front_lower=(.5-source_lip_v(.997,0.))*model_aspect;
    float cap_mask=smoothstep(.488,.494,pos.x)*max(smoothstep(front_upper+.0005,front_upper+.003,pos.y),1.-smoothstep(front_lower-.003,front_lower-.0005,pos.y));
    c=mix(c,source_opaque_color(vec2(.975,.5-pos.y/model_aspect)),cap_mask);
    return c;
}

// 100: full body dorsal/ventral charts. Side silhouette ink must not wrap
// around the rounded caps. Coordinates use actual model sections, not the
// head-only envelope. Native source pixel clusters remain nearest sampled.
uniform bool body_cap_chart=false;
uniform int body_cap_count=0;
uniform vec4 body_cap_sections[128];
uniform float body_cap_margin_px=65.;
uniform float body_cap_transverse_scale=.8;
uniform vec2 body_cap_blend=vec2(.55,.92);
vec4 body_cap_section(float x){
    vec4 a=body_cap_sections[0];
    for(int i=1;i<body_cap_count;i++){
        vec4 b=body_cap_sections[i];
        if(x<=b.x)return mix(a,b,clamp((x-a.x)/max(b.x-a.x,1e-7),0.,1.));
        a=b;
    }
    return a;
}
vec3 body_cap_source_color(vec2 uv){
#ifdef FOUNDRY_BODY_CHART
    return clean_skin_color(uv).rgb;
#else
    return source_opaque_color(uv);
#endif
}
vec3 yellow_head_color(vec2 uv,vec3 pos,vec3 base){
    if(!body_cap_chart)return base;
    vec4 section=body_cap_section(pos.x);
    float across=abs(pos.z)/max(section.w,1e-6);
    float cap=1.-smoothstep(body_cap_blend.x,body_cap_blend.y,across);
    float top_px=(.5-(section.y+section.z)/model_aspect)*source_size.y;
    float bottom_px=(.5-(section.y-section.z)/model_aspect)*source_size.y;
    float depth_px=max(bottom_px-top_px,1.);
    float margin=min(body_cap_margin_px,depth_px*.30);
    float transverse=pos.z*source_size.x*body_cap_transverse_scale;
    // Continuous transverse chart: no constant source row stretched over the
    // whole cap, no periodic noise and no palette/desaturation replacement.
    float dorsal_y=clamp(top_px+margin+transverse,top_px+margin*.5,top_px+depth_px*.45);
    float ventral_y=clamp(bottom_px-margin+transverse,bottom_px-depth_px*.45,bottom_px-margin*.5);
    float upper=step(section.y,pos.y);
    vec2 chart_uv=vec2(uv.x,mix(ventral_y,dorsal_y,upper)/source_size.y);
    vec3 donor=body_cap_source_color(chart_uv);
    float chart_eye=source_eye_footprint(chart_uv)*upper;
    vec2 forehead=vec2(1780.+(uv.x-source_eye.x)*source_size.x*.30,270.+pos.z*source_size.x*.70)/source_size;
    donor=mix(donor,source_opaque_color(forehead),chart_eye);
    vec3 c=mix(base,donor,cap);
    // Source gill and jaw silhouette are lateral features, not a ring below
    // the chin. Continue registered clean head skin over the unseen underside.
    float head=smoothstep(.26,.34,pos.x);
    vec2 rim=local_rim_distance(pos);
    float upper_head=pos.x>.44?rim.y:upper;
    float upper_u=mix(1940.,1960.,clamp((pos.z/section.w+1.)*.5,0.,1.));
    float lower_u=mix(1780.,1810.,clamp((pos.x-.34)/.15,0.,1.))+pos.z*source_size.x*.35;
    float upper_y=clamp(348.+pos.z*source_size.x*.5,338.,358.);
    float lower_y=clamp(462.+pos.z*source_size.x*.5,452.,472.);
    vec2 clean=vec2(mix(lower_u,upper_u,upper_head)/source_size.x,mix(lower_y,upper_y,upper_head)/source_size.y);
    float head_weight=head*cap*mix(1.,smoothstep(.43,.47,pos.x),upper_head);
    c=mix(c,source_opaque_color(clean),head_weight);
    float eye_repeat=cap*source_eye_footprint(uv);
    c=mix(c,source_opaque_color(vec2(eye_donor_u,eye_donor_v)),eye_repeat*(1.-head_weight));
    return c;
}

vec3 repaired_head_color(vec2 uv,vec3 pos,float upper,vec3 base){
    if(yellow_source_trial)return yellow_head_color(uv,pos,base);
    if(rim_local_source)return local_head_color(uv,pos,base);
    upper=step(0.5,upper);
    vec3 c=base;
    if(mouth_source_projection && pos.x+0.5>0.95){
        c=source_opaque_color(head_source_uv(uv,pos,upper));
        float width=max(0.00001,source_halfwidth(pos.x+0.5));
        float front=head_front_weight(pos);
        float fade=smoothstep(model_path[0].x,model_path[0].x+0.012,pos.x+0.5);
        float edge=(0.5-model_slit_v(pos.x+0.5))*model_aspect+(upper*2.0-1.0)*(model_gap*0.5+model_lip_roll*fade);
        float away=smoothstep(0.0015,0.006,abs(pos.y-edge));
        vec4 patch=mix(lower_skin_patch,upper_skin_patch,upper);
        vec2 grain_uv=fract(vec2(abs(pos.z),pos.y)*source_size.x/7.0);
        vec2 clean_uv=mix(patch.xy,patch.zw,grain_uv);
        c=mix(c,source_opaque_color(clean_uv),front*away);
    }
    float clean=source_eye_footprint(uv)*(1.0-source_eye_keep(pos));
    if(secondary_feature_enabled){
        float feature=1.0-smoothstep(1.0,1.25,length((uv-secondary_feature.xy)/secondary_feature.zw));
        clean=max(clean,feature*(1.0-source_eye_keep(pos)));
    }
    vec2 donor=vec2(eye_donor_u+(uv.x-source_eye.x)*0.15,eye_donor_v+(uv.y-source_eye.y)*0.25);
    return mix(c,source_opaque_color(donor),clean);
}
