shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_disabled;
uniform sampler2D source_texture : source_color, filter_nearest, repeat_disable;
uniform vec2 source_size;
uniform vec2 pigment_top_uv;
uniform vec2 pigment_bottom_uv;
uniform vec2 pigment_height;
uniform float rim_width_native = 0.0022;
uniform float recess_width_native = 0.007;
varying vec3 rest_position;
void vertex(){rest_position=VERTEX;}
uniform sampler2D opaque_skin : source_color, filter_nearest, repeat_disable;
#include "res://scripts/aquarium/FishHeadSource.gdshaderinc"
void fragment(){
    if(yellow_source_trial){
        vec2 rim=local_rim_distance(rest_position);
        vec3 boundary=source_opaque_color(UV);
        // Source lower-lip skin is an explicit style donor for unseen lining.
        vec3 lining=source_opaque_color(vec2(1940./2014.,446./727.));
        vec3 interior=mix(boundary,lining,smoothstep(.001,.004,rim.x));
        interior*=mix(1.0,.72,smoothstep(.004,.014,rim.x));
        ALBEDO=yellow_head_color(UV,rest_position,interior);ROUGHNESS=1.0;METALLIC=0.0;
    }else if(rim_local_source){
        vec2 rim=local_rim_distance(rest_position);
        vec3 boundary=source_opaque_color(UV);
        float native_u=.982;
        vec2 tissue_uv=vec2(native_u,source_lip_v(native_u,rim.y)+(rim.y>.5?-3.0:3.0)/source_size.y);
        vec3 tissue=source_opaque_color(tissue_uv);
        vec3 c=mix(boundary,tissue,smoothstep(.001,.0035,rim.x));
        float upper_front=(.5-source_lip_v(.994,1.))*model_aspect;
        float lower_front=(.5-source_lip_v(.997,0.))*model_aspect;
        float external_upper=smoothstep(upper_front+.0005,upper_front+.003,rest_position.y);
        float external_lower=1.-smoothstep(lower_front-.003,lower_front-.0005,rest_position.y);
        float external_cap=smoothstep(.488,.494,rest_position.x)*max(external_upper,external_lower);
        vec2 cap_uv=vec2(.975,.5-rest_position.y/model_aspect);
        vec3 shaded=c*mix(1.0,.28,smoothstep(.0025,.010,rim.x));
        ALBEDO=mix(shaded,source_opaque_color(cap_uv),external_cap);
        ROUGHNESS=1.0;METALLIC=0.0;
    }else{

    float upper=step(0.5,UV2.y);
    vec3 lip=source_opaque_color(head_source_uv(UV,rest_position,upper));
    float distance=max(0.0,UV2.x-abs(rest_position.z));
    float inner_u=mix(mouth_donor_window.x,mouth_donor_window.y,0.5);
    vec2 inner_uv=vec2(inner_u,source_lip_v(inner_u,upper)+(upper>0.5?-3.0:3.0)/source_size.y);
    lip=mix(lip,source_opaque_color(inner_uv),smoothstep(0.0003,0.002,distance));
    float recess=smoothstep(rim_width_native,recess_width_native,distance);
    ALBEDO=mix(lip,lip*0.23,recess);
    ROUGHNESS=1.0;
    METALLIC=0.0;
}
}
