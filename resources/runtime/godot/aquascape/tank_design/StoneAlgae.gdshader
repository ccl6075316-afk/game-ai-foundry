shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D stone_art : source_color, filter_nearest, repeat_disable;
uniform sampler2D algae_art : source_color, filter_nearest, repeat_enable;
uniform float tiles_per_model_unit = 1.0;

varying vec3 surface_position;
varying vec3 surface_normal;

vec4 film(vec2 coord) {
    vec3 rgb = texture(algae_art, coord).rgb;
    float brightest = max(max(rgb.r, rgb.g), rgb.b);
    return vec4(rgb, smoothstep(0.012, 0.045, brightest));
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
    ALBEDO = mix(base, algae, coverage * exposed);
    METALLIC = 0.0;
    ROUGHNESS = 1.0;
}
