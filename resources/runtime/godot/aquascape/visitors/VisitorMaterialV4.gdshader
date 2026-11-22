shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

uniform sampler2D visitor_atlas : source_color, filter_linear, repeat_disable;
uniform float crowd_time = 0.0;
uniform bool distance_driven = false;
uniform bool clay_preview = false;

varying flat float surface_region;
varying flat float clothing_palette;

// The mesh faces -Z. Joint height and sole contacts are in the sculpt's rest space.
const float STRIDE = 0.84;
const float STANCE = 0.56;
const float ANKLE = 0.088;
const float KNEE = 0.406;
const float ELBOW = 0.944;
const float HEEL = 0.065;
const float TOE = -0.137;

vec3 rotate_x(vec3 v, float a) {
    float c = cos(a), s = sin(a);
    return vec3(v.x, c*v.y - s*v.z, s*v.y + c*v.z);
}

vec3 rotate_y(vec3 v, float a) {
    float c = cos(a), s = sin(a);
    return vec3(c*v.x + s*v.z, v.y, -s*v.x + c*v.z);
}

vec3 rotate_z(vec3 v, float a) {
    float c = cos(a), s = sin(a);
    return vec3(c*v.x - s*v.y, s*v.x + c*v.y, v.z);
}

// Sagittal sections of the rounded outsole. When the heel lifts, the ground
// contact walks along the shoe's toe spring instead of floating above it.
float toe_clearance(float pitch) {
    vec2 floor_axis = vec2(cos(pitch), -sin(pitch));
    float lowest = min(0.0, dot(floor_axis, vec2(0.000148, -0.048742)));
    lowest = min(lowest, dot(floor_axis, vec2(0.001015, -0.085829)));
    lowest = min(lowest, dot(floor_axis, vec2(0.002648, -0.113690)));
    lowest = min(lowest, dot(floor_axis, vec2(0.004301, -0.131082)));
    lowest = min(lowest, dot(floor_axis, vec2(0.005, TOE)));
    return lowest - floor_axis.y*TOE;
}

void vertex() {
    float appearance = round(INSTANCE_CUSTOM.w);
    if (appearance > 1.5) { VERTEX += CUSTOM2.xyz; UV = CUSTOM3.xy; }
    else if (appearance > 0.5) { VERTEX += CUSTOM1.xyz; UV = UV2; }

    vec3 pivot = CUSTOM0.xyz;
    float limb = CUSTOM0.w;
    float weight = CUSTOM3.z;
    float rest_height = VERTEX.y;
    float motion = smoothstep(0.0, 1.0, INSTANCE_CUSTOM.y);
    float phase = INSTANCE_CUSTOM.x + (distance_driven ? 0.0 : crowd_time*5.65);
    float t = fract(phase/TAU + ((limb == 2.0 || limb == 4.0) ? 0.5 : 0.0));
    float sink = (0.006 + 0.022*(0.5 + 0.5*cos(2.0*phase - 1.05)))*motion;
    // Weight travels over the supporting foot, peaking in single support.
    float load = sin(phase - 0.13)*motion;
    float idle = sin(crowd_time*1.58 + INSTANCE_CUSTOM.x)*(1.0 - motion);

    if (limb == 3.0 || limb == 4.0) {
        float recovery = clamp((t - STANCE)/(1.0 - STANCE), 0.0, 1.0);
        // In support, every metre of root translation is subtracted at the sole.
        // The cubic return joins with the same slope on both contact boundaries.
        float travel = STRIDE*(t - 0.226 - smoothstep(0.0, 1.0, recovery))*motion;
        float pitch = 0.25*(1.0 - smoothstep(0.0, 0.14, t)) - 0.48*smoothstep(0.30, STANCE, t);
        if (t > STANCE) {
            pitch = -0.48 - 0.05*sin(PI*recovery) + 0.73*smoothstep(0.16, 0.89, recovery);
        }
        pitch *= motion;
        float arc = sin(PI*recovery);
        float lift = 0.077*arc*arc*motion;
        if (pitch < 0.0) { lift -= toe_clearance(pitch); }
        vec3 contact = vec3(pivot.x, 0.0, pivot.z + (pitch > 0.0 ? HEEL : TOE));
        vec3 step_offset = vec3(0.0, lift + sink, travel);
        vec3 shoe = contact + rotate_x(VERTEX - contact, pitch) + step_offset;
        vec3 ankle_rest = vec3(pivot.x, ANKLE, pivot.z);
        vec3 ankle_target = contact + rotate_x(ankle_rest - contact, pitch) + step_offset;

        // Aim the two links with the ankle already on the rotating shoe.
        // The links are equal in the authored rest pose, knee halfway to ankle.
        float down = pivot.y - ankle_target.y;
        float dz = ankle_target.z - pivot.z;
        float aim = atan(-dz, down);
        float bend = acos(clamp(length(vec2(down, dz))/(pivot.y - ANKLE), 0.0, 1.0));
        float thigh = aim + bend, shin = aim - bend;
        vec3 knee = vec3(pivot.x, KNEE, pivot.z);
        vec3 lower_leg = pivot + rotate_x(knee - pivot, thigh) + rotate_x(VERTEX - knee, shin);
        float lower = 1.0 - smoothstep(KNEE - 0.03, KNEE + 0.03, rest_height);
        vec3 leg = mix(pivot + rotate_x(VERTEX - pivot, thigh), lower_leg, lower);
        vec3 leg_normal = mix(rotate_x(NORMAL, thigh), rotate_x(NORMAL, shin), lower);
        float foot = CUSTOM3.w == 4.0 ? 1.0 : 1.0 - smoothstep(ANKLE, ANKLE + 0.04, rest_height);
        VERTEX = mix(VERTEX, mix(leg, shoe, foot), weight);
        NORMAL = normalize(mix(NORMAL, mix(leg_normal, rotate_x(NORMAL, pitch), foot), weight));
    } else if (limb == 1.0 || limb == 2.0) {
        float swing = -0.32*cos(TAU*t - 0.09)*motion;
        float elbow_flex = (0.09 + 0.14*(0.5 - 0.5*cos(TAU*t + 0.21)))*motion;
        vec3 elbow = vec3(pivot.x, ELBOW, pivot.z);
        float below = 1.0 - smoothstep(ELBOW - 0.035, ELBOW + 0.035, rest_height);
        vec3 forearm = mix(VERTEX, elbow + rotate_x(VERTEX - elbow, elbow_flex), below);
        // The forearm comes slightly inward on its forward arc.
        float across = (limb == 1.0 ? 0.046 : -0.046)*smoothstep(0.0, 0.30, swing);
        VERTEX = mix(VERTEX, pivot + rotate_z(rotate_x(forearm - pivot, swing), across), weight);
        NORMAL = normalize(mix(NORMAL, rotate_z(rotate_x(NORMAL, swing + elbow_flex*below), across), weight));
    } else if (limb == 9.0) {
        float look = 0.045*sin(crowd_time*0.73 + INSTANCE_CUSTOM.x)*(1.0 - motion)*weight;
        VERTEX = pivot + rotate_y(VERTEX - pivot, look);
        NORMAL = rotate_y(NORMAL, look);
    }

    // Leave the sole and ankle entirely outside pelvis and shoulder rotations.
    float carried = smoothstep(0.15, 0.68, rest_height);
    float upper = smoothstep(0.73, 1.16, rest_height);
    // The entire arm travels with the shoulder, including the low-hanging hand.
    if (limb == 1.0 || limb == 2.0) { carried = 1.0; upper = 1.0; }
    float twist = mix(-0.045, 0.072, upper)*cos(phase)*motion*carried;
    twist *= 1.0 - 0.60*smoothstep(1.24, 1.37, rest_height);
    float roll = -0.016*load*carried;
    float lean = -0.020*upper*motion;
    vec3 waist = vec3(0.0, 0.724, 0.0);
    VERTEX = waist + rotate_z(rotate_y(rotate_x(VERTEX - waist, lean), twist), roll);
    NORMAL = normalize(rotate_z(rotate_y(rotate_x(NORMAL, lean), twist), roll));
    VERTEX.x -= 0.022*load*carried;
    VERTEX.y += 0.002*idle*upper - sink;
    surface_region = CUSTOM3.w;
    clothing_palette = INSTANCE_CUSTOM.z;
}

