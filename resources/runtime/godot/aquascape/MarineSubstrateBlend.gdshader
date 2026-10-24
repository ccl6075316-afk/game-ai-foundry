shader_type spatial;
render_mode diffuse_burley, specular_disabled;
uniform sampler2D substrate_0 : source_color, filter_nearest, repeat_enable;
uniform sampler2D substrate_1 : source_color, filter_nearest, repeat_enable;
uniform sampler2D substrate_2 : source_color, filter_nearest, repeat_enable;
uniform sampler2D substrate_3 : source_color, filter_nearest, repeat_enable;
uniform sampler2D substrate_4 : source_color, filter_nearest, repeat_enable;
varying vec4 coverage;
void vertex(){coverage=COLOR;}
void fragment(){
    vec4 w=clamp(coverage,vec4(0.0),vec4(1.0));
    float fifth=max(0.0,1.0-dot(w,vec4(1.0)));
    float total=max(.00001,dot(w,vec4(1.0))+fifth);
    ALBEDO=(texture(substrate_0,UV*5.0).rgb*w.r+texture(substrate_1,UV*5.0).rgb*w.g+texture(substrate_2,UV*5.0).rgb*w.b+texture(substrate_3,UV*5.0).rgb*w.a+texture(substrate_4,UV*5.0).rgb*fifth)/total;
    ROUGHNESS=1.0;
    SPECULAR=0.0;
}
