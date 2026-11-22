shader_type spatial;
render_mode unshaded, shadows_disabled, depth_draw_never;

varying vec2 floor_position;
varying flat vec2 gait;

void vertex() {
    floor_position = VERTEX.xz;
    gait = INSTANCE_CUSTOM.xy;
}

// Area occlusion from the body, with a smaller contact patch under each shoe.
float shoe_shadow(float t, float side, float motion) {
    float recovery = clamp((t - 0.56)/0.44, 0.0, 1.0);
    float travel = 0.84*(t - 0.226 - smoothstep(0.0,1.0,recovery))*motion;
    float lift = sin(PI*recovery)*motion;
    vec2 at = vec2(side*0.10, travel-0.034);
    vec2 extent = vec2(0.088, 0.154)*(1.0 + 0.18*lift);
    return (1.0-smoothstep(0.18,1.0,length((floor_position-at)/extent))) * (0.42-0.26*lift);
}

void fragment() {
    float t = fract(gait.x/TAU);
    float motion = smoothstep(0.0,1.0,gait.y);
    float body = 1.0-smoothstep(0.0,1.0,length(floor_position/vec2(0.33,0.34)));
    float left = shoe_shadow(t, -1.0, motion);
    float right = shoe_shadow(fract(t+0.5), 1.0, motion);
    ALBEDO = vec3(0.012,0.017,0.025);
    ALPHA = 0.30*body+max(left,right);
}
