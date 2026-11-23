shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

#include "res://scripts/aquarium/PlantSwayMotion.gdshaderinc"

uniform sampler2D artwork : source_color, filter_nearest, repeat_disable;
uniform float alpha_cutoff = 0.0;

void vertex() {
    sway_plant(VERTEX, NORMAL, UV2, COLOR, MODEL_MATRIX, vec4(0.0, 0.5, 0.0, 0.0), TIME);
}

void fragment() {
    vec4 texel = texture(artwork, UV);
    if (texel.a < alpha_cutoff) { discard; }
    ALBEDO = texel.rgb;
    ROUGHNESS = 1.0;
}
