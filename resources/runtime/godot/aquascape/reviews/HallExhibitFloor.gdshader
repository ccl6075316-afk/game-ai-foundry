shader_type spatial;
render_mode diffuse_burley, specular_disabled;

uniform vec3 slate : source_color = vec3(0.33, 0.36, 0.38);
uniform vec3 grout : source_color = vec3(0.26, 0.28, 0.28);
varying vec2 ground;

float random_cell(vec2 cell) {
    vec3 p = fract(cell.xyx * 0.1031);
    p += dot(p, p.yzx + 33.33);
    return fract((p.x + p.y) * p.z);
}

float soft_noise(vec2 point) {
    vec2 cell = floor(point);
    vec2 weight = smoothstep(vec2(0.0), vec2(1.0), fract(point));
    float lower = mix(random_cell(cell), random_cell(cell + vec2(1, 0)), weight.x);
    float upper = mix(random_cell(cell + vec2(0, 1)), random_cell(cell + vec2(1, 1)), weight.x);
    return mix(lower, upper, weight.y);
}

void vertex() {
    ground = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

void fragment() {
    vec2 footprint = fwidth(ground);
    float row = floor(ground.y / 0.75);
    vec2 staggered = vec2(ground.x + mod(row, 2.0) * 0.75, ground.y);
    vec2 size = vec2(1.5, 0.75);
    vec2 cell = floor(staggered / size);
    vec2 edges = (0.5 - abs(fract(staggered / size) - 0.5)) * size;
    vec2 seam = 1.0 - smoothstep(vec2(0.003), vec2(0.007) + footprint * 0.6, edges);
    float joint = max(seam.x, seam.y) * (1.0 - smoothstep(0.01, 0.06, max(footprint.x, footprint.y)));
    float layers = soft_noise(ground * vec2(3.0, 10.0));
    vec3 slab = slate * (0.76 + 0.28 * random_cell(cell) + 0.22 * layers);
    ALBEDO = mix(slab, grout, joint * 0.72);
    ROUGHNESS = 1.0;
}
