shader_type spatial;
render_mode diffuse_burley, specular_disabled;
uniform vec4 tile_color : source_color = vec4(0.48,0.57,0.56,1.0);
uniform vec4 seam_color : source_color = vec4(0.21,0.31,0.33,1.0);
uniform sampler2D floor_art : source_color, filter_nearest_mipmap, repeat_enable;
uniform bool use_artwork = true;
varying vec3 location;
void vertex(){location=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;}
void fragment(){
    vec2 q=abs(fract(location.xz)-0.5);
    float seam=smoothstep(0.485,0.495,max(q.x,q.y));
    ALBEDO=mix(tile_color.rgb,seam_color.rgb,seam);
    // One native generated two-tile repeat per 2 metres, across parcel seams.
    if (use_artwork) ALBEDO=texture(floor_art,location.xz*0.5).rgb*tile_color.rgb/vec3(0.4667,0.5529,0.5451);
    ROUGHNESS=1.0;
}
