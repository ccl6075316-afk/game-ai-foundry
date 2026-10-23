shader_type spatial;
render_mode cull_disabled, diffuse_burley;
uniform sampler2D original_source:source_color,filter_nearest,repeat_disable;
uniform sampler2D original_opaque:source_color,filter_nearest,repeat_disable;
uniform sampler2D continuation:source_color,filter_nearest,repeat_disable;
uniform float edge_probe=0.;
void fragment(){
    vec4 source=texture(original_source,UV);
    vec3 known=source.a<.95?texture(original_opaque,UV).rgb:source.rgb;
    vec3 central=texture(continuation,UV2).rgb;
    ALBEDO=mix(known,edge_probe>.5?vec3(0.,0.,1.):central,COLOR.r);
    if(edge_probe>.5)EMISSION=vec3(0.,0.,1.)*COLOR.r;
    ROUGHNESS=1.;METALLIC=0.;SPECULAR=.5;
}
