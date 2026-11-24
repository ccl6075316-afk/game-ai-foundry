shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D stone_art : source_color, filter_nearest, repeat_disable;
uniform sampler2D algae_art : source_color, filter_nearest, repeat_enable;
uniform float tiles_per_model_unit = 1.0;
uniform float coverage_area : hint_range(0.0, 1.0) = 0.5;
uniform float color_strength : hint_range(0.0, 1.0) = 0.72;

varying vec3 surface_position;
varying vec3 surface_normal;

vec4 film(vec2 coord) {
    vec4 texel = texture(algae_art, coord);
    float threshold = 1.0 - coverage_area;
    float mask = smoothstep(threshold - .018, threshold + .018, texel.a);
    if (coverage_area <= 0.001) { mask = 0.0; }
    if (coverage_area >= 0.999) { mask = 1.0; }
    return vec4(texel.rgb, mask);
}

void vertex() {
    surface_position = VERTEX;
    surface_normal = NORMAL;
}

void fragment() {
    vec3 base = texture(stone_art, UV).rgb;
    vec3 direction = normalize(surface_normal);
    vec3 weight = pow(abs(direction), vec3(5.0));
    weight /= weight.x + weight.y + weight.z;
    vec3 position = surface_position * tiles_per_model_unit;
    vec4 side = film(position.zy + vec2(0.11, 0.29));
    vec4 top = film(position.xz + vec2(0.43, 0.09));
    vec4 front = film(position.xy + vec2(0.18, 0.65));
    vec3 film_weights = vec3(side.a, top.a, front.a) * weight;
    float coverage = film_weights.x + film_weights.y + film_weights.z;
    vec3 algae = (side.rgb * film_weights.x + top.rgb * film_weights.y +
            front.rgb * film_weights.z) / max(coverage, 0.0001);
    float exposed = mix(0.28, 0.78, smoothstep(-0.65, 0.8, direction.y));
    ALBEDO = mix(base, algae, coverage * exposed * color_strength);
    METALLIC = 0.0;
    ROUGHNESS = 1.0;
}
