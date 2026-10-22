uniform sampler2D front112_source:source_color,filter_nearest,repeat_disable;
uniform vec2 front112_source_size;
uniform vec2 front112_x;
uniform vec4 front112_upper;
uniform vec4 front112_lower;
uniform float front112_y_split;
uniform float front112_half_width;
uniform float front112_pixel_per_native;
varying vec3 front112_rest;
varying vec3 front112_normal;
vec3 front112_color(vec3 base){
    float amount=smoothstep(front112_x.x,front112_x.y,front112_rest.x)*smoothstep(.05,.75,normalize(front112_normal).x);
    amount*=1.-smoothstep(.65,1.,abs(front112_rest.z)/front112_half_width);
    vec4 r=front112_rest.y>front112_y_split?front112_upper:front112_lower;
    vec2 size=max((r.zw-r.xy)*front112_source_size,vec2(1.));
    vec2 pixel=mod(floor(vec2(front112_rest.z,front112_rest.y)*front112_pixel_per_native),size);
    vec2 uv=r.xy+(pixel+vec2(.5))/front112_source_size;
    return mix(base,texture(front112_source,uv).rgb,amount);
}
