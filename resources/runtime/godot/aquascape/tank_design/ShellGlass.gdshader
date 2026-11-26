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
    float grazing = pow(1.0 - abs(dot(normalize(NORMAL),normalize(VIEW))), 3.2);
    if (water) {
        vec2 p = local_position.xz;
        float w = 0.0;
        w += exp(sin(dot(p, vec2(0.94, 0.34)) * 2.1 + TIME * 1.10) - 1.0) * 0.42;
        w += exp(sin(dot(p, vec2(-0.28, 0.96)) * 2.9 + TIME * 1.28 + 1.7) - 1.0) * 0.28;
        w += exp(sin(dot(p, vec2(-0.88, -0.47)) * 4.1 + TIME * 1.45 + 3.4) - 1.0) * 0.18;
        w += exp(sin(dot(p, vec2(0.56, -0.83)) * 5.6 + TIME * 1.65 + 5.1) - 1.0) * 0.12;
        float crest = smoothstep(0.32, 0.85, w * 1.25);
        vec3 deep_surf = vec3(0.06, 0.22, 0.32);
        vec3 shallow_surf = vec3(0.24, 0.56, 0.68);
        vec3 highlight = vec3(0.76, 0.90, 0.92);
        ALBEDO = mix(deep_surf, shallow_surf, 0.35 + 0.55 * crest) + highlight * (crest * 0.16 + grazing * 0.22);
        ALPHA = clamp(0.24 + 0.36 * grazing + 0.10 * crest, 0.18, 0.72);
    } else {
        ALBEDO = mix(vec3(.16,.34,.42),vec3(.46,.68,.74),grazing);
        ALPHA = .028+.20*grazing;
    }
}
