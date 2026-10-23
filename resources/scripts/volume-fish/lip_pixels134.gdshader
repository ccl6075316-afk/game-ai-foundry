shader_type spatial;
render_mode cull_disabled, diffuse_burley;
uniform sampler2D lip_atlas:source_color,filter_nearest,repeat_disable;
uniform sampler2D pigment_dabs:source_color,filter_nearest,repeat_disable;
uniform float edge_probe=0.;
void fragment(){
    vec3 base=texture(lip_atlas,UV).rgb;
    vec4 dab=texture(pigment_dabs,UV2);
    ALBEDO=mix(base,edge_probe>.5?vec3(0.,0.,1.):dab.rgb,dab.a);
    if(edge_probe>.5)EMISSION=vec3(0.,0.,1.)*dab.a;
    ROUGHNESS=1.;METALLIC=0.;SPECULAR=.5;
}
