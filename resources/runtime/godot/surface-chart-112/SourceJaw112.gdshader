shader_type spatial;
render_mode cull_disabled;
uniform sampler2D source_texture:source_color,filter_nearest,repeat_disable;
uniform vec2 source_size;
varying vec3 jaw112_rest;
void vertex(){jaw112_rest=VERTEX;}
void fragment(){
    float inset=max(0.,UV2.x-abs(jaw112_rest.z));
    float upper=step(.5,UV2.y);
    vec2 rim_uv=UV+vec2(0.,mix(3.,-3.,upper)/source_size.y);
    vec3 rim=texture(source_texture,rim_uv).rgb;
    vec3 cavity=texture(source_texture,UV).rgb;
    float depth=smoothstep(2./source_size.x,12./source_size.x,inset);
    ALBEDO=mix(rim,cavity,depth);ROUGHNESS=1.;METALLIC=0.;SPECULAR=0.;
}
