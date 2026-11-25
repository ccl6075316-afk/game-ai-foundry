shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never;

uniform bool water = false;
uniform int passage_count=0;
uniform vec4 passage_points[12];
varying vec3 local_position;
void vertex() {
    local_position = VERTEX;
}
void fragment() {
    if (!water && passage_count>1) {
        for(int i=0;i<11;i++){
            if(i>=passage_count-1)break;
            vec2 a=passage_points[i].xy;
            vec2 b=passage_points[i+1].xy;
            vec2 delta=b-a;
            float t=clamp(dot(local_position.xz-a,delta)/max(dot(delta,delta),.00001),0.0,1.0);
            float start_radius=passage_points[i].z;
            float end_radius=passage_points[i].w;
            float transition=min(length(delta),max(1.2,abs(end_radius-start_radius)*3.0));
            float blend=smoothstep(0.0,max(transition,.00001),t*length(delta));
            float radius=mix(start_radius,end_radius,blend);
            float distance_to_route=length(local_position.xz-(a+t*delta));
            float top=1.4+sqrt(max(0.0,radius*radius-distance_to_route*distance_to_route));
            if(distance_to_route<radius && local_position.y<top)discard;
        }
    }
    float grazing = pow(1.0 - abs(dot(normalize(NORMAL),normalize(VIEW))), 2.5);
    if (water) {
        vec2 p = local_position.xz;
        float waves = sin(p.x*4.7+p.y*2.2+TIME*.72) + sin(p.y*7.6-p.x*1.8-TIME*.53);
        float glint = smoothstep(1.55,2.0,waves);
        ALBEDO = mix(vec3(.045,.19,.24),vec3(.42,.66,.68),grazing+.14*glint);
        ALPHA = .23+.30*grazing+.07*glint;
    } else {
        ALBEDO = mix(vec3(.16,.30,.34),vec3(.53,.72,.73),grazing);
        ALPHA = .065+.27*grazing;
    }
}
