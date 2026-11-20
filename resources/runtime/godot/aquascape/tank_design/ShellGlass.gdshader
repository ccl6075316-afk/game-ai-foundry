shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never;

uniform bool water = false;
varying vec3 local_position;
void vertex() {
    local_position = VERTEX;
}
void fragment() {
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
