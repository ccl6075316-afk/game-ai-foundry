uniform sampler2D mouth126_source : source_color,filter_nearest,repeat_disable;
uniform sampler2D mouth126_side_skin : source_color,filter_nearest,repeat_disable;
uniform vec2 mouth126_size;
uniform vec4 mouth126_head_rect;
uniform vec4 mouth126_upper_rect;
uniform vec4 mouth126_lower_rect;
uniform vec4 mouth126_region;
uniform vec2 mouth126_front_lips;
vec3 mouth126_patch(vec4 rect,vec2 t){
    vec2 px=mix(rect.xy+vec2(.5),rect.zw-vec2(.5),clamp(t,vec2(0.),vec2(1.)));
    return texture(mouth126_source,px/mouth126_size).rgb;
}
vec3 mouth126_color(vec3 base){
    vec3 p=rest114_position;
    vec3 n=normalize(rest114_normal);
    // Restore the visible source-plane pigment rather than preserving the old
    // stretched lower-jaw UV/paint. Supplemental cap pigment is separate below.
    vec2 side_uv=vec2(p.x+.5,.5-p.y*mouth126_size.x/mouth126_size.y);
    float side_amount=smoothstep(.419,.427,p.x)*(1.-smoothstep(-.012,-.006,p.y));
    side_amount*=smoothstep(-.122,-.112,p.y)*(1.-smoothstep(.65,.95,n.x));
    base=mix(base,texture(mouth126_side_skin,side_uv).rgb,side_amount);
    float amount=smoothstep(mouth126_region.x,mouth126_region.y,p.x)*smoothstep(.05,.55,n.x);
    float across=p.z/(2.*mouth126_region.z)+.5;
    float mid=(mouth126_front_lips.x+mouth126_front_lips.y)*.5;
    bool upper=p.y>=mid;
    float distance=upper?p.y-mouth126_front_lips.x:mouth126_front_lips.y-p.y;
    float lip=1.-smoothstep(2./mouth126_size.x,6./mouth126_size.x,max(0.,distance));
    vec3 head=mouth126_patch(mouth126_head_rect,vec2(across,1.-distance/mouth126_region.w));
    vec3 rim=mouth126_patch(upper?mouth126_upper_rect:mouth126_lower_rect,vec2(across,clamp(distance*mouth126_size.x/4.,0.,1.)));
    vec3 pigment=upper?mix(head,rim,lip):rim;
    return mix(base,pigment,amount);
}