void fragment() {
    vec3 paint = texture(visitor_atlas, UV).rgb;
    if (surface_region == 1.0) {
        paint *= mix(vec3(0.97, 1.01, 1.03), vec3(1.04, 0.98, 0.96), fract(clothing_palette*0.37));
    }
    if (clay_preview) { paint = vec3(0.62, 0.59, 0.53); }
    vec3 n = normalize(NORMAL);
    vec3 world_normal = normalize(mat3(INV_VIEW_MATRIX)*n);
    // Two broad sources: skylight beyond the glass and warmer reflected light
    // entering from the gallery. The face keeps a readable cheek plane as it turns.
    float hall_key = dot(world_normal, normalize(vec3(-0.50,0.76,0.43)));
    float softbox = dot(n, normalize(vec3(-0.58,0.58,0.57)));
    float key = smoothstep(-0.58, 0.82, 0.56*hall_key + 0.44*softbox);
    float skin = surface_region == 0.0 ? 1.0 : 0.0;
    float eye = surface_region == 5.0 ? 1.0 : 0.0;
    float hair = surface_region == 3.0 ? 1.0 : 0.0;
    vec3 shade = mix(vec3(0.43,0.46,0.53), vec3(0.60,0.50,0.47), skin);
    vec3 sunny = mix(vec3(1.04,0.99,0.90), vec3(1.075,0.995,0.92), skin);
    vec3 indirect = mix(shade, sunny, key);
    // A narrow aquarium-side reflection picks up the hair and jacket edges.
    float edge = pow(1.0 - clamp(dot(n, normalize(VIEW)), 0.0, 1.0), 3.0);
    float rim = edge*smoothstep(-0.22,0.72,dot(world_normal,normalize(vec3(0.74,0.64,-0.18))));
    vec3 reflected = paint*indirect + vec3(0.15,0.21,0.24)*rim*(0.40 + 0.73*hair);
    // A broad satin sheen follows the curved locks; catchlights are in the sculpt.
    float glancing = pow(max(0.0,dot(n,normalize(vec3(-0.38,0.79,0.47)))), 10.0);
    reflected += vec3(0.070,0.046,0.030)*hair*glancing;
    if (clay_preview) { reflected = paint*(0.44 + 0.53*key); }
    ALBEDO = paint;
    EMISSION = reflected * 0.88;
    ROUGHNESS = mix(mix(0.96,0.83,skin),0.67,hair) - 0.38*eye;
    SPECULAR = 0.20 + 0.14*eye;
}
