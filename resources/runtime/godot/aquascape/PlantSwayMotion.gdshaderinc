uniform vec3 anchor_min;
uniform vec3 anchor_size;
uniform float amplitude = 0.085;
uniform float enabled = 1.0;

vec3 rotate_axis(vec3 p, vec3 axis, float angle) {
    return p*cos(angle)+cross(axis,p)*sin(angle)+axis*dot(axis,p)*(1.0-cos(angle));
}
void sway_plant(inout vec3 vertex, inout vec3 normal, vec2 phase_uv, vec4 color, mat4 model, vec4 instance_data, float seconds) {
    vec3 anchor=anchor_min+color.rgb*anchor_size;
    float weight=smoothstep(0.08,1.0,phase_uv.x)*color.a;
    float phase=phase_uv.y*6.2831853+instance_data.x*6.2831853;
    float wave=0.78*sin(seconds*0.62831853+phase-phase_uv.x*0.6)+0.22*sin(seconds*1.25663706+phase*1.7-phase_uv.x);
    float strength=mix(0.85,1.15,instance_data.y);
    vec3 current=normalize(inverse(mat3(model))*vec3(1.0,0.0,0.35));
    vec3 axis=normalize(cross(vec3(0.0,1.0,0.0),current));
    float angle=wave*amplitude*weight*strength*enabled;
    vertex=anchor+rotate_axis(vertex-anchor,axis,angle);
    normal=rotate_axis(normal,axis,angle);
}
