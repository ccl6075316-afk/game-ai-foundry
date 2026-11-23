shader_type spatial;
render_mode unshaded, cull_back;
uniform sampler2D artwork : source_color, filter_nearest, repeat_disable;
#include "res://scripts/aquarium/PlantSwayMotion.gdshaderinc"

uniform float clock = 0.0;
varying vec2 art_uv;

void vertex() {
    art_uv = UV;
    sway_plant(VERTEX, NORMAL, UV2, COLOR, MODEL_MATRIX, INSTANCE_CUSTOM, clock);
}
void fragment() {
    vec4 paint=texture(artwork,art_uv);
    if (paint.a<0.5) { discard; }
    ALBEDO=paint.rgb;
}
