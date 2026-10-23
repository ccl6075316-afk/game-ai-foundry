shader_type spatial;
render_mode cull_disabled, diffuse_burley;
uniform sampler2D lip_atlas:source_color,filter_nearest,repeat_disable;
uniform vec3 lip_ink:source_color;
uniform float edge_probe=0.;
// Vertex COLOR.r encodes distance inward from the actual outer lip edge,
// divided by four ink widths. COLOR.g tapers the stroke at the mouth corners.
// It is independent of the folded original source UVs.
void fragment(){
    vec3 pigment=texture(lip_atlas,UV).rgb;
    float stroke=(1.-smoothstep(.225,.2625,COLOR.r))*COLOR.g;
    ALBEDO=mix(pigment,edge_probe>.5?vec3(0.,0.,1.):lip_ink,stroke);
    if(edge_probe>.5)EMISSION=vec3(0.,0.,1.)*stroke;
    ROUGHNESS=1.;METALLIC=0.;SPECULAR=.5;
}
