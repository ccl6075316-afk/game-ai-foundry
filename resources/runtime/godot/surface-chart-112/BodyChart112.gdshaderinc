uniform sampler2D chart112_dorsal : source_color,filter_nearest,repeat_disable;
uniform sampler2D chart112_ventral : source_color,filter_nearest,repeat_disable;
uniform vec4 chart112_sections[128];
uniform int chart112_section_count=0;
uniform vec2 chart112_u_affine;
uniform vec2 chart112_normal_blend;
uniform vec4 chart112_longitudinal;
uniform float chart112_pixel_per_native;
uniform float chart112_height;
uniform vec4 chart112_eye_rect_native;
varying vec3 chart112_rest_position;
varying vec3 chart112_rest_normal;
vec4 chart112_section(float x){
    vec4 a=chart112_sections[0];
    for(int i=1;i<chart112_section_count;i++){
        vec4 b=chart112_sections[i];
        if(x<=b.x)return mix(a,b,clamp((x-a.x)/max(b.x-a.x,1e-8),0.,1.));
        a=b;
    }
    return a;
}
vec3 chart112_color(vec3 base){
    vec3 p=chart112_rest_position;
    vec4 section=chart112_section(p.x);
    float u=p.x*chart112_u_affine.x+chart112_u_affine.y;
    float y=(p.y-section.y)/max(section.z,1e-7);
    float z=p.z/max(section.w,1e-7);
    float angle=atan(abs(z),abs(y));
    float arc=angle*section.w;
    float posterior=1.-smoothstep(chart112_sections[0].x+.008,chart112_sections[0].x+.04,p.x);
    vec2 uv=vec2(u+posterior*.025,clamp(arc*chart112_pixel_per_native/chart112_height,0.,.999));
    vec3 grain=y>0.?texture(chart112_dorsal,uv).rgb:texture(chart112_ventral,uv).rgb;
    float amount=smoothstep(chart112_normal_blend.x,chart112_normal_blend.y,abs(normalize(chart112_rest_normal).y));
    amount=max(amount,posterior*smoothstep(.4,.8,-normalize(chart112_rest_normal).x));
    amount*=1.-smoothstep(chart112_longitudinal.z,chart112_longitudinal.w,u);
    if(chart112_eye_rect_native.z>0.)amount*=smoothstep(1.,1.35,length((p.xy-chart112_eye_rect_native.xy)/chart112_eye_rect_native.zw));
    return mix(base,grain,amount);
}
