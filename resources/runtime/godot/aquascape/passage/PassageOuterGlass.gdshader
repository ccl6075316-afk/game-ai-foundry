shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never;
#include "res://scripts/aquarium/passage/PassageDryVolume.gdshaderinc"
varying vec3 world_position;
void vertex(){world_position=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;}
void fragment(){
    if(passage_contains(world_position)){discard;}
    ALBEDO=vec3(0.19,0.43,0.57);ALPHA=0.065;
}
