shader_type spatial;
render_mode unshaded, cull_back;
uniform sampler2D artwork : source_color, filter_nearest, repeat_disable;
uniform vec3 anchor_min;
uniform vec3 anchor_size;
uniform float clock = 0.0;
uniform float amplitude = 0.085;
uniform float enabled = 1.0;
varying vec2 art_uv;

vec3 rotate_axis(vec3 p, vec3 axis, float angle) {
    return p*cos(angle)+cross(axis,p)*sin(angle)+axis*dot(axis,p)*(1.0-cos(angle));
}
void vertex() {
    art_uv=UV;
    vec3 anchor=anchor_min+COLOR.rgb*anchor_size;
    float weight=smoothstep(0.08,1.0,UV2.x)*COLOR.a;
    float phase=UV2.y*6.2831853+INSTANCE_CUSTOM.x*6.2831853;
    float wave=0.78*sin(clock*0.62831853+phase-UV2.x*0.6)+0.22*sin(clock*1.25663706+phase*1.7-UV2.x);
    float strength=mix(0.85,1.15,INSTANCE_CUSTOM.y);
    vec3 current=normalize(inverse(mat3(MODEL_MATRIX))*vec3(1.0,0.0,0.35));
    vec3 axis=normalize(cross(vec3(0.0,1.0,0.0),current));
    float angle=wave*amplitude*weight*strength*enabled;
    VERTEX=anchor+rotate_axis(VERTEX-anchor,axis,angle);
    NORMAL=rotate_axis(NORMAL,axis,angle);
}
void fragment() {
    vec4 paint=texture(artwork,art_uv);
    if (paint.a<0.5) { discard; }
    ALBEDO=paint.rgb;
}
