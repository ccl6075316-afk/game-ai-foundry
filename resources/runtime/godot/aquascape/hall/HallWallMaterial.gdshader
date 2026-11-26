shader_type spatial;
render_mode diffuse_burley, specular_disabled;
uniform sampler2D artwork : source_color, filter_nearest_mipmap, repeat_enable;
uniform vec2 repeat_metres = vec2(2.0);
uniform vec4 artwork_tint : source_color = vec4(1.0);
uniform bool blend_axes = false;
uniform float cut_height = 1000000.0;
varying vec3 world_position;
varying vec3 world_normal;
void vertex() {
    world_position=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
    world_normal=normalize(MODEL_NORMAL_MATRIX*NORMAL);
}
void fragment() {
    if(world_position.y>cut_height) discard;
    vec3 n=abs(world_normal);
    vec2 uv=vec2(world_position.x,-world_position.y);
    if(n.x>n.z && n.x>n.y) uv=vec2(world_position.z,-world_position.y);
    if(n.y>n.x && n.y>n.z) uv=world_position.xz;
    ALBEDO=texture(artwork,uv/repeat_metres).rgb;
    if(blend_axes) {
        vec3 weights=pow(n,vec3(6.0));weights/=max(dot(weights,vec3(1.0)),.0001);
        ALBEDO=texture(artwork,vec2(world_position.z,-world_position.y)/repeat_metres).rgb*weights.x
            +texture(artwork,world_position.xz/repeat_metres).rgb*weights.y
            +texture(artwork,vec2(world_position.x,-world_position.y)/repeat_metres).rgb*weights.z;
    }
    ALBEDO*=artwork_tint.rgb;
    ROUGHNESS=1.0;
}
