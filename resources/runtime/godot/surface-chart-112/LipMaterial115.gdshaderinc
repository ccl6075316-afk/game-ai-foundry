uniform vec3 lip115_curve[32];
uniform int lip115_count;
uniform float lip115_pixel;
uniform vec2 lip115_margin_pixels;
uniform vec2 lip115_lower_margin_pixels;
vec3 lip115_color(vec3 base,vec3 chart){
    vec3 p=rest114_position;
    float upper=lip115_curve[lip115_count-1].y;
    float lower=lip115_curve[lip115_count-1].z;
    for(int i=1;i<lip115_count;i++){
        vec3 a=lip115_curve[i-1];vec3 b=lip115_curve[i];
        if(p.x<=b.x){vec2 yy=mix(a.yz,b.yz,clamp((p.x-a.x)/max(b.x-a.x,1e-8),0.,1.));upper=yy.x;lower=yy.y;break;}
    }
    float longitudinal=smoothstep(lip115_curve[0].x,lip115_curve[0].x+2.*lip115_pixel,p.x);
    float mouth=1.-smoothstep(upper+lip115_margin_pixels.x*lip115_pixel,upper+lip115_margin_pixels.y*lip115_pixel,p.y);
    mouth*=smoothstep(lower-lip115_lower_margin_pixels.y*lip115_pixel,lower-lip115_lower_margin_pixels.x*lip115_pixel,p.y);
    return mix(chart,base,longitudinal*mouth);
}
