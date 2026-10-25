shader_type spatial;
render_mode unshaded, fog_disabled, cull_disabled, depth_test_disabled, depth_draw_never;
uniform sampler2D scene_color : hint_screen_texture, repeat_disable, filter_nearest;
uniform sampler2D scene_depth : hint_depth_texture, repeat_disable, filter_nearest;
uniform int water_count = 0;
uniform vec4 water_x[8];
uniform vec4 water_y[8];
uniform vec4 water_z[8];
uniform vec4 water_color[8];
uniform vec4 water_optics[8];
uniform vec4 water_extra[8];
uniform float clock = 0.0;

void vertex(){POSITION=vec4(VERTEX.xy,1.0,1.0);}
vec3 unproject(vec2 uv,float depth,mat4 inverse_projection,mat4 inverse_view){
    vec3 ndc;
    #if CURRENT_RENDERER == RENDERER_COMPATIBILITY
        ndc=vec3(uv,depth)*2.0-1.0;
    #else
        ndc=vec3(uv*2.0-1.0,depth);
    #endif
    vec4 p=inverse_projection*vec4(ndc,1.0);
    return (inverse_view*vec4(p.xyz/p.w,1.0)).xyz;
}
vec3 local_point(vec3 p,int i){return vec3(dot(water_x[i],vec4(p,1.0)),dot(water_y[i],vec4(p,1.0)),dot(water_z[i],vec4(p,1.0)));}
vec3 local_direction(vec3 d,int i){return vec3(dot(water_x[i].xyz,d),dot(water_y[i].xyz,d),dot(water_z[i].xyz,d));}
bool inside_water(vec3 p){return all(greaterThanEqual(p,vec3(-3.0,0.0,-1.5)))&&all(lessThanEqual(p,vec3(3.0,2.775,1.5)));}
vec2 interval(vec3 p,vec3 d,float distance_to_hit){
    // Preserve world-metre ray parameter even when the tank is scaled/rotated.
    vec3 safe_d=mix(vec3(-0.000001),vec3(0.000001),greaterThanEqual(d,vec3(0.0)));
    safe_d=mix(d,safe_d,lessThan(abs(d),vec3(0.000001)));
    vec3 a=(vec3(-3.0,0.0,-1.5)-p)/safe_d;
    vec3 b=(vec3(3.0,2.775,1.5)-p)/safe_d;
    vec3 mn=min(a,b);vec3 mx=max(a,b);
    return vec2(max(0.0,max(mn.x,max(mn.y,mn.z))),min(distance_to_hit,min(mx.x,min(mx.y,mx.z))));
}
void fragment(){
    vec3 hit=unproject(SCREEN_UV,texture(scene_depth,SCREEN_UV).r,INV_PROJECTION_MATRIX,INV_VIEW_MATRIX);
    vec3 near_point=unproject(SCREEN_UV,1.0,INV_PROJECTION_MATRIX,INV_VIEW_MATRIX);
    vec3 far_point=unproject(SCREEN_UV,0.00001,INV_PROJECTION_MATRIX,INV_VIEW_MATRIX);
    vec3 direction=normalize(far_point-near_point);
    vec3 origin=near_point;
    float distance_to_hit=max(0.0,dot(hit-origin,direction));
    vec3 color=texture(scene_color,SCREEN_UV).rgb;
    vec3 optical_depth=vec3(0.0);vec3 fog_sum=vec3(0.0);float fog_weight=0.0;
    bool covered=false;
    for(int i=0;i<8;i++){
        if(i>=water_count){break;}
        vec3 p=local_point(origin,i);vec3 d=local_direction(direction,i);
        vec2 segment=interval(p,d,distance_to_hit);
        float length_in_water=max(0.0,segment.y-segment.x);
        if(length_in_water<0.0001){continue;}
        covered=true;
        vec4 optics=water_optics[i];vec4 tint=water_color[i];
        float amount=length_in_water*tint.a/max(optics.x,0.01);
        // RGB-selective transmission; visibility is in world metres.
        vec3 extinction=mix(vec3(1.0),vec3(2.5,1.0,0.55),clamp(tint.b-tint.r+0.5,0.0,1.0));
        optical_depth+=extinction*amount;
        fog_sum+=tint.rgb*0.48*amount;fog_weight+=amount;
        vec3 sample_local=local_point(hit,i);
        vec3 entry=p+d*segment.x;
        bool camera_inside=inside_water(p);
        bool hit_inside=inside_water(sample_local);
        float top_interface=(!camera_inside&&abs(entry.y-2.775)<0.008)?1.0:0.0;
        vec2 wave_p=entry.xz*water_extra[i].x;
        vec2 wave=vec2(sin(wave_p.x*2.4+clock*0.45+sin(wave_p.y)),cos(wave_p.y*2.8-clock*0.35));
        // Refraction is restrained and never samples a foreground frame/room pixel.
        if(hit_inside&&optics.z>0.001){
            vec2 offset=wave*optics.z*mix(0.00045,0.0025,top_interface);
            vec2 uv=clamp(SCREEN_UV+offset,vec2(0.001),vec2(0.999));
            vec3 shifted_hit=unproject(uv,texture(scene_depth,uv).r,INV_PROJECTION_MATRIX,INV_VIEW_MATRIX);
            if(inside_water(local_point(shifted_hit,i))){color=mix(color,texture(scene_color,uv).rgb,0.6);}
        }
        if(hit_inside&&optics.w>0.001){
            // A world-anchored approximation on visible opaque surfaces, including fish.
            vec2 q=floor(hit.xz/0.035)*0.035;
            float pattern=abs(sin(q.x*3.1+sin(q.y*2.2+clock*0.43))+sin(q.y*3.7-clock*0.31));
            float caustic=1.0-smoothstep(0.025,0.17,pattern);
            color+=vec3(0.12,0.18,0.17)*caustic*optics.w;
        }
        if(top_interface>0.5){
            float fresnel=pow(1.0-clamp(abs(normalize(d).y),0.0,1.0),5.0);
            float glint=pow(max(0.0,wave.x*wave.y),12.0);
            // Stylized environment reflection, not an SSR/planar scene reflection.
            color=mix(color,vec3(0.15,0.31,0.40)+glint*0.28,optics.y*(0.16+0.84*fresnel));
        }
    }
    // Preserve the original framebuffer outside water, including low-value colors.
    if(!covered){discard;}
    vec3 transmission=exp(-optical_depth);
    vec3 scatter=fog_sum/max(fog_weight,0.00001);
    ALBEDO=color*transmission+scatter*(vec3(1.0)-transmission);
    ALPHA=1.0;
}
