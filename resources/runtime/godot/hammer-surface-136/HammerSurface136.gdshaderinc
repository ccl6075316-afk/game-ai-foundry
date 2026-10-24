uniform sampler2D hammer136_top:source_color,filter_nearest,repeat_disable;
uniform sampler2D hammer136_side:source_color,filter_nearest,repeat_disable;
uniform sampler2D hammer136_opaque:source_color,filter_nearest,repeat_disable;
uniform bool hammer136_wing=false;
uniform vec4 hammer137_projection=vec4(1.2326625138,.3911223218,3.3244534464,.4985569986);
uniform float hammer137_side_aspect=2.51464968;
uniform vec4 hammer137_top_eye=vec4(.9695,.0956,.0118,.0346);
uniform bool hammer137_ventral=false;
uniform sampler2D hammer137_bottom:source_color,filter_nearest,repeat_disable;
uniform sampler2D hammer137_bottom_opaque:source_color,filter_nearest,repeat_disable;
uniform vec4 hammer137_mouth_curve[3];
varying vec3 chart112_rest_position;
varying vec3 chart112_rest_normal;
float hammer137_smooth(float t){t=clamp(t,0.,1.);return t*t*t*(10.+t*(-15.+6.*t));}
float hammer137_mouth_u(float x){
    x=clamp(x,.33,.5);
    int i=x<.375 ? 0 : (x<.425 ? 1 : 2);
    float t=x-(i==0 ? .33 : (i==1 ? .375 : .425));
    vec4 c=hammer137_mouth_curve[i];return ((c.x*t+c.y)*t+c.z)*t+c.w;
}
vec3 hammer136_color(vec3 original){
    vec3 p=chart112_rest_position;
    vec3 n=normalize(chart112_rest_normal);
    if(hammer137_ventral){
        vec2 mouth_uv=vec2(hammer137_mouth_u(p.x),.5-p.z*3.);
        vec4 mouth=texture(hammer137_bottom,mouth_uv);
        if(mouth.a<.95)mouth=texture(hammer137_bottom_opaque,mouth_uv);
        float amount=hammer137_smooth((p.x-.33)/.045)*(1.-hammer137_smooth((abs(p.z)-.045)/.035));
        return mix(original,mouth.rgb,amount);
    }
    float head_weight=smoothstep(.28,.38,p.x);
    // 137: same isotropic source/head transform as the corrected cephalofoil.
    float cross_scale=mix(1.6,hammer137_projection.z,head_weight);
    float u=mix(p.x+.5,hammer137_projection.x*p.x+hammer137_projection.y,head_weight);
    vec2 uv=vec2(u,hammer137_projection.w-p.z*cross_scale);
    if(hammer136_wing){
        uv.x-=.006*n.x*smoothstep(.2,.8,abs(n.x));
    }
    vec4 dorsal=texture(hammer136_top,uv);
    // The original top image also paints the lateral eyes. Keep the separate
    // closed 3D eyes; redirect only their painted footprint to adjacent skin.
    float eye_v=uv.y<hammer137_projection.w ? hammer137_top_eye.y : 2.*hammer137_projection.w-hammer137_top_eye.y;
    vec2 eye_delta=(uv-vec2(hammer137_top_eye.x,eye_v))/hammer137_top_eye.zw;
    float eye_weight=1.-smoothstep(.75,1.25,length(eye_delta));
    vec2 eye_donor=uv+vec2(-.035,uv.y<hammer137_projection.w ? .060 : -.060);
    vec4 skin=texture(hammer136_top,eye_donor);
    if(skin.a>.95)dorsal=mix(dorsal,skin,eye_weight);
    // The wing's vertical rim is hidden in the top artwork. Infer it from the
    // reviewed lateral head skin, excluding side-view eyes and gill ink.
    // Use a two-dimensional lateral skin block, never repeat one source column.
    float rim_u=.865+.025*clamp(abs(p.z)/.139,0.,1.)+.010*clamp((p.x-.35)/.15,0.,1.);
    vec2 suv=vec2(hammer136_wing ? rim_u : p.x+.5,.5-p.y*hammer137_side_aspect);
    vec4 lateral=texture(hammer136_side,suv);
    if(lateral.a<.95)lateral=texture(hammer136_opaque,suv);
    float dorsal_weight=smoothstep(.15,.70,n.y);
    if(dorsal.a<.95)dorsal_weight=0.;
    if(hammer136_wing)return mix(lateral.rgb,dorsal.rgb,dorsal_weight);
    // Ventral primitives, fin roots and all fins keep their existing material.
    return mix(lateral.rgb,dorsal.rgb,dorsal_weight);
}
