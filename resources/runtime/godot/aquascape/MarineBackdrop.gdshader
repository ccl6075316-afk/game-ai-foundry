shader_type spatial;
render_mode unshaded, cull_disabled;
void fragment() {
    float depth = clamp(1.0-UV.y,0.0,1.0);
    ALBEDO=mix(vec3(0.025,0.13,0.18),vec3(0.10,0.32,0.37),depth);
}
