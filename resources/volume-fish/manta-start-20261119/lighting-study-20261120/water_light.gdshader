shader_type spatial;
render_mode cull_disabled;
uniform sampler2D skin : source_color, filter_nearest_mipmap;
uniform sampler2D filtered_skin : source_color, filter_linear_mipmap_anisotropic;
uniform bool use_filtered_skin = false;
uniform float skin_sheen = 1.;
uniform sampler2D grain : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool seabed = false;
uniform float water_time = 0.0;
uniform float surface_light = 0.0;
varying vec3 ocean_position;

void vertex() {
    ocean_position = (MODEL_MATRIX * vec4(VERTEX,1.0)).xyz;
}

// Interfering waves based on the project aquarium_tank_lighting study.
// Locate their highlights in the world light path so the ray swims through them.
float light_field(vec2 p, float t) {
    vec2 q = p + vec2(0.45*sin(p.y*1.45+t*.33),0.40*sin(p.x*1.30-t*.29));
    float a = sin(q.x*3.10+q.y*1.30+t*.48)+.65*sin(q.y*4.20-q.x*.70-t*.36);
    float b = sin(q.y*2.80+q.x*1.20-t*.41)+.55*sin(q.x*3.70-q.y*.80+t*.29);
    float strands = max(exp(-a*a*17.0),exp(-b*b*24.0));
    float passing = smoothstep(-.60,.78,sin(.78*p.y-.42*p.x+.22*t)+.48*sin(.81*p.x+.61*p.y-.18*t));
    return strands*(.12+.88*passing);
}

void fragment() {
    if (seabed) {
        float sand = texture(grain, ocean_position.xz*.53).g;
        float swell = .5+.5*sin(ocean_position.x*1.7+ocean_position.z*.36+.65*sin(ocean_position.z*.82));
        ALBEDO = mix(vec3(.18,.25,.25),vec3(.43,.44,.36),sand) * (.89+.11*swell);
        ROUGHNESS = 1.;
    } else {
        vec3 pigment = use_filtered_skin ? texture(filtered_skin,UV).rgb : texture(skin,UV).rgb;
        float pale = smoothstep(.40,.88,dot(pigment,vec3(.21,.72,.07)));
        ALBEDO = pigment*(1.0-.19*pale);
        ROUGHNESS = .62;
    }
}
void light() {
    float facing = max(dot(NORMAL,LIGHT),0.);
    vec2 lookup = (ocean_position.xz + ocean_position.y*vec2(.32,-.19))*2.65;
    float ripple = surface_light*light_field(lookup,water_time);
    vec3 illumination = LIGHT_COLOR * ATTENUATION * facing / 3.141593;
    DIFFUSE_LIGHT += illumination * (1.+ripple*(seabed ? .56 : 1.10));
    if (!seabed && facing>0.) {
        float ang = max(dot(NORMAL, normalize(LIGHT+VIEW)),0.);
        float sheen = (.027*pow(ang,14.)+.045*pow(ang,70.))*(1.+ripple*.8);
        SPECULAR_LIGHT += skin_sheen*LIGHT_COLOR*ATTENUATION*(sheen + ripple*.043*facing)*vec3(.77,.92,.97);
    }
}
