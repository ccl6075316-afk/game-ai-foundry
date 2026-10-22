shader_type spatial;
render_mode blend_mix,depth_prepass_alpha,cull_disabled;
uniform sampler2D source_texture:source_color,filter_nearest,repeat_disable;
uniform vec4 tint:source_color=vec4(1.);
uniform vec4 left_eye=vec4(.357,.778,.032,.047);
uniform vec4 right_eye=vec4(.643,.778,.032,.047);
float feature(vec2 uv,vec4 e){return 1.-smoothstep(.85,1.15,length((uv-e.xy)/e.zw));}
void fragment(){
    vec4 c=texture(source_texture,UV)*tint*COLOR;
    float duplicate=max(feature(UV,left_eye),feature(UV,right_eye));
    ALBEDO=c.rgb;ALPHA=c.a*(1.-duplicate);ROUGHNESS=1.;METALLIC=0.;SPECULAR=0.;
}
