shader_type spatial;
render_mode unshaded, cull_disabled;
uniform vec4 upper_color : source_color = vec4(0.055,0.21,0.38,1.0);
uniform vec4 lower_color : source_color = vec4(0.012,0.045,0.12,1.0);
varying vec3 local_position;
void vertex(){local_position=VERTEX;}
void fragment(){
    float height=clamp(local_position.y/2.8+0.5,0.0,1.0);
    float edge=1.0-0.18*pow(clamp(abs(local_position.x)/3.0,0.0,1.0),2.0);
    ALBEDO=mix(lower_color.rgb,upper_color.rgb,smoothstep(0.0,1.0,height))*edge;
}
